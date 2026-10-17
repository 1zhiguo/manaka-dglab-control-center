"""Development-only Fish Audio batch generation helpers.

This module is used by the control center's Voice Studio and the developer CLI.
It is deliberately separate from the BepInEx runtime plugin: the shipped game
plugin only reads local WAV and TXT files and never imports this module.
"""

from __future__ import annotations

import json
import os
import struct
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


API_ROOT = "https://api.fish.audio"
DEFAULT_MODEL = "s2.1-pro-free"
ProgressCallback = Callable[[dict], None]


class FishVoiceError(RuntimeError):
    """A safe, user-facing Fish Audio generation error."""


def normalize_wav_container(data: bytes) -> bytes:
    """Finalize streaming RIFF/data sizes returned as 0xffffffff by some TTS responses."""
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise FishVoiceError("Fish Audio 返回的内容不是有效 WAV")
    output = bytearray(data)
    riff_size = struct.unpack_from("<I", output, 4)[0]
    if riff_size == 0xFFFFFFFF or riff_size > len(output) - 8:
        struct.pack_into("<I", output, 4, len(output) - 8)

    position = 12
    found_data = False
    while position + 8 <= len(output):
        chunk = bytes(output[position : position + 4])
        length = struct.unpack_from("<I", output, position + 4)[0]
        start = position + 8
        remaining = len(output) - start
        if chunk == b"data":
            found_data = True
            if length == 0xFFFFFFFF or length > remaining:
                struct.pack_into("<I", output, position + 4, remaining)
            break
        if length == 0xFFFFFFFF or length > remaining:
            break
        position = start + length + (length & 1)
    if not found_data:
        raise FishVoiceError("Fish Audio WAV 缺少 data 区块")
    return bytes(output)


@dataclass(frozen=True)
class VoiceEntry:
    language: str
    state: str
    voice_key: str
    voice_title: str
    output_profile: str
    file_prefix: str
    index: int
    text: str
    prompt: str

    @property
    def base_name(self) -> str:
        return f"{self.file_prefix}_{self.index:02d}"

    @property
    def relative_base(self) -> Path:
        base = Path(self.language) / self.state
        if self.output_profile:
            base /= self.output_profile
        return base / self.base_name


def load_manifest(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    languages = data.get("languages")
    if not isinstance(languages, dict) or not languages:
        raise FishVoiceError("语音清单缺少 languages")
    for language, language_data in languages.items():
        voices = language_data.get("fish_voices")
        states = language_data.get("states")
        delivery = language_data.get("delivery")
        if not isinstance(voices, dict) or not voices:
            raise FishVoiceError(f"{language} 缺少 fish_voices")
        if not isinstance(states, dict) or not isinstance(delivery, dict):
            raise FishVoiceError(f"{language} 缺少 states 或 delivery")
        for state, lines in states.items():
            prompts = delivery.get(state)
            if not isinstance(lines, list) or not isinstance(prompts, list) or len(lines) != len(prompts):
                raise FishVoiceError(f"{language}/{state} 的字幕与情绪提示数量不一致")
        for voice_key, voice_spec in voices.items():
            voice_states = voice_spec.get("states")
            voice_delivery = voice_spec.get("delivery")
            if voice_states is None and voice_delivery is None:
                continue
            if not isinstance(voice_states, dict) or not isinstance(voice_delivery, dict):
                raise FishVoiceError(f"{language}/{voice_key} 的专属台词或情绪提示无效")
            for state, lines in voice_states.items():
                prompts = voice_delivery.get(state)
                if not isinstance(lines, list) or not isinstance(prompts, list) or len(lines) != len(prompts):
                    raise FishVoiceError(f"{language}/{voice_key}/{state} 的台词与情绪提示数量不一致")
    return data


def iter_entries(
    manifest: dict,
    *,
    language_filter: str = "",
    state_filter: str = "",
) -> Iterable[VoiceEntry]:
    for language, language_data in manifest["languages"].items():
        if language_filter and language != language_filter:
            continue
        voices = language_data["fish_voices"]
        for voice_key, voice_spec in voices.items():
            title = str(voice_spec["title"])
            output_profile = str(voice_spec.get("output_profile", "")).strip()
            file_prefix = str(voice_spec.get("file_prefix", voice_key)).strip() or voice_key
            states = voice_spec.get("states", language_data["states"])
            delivery = voice_spec.get("delivery", language_data["delivery"])
            for state, lines in states.items():
                if state_filter and state != state_filter:
                    continue
                prompts = delivery[state]
                for index, (text, prompt) in enumerate(zip(lines, prompts), start=1):
                    yield VoiceEntry(
                        language,
                        state,
                        voice_key,
                        title,
                        output_profile,
                        file_prefix,
                        index,
                        str(text),
                        str(prompt),
                    )


def preview_rows(manifest: dict) -> list[dict]:
    """Return one row per spoken line (not duplicated for the two voices)."""
    rows: list[dict] = []
    for language, language_data in manifest["languages"].items():
        voices = ", ".join(str(item["title"]) for item in language_data["fish_voices"].values())
        for state, lines in language_data["states"].items():
            prompts = language_data["delivery"][state]
            for index, (text, prompt) in enumerate(zip(lines, prompts), start=1):
                rows.append(
                    {
                        "language": language,
                        "state": state,
                        "index": index,
                        "text": str(text),
                        "prompt": str(prompt),
                        "voices": voices,
                    }
                )
    return rows


def _normalized_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value))
    return " ".join(normalized.casefold().split())


class FishAudioClient:
    def __init__(self, api_key: str, *, model: str = DEFAULT_MODEL, timeout: int = 120) -> None:
        self.api_key = str(api_key).strip()
        if not self.api_key:
            raise FishVoiceError("尚未配置 Fish Audio API Key")
        self.model = str(model).strip() or DEFAULT_MODEL
        self.timeout = max(15, int(timeout))

    def _request(self, request: urllib.request.Request) -> bytes:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                detail = ""
            suffix = f"：{detail}" if detail else ""
            raise FishVoiceError(f"Fish Audio 请求失败（HTTP {exc.code}）{suffix}") from None
        except urllib.error.URLError as exc:
            raise FishVoiceError(f"无法连接 Fish Audio：{exc.reason}") from None

    def list_models(self, *, title: str, language: str, licensed: bool = True) -> list[dict]:
        query = urllib.parse.urlencode(
            {
                "title": title,
                "language": language,
                "page_size": 100,
                "licensed": "true" if licensed else "false",
            }
        )
        request = urllib.request.Request(
            f"{API_ROOT}/model?{query}",
            headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
        )
        payload = json.loads(self._request(request).decode("utf-8"))
        items = payload.get("items", payload if isinstance(payload, list) else [])
        return items if isinstance(items, list) else []

    def resolve_voice(self, spec: dict) -> str:
        explicit = str(spec.get("reference_id", "")).strip()
        if explicit:
            return explicit
        title = str(spec.get("title", "")).strip()
        language = str(spec.get("language", "")).strip()
        wanted = _normalized_title(title)
        matches: list[dict] = []
        for item in self.list_models(title=title, language=language, licensed=True):
            author = item.get("author") if isinstance(item.get("author"), dict) else {}
            if _normalized_title(item.get("title", "")) != wanted:
                continue
            if str(author.get("nickname", "")).strip() != "Fish Official":
                continue
            if item.get("licensed") is False:
                continue
            matches.append(item)
        if len(matches) != 1:
            raise FishVoiceError(f"无法唯一找到 Fish Official 声线：{title}")
        reference_id = str(matches[0].get("_id", matches[0].get("id", ""))).strip()
        if not reference_id:
            raise FishVoiceError(f"Fish 声线缺少 ID：{title}")
        return reference_id

    def synthesize_wav(self, *, prompt: str, reference_id: str, output_path: Path) -> None:
        body = json.dumps(
            {
                "text": prompt,
                "reference_id": reference_id,
                "format": "wav",
                "normalize": True,
                "latency": "normal",
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{API_ROOT}/v1/tts",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "audio/wav",
                "model": self.model,
            },
        )
        last_error: FishVoiceError | None = None
        for attempt in range(4):
            try:
                audio = normalize_wav_container(self._request(request))
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = output_path.with_suffix(output_path.suffix + ".part")
                temporary.write_bytes(audio)
                os.replace(temporary, output_path)
                return
            except FishVoiceError as exc:
                last_error = exc
                if attempt == 3 or "HTTP 4" in str(exc) and "HTTP 429" not in str(exc):
                    break
                time.sleep(2**attempt)
        raise last_error or FishVoiceError("Fish Audio 生成失败")


def generate_batch(
    *,
    manifest_path: Path,
    output_root: Path,
    api_key: str,
    language_filter: str = "",
    state_filter: str = "",
    force: bool = False,
    model: str = DEFAULT_MODEL,
    cache_path: Path | None = None,
    progress: ProgressCallback | None = None,
    cancel_event=None,
    client: FishAudioClient | None = None,
) -> dict:
    manifest = load_manifest(manifest_path)
    entries = list(
        iter_entries(manifest, language_filter=language_filter, state_filter=state_filter)
    )
    if not entries:
        raise FishVoiceError("当前筛选条件下没有台词")
    client = client or FishAudioClient(api_key, model=model)
    output_root = Path(output_root)
    cache_path = Path(cache_path) if cache_path else output_root / ".fish_voice_ids.local.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cache = {}

    voice_ids: dict[tuple[str, str], str] = {}
    for language, language_data in manifest["languages"].items():
        if language_filter and language != language_filter:
            continue
        for voice_key, spec in language_data["fish_voices"].items():
            cache_key = f"{language}:{voice_key}:{spec['title']}"
            reference_id = str(cache.get(cache_key, "")).strip()
            if not reference_id:
                reference_id = client.resolve_voice(spec)
                cache[cache_key] = reference_id
            voice_ids[(language, voice_key)] = reference_id
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    generated = 0
    skipped = 0
    total = len(entries)
    for position, entry in enumerate(entries, start=1):
        if cancel_event is not None and cancel_event.is_set():
            return {"generated": generated, "skipped": skipped, "total": total, "cancelled": True}
        relative_base = entry.relative_base
        wav_path = output_root / relative_base.with_suffix(".wav")
        if wav_path.exists() and not force:
            skipped += 1
        else:
            client.synthesize_wav(
                prompt=entry.prompt,
                reference_id=voice_ids[(entry.language, entry.voice_key)],
                output_path=wav_path,
            )
            generated += 1
        if progress:
            progress(
                {
                    "done": position,
                    "total": total,
                    "generated": generated,
                    "skipped": skipped,
                    "language": entry.language,
                    "state": entry.state,
                    "voice_key": entry.voice_key,
                    "output_profile": entry.output_profile,
                    "text": entry.text,
                }
            )
    return {"generated": generated, "skipped": skipped, "total": total, "cancelled": False}

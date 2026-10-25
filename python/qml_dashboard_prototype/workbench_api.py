"""Workbench operations; the QObject facade in backend exposes these to QML."""
import hashlib
import json
from pathlib import Path
import uuid

from PySide6.QtCore import QUrl
from manaka_channel_engine import Binding
from manaka_wave_rules import WavePolicy
from manaka_wave_library import MAX_BYTES, parse_import, parse_text, preview_samples
from manaka_waveforms import PRESETS


def revision(owner):
    data = dict(mapping=owner.channelSettings, policy=owner.wave_policy.to_dict(), legacy_wave=owner.legacyWaveSettings)
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def local_path(value):
    url = QUrl(value)
    if url.isLocalFile():
        return Path(url.toLocalFile())
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("请选择本地文件 / Select a local file")
    return path


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def merge_intensity(owner, raw):
    current = owner.channelSettings
    current["intensity_sync"] = raw["intensity_sync"]
    for field in ("min_strength", "output_max"):
        current["legacy"][field] = raw["legacy"][field]
    for key in "AB":
        for field in ("minimum", "maximum", "hard_cap", "attack", "release", "combine"):
            current[key][field] = raw[key][field]
        for index, binding in enumerate(current[key]["bindings"]):
            for field in ("weight", "weak", "medium", "strong"):
                binding[field] = raw[key]["bindings"][index][field]
        for event in ("climax", "failure"):
            current[key][event]["percent"] = raw[key][event]["percent"]
    return current


def merge_workbench(owner, raw):
    current = owner.channelSettings
    current["mode"] = raw["mode"]
    for field in ("trigger_bpm", "full_bpm"):
        current["legacy"][field] = raw["legacy"][field]
    for key in "AB":
        current[key]["enabled"] = raw[key]["enabled"]
        current[key]["device"] = raw[key]["device"]
        # Each draft row carries its original index. Reordering/deleting rows
        # retains their strength calibration; a new row uses explicit defaults.
        bindings = []
        used = set()
        for row in raw[key]["bindings"]:
            origin = row.get("origin", -1)
            if type(origin) is not int or origin < -1 or origin >= len(current[key]["bindings"]) or origin in used:
                raise ValueError("Invalid source row identity")
            if origin >= 0:
                used.add(origin)
            value = dict(current[key]["bindings"][origin]) if origin >= 0 else dict(Binding().__dict__)
            for field in ("source", "low", "high", "input_start", "input_full", "curve"):
                value[field] = row[field]
            value.update(wave="auto", phase_ms=0)
            bindings.append(value)
        current[key]["bindings"] = bindings
        for event in ("climax", "failure"):
            for field in ("enabled", "duration_ms", "cooldown_ms"):
                current[key][event][field] = raw[key][event][field]
    return current


def draft(owner):
    mapping = owner.channelSettings
    for key in "AB":
        for index, row in enumerate(mapping[key]["bindings"]):
            row["origin"] = index
    return dict(mapping=mapping, policy=owner.wave_policy.to_dict(), legacy_wave=owner.legacyWaveSettings, base_revision=revision(owner))


def save_workbench(owner, encoded):
    raw = json.loads(encoded)
    if raw["base_revision"] != revision(owner):
        raise ValueError("设置已更新，请先重新载入 / Settings changed; reload the draft")
    policy = WavePolicy.parse(raw["policy"])
    for key in "AB":
        channel = getattr(policy, key)
        if any(not owner._is_assignable_wave_key(wave) for wave in [channel.default_wave]+[x.wave for x in channel.rules]):
            raise ValueError(key+": 波形已失效，请重新选择 / Waveform unavailable")
        # One event timer per channel/source. Rules and intensity must use the
        # same duration/cooldown, avoiding two conflicting event lifetimes.
        for source in ("climax", "failure"):
            events = [x for x in channel.rules if x.source == source and x.enabled]
            if len(events) > 1:
                raise ValueError(key+": 同类事件最多启用一条规则 / One enabled rule per event")
            event = raw["mapping"][key][source]
            event["enabled"] = bool(events)
            if events:
                event.update(duration_ms=events[0].duration_ms, cooldown_ms=events[0].cooldown_ms)
    mapping = merge_workbench(owner, raw["mapping"])
    owner._parse_channel_settings(json.dumps(mapping))
    previous = owner.wave_policy
    old_legacy = owner.legacyWaveSettings
    legacy = raw["legacy_wave"]
    if legacy["mode"] not in {"smart","fixed"} or set(legacy["zones"]) != set(old_legacy["zones"]):
        raise ValueError("原版波形策略无效 / Invalid original waveform settings")
    if any(key == "off" or not owner._is_assignable_wave_key(key) for key in [legacy["fixed"]]+list(legacy["zones"].values())):
        raise ValueError("请选择可用的原版波形 / Select an available original waveform")
    if any(not owner._is_assignable_wave_key(key) for key in legacy["actions"].values()):
        raise ValueError("原版动作映射包含失效波形 / Missing original action waveform")
    def apply_legacy(value):
        owner.wave_mode_value,owner.fixed_wave_value = value["mode"],value["fixed"]
        owner.wave_map_value,owner.action_wave_map_value = dict(value["zones"]),dict(value["actions"])
    owner.wave_policy = policy
    apply_legacy(legacy)
    try:
        if not owner.saveChannelSettings(json.dumps(mapping), False):
            owner.wave_policy = previous
            apply_legacy(old_legacy)
            return dict(ok=False, error="保存失败 / Save failed")
    except Exception:
        owner.wave_policy = previous
        apply_legacy(old_legacy)
        raise
    return dict(ok=True, error="")


def assets(owner):
    result = []
    preferences = owner.saved.get("wave_favorites", {})
    for key in list(PRESETS)+["custom"]+[x["key"] for x in owner.custom_wave_library_value]:
        wave = owner._waveform_from_key(key)
        entry = owner._library_entry_by_key(key) or {}
        result.append(dict(key=key, name="Climax" if key == "climax" else wave.name, category=entry.get("category", "内置 / Built-in"),
            source=entry.get("source", wave.source), favorite=bool(preferences.get(key, entry.get("favorite", False))),
            readOnly=key in PRESETS or key == "custom", frames=len(wave.v3_frames()), durationMs=len(wave.v3_frames())*100))
    return result


def asset(owner, key):
    wave = owner._waveform_from_key(key)
    if wave is None:
        raise ValueError("波形不存在 / Waveform not found")
    value = next(x for x in assets(owner) if x["key"] == key)
    frames = wave.v3_frames()
    # UI aliases must not rename serialized waveform metadata on export.
    return dict(value, storedName=wave.name, framesText="\n".join(frames), **preview_samples(frames))


def refresh(owner):
    owner.custom_wave_library_value = owner._read_custom_wave_library()
    owner.configChanged.emit()


def import_file(owner, value, directory):
    path = local_path(value)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("文件超过 2 MiB / File exceeds 2 MiB")
    records = parse_import(path.read_text(encoding="utf-8-sig"), path.stem)
    created = []
    try:
        for record in records:
            target = directory/(uuid.uuid4().hex+".json")
            atomic_json(target, dict(record, schema=1, frame_ms=100))
            created.append(target)
    except Exception:
        for target in created:
            target.unlink(missing_ok=True)
        raise
    refresh(owner)
    return dict(ok=True, error="", count=len(created), key="library:"+created[0].stem)


def save_asset(owner, key, name, category, text, directory):
    frames = parse_text(text)
    if not name.strip() or len(name) > 120 or len(category) > 60:
        raise ValueError("名称须为 1–120 字，分类最多 60 字 / Invalid name or category")
    existing = owner._library_entry_by_key(key) if key else None
    if key and existing is None:
        raise ValueError("内置波形请先复制 / Duplicate built-in waveforms before editing")
    stem = Path(existing["id"]).stem if existing else uuid.uuid4().hex
    target = directory/(stem+".json")
    if target.resolve().parent != directory.resolve():
        raise ValueError("Invalid library path")
    atomic_json(target, dict(schema=1, frame_ms=100, name=name.strip(), category=category.strip(),
        frames=frames, source=(existing or {}).get("source", "User")))
    refresh(owner)
    return dict(ok=True, error="", key="library:"+stem)


def delete_asset(owner, key, directory):
    refs = []
    for channel in "AB":
        policy = getattr(owner.wave_policy, channel)
        if policy.default_wave == key:
            refs.append(channel+": default")
        refs.extend(channel+": "+rule.id for rule in policy.rules if rule.wave == key)
    refs.extend("原版动作 / Original: "+action for action,wave in owner.action_wave_map_value.items() if wave == key)
    if owner.fixed_wave_value == key or key in owner.wave_map_value.values():
        refs.append("原版固定或阶段波形 / Original fixed or stage waveform")
    if refs:
        raise ValueError("波形仍被规则引用，请先替换并保存 / Still referenced: "+", ".join(refs))
    entry = owner._library_entry_by_key(key)
    if entry is None:
        raise ValueError("内置波形不能删除 / Built-in waveform is read-only")
    target = directory/entry["id"]
    if target.resolve().parent != directory.resolve():
        raise ValueError("Invalid library path")
    target.unlink()
    refresh(owner)
    return dict(ok=True, error="")

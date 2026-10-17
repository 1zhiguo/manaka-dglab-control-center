import json
import tempfile
import unittest
from pathlib import Path

from fish_voice_batch import (
    FishAudioClient,
    FishVoiceError,
    generate_batch,
    iter_entries,
    load_manifest,
    normalize_wav_container,
    preview_rows,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manaka_npc_voices" / "devtools" / "interjection_lines.json"
PROFILE_MANIFEST = ROOT / "manaka_npc_voices" / "devtools" / "profile_interjection_lines.json"


class FakeClient:
    def __init__(self) -> None:
        self.prompts = []

    def resolve_voice(self, spec: dict) -> str:
        return "official-" + spec["role"]

    def synthesize_wav(self, *, prompt: str, reference_id: str, output_path: Path) -> None:
        self.prompts.append((prompt, reference_id))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 36)


class VoiceManifestTests(unittest.TestCase):
    def test_streaming_wav_sizes_are_finalized_for_the_game_loader(self) -> None:
        payload = (
            b"RIFF" + b"\xff\xff\xff\xff" + b"WAVE"
            + b"fmt " + (16).to_bytes(4, "little")
            + b"\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00"
            + b"data" + b"\xff\xff\xff\xff" + b"\x00\x00\x01\x00"
        )

        normalized = normalize_wav_container(payload)

        self.assertEqual(int.from_bytes(normalized[4:8], "little"), len(normalized) - 8)
        self.assertEqual(int.from_bytes(normalized[40:44], "little"), 4)

    def test_manifest_has_all_languages_lines_and_two_voices(self) -> None:
        manifest = load_manifest(MANIFEST)
        rows = preview_rows(manifest)
        clips = list(iter_entries(manifest))

        self.assertEqual({row["language"] for row in rows}, {"zh", "ja", "en"})
        self.assertEqual(len(rows), 45)
        self.assertEqual(len(clips), 90)

    def test_each_line_has_delivery_cues_and_whispering_is_common(self) -> None:
        manifest = load_manifest(MANIFEST)
        prompts = [row["prompt"] for row in preview_rows(manifest)]

        self.assertTrue(all(prompt.startswith("[") for prompt in prompts))
        self.assertGreaterEqual(sum("[whispering]" in prompt for prompt in prompts), len(prompts) // 3)
        self.assertTrue(all("[whispering]" in prompt for prompt in prompts if "[tired]" in prompt))
        self.assertTrue(any("[muttering]" in prompt for prompt in prompts))

    def test_official_voice_resolution_rejects_community_clone(self) -> None:
        client = FishAudioClient("not-a-real-key")
        client.list_models = lambda **_kwargs: [
            {"_id": "community", "title": "Sarah", "licensed": True, "author": {"nickname": "Someone"}},
            {"_id": "official", "title": "Sarah", "licensed": True, "author": {"nickname": "Fish Official"}},
        ]

        self.assertEqual(client.resolve_voice({"title": "Sarah", "language": "en"}), "official")

    def test_manifest_pins_unique_official_reference_ids(self) -> None:
        manifest = load_manifest(MANIFEST)
        reference_ids = [
            voice["reference_id"]
            for language in manifest["languages"].values()
            for voice in language["fish_voices"].values()
        ]

        self.assertEqual(len(reference_ids), 6)
        self.assertEqual(len(set(reference_ids)), 6)
        self.assertTrue(all(len(reference_id) == 32 for reference_id in reference_ids))
        self.assertTrue(all(all(char in "0123456789abcdef" for char in reference_id) for reference_id in reference_ids))

    def test_explicit_reference_id_skips_model_search(self) -> None:
        client = FishAudioClient("not-a-real-key")

        def unexpected_lookup(**_kwargs):
            self.fail("Pinned voice IDs must not invoke the model search endpoint")

        client.list_models = unexpected_lookup
        self.assertEqual(
            client.resolve_voice(
                {
                    "title": "语彤 Yutong",
                    "language": "zh",
                    "reference_id": "74c6aba5cbf94a15bbdc547ffce5cb38",
                }
            ),
            "74c6aba5cbf94a15bbdc547ffce5cb38",
        )

    def test_generation_writes_runtime_wav_without_duplicate_text_sidecar(self) -> None:
        fake = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = generate_batch(
                manifest_path=MANIFEST,
                output_root=root / "VoicePacks",
                api_key="session-only",
                language_filter="zh",
                state_filter="watching",
                cache_path=root / "ids.local.json",
                client=fake,
            )
            wav = root / "VoicePacks" / "zh" / "watching" / "voice_a_01.wav"
            sidecar = root / "VoicePacks" / "zh" / "watching" / "voice_a_01.txt"

            self.assertEqual(result["generated"], 6)
            self.assertTrue(wav.is_file())
            self.assertFalse(sidecar.exists())
            self.assertTrue(all("[" in prompt for prompt, _reference in fake.prompts))

    def test_profiled_japanese_generation_uses_runtime_profile_directories(self) -> None:
        fake = FakeClient()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = generate_batch(
                manifest_path=PROFILE_MANIFEST,
                output_root=root / "VoicePacks",
                api_key="session-only",
                language_filter="ja",
                state_filter="alert",
                cache_path=root / "ids.local.json",
                client=fake,
            )

            self.assertEqual(result["generated"], 12)
            self.assertTrue(
                (root / "VoicePacks" / "ja" / "alert" / "young_female" / "voice_a_01.wav").is_file()
            )
            self.assertTrue(
                (root / "VoicePacks" / "ja" / "alert" / "older_male" / "voice_b_01.wav").is_file()
            )

    def test_profile_manifest_pins_the_four_selected_models(self) -> None:
        manifest = load_manifest(PROFILE_MANIFEST)
        voices = manifest["languages"]["ja"]["fish_voices"]

        self.assertEqual(
            {voice["output_profile"] for voice in voices.values()},
            {"young_female", "young_male", "older_female", "older_male"},
        )
        self.assertEqual(
            {voice["reference_id"] for voice in voices.values()},
            {
                "0089dce5fefb4c6ba9b9f2f0debe1ddc",
                "8f99ad75c8184f1db0c21d3a906445a4",
                "0429f2b252464b88b2ab2128f084290c",
                "a365c3050dd04026a81291145e017d6f",
            },
        )


if __name__ == "__main__":
    unittest.main()

"""Generate the offline NPC voice pack with Fish Audio's development API."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from fish_voice_batch import DEFAULT_MODEL, FishVoiceError, generate_batch, iter_entries, load_manifest


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Development-only Fish Audio generator; the game plugin remains offline.",
    )
    parser.add_argument("--manifest", type=Path, default=script_dir / "profile_interjection_lines.json")
    parser.add_argument("--output", type=Path, default=script_dir.parent / "VoicePacks")
    parser.add_argument("--language", choices=("zh", "ja", "en"), default="")
    parser.add_argument("--state", choices=("phone", "watching", "alert", "found", "failure"), default="")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--force", action="store_true", help="Regenerate files that already exist")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without calling Fish Audio")
    parser.add_argument("--list", action="store_true", help="List the line manifest and exit")
    parser.add_argument(
        "--api-key-env",
        default="FISH_API_KEY",
        help="Environment variable containing the key (literal command-line keys are intentionally unsupported)",
    )
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    entries = [
        entry for entry in iter_entries(manifest)
        if (not args.language or entry.language == args.language)
        and (not args.state or entry.state == args.state)
    ]
    if args.list or args.dry_run:
        for entry in entries:
            print(
                f"[{entry.language}/{entry.state}/{entry.voice_key}/{entry.index:02d}] "
                f"{entry.prompt}"
            )
        print(f"{len(entries)} generated clips.")
        return 0

    api_key = os.getenv(args.api_key_env, "").strip()
    if not api_key:
        raise FishVoiceError(f"请先在环境变量 {args.api_key_env} 中设置 Fish Audio API Key")

    def show_progress(item: dict) -> None:
        print(
            f"[{item['done']:03d}/{item['total']:03d}] "
            f"{item['language']}/{item['state']}/{item['voice_key']}: {item['text']}"
        )

    result = generate_batch(
        manifest_path=manifest_path,
        output_root=args.output.resolve(),
        api_key=api_key,
        language_filter=args.language,
        state_filter=args.state,
        force=args.force,
        model=args.model,
        progress=show_progress,
    )
    print(f"Generated {result['generated']} clips; skipped {result['skipped']} existing clips.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FishVoiceError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None

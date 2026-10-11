"""Generate the website's release manifest with strict input validation."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse


VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")


def validate_https_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"Expected an HTTPS URL, got: {value!r}")
    return value


def render_config(*, version: str, file_name: str, sha256: str, cos_url: str, github_url: str) -> str:
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"Invalid release version: {version!r}")
    if Path(file_name).name != file_name or not file_name.endswith(".zip"):
        raise ValueError(f"Invalid release file name: {file_name!r}")
    if not SHA256_RE.fullmatch(sha256):
        raise ValueError("SHA-256 must contain exactly 64 hexadecimal characters.")
    validate_https_url(cos_url)
    validate_https_url(github_url)
    return (
        "window.MANAKA_DOWNLOADS = Object.freeze({\n"
        f'  version: "{version}",\n'
        f'  fileName: "{file_name}",\n'
        f'  sha256: "{sha256.upper()}",\n'
        f'  cosUrl: "{cos_url}",\n'
        f'  githubUrl: "{github_url}"\n'
        "});\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--file-name", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--cos-url", required=True)
    parser.add_argument("--github-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    content = render_config(
        version=args.version,
        file_name=args.file_name,
        sha256=args.sha256,
        cos_url=args.cos_url,
        github_url=args.github_url,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

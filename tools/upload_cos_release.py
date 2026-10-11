"""Upload one release archive to Tencent COS and verify the result."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
from pathlib import Path
from urllib.parse import quote

from qcloud_cos import CosConfig, CosS3Client


VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", required=True)
    args = parser.parse_args()

    if not args.file.is_file() or args.file.suffix.lower() != ".zip":
        raise SystemExit(f"Release archive not found or not a ZIP: {args.file}")
    if not VERSION_RE.fullmatch(args.version):
        raise SystemExit(f"Invalid release version: {args.version!r}")

    secret_id = os.environ.get("TENCENT_COS_SECRET_ID", "")
    secret_key = os.environ.get("TENCENT_COS_SECRET_KEY", "")
    if not secret_id or not secret_key:
        raise SystemExit("Tencent COS credentials are missing.")

    object_key = f"releases/{args.version}/{args.file.name}"
    config = CosConfig(Region=args.region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(config)
    client.upload_file(
        Bucket=args.bucket,
        LocalFilePath=str(args.file),
        Key=object_key,
        PartSize=10,
        MAXThread=5,
        EnableMD5=True,
    )
    # The bucket stays private. Only this published archive is anonymously readable.
    client.put_object_acl(Bucket=args.bucket, Key=object_key, ACL="public-read")
    metadata = client.head_object(Bucket=args.bucket, Key=object_key)
    remote_size = int(metadata.get("Content-Length", -1))
    local_size = args.file.stat().st_size
    if remote_size != local_size:
        raise SystemExit(f"COS verification failed: local={local_size}, remote={remote_size}")

    sha256 = file_sha256(args.file)
    url = f"https://{args.bucket}.cos.{args.region}.myqcloud.com/{quote(object_key, safe='/')}"
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(f"cos_url={url}\n")
            stream.write(f"sha256={sha256}\n")
            stream.write(f"object_key={object_key}\n")
    print(f"Uploaded and verified {object_key} ({local_size} bytes, SHA-256 {sha256})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

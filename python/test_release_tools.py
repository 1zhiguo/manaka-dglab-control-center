from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.write_download_config import render_config


class DownloadConfigTests(unittest.TestCase):
    def test_renders_normalized_manifest(self):
        content = render_config(
            version="v1.2.3",
            file_name="ManakaQmlControlCenter-v1.2.3-win64-with-mods.zip",
            sha256="ab" * 32,
            cos_url="https://example.cos.ap-shanghai.myqcloud.com/releases/v1.2.3/app.zip",
            github_url="https://github.com/example/project/releases/download/v1.2.3/app.zip",
        )
        self.assertIn('version: "v1.2.3"', content)
        self.assertIn(("AB" * 32), content)
        self.assertTrue(content.endswith("\n"))

    def test_rejects_unsafe_or_malformed_values(self):
        common = dict(
            version="v1.2.3",
            file_name="app.zip",
            sha256="00" * 32,
            cos_url="https://cos.example/app.zip",
            github_url="https://github.example/app.zip",
        )
        for key, value in (
            ("version", "latest"),
            ("file_name", "../app.zip"),
            ("sha256", "nope"),
            ("cos_url", "http://cos.example/app.zip"),
        ):
            invalid = dict(common)
            invalid[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                render_config(**invalid)


if __name__ == "__main__":
    unittest.main()

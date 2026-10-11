"""Normalize user-provided Manaka mods into a safe local overlay repository."""

from __future__ import annotations

import shutil
import stat
import tempfile
import zipfile
from pathlib import Path


class DropInImportError(RuntimeError):
    pass


class DropInModImporter:
    MAX_FILES = 5000
    MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024

    def __init__(self, dropin_root: Path) -> None:
        self.root = dropin_root
        self.incoming = dropin_root / "incoming"
        self.repository = dropin_root / "repository"
        self.plugins = self.repository / "BepInEx" / "plugins"
        self.v1 = self.repository / "CustomMissions1"
        self.v2 = self.repository / "CustomMissions2"
        self.staging = dropin_root / ".staging"
        self.archive = dropin_root / "archive"

    def ensure_layout(self) -> None:
        for directory in (self.incoming, self.plugins, self.v1, self.v2, self.staging, self.archive):
            directory.mkdir(parents=True, exist_ok=True)

    def import_all(self) -> dict:
        self.ensure_layout()
        totals = {"sources": 0, "plugins": 0, "v1": 0, "v2": 0, "errors": []}
        for source in sorted(self.incoming.iterdir(), key=lambda path: path.name.casefold()):
            if source.name.startswith(".") or source.is_symlink():
                continue
            try:
                counts = self._import_source(source)
                totals["sources"] += 1
                for key in ("plugins", "v1", "v2"):
                    totals[key] += counts[key]
                self._archive_source(source)
            except (DropInImportError, OSError, zipfile.BadZipFile) as error:
                totals["errors"].append(f"{source.name}：{error}")
        return totals

    def _archive_source(self, source: Path) -> None:
        """Empty the inbox after success while retaining a recoverable original."""
        target = self.archive / source.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(source), str(target))

    def _import_source(self, source: Path) -> dict:
        if source.is_file() and source.suffix.casefold() == ".zip":
            with tempfile.TemporaryDirectory(dir=self.staging) as temporary:
                extracted = Path(temporary)
                self._safe_extract(source, extracted)
                return self._import_tree(extracted, suggested_name=source.stem)
        if source.is_file() and source.suffix.casefold() in {".dll", ".disabled"}:
            name = source.name.removesuffix(".disabled")
            if not name.casefold().endswith(".dll"):
                raise DropInImportError("只接受 DLL、JSON、ZIP 或 Mod 文件夹")
            shutil.copy2(source, self.plugins / name)
            return {"plugins": 1, "v1": 0, "v2": 0}
        if source.is_file() and source.suffix.casefold() == ".json":
            shutil.copy2(source, self.v1 / source.name)
            return {"plugins": 0, "v1": 1, "v2": 0}
        if source.is_dir():
            return self._import_tree(source, suggested_name=source.name)
        raise DropInImportError("无法识别的文件类型")

    def _safe_extract(self, archive: Path, destination: Path) -> None:
        with zipfile.ZipFile(archive) as bundle:
            infos = bundle.infolist()
            if len(infos) > self.MAX_FILES:
                raise DropInImportError(f"ZIP 文件过多（上限 {self.MAX_FILES}）")
            total = sum(info.file_size for info in infos)
            if total > self.MAX_UNCOMPRESSED_BYTES:
                raise DropInImportError("ZIP 解压后超过 512 MiB 安全上限")
            root = destination.resolve()
            for info in infos:
                relative = Path(info.filename.replace("\\", "/"))
                if relative.is_absolute() or ".." in relative.parts:
                    raise DropInImportError("ZIP 包含越界路径")
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise DropInImportError("ZIP 包含符号链接")
                target = (destination / relative).resolve(strict=False)
                if target != root and root not in target.parents:
                    raise DropInImportError("ZIP 包含越界路径")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info) as reader, target.open("wb") as writer:
                    shutil.copyfileobj(reader, writer)

    def _import_tree(self, root: Path, *, suggested_name: str | None = None) -> dict:
        counts = {"plugins": 0, "v1": 0, "v2": 0}
        visible = [path for path in root.iterdir() if not path.name.startswith(".")]
        if len(visible) == 1 and visible[0].is_dir() and not visible[0].is_symlink():
            return self._import_tree(visible[0], suggested_name=visible[0].name)
        structure_roots = [root]
        structure_roots.extend(path for path in root.iterdir() if path.is_dir() and not path.is_symlink())
        found_structure = False
        for candidate in structure_roots:
            plugin_dir = candidate / "BepInEx" / "plugins"
            if plugin_dir.is_dir():
                counts["plugins"] += self._copy_plugin_tree(plugin_dir)
                found_structure = True
                self._copy_game_root_assets(candidate)
            for name in ("CustomMissions1", "CustomMissions"):
                mission_dir = candidate / name
                if mission_dir.is_dir():
                    counts["v1"] += self._copy_v1_files(mission_dir)
                    found_structure = True
            mission_v2 = candidate / "CustomMissions2"
            if mission_v2.is_dir():
                counts["v2"] += self._copy_v2_packages(mission_v2)
                found_structure = True
        if found_structure:
            return counts

        if (root / "meta.json").is_file() or any(root.glob("*.code")):
            self._copy_directory(root, self.v2 / root.name)
            counts["v2"] = 1
            return counts
        dlls = [path for path in root.rglob("*.dll") if path.is_file() and not path.is_symlink()]
        if dlls:
            bundle_name = suggested_name or root.name
            self._copy_directory(root, self.plugins / bundle_name)
            counts["plugins"] = len(dlls)
            return counts
        json_files = [path for path in root.glob("*.json") if path.is_file() and not path.is_symlink()]
        if json_files:
            for path in json_files:
                shutil.copy2(path, self.v1 / path.name)
            counts["v1"] = len(json_files)
            return counts
        raise DropInImportError("未找到 BepInEx 插件、V1 JSON 或 V2 .code 包")

    def _copy_plugin_tree(self, source: Path) -> int:
        dlls = [path for path in source.rglob("*.dll") if path.is_file() and not path.is_symlink()]
        for child in source.iterdir():
            if child.is_symlink():
                continue
            target = self.plugins / child.name
            if child.is_dir():
                self._copy_directory(child, target)
            elif child.is_file():
                shutil.copy2(child, target)
        return len(dlls)

    def _copy_v1_files(self, source: Path) -> int:
        files = [path for path in source.glob("*.json") if path.is_file() and not path.is_symlink()]
        for path in files:
            shutil.copy2(path, self.v1 / path.name)
        return len(files)

    def _copy_v2_packages(self, source: Path) -> int:
        packages = [path for path in source.iterdir() if path.is_dir() and not path.is_symlink()]
        for path in packages:
            self._copy_directory(path, self.v2 / path.name)
        return len(packages)

    def _copy_game_root_assets(self, source: Path) -> None:
        asset_root = self.plugins / "_game_root"
        font = source / "NotoSerifSC-Regular.otf"
        if font.is_file() and not font.is_symlink():
            asset_root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(font, asset_root / font.name)
        npc_config = source / "NPCBehaviorMod"
        if npc_config.is_dir() and not npc_config.is_symlink():
            self._copy_directory(npc_config, asset_root / "NPCBehaviorMod")

    @staticmethod
    def _copy_directory(source: Path, target: Path) -> None:
        if source.is_symlink():
            raise DropInImportError("不接受符号链接目录")
        if any(path.is_symlink() for path in source.rglob("*")):
            raise DropInImportError("Mod 文件夹包含符号链接")
        # A same-name import is a replacement, not a merge.  Merging left files
        # removed by the new version in the repository, so a later scan could
        # still load code and assets from the previous version.
        target.parent.mkdir(parents=True, exist_ok=True)
        staged = target.with_name(target.name + ".importing")
        backup = target.with_name(target.name + ".previous")
        if staged.exists():
            shutil.rmtree(staged)
        if backup.exists():
            shutil.rmtree(backup)
        shutil.copytree(source, staged, symlinks=False)
        try:
            if target.exists():
                target.replace(backup)
            staged.replace(target)
        except OSError:
            if not target.exists() and backup.exists():
                backup.replace(target)
            raise
        finally:
            if staged.exists():
                shutil.rmtree(staged)
            if backup.exists():
                shutil.rmtree(backup)

"""Safe, guided import of the user9527 Chinese localization/mod collection.

The importer deliberately treats the downloaded collection as untrusted data:
it never executes files from the pack, follows no symlinks, and only copies the
known game-content folders.  Imported content starts in a minimal preset where
only the V1/V2 Custom Mission loaders are active.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from manaka_mod_manager import game_is_running


class Pack9527Error(RuntimeError):
    pass


KEEP_ENABLED_LOADERS = {
    "sfm_custom_mission.dll",
    "sfm_custom_mission_v2.dll",
}
MANIFEST_NAME = "9527-install-manifest.json"


@dataclass(frozen=True)
class Pack9527Analysis:
    root: str
    plugins: int
    v1_missions: int
    v2_packages: int
    readmes: tuple[str, ...]
    loader_v1: bool
    loader_v2: bool
    total_bytes: int

    @property
    def ready(self) -> bool:
        return self.loader_v1 and self.loader_v2 and self.v1_missions > 0 and self.v2_packages > 0

    def as_dict(self) -> dict:
        value = asdict(self)
        value["ready"] = self.ready
        value["readmes"] = list(self.readmes)
        return value


def _is_pack_root(folder: Path) -> bool:
    return (
        (folder / "BepInEx" / "plugins").is_dir()
        and (folder / "CustomMissions").is_dir()
        and (folder / "CustomMissions2").is_dir()
    )


def _assert_plain_tree(folder: Path) -> None:
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise Pack9527Error(f"整合包包含不允许的链接文件：{path.name}")


def _files(folder: Path):
    if not folder.is_dir():
        return
    for path in folder.rglob("*"):
        if path.is_file() and not path.is_symlink():
            yield path


class Pack9527Importer:
    def locate(self, selected: Path) -> Path:
        selected = selected.expanduser().resolve()
        if _is_pack_root(selected):
            return selected
        candidates: list[Path] = []
        if selected.is_dir():
            for child in selected.iterdir():
                if child.is_dir() and _is_pack_root(child):
                    candidates.append(child)
                elif child.is_dir():
                    for grandchild in child.iterdir():
                        if grandchild.is_dir() and _is_pack_root(grandchild):
                            candidates.append(grandchild)
        unique = list(dict.fromkeys(path.resolve() for path in candidates))
        if len(unique) == 1:
            return unique[0]
        if len(unique) > 1:
            raise Pack9527Error("发现多个可能的整合包，请选择直接包含 BepInEx、CustomMissions 和 CustomMissions2 的目录")
        raise Pack9527Error("未识别到 9527 整合包；所选目录应直接包含 BepInEx、CustomMissions 和 CustomMissions2")

    def inspect(self, selected: Path) -> Pack9527Analysis:
        root = self.locate(selected)
        _assert_plain_tree(root)
        plugins_root = root / "BepInEx" / "plugins"
        dlls = list(plugins_root.rglob("*.dll"))
        names = {path.name.casefold() for path in dlls}
        v1_files = list((root / "CustomMissions").rglob("*.json"))
        v2_packages = [path for path in (root / "CustomMissions2").iterdir() if path.is_dir()]
        readmes = tuple(
            path.name
            for path in sorted(root.glob("*.txt"), key=lambda item: item.name.casefold())
            if "必读" in path.name or "readme" in path.name.casefold() or "说明" in path.name
        )
        total_bytes = sum(path.stat().st_size for path in _files(root))
        return Pack9527Analysis(
            root=str(root),
            plugins=len(dlls),
            v1_missions=len(v1_files),
            v2_packages=len(v2_packages),
            readmes=readmes,
            loader_v1="sfm_custom_mission.dll" in names,
            loader_v2="sfm_custom_mission_v2.dll" in names,
            total_bytes=total_bytes,
        )

    @staticmethod
    def _safe_target(game_root: Path, relative: Path) -> Path:
        target = (game_root / relative).resolve(strict=False)
        root = game_root.resolve()
        if target != root and root not in target.parents:
            raise Pack9527Error("整合包目标路径超出游戏目录")
        return target

    @staticmethod
    def _remove(path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)

    def install(self, selected: Path, game_root: Path) -> dict:
        analysis = self.inspect(selected)
        source_root = Path(analysis.root).resolve()
        game_root = game_root.expanduser().resolve()
        # The cleanup plan can remove active missions before the copy phase.
        # Reject overlapping trees before any backup/removal, rather than merely
        # skipping copy2's SameFileError after sources may already be touched.
        if (
            source_root == game_root
            or source_root in game_root.parents
            or game_root in source_root.parents
        ):
            raise Pack9527Error(
                "整合包目录与游戏目录不能相同或互相包含。"
                "请将 9527 整合包解压到游戏目录之外，再选择该解压目录。"
                "如果已手动安装，请到 Mod 管理器扫描本地游戏。"
            )
        if not analysis.ready:
            missing: list[str] = []
            if not analysis.loader_v1:
                missing.append("SFM_custom_mission.dll")
            if not analysis.loader_v2:
                missing.append("SFM_custom_mission_v2.dll")
            if not analysis.v1_missions:
                missing.append("V1 JSON 任务")
            if not analysis.v2_packages:
                missing.append("V2 任务目录")
            raise Pack9527Error("整合包校验未通过，缺少：" + "、".join(missing))

        if not (game_root / "SecretFlasherManaka.exe").is_file():
            raise Pack9527Error("请先选择能直接看到 SecretFlasherManaka.exe 的游戏目录")
        if not (game_root / "BepInEx" / "core" / "BepInEx.Core.dll").is_file():
            raise Pack9527Error("请先在“设备与游戏”中安装 / 修复 BepInEx 运行环境")
        if game_is_running():
            raise Pack9527Error("请完全退出游戏后再导入 9527 整合包")

        manager_root = game_root / "ManakaModManager"
        manifest_path = manager_root / MANIFEST_NAME
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup_root = manager_root / "backups" / f"9527-{stamp}"
        backup_files = backup_root / "files"
        backed_up: set[str] = set()
        touched: set[str] = set()

        def relative_target(path: Path) -> str:
            return path.resolve(strict=False).relative_to(game_root).as_posix()

        def backup(path: Path) -> None:
            if not path.exists():
                return
            relative = relative_target(path)
            if relative in backed_up:
                return
            destination = backup_files / Path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if path.is_dir():
                shutil.copytree(path, destination)
            else:
                shutil.copy2(path, destination)
            backed_up.add(relative)

        def remove_managed(path: Path) -> None:
            backup(path)
            touched.add(relative_target(path))
            self._remove(path)

        old_files: list[str] = []
        try:
            old_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            old_files = [str(value) for value in old_data.get("managedFiles", [])]
        except (OSError, ValueError, TypeError):
            old_files = []

        copy_plan: list[tuple[Path, Path]] = []
        plugins_root = source_root / "BepInEx" / "plugins"
        for source in _files(plugins_root):
            relative = source.relative_to(plugins_root)
            target_relative = Path("BepInEx") / "plugins" / relative
            if source.suffix.casefold() == ".dll" and source.name.casefold() not in KEEP_ENABLED_LOADERS:
                target_relative = target_relative.with_name(target_relative.name + ".disabled")
            copy_plan.append((source, target_relative))

        config_root = source_root / "BepInEx" / "config"
        for source in _files(config_root):
            copy_plan.append((source, Path("BepInEx") / "config" / source.relative_to(config_root)))

        v1_root = source_root / "CustomMissions"
        for source in _files(v1_root):
            copy_plan.append((source, Path("ManakaModManager") / "disabled" / "v1" / source.relative_to(v1_root)))

        v2_root = source_root / "CustomMissions2"
        for source in _files(v2_root):
            copy_plan.append((source, Path("ManakaModManager") / "disabled" / "v2" / source.relative_to(v2_root)))

        optional_root = source_root / "NPCBehaviorMod"
        for source in _files(optional_root):
            copy_plan.append((source, Path("NPCBehaviorMod") / source.relative_to(optional_root)))
        for source in source_root.iterdir():
            if source.is_file() and source.suffix.casefold() in {".otf", ".ttf"}:
                copy_plan.append((source, Path(source.name)))

        planned_relatives = {relative.as_posix() for _, relative in copy_plan}
        plugin_alternates: set[Path] = set()
        for source, relative in copy_plan:
            if source.suffix.casefold() != ".dll":
                continue
            if relative.name.casefold().endswith(".dll.disabled"):
                plugin_alternates.add(relative.with_name(relative.name.removesuffix(".disabled")))
            else:
                plugin_alternates.add(relative.with_name(relative.name + ".disabled"))

        v1_active = [Path("CustomMissions") / path.relative_to(v1_root) for path in _files(v1_root)]
        v2_names = [path.name for path in v2_root.iterdir() if path.is_dir()]

        try:
            for value in old_files:
                target = self._safe_target(game_root, Path(value))
                if target.exists():
                    remove_managed(target)
            for relative in plugin_alternates:
                target = self._safe_target(game_root, relative)
                if target.exists():
                    remove_managed(target)
            for relative in v1_active:
                target = self._safe_target(game_root, relative)
                if target.exists():
                    remove_managed(target)
            for name in v2_names:
                target = self._safe_target(game_root, Path("CustomMissions2") / name)
                if target.exists():
                    remove_managed(target)

            for source, relative in copy_plan:
                target = self._safe_target(game_root, relative)
                backup(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                touched.add(relative.as_posix())

            backup_root.mkdir(parents=True, exist_ok=True)
            (backup_root / "backup-manifest.json").write_text(
                json.dumps({"originalFiles": sorted(backed_up)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            manager_root.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "installedAt": stamp,
                        "source": analysis.root,
                        "managedFiles": sorted(planned_relatives),
                        "preset": "custom-mission-loaders-only",
                        "backup": str(backup_root),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception:
            for value in sorted(touched, key=lambda item: len(Path(item).parts), reverse=True):
                self._remove(self._safe_target(game_root, Path(value)))
            for value in sorted(backed_up, key=lambda item: len(Path(item).parts)):
                source = backup_files / Path(value)
                target = self._safe_target(game_root, Path(value))
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    shutil.copytree(source, target, dirs_exist_ok=True)
                elif source.is_file():
                    shutil.copy2(source, target)
            raise

        return {
            **analysis.as_dict(),
            "backup": str(backup_root),
            "enabled_plugins": 2,
            "disabled_plugins": max(0, analysis.plugins - 2),
            "disabled_v1": analysis.v1_missions,
            "disabled_v2": analysis.v2_packages,
        }

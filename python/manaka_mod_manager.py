"""Safe, reversible mod inventory and toggling for Secret Flasher Manaka.

Third-party files are never bundled by the application.  A user-selected pack is
treated as a read-only source library; the selected game folder is the only
managed destination.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class ModManagerError(RuntimeError):
    pass


PLUGIN_DESCRIPTIONS = {
    "barenai_manaka_helper": "通用辅助插件；部分玩法或任务可能依赖它。",
    "bettercompass": "改进游戏内罗盘显示。",
    "bgmkr.manaka.animcancel": "允许取消部分动作动画。",
    "desperatedash": "扩展冲刺相关玩法。",
    "doorinspect": "增加门与入口的检查交互。",
    "rotorsoundfix": "修正转子类道具的声音表现。",
    "sfm_custom_mission": "V1 CustomMissions JSON 任务加载器。",
    "sfm_custom_mission_v2": "V2 .code 任务与功能包加载器。",
    "sfm_disable_missions": "隐藏/停用原版任务；建议完成原版地图任务后再启用。",
    "sfmcmextender": "V1 自定义任务扩展依赖，部分大型任务包需要。",
    "sfmcosplayloadermod": "自定义服装与模型资源加载器。",
    "texture_replacer_be_il2cpp": "图片/材质替换加载器。",
    "sfmfluidsmod": "额外流体视觉效果与相关资源。",
    "secretflasher.voicepack-plus": "附加语音包及音频资源。",
    "npcbehaviormodifier": "改变 NPC 行为；与部分追逐或接管 NPC 的任务冲突。",
    "xxxhibition_sex": "扩展互动玩法；已知可能与 Aftermath 系列产生严重冲突。",
    "freer": "解除或放宽部分游戏限制。",
}

SOFT_WARNINGS = {
    "aftermath&stagelock": "与其他 Aftermath 变体互斥；也可能与接管 NPC 或场景流程的模组冲突。",
    "hunted": "与 NPCBehaviorModifier、Aftermath 系列及其他接管 NPC 的模组存在冲突。",
    "vampire": "与 NPCBehaviorModifier 及改变快感值机制的模组存在冲突。",
    "npcs pickup items": "可能干扰 Hunted 等需要控制 NPC 的任务。",
    "custom ecstasy": "会覆盖快感值机制，属于高兼容性风险功能。",
    "exhiburges": "第 4 章终局建议停用 NPCBehaviorModifier 和所有 Aftermath 变体。",
    "xxxhibition-sex": "需要配套配置；与 Aftermath 系列有已知严重冲突。",
    "conditionalhomedoor": "在室外时修改设置或停用，既有效果可能要回家后才会刷新。",
}

EXCLUSIVE_V2_GROUPS = (
    frozenset({"aftermath", "aftermath&stagelock"}),
    frozenset({"multistageitemsearch", "multistageitemsearchplus"}),
)


@dataclass
class ModEntry:
    id: str
    kind: str
    name: str
    description: str
    enabled: bool
    available: bool
    status: str
    warning: str = ""
    files: list[str] = field(default_factory=list)
    source: str = ""
    target: str = ""
    source_map: dict[str, str] = field(default_factory=dict)
    required_plugin_id: str = ""
    required_plugin_name: str = ""
    dependency_ready: bool = True
    dependency_available: bool = True

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "kindLabel": {"plugin": "插件", "v1": "V1 任务", "v2": "V2 包"}[self.kind],
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "available": self.available,
            "status": self.status,
            "warning": self.warning,
            "fileCount": len(self.files),
            "requiredPluginId": self.required_plugin_id,
            "requiredPluginName": self.required_plugin_name,
            "dependencyReady": self.dependency_ready,
            "dependencyAvailable": self.dependency_available,
        }


def _safe_child(root: Path, candidate: Path) -> Path:
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve(strict=False)
    if candidate_resolved != root_resolved and root_resolved not in candidate_resolved.parents:
        raise ModManagerError("路径超出允许的 Mod 目录")
    return candidate


def _plain_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("Sc", "En", "Tc", "Ja", "Ko"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
    return ""


def _read_v2_meta(folder: Path) -> tuple[str, str]:
    meta = folder / "meta.json"
    try:
        data = json.loads(meta.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, UnicodeDecodeError):
        return folder.name, "V2 自定义任务或功能包"
    title = _plain_text(data.get("title")) or folder.name
    description = _plain_text(data.get("description"))
    if not description or description.lower() == "settings":
        for item in data.get("settings", []):
            if isinstance(item, dict) and item.get("type") == "Label":
                description = _plain_text(item.get("title"))
                if description:
                    break
    description = re.sub(r"\s+", " ", description)[:180]
    return title, description or "V2 自定义任务或功能包"


def _v1_group(stem: str) -> str:
    if re.match(r"^\d", stem):
        return "基础地点任务包"
    if "_" in stem:
        return stem.split("_", 1)[0].strip() or stem
    clean = re.sub(r"(?:[ ._-]?\d+(?:[._-]\d+)*)$", "", stem).strip(" ._-")
    return clean or stem


def game_is_running() -> bool:
    """Return whether the game process is present without opening a console."""
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq SecretFlasherManaka.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=flags,
            check=False,
        )
        return "SecretFlasherManaka.exe" in result.stdout
    except (OSError, subprocess.SubprocessError):
        return False


class ManakaModManager:
    def __init__(
        self,
        game_root: Path,
        source_root: Path,
        additional_source_roots: list[Path] | tuple[Path, ...] = (),
    ) -> None:
        self.game_root = game_root
        self.source_root = source_root
        self.additional_source_roots = [
            path for path in additional_source_roots if path != source_root
        ]
        # Explicit user drop-ins take precedence over bundled files with the
        # same relative name, while the curated repository remains the base.
        self.source_roots = list(self.additional_source_roots) + [source_root]
        self.disabled_root = game_root / "ManakaModManager" / "disabled"
        self.entries: dict[str, ModEntry] = {}

    @staticmethod
    def _plugins_dir_for(root: Path) -> Path:
        candidates = (
            root / "BepInEx" / "plugins",
            root / "plugins" / "files",
            root / "plugins" / "BepInEx" / "plugins",
        )
        return next((path for path in candidates if path.is_dir()), candidates[0])

    @staticmethod
    def _v1_dir_for(root: Path) -> Path:
        candidates = (
            root / "custommissions1" / "files",
            root / "CustomMissions1",
        )
        return next((path for path in candidates if path.is_dir()), candidates[0])

    @staticmethod
    def _v2_dir_for(root: Path) -> Path:
        candidates = (
            root / "custommissions2" / "files",
            root / "CustomMissions2",
        )
        return next((path for path in candidates if path.is_dir()), candidates[0])

    def _source_plugins_dirs(self) -> list[Path]:
        return [path for path in (self._plugins_dir_for(root) for root in self.source_roots) if path.is_dir()]

    def _source_v1_dirs(self) -> list[Path]:
        return [path for path in (self._v1_dir_for(root) for root in self.source_roots) if path.is_dir()]

    def _source_v2_dirs(self) -> list[Path]:
        return [path for path in (self._v2_dir_for(root) for root in self.source_roots) if path.is_dir()]

    def _plugin_root_for(self, source: Path) -> Path | None:
        resolved = source.resolve(strict=False)
        for root in self._source_plugins_dirs():
            root_resolved = root.resolve()
            if resolved == root_resolved or root_resolved in resolved.parents:
                return root
        return None

    def _require_roots(self) -> None:
        if not (self.game_root / "SecretFlasherManaka.exe").is_file():
            raise ModManagerError("游戏目录无效：应能直接看到 SecretFlasherManaka.exe")
        if not self.source_root.is_dir():
            raise ModManagerError("Mod 来源目录不存在")

    def scan(self) -> list[dict]:
        self._require_roots()
        entries: list[ModEntry] = []
        entries.extend(self._scan_plugins())
        entries.extend(self._scan_v1())
        entries.extend(self._scan_v2())
        self._annotate_dependencies(entries)
        self.entries = {entry.id: entry for entry in entries}
        return [entry.as_dict() for entry in entries]

    @staticmethod
    def _annotate_dependencies(entries: list[ModEntry]) -> None:
        """Expose the V1/V2 runtime loader relationship to the UI.

        Mission content may still be staged while its loader is disabled; the
        dashboard must make it clear that it will not run until the matching
        Custom Mission DLL is enabled.
        """
        plugins = {
            Path(entry.files[0]).name.casefold(): entry
            for entry in entries
            if entry.kind == "plugin" and entry.files
        }
        requirements = {
            "v1": ("SFM_custom_mission.dll", "CustomMission 1"),
            "v2": ("SFM_custom_mission_v2.dll", "CustomMission 2"),
        }
        for entry in entries:
            requirement = requirements.get(entry.kind)
            if requirement is None:
                continue
            filename, display_name = requirement
            plugin = plugins.get(filename.casefold())
            entry.required_plugin_id = f"plugin|{filename}"
            entry.required_plugin_name = display_name
            entry.dependency_available = bool(plugin and plugin.available)
            entry.dependency_ready = bool(plugin and plugin.enabled)

    def _scan_plugins(self) -> list[ModEntry]:
        target_plugins = self.game_root / "BepInEx" / "plugins"
        candidates: dict[str, tuple[Path | None, Path]] = {}

        def add_source(path: Path, source_plugins: Path) -> None:
            relative = path.relative_to(source_plugins)
            if relative.parts and relative.parts[0].casefold() == "save":
                target_rel = Path(path.name)
            else:
                target_rel = relative
            if path.name.casefold() == "manakadglabtelemetry.dll":
                return
            candidates.setdefault(target_rel.as_posix().casefold(), (path, target_rel))

        for source_plugins in self._source_plugins_dirs():
            for path in source_plugins.rglob("*.dll"):
                if not path.is_symlink():
                    add_source(path, source_plugins)
            for path in source_plugins.rglob("*.dll.disabled"):
                if not path.is_symlink():
                    relative = path.relative_to(source_plugins)
                    target_rel = relative.with_name(path.name.removesuffix(".disabled"))
                    candidates.setdefault(target_rel.as_posix().casefold(), (path, target_rel))
        if target_plugins.is_dir():
            for path in target_plugins.rglob("*.dll"):
                if path.name.casefold() == "manakadglabtelemetry.dll":
                    continue
                rel = path.relative_to(target_plugins)
                candidates.setdefault(rel.as_posix().casefold(), (None, rel))
            for path in target_plugins.rglob("*.dll.disabled"):
                rel = path.relative_to(target_plugins).with_name(path.name.removesuffix(".disabled"))
                candidates.setdefault(rel.as_posix().casefold(), (None, rel))

        result: list[ModEntry] = []
        for _, (source, rel) in sorted(candidates.items()):
            target = target_plugins / rel
            disabled = target.with_name(target.name + ".disabled")
            stem = target.stem
            key = stem.casefold()
            enabled = target.is_file()
            available = enabled or disabled.is_file() or bool(source and source.is_file())
            status = "已启用" if enabled else "已停用" if disabled.is_file() else "可安装"
            warning = ""
            if key == "npcbehaviormodifier":
                warning = "与 Hunted、Vampire、NpcGotUsedToIt 等接管 NPC 的内容可能冲突。"
            elif key == "xxxhibition_sex":
                warning = "与 Aftermath 系列存在已知严重冲突。"
            result.append(ModEntry(
                id="plugin|" + rel.as_posix(), kind="plugin", name=stem,
                description=PLUGIN_DESCRIPTIONS.get(key, "BepInEx 扩展插件"),
                enabled=enabled, available=available, status=status, warning=warning,
                files=[rel.as_posix()], source=str(source or ""), target=str(target),
            ))
        return result

    def _v1_files(self, root: Path) -> list[Path]:
        if not root.is_dir():
            return []
        return [path for path in root.glob("*.json") if path.is_file() and not path.is_symlink()]

    def _scan_v1(self) -> list[ModEntry]:
        source_dirs = self._source_v1_dirs()
        active_dir = self.game_root / "CustomMissions"
        disabled_dir = self.disabled_root / "v1"
        groups: dict[str, dict[str, Path]] = {}
        source_files: dict[str, Path] = {}
        for directory in source_dirs:
            for path in self._v1_files(directory):
                source_files.setdefault(path.name.casefold(), path)
        for directory in (*source_dirs, active_dir, disabled_dir):
            for path in self._v1_files(directory):
                group = _v1_group(path.stem)
                groups.setdefault(group, {}).setdefault(path.name.casefold(), path)
        result: list[ModEntry] = []
        for group, known in sorted(groups.items(), key=lambda item: item[0].casefold()):
            names = sorted({path.name for path in known.values()}, key=str.casefold)
            active_count = sum((active_dir / name).is_file() for name in names)
            enabled = bool(names) and active_count == len(names)
            status = "已启用" if enabled else f"部分启用 {active_count}/{len(names)}" if active_count else "已停用"
            sample = "、".join(Path(name).stem for name in names[:3])
            result.append(ModEntry(
                id="v1|" + group, kind="v1", name=group,
                description=f"{len(names)} 个 V1 JSON 任务" + (f"：{sample}" if sample else ""),
                enabled=enabled, available=bool(names), status=status, files=names,
                source=str(source_dirs[0]) if source_dirs else "", target=str(active_dir),
                source_map={key: str(path) for key, path in source_files.items() if key in known},
            ))
        return result

    def _v2_names(self, root: Path) -> set[str]:
        if not root.is_dir():
            return set()
        return {path.name for path in root.iterdir() if path.is_dir() and not path.is_symlink()}

    def _scan_v2(self) -> list[ModEntry]:
        source_dirs = self._source_v2_dirs()
        active_dir = self.game_root / "CustomMissions2"
        disabled_dir = self.disabled_root / "v2"
        source_map: dict[str, Path] = {}
        for directory in source_dirs:
            for name in self._v2_names(directory):
                source_map.setdefault(name.casefold(), directory / name)
        names = {path.name for path in source_map.values()} | self._v2_names(active_dir) | self._v2_names(disabled_dir)
        result: list[ModEntry] = []
        for name in sorted(names, key=str.casefold):
            source = source_map.get(name.casefold(), (source_dirs[0] / name) if source_dirs else Path())
            active = active_dir / name
            disabled = disabled_dir / name
            meta_folder = active if active.is_dir() else source if source.is_dir() else disabled
            title, description = _read_v2_meta(meta_folder)
            result.append(ModEntry(
                id="v2|" + name, kind="v2", name=title,
                description=description, enabled=active.is_dir(), available=True,
                status="已启用" if active.is_dir() else "已停用",
                warning=SOFT_WARNINGS.get(name.casefold(), ""), files=[name],
                source=str(source), target=str(active),
            ))
        return result

    def set_enabled(self, entry_id: str, enabled: bool) -> str:
        self._require_roots()
        if game_is_running():
            raise ModManagerError("请完全退出游戏后再修改 Mod；仅暂停或回到标题画面还不够")
        if entry_id not in self.entries:
            self.scan()
        entry = self.entries.get(entry_id)
        if entry is None:
            raise ModManagerError("找不到这个 Mod，请重新扫描")
        if entry.enabled == enabled:
            return entry.status
        if enabled and entry.kind == "v2":
            self._check_v2_conflict(entry)
        if entry.kind == "plugin":
            self._toggle_plugin(entry, enabled)
        elif entry.kind == "v1":
            self._toggle_v1(entry, enabled)
        else:
            self._toggle_v2(entry, enabled)
        self._write_state(entry_id, enabled)
        self.scan()
        return "已启用" if enabled else "已停用"

    def _check_v2_conflict(self, entry: ModEntry) -> None:
        name = entry.files[0].casefold()
        active_names = {
            item.files[0].casefold() for item in self.entries.values()
            if item.kind == "v2" and item.enabled
        }
        for group in EXCLUSIVE_V2_GROUPS:
            if name in group:
                conflict = next((value for value in group if value != name and value in active_names), None)
                if conflict:
                    raise ModManagerError(f"互斥冲突：请先停用 {conflict}")

    def _toggle_plugin(self, entry: ModEntry, enabled: bool) -> None:
        target = _safe_child(self.game_root, Path(entry.target))
        disabled = target.with_name(target.name + ".disabled")
        target.parent.mkdir(parents=True, exist_ok=True)
        if enabled:
            if disabled.is_file():
                disabled.replace(target)
                return
            source = Path(entry.source) if entry.source else None
            if source is None or not source.is_file():
                raise ModManagerError("来源库中缺少插件文件")
            if source.name.endswith(".disabled"):
                shutil.copy2(source, target)
            else:
                source_plugins = self._plugin_root_for(source)
                if source_plugins is not None and source.parent != source_plugins and source.parent.name.casefold() != "save":
                    bundle_target = target.parent
                    shutil.copytree(source.parent, bundle_target, dirs_exist_ok=True)
                else:
                    shutil.copy2(source, target)
            self._copy_plugin_resources(target.stem, source)
        else:
            if target.is_file():
                target.replace(disabled)

    def _copy_plugin_resources(self, plugin_stem: str, source_plugin: Path) -> None:
        mapping = {
            "sfm_custom_mission_v2": ["SFM_custom_mission_v2"],
            "sfmcosplayloadermod": ["ModCosplays", "ModMaterials"],
            "texture_replacer_be_il2cpp": ["ModImages"],
        }
        source_plugins = self._plugin_root_for(source_plugin)
        if source_plugins is None:
            return
        target_plugins = self.game_root / "BepInEx" / "plugins"
        for name in mapping.get(plugin_stem.casefold(), []):
            source = source_plugins / name
            if source.is_dir() and not source.is_symlink():
                shutil.copytree(source, target_plugins / name, dirs_exist_ok=True)

        root_asset_candidates = tuple(self.source_roots) + (source_plugins / "_game_root",)
        root_assets = next(
            (path for path in root_asset_candidates if (path / "NotoSerifSC-Regular.otf").is_file()),
            None,
        )
        if root_assets is not None and plugin_stem.casefold() in {
            "sfm_custom_mission", "sfm_custom_mission_v2", "sfmcmextender"
        }:
            shutil.copy2(root_assets / "NotoSerifSC-Regular.otf", self.game_root / "NotoSerifSC-Regular.otf")

        if plugin_stem.casefold() == "npcbehaviormodifier":
            config_root = next(
                (path / "NPCBehaviorMod" for path in root_asset_candidates if (path / "NPCBehaviorMod").is_dir()),
                None,
            )
            if config_root is not None:
                shutil.copytree(config_root, self.game_root / "NPCBehaviorMod", dirs_exist_ok=True)

    def _toggle_v1(self, entry: ModEntry, enabled: bool) -> None:
        active_dir = self.game_root / "CustomMissions"
        disabled_dir = self.disabled_root / "v1"
        active_dir.mkdir(parents=True, exist_ok=True)
        disabled_dir.mkdir(parents=True, exist_ok=True)
        for name in entry.files:
            active = _safe_child(active_dir, active_dir / name)
            disabled = _safe_child(disabled_dir, disabled_dir / name)
            source_value = entry.source_map.get(name.casefold(), "")
            source = Path(source_value) if source_value else Path()
            if enabled and not active.exists():
                if disabled.is_file():
                    disabled.replace(active)
                elif source_value and source.is_file():
                    shutil.copy2(source, active)
                else:
                    raise ModManagerError(f"缺少任务文件：{name}")
            elif not enabled and active.is_file():
                active.replace(disabled)

    def _toggle_v2(self, entry: ModEntry, enabled: bool) -> None:
        name = entry.files[0]
        source = Path(entry.source) if entry.source else Path()
        active = _safe_child(self.game_root / "CustomMissions2", self.game_root / "CustomMissions2" / name)
        disabled = _safe_child(self.disabled_root / "v2", self.disabled_root / "v2" / name)
        active.parent.mkdir(parents=True, exist_ok=True)
        disabled.parent.mkdir(parents=True, exist_ok=True)
        if enabled and not active.exists():
            if disabled.is_dir():
                shutil.move(str(disabled), str(active))
            elif entry.source and source.is_dir():
                shutil.copytree(source, active)
            else:
                raise ModManagerError("来源库中缺少该 V2 包")
        elif not enabled and active.is_dir():
            if disabled.exists():
                raise ModManagerError("隔离区已有同名包，请先处理重复文件")
            shutil.move(str(active), str(disabled))

    def _write_state(self, entry_id: str, enabled: bool) -> None:
        state_dir = self.game_root / "ManakaModManager"
        state_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "schema": 1,
            "sourceRoot": str(self.source_root),
            "additionalSourceRoots": [str(path) for path in self.additional_source_roots],
            "lastChanged": entry_id,
            "lastEnabled": enabled,
        }
        (state_dir / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )


"""Safe, reversible mod inventory and toggling for Secret Flasher Manaka.

Third-party files are never bundled by the application. The selected game folder
is the default local inventory; an optional user-selected pack is treated as a
read-only source library and the game folder remains the only managed destination.
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
    "animreplacer": "动作替换插件，按 F1 打开设置。",
    "bj_sounds": "为 Xxxhibition_Sex 提供口交声音。",
    "collarasset": "锁链拘束具；配合 ChainCollar 或 PetCollar，面对墙体按 ] 使用。",
    "com.tetorafetora.sfmfluidsmod": "增强淫水和液体的视觉效果。",
    "sfmfluidsmod": "增强淫水和液体的视觉效果。",
    "cosplayascoat": "整合额外服装的私服、穿脱等扩展功能；请备份 partgroups 配置。",
    "sfm_maploader": "加载自定义地图及其资源。",
    "sfmcosplaycache": "提升额外服装加载速度，可通过 cfg 配置。",
    "allowall": "设置角色可以与哪些类型的 NPC 互动。",
    "barenai_manaka_helper": "去除马赛克补丁。",
    "bettercompass": "罗盘会提示物品与角色的垂直位置关系。",
    "bgmkr.manaka.animcancel": "允许角色趴着时做姿势动作。",
    "cmv2extras": "CustomMission 2 的必需扩展功能。",
    "desperatedash": "震动器处于强档时仍可消耗体力冲刺。",
    "disablecollectall": "禁止使用 PC 回收全部物品。",
    "disablefasttravel": "禁止使用 Tab 快速传送。",
    "eyemaskplus": "设置佩戴眼罩后的视野，可通过 cfg 配置。",
    "freer": "重做手铐系统，让受束缚后的行动更符合真实逻辑。",
    "gameoversounddisabler": "禁用被发现后的提示音效。",
    "handcuffskillcheck": "把手铐解锁改为按空格完成 QTE，可通过 cfg 配置。",
    "heartfx": "高心率时增加屏幕晃动效果。",
    "hidefinishedpanel": "完成原版任务后隐藏任务面板。",
    "manakacamera": "额外摄像机；* 开关、[ 切换模式，Ctrl 配合方向键移动。",
    "minimapplugin": "F5 显示小地图，F6 显示大地图。",
    "mpasset": "ManakaPlus 任务的必需插件。",
    "nakedcountedasflashing": "全裸时同时计为多种暴露状态，可能一次出现大量任务。",
    "npcbehaviormodifier": "改变 NPC 行为；暴露后进入追逐，被抓后进入惩罚流程。",
    "npccompass": "显示周围 NPC 位置的平面图，可通过 cfg 配置。",
    "npcturn": "修复插件控制 NPC 转身时可能出现的错误。",
    "rotorsoundfix": "为两种转子补充震动音效。",
    "sfm_custom_mission": "V1 CustomMissions JSON 任务加载器。",
    "sfm_custom_mission_v2": "V2 .code 任务与功能包加载器。",
    "sfm_disable_missions": "隐藏/停用原版任务；建议完成原版地图任务后再启用。",
    "sfmcmextender": "CustomMissions/challenges 的必需扩展插件。",
    "sfmcosplayloadermod": "额外服装加载器，可在家中 PC 的在线商店购买服装。",
    "texture_replacer_be_il2cpp": "用命名正确的自定义贴图覆盖游戏贴图。",
    "transparenttoys": "设置外套与成人玩具的透明度，可通过 cfg 配置。",
    "xxxhibition_sex": "新增互动姿势与 Aftermath 惩罚系统；与 Aftermath 系列可能冲突。",
}

V2_DESCRIPTIONS = {
    "aftermath": "控制角色互动结束后的后果。",
    "aftermath&stagelock": "扩展版 Aftermath；与普通版互相干涉，只能谨慎选择一个。",
    "autobrightness": "为不同地图分别设置亮度。",
    "autostamina": "设置不同情况下的体力消耗与恢复。",
    "blackmailv2": "自定义剧情任务，起点在家门口右边。",
    "cameraflash": "使用手机相机推进的自定义任务。",
    "caught": "为 NPCBehaviorModifier 的多人惩罚模式提供额外效果。",
    "clothesstolen": "NPC 会抢走外套和服装；与 dropClothes 不兼容。",
    "conditionalhomedoor": "按条件限制回家；在室外生效后，修改设置不会立刻刷新。",
    "cosplaylink": "为服装绑定成人玩具功能。",
    "cosplayshop": "在多个商店使用 RP 购买身体彩绘、道具、钥匙与服装。",
    "countdownexposure": "长时间没有进行暴露会受到逐渐叠加的惩罚。",
    "custom ecstasy": "自定义快感值；说明标记为不稳定，请谨慎使用。",
    "destructive exposure": "破灭露出任务，依赖 DesperateDash、Freer、SFM_disable_missions 与 EdgingPatch。",
    "detective manaka": "自定义剧情任务，起点在家中落地镜边或吧台边。",
    "dial a kidnapper": "可通过手机主动触发绑架并获得 RP。",
    "d's clothes": "可通过手机下单取得一套私服。",
    "edgingpatch": "使用快捷键消耗体力降低快感值；修改按键后需重新载入存档。",
    "exhiburges": "章节式剧情任务；第三章结尾前需禁用所有 Aftermath 变体。",
    "exposureapocalypse": "自定义剧情任务，起点在家中落地镜边。",
    "fanschat": "直播/拍照玩法，可按 V 键直接拍照。",
    "fetch": "自定义剧情任务，起点在家门口左边。",
    "find my": "提供物品定位和手铐问题修复。",
    "goodvibrations": "扩展震动器与活塞机功能、开关掉落和 NPC 拾取。",
    "hideandseek": "躲猫猫玩法。",
    "homekeysearch": "寻找家门钥匙的小游戏。",
    "hunted": "生成特殊 NPC 追猎角色，可在家中时钟下设置惩罚。",
    "itemshifter": "远离掉落物后，将其转移到随机位置。",
    "lilith’s fun": "随机命令任务，并显示一套固定 UI。",
    "manaka adventure": "系列剧情任务，会自动加入 Tab 任务列表。",
    "manakahub": "直播姬玩法，必须配合 MPAsset。",
    "manakaplus": "额外小游戏扩展包，必须配合 MPAsset。",
    "mechanicspack": "限制佩戴或摘除成人玩具。",
    "mistake": "章节式剧情任务，起点在家里床边。",
    "moaning3": "呻吟音效与高潮动画扩展；声音类插件只建议启用一个。",
    "moremode": "提供多种震动器运行模式。",
    "multistageitemsearch": "多阶段物品搜索玩法，跟随游戏提示使用。",
    "nakedcoatsnatch": "夺回外套小游戏。",
    "nakedkeysnatch": "夺回钥匙小游戏。",
    "night trial": "自定义剧情任务，起点在家里床边。",
    "oops": "行动过程中自动打开外套或摔倒。",
    "park stroll": "公园相关自定义剧情任务。",
    "piercing jingle": "为服装增加音效；可能频繁产生无害的后台报错。",
    "policeofficer": "暴露后 NPC 会拍照并呼叫警察。",
    "prefectmanaka": "章节式剧情任务，可通过存档中的 progress 值回退进度。",
    "restricted": "整合多种限制与功能，默认开启；请在手机设置中逐项检查。",
    "shamegameover": "增加羞耻值系统。",
    "steal one pay ten": "自定义剧情任务，起点在家里正中。",
    "the dress": "大型综合任务；不熟悉 CustomMission 2 时不建议直接启用。",
    "the price of losing control": "单章节自定义剧情任务。",
    "timedcuffgame": "计时手铐小游戏，跟随游戏提示使用。",
    "timeforadventure": "自定义剧情任务。",
    "traveling tasks": "旅行任务，在家门口左边石碑或手机设置中查看规则。",
    "vampire": "夜间户外吸血玩法；与干涉快感值的插件不兼容。",
}

CORE_MODS = {
    "sfm_custom_mission", "sfm_custom_mission_v2", "cmv2extras",
    "mpasset", "sfmcmextender",
}
MEDIA_MODS = {
    "animreplacer", "bj_sounds", "com.tetorafetora.sfmfluidsmod",
    "cosplayascoat", "sfmcosplaycache", "barenai_manaka_helper",
    "eyemaskplus", "heartfx", "manakacamera", "minimapplugin",
    "npccompass", "rotorsoundfix", "sfmcosplayloadermod",
    "texture_replacer_be_il2cpp", "transparenttoys", "moaning3",
    "piercing jingle", "d's clothes", "sfmfluidsmod",
}
V2_STORY_MODS = {
    "blackmailv2", "cameraflash", "destructive exposure", "detective manaka",
    "exhiburges", "exposureapocalypse", "fetch", "manaka adventure", "mistake",
    "n96k", "night trial", "park stroll", "prefectmanaka", "steal one pay ten",
    "the dress", "the price of losing control", "timeforadventure", "traveling tasks",
}
UTILITY_MODS = {
    "bettercompass", "gameoversounddisabler", "hidefinishedpanel", "npcturn",
    "sfm_maploader", "autobrightness", "autostamina", "find my", "itemshifter",
}
GAMEPLAY_MODS = {
    "collarasset", "allowall", "bgmkr.manaka.animcancel", "desperatedash",
    "disablecollectall", "disablefasttravel", "freer", "handcuffskillcheck",
    "nakedcountedasflashing", "npcbehaviormodifier", "sfm_disable_missions",
    "xxxhibition_sex",
}

CATEGORY_LABELS = {
    "core": "必备前置",
    "v1": "V1 任务",
    "v2_story": "V2 剧情",
    "gameplay": "玩法与限制",
    "media": "外观与音效",
    "utility": "工具与辅助",
}


def _mod_category(kind: str, name: str) -> tuple[str, str]:
    key = name.casefold()
    if key in CORE_MODS:
        category = "core"
    elif kind == "v1":
        category = "v1"
    elif key in MEDIA_MODS:
        category = "media"
    elif key in UTILITY_MODS:
        category = "utility"
    elif key in GAMEPLAY_MODS:
        category = "gameplay"
    elif kind == "v2" and key in V2_STORY_MODS:
        category = "v2_story"
    elif kind == "v2":
        category = "gameplay"
    else:
        category = "utility"
    return category, CATEGORY_LABELS[category]

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
    user_imported: bool = False
    classification_key: str = ""

    def as_dict(self) -> dict:
        classification_key = self.classification_key or self.name
        category, category_label = _mod_category(self.kind, classification_key)
        return {
            "id": self.id,
            "kind": self.kind,
            "kindLabel": {"plugin": "插件", "v1": "V1 任务", "v2": "V2 包"}[self.kind],
            "name": self.name,
            "description": self.description,
            "category": category,
            "categoryLabel": category_label,
            "classificationKey": classification_key,
            "enabled": self.enabled,
            "available": self.available,
            "status": self.status,
            "warning": self.warning,
            "fileCount": len(self.files),
            "requiredPluginId": self.required_plugin_id,
            "requiredPluginName": self.required_plugin_name,
            "dependencyReady": self.dependency_ready,
            "dependencyAvailable": self.dependency_available,
            "userImported": self.user_imported,
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
        # Explicit user drop-ins take precedence over the selected source pack
        # when both contain the same relative name.
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
            root / "CustomMissions",
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
        for entry in entries:
            sources = [Path(entry.source)] if entry.source else []
            sources.extend(Path(value) for value in entry.source_map.values())
            entry.user_imported = any(self._dropin_root_for(path) is not None for path in sources)
        self._annotate_dependencies(entries)
        self.entries = {entry.id: entry for entry in entries}
        return [entry.as_dict() for entry in entries]

    def _dropin_root_for(self, source: Path) -> Path | None:
        resolved = source.resolve(strict=False)
        for root in self.additional_source_roots:
            root_resolved = root.resolve(strict=False)
            if resolved == root_resolved or root_resolved in resolved.parents:
                return root
        return None

    @staticmethod
    def _replace_directory(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        staged = target.with_name(target.name + ".updating")
        backup = target.with_name(target.name + ".previous")
        for temporary in (staged, backup):
            if temporary.exists():
                shutil.rmtree(temporary)
        shutil.copytree(source, staged)
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

    def refresh_enabled_from_sources(self) -> int:
        """Refresh enabled game copies after a same-name repository import."""
        self._require_roots()
        if game_is_running():
            raise ModManagerError("仓库已更新；请完全退出游戏后再次点击“导入并扫描”以替换已启用版本")
        if not self.entries:
            self.scan()
        refreshed = 0
        for entry in tuple(self.entries.values()):
            if not entry.enabled or not entry.user_imported:
                continue
            if entry.kind == "plugin":
                source = Path(entry.source) if entry.source else Path()
                target = _safe_child(self.game_root, Path(entry.target))
                if entry.source and source.is_file() and target.is_file():
                    shutil.copy2(source, target)
                    self._copy_plugin_resources(target.stem, source)
                    target.with_name(target.name + ".disabled").unlink(missing_ok=True)
                    refreshed += 1
            elif entry.kind == "v1":
                changed = False
                active_dir = self.game_root / "CustomMissions"
                disabled_dir = self.disabled_root / "v1"
                for relative_name in entry.files:
                    source_value = entry.source_map.get(relative_name.casefold(), "")
                    source = Path(source_value) if source_value else Path()
                    active = _safe_child(active_dir, active_dir / Path(relative_name))
                    if source_value and source.is_file() and active.is_file():
                        active.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, active)
                        disabled = _safe_child(disabled_dir, disabled_dir / Path(relative_name))
                        disabled.unlink(missing_ok=True)
                        changed = True
                refreshed += int(changed)
            else:
                source = Path(entry.source) if entry.source else Path()
                active = _safe_child(self.game_root / "CustomMissions2", Path(entry.target))
                if entry.source and source.is_dir() and active.is_dir():
                    self._replace_directory(source, active)
                    disabled = self.disabled_root / "v2" / entry.files[0]
                    if disabled.exists():
                        shutil.rmtree(disabled)
                    refreshed += 1
        self.scan()
        return refreshed

    def delete_dropin(self, entry_id: str) -> str:
        """Remove a user-imported item from repository, game, and isolation."""
        self._require_roots()
        if game_is_running():
            raise ModManagerError("请完全退出游戏后再删除 Mod")
        if entry_id not in self.entries:
            self.scan()
        entry = self.entries.get(entry_id)
        if entry is None or not entry.user_imported:
            raise ModManagerError("只能删除通过 Drop-in 收件箱导入的 Mod")

        if entry.kind == "plugin":
            source = Path(entry.source)
            target = _safe_child(self.game_root, Path(entry.target))
            target.unlink(missing_ok=True)
            target.with_name(target.name + ".disabled").unlink(missing_ok=True)
            if self._dropin_root_for(source) is not None:
                source.unlink(missing_ok=True)
                self._prune_empty_parents(source.parent, self._plugin_root_for(source))
        elif entry.kind == "v1":
            active_dir = self.game_root / "CustomMissions"
            disabled_dir = self.disabled_root / "v1"
            for relative_name in entry.files:
                active = _safe_child(active_dir, active_dir / Path(relative_name))
                disabled = _safe_child(disabled_dir, disabled_dir / Path(relative_name))
                active.unlink(missing_ok=True)
                disabled.unlink(missing_ok=True)
                source_value = entry.source_map.get(relative_name.casefold(), "")
                source = Path(source_value) if source_value else Path()
                if source_value and self._dropin_root_for(source) is not None:
                    source.unlink(missing_ok=True)
        else:
            source = Path(entry.source)
            active = _safe_child(self.game_root / "CustomMissions2", Path(entry.target))
            disabled = self.disabled_root / "v2" / entry.files[0]
            for folder in (active, disabled):
                if folder.exists():
                    shutil.rmtree(folder)
            if self._dropin_root_for(source) is not None and source.exists():
                shutil.rmtree(source)

        self.scan()
        return "已从仓库和游戏目录删除"

    @staticmethod
    def _prune_empty_parents(folder: Path, stop: Path | None) -> None:
        if stop is None:
            return
        stop_resolved = stop.resolve(strict=False)
        current = folder
        while current.resolve(strict=False) != stop_resolved:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

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
        return [path for path in root.rglob("*.json") if path.is_file() and not path.is_symlink()]

    @staticmethod
    def _v1_relative(root: Path, path: Path) -> str:
        return path.relative_to(root).as_posix()

    @classmethod
    def _v1_group_for(cls, root: Path, path: Path) -> str:
        relative = path.relative_to(root)
        if len(relative.parts) > 1:
            return relative.parts[0]
        return _v1_group(path.stem)

    def _scan_v1(self) -> list[ModEntry]:
        source_dirs = self._source_v1_dirs()
        active_dir = self.game_root / "CustomMissions"
        disabled_dir = self.disabled_root / "v1"
        groups: dict[str, dict[str, str]] = {}
        source_files: dict[str, Path] = {}
        for directory in source_dirs:
            for path in self._v1_files(directory):
                relative_name = self._v1_relative(directory, path)
                source_files.setdefault(relative_name.casefold(), path)
        for directory in (*source_dirs, active_dir, disabled_dir):
            for path in self._v1_files(directory):
                relative_name = self._v1_relative(directory, path)
                group = self._v1_group_for(directory, path)
                groups.setdefault(group, {}).setdefault(relative_name.casefold(), relative_name)
        result: list[ModEntry] = []
        for group, known in sorted(groups.items(), key=lambda item: item[0].casefold()):
            names = sorted(set(known.values()), key=str.casefold)
            active_count = sum((active_dir / Path(name)).is_file() for name in names)
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
            description = V2_DESCRIPTIONS.get(name.casefold(), description)
            result.append(ModEntry(
                id="v2|" + name, kind="v2", name=title,
                description=description, enabled=active.is_dir(), available=True,
                status="已启用" if active.is_dir() else "已停用",
                warning=SOFT_WARNINGS.get(name.casefold(), ""), files=[name],
                source=str(source), target=str(active),
                classification_key=name,
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
            source = Path(entry.source) if entry.source else None
            # In local-only mode the selected game directory is also the scan
            # root.  A disabled plug-in is therefore discovered as both the
            # recoverable copy and its own "source".  Do not unlink that file
            # before copying it; restoring the renamed DLL is the operation we
            # want in this case.
            if (
                source is not None
                and disabled.is_file()
                and source.resolve(strict=False) == disabled.resolve(strict=False)
            ):
                disabled.replace(target)
                return
            if source is not None and source.is_file():
                disabled.unlink(missing_ok=True)
                source_plugins = self._plugin_root_for(source)
                if source_plugins is not None and source.parent != source_plugins and source.parent.name.casefold() != "save":
                    bundle_target = target.parent
                    shutil.copytree(source.parent, bundle_target, dirs_exist_ok=True)
                else:
                    shutil.copy2(source, target)
                self._copy_plugin_resources(target.stem, source)
                return
            if disabled.is_file():
                disabled.replace(target)
                return
            raise ModManagerError("来源库中缺少插件文件")
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
        for relative_name in entry.files:
            active = _safe_child(active_dir, active_dir / Path(relative_name))
            disabled = _safe_child(disabled_dir, disabled_dir / Path(relative_name))
            source_value = entry.source_map.get(relative_name.casefold(), "")
            source = Path(source_value) if source_value else Path()
            if enabled:
                active.parent.mkdir(parents=True, exist_ok=True)
                if source_value and source.is_file():
                    shutil.copy2(source, active)
                    disabled.unlink(missing_ok=True)
                elif not active.exists() and disabled.is_file():
                    disabled.replace(active)
                elif not active.exists():
                    raise ModManagerError(f"缺少任务文件：{relative_name}")
            elif not enabled and active.is_file():
                disabled.parent.mkdir(parents=True, exist_ok=True)
                active.replace(disabled)

    def _toggle_v2(self, entry: ModEntry, enabled: bool) -> None:
        name = entry.files[0]
        source = Path(entry.source) if entry.source else Path()
        active = _safe_child(self.game_root / "CustomMissions2", self.game_root / "CustomMissions2" / name)
        disabled = _safe_child(self.disabled_root / "v2", self.disabled_root / "v2" / name)
        active.parent.mkdir(parents=True, exist_ok=True)
        disabled.parent.mkdir(parents=True, exist_ok=True)
        if enabled:
            if entry.source and source.is_dir():
                if disabled.exists():
                    shutil.rmtree(disabled)
                self._replace_directory(source, active)
            elif not active.exists() and disabled.is_dir():
                shutil.move(str(disabled), str(active))
            elif not active.exists():
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


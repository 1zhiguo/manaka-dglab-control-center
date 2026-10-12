"""Qt-facing backend for the production QML Manaka control center."""

from __future__ import annotations

import base64
import ctypes
import hashlib
import io
import json
import math
import os
import queue
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import qrcode
from PySide6.QtCore import QObject, Property, QLocale, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from manaka_dglab_bridge import DEFAULT_PORT, DGLabBridge
from manaka_dropin_importer import DropInModImporter
from manaka_9527_importer import Pack9527Error, Pack9527Importer
from manaka_mod_manager import ManakaModManager, ModManagerError
from manaka_trigger_engine import ManakaTriggerEngine, RollingPeakLimiter, TriggerFrame, clamp
from manaka_waveforms import (
    GAME_ACTION_TYPES,
    DEFAULT_WAVE_MAP,
    LEGACY_DEFAULT_WAVE_MAP,
    PRESETS,
    WaveformPreset,
    WaveformSelector,
    action_label,
    action_style,
    recommended_wave_for_action,
    sanitize_wave_map,
)
try:
    from .i18n import translate
    from .mod_catalog import build_mod_catalog
except ImportError:  # Direct source/packaged entry point.
    from i18n import translate
    from mod_catalog import build_mod_catalog


def windows_network_repair_script(lan_ip: str, port: int) -> str:
    """Build the narrowly scoped, user-confirmed Windows network repair script."""
    import ipaddress

    address = ipaddress.ip_address(str(lan_ip).strip())
    if not isinstance(address, ipaddress.IPv4Address) or address.is_loopback or address.is_link_local:
        raise ValueError("当前二维码没有可修复的局域网 IPv4 地址")
    safe_port = int(port)
    if not 1 <= safe_port <= 65535:
        raise ValueError("Socket 端口无效")
    rule_name = f"ManakaDGLab-TCP-{safe_port}"
    return f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationFramework
try {{
    $targetIp = '{address}'
    $port = {safe_port}
    $config = Get-NetIPConfiguration | Where-Object {{
        $_.IPv4Address.IPAddress -contains $targetIp
    }} | Select-Object -First 1
    if ($null -eq $config) {{ throw '找不到二维码对应的 Windows 网卡 / The selected network adapter is unavailable.' }}
    $profile = Get-NetConnectionProfile -InterfaceIndex $config.InterfaceIndex
    if ($profile.NetworkCategory -ne 'DomainAuthenticated') {{
        Set-NetConnectionProfile -InterfaceIndex $config.InterfaceIndex -NetworkCategory Private
    }}
    $rule = Get-NetFirewallRule -Name '{rule_name}' -ErrorAction SilentlyContinue
    if ($null -eq $rule) {{
        New-NetFirewallRule -Name '{rule_name}' -DisplayName 'Manaka DG-LAB TCP {safe_port}' `
            -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port -Profile Private | Out-Null
    }} else {{
        Set-NetFirewallRule -Name '{rule_name}' -Enabled True -Action Allow -Profile Private
    }}
    [System.Windows.MessageBox]::Show(
        '网络权限已修复，请返回 DG-LAB App 重新扫码。 / Network access repaired. Scan the QR code again.',
        'Manaka DG-LAB'
    ) | Out-Null
}} catch {{
    [System.Windows.MessageBox]::Show($_.Exception.Message, 'Manaka DG-LAB') | Out-Null
    exit 1
}}
""".strip()


def _load_app_version() -> str:
    """Read the build-time version while keeping source runs convenient."""

    if getattr(sys, "frozen", False):
        version_file = Path(getattr(sys, "_MEIPASS")) / "assets" / "VERSION"
    else:
        version_file = Path(__file__).with_name("VERSION")
    try:
        version = version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"
    return version or "dev"


APP_VERSION = _load_app_version()
AGREEMENT_VERSION = "2026-10-11-v2"
UDP_HOST = "127.0.0.1"
UDP_PORT = 45678
COMMAND_PORT = 45679
HUD_PORT = 45680
STALE_SECONDS = 0.75
DEFAULT_CUSTOM_POINTS = [0, 18, 48, 82, 100, 58, 20, 0, 0, 25, 68, 45, 15, 0, 0, 0]
RECOMMENDED_MODS = (
    {
        "id": "plugin|SFM_custom_mission.dll",
        "displayName": "CustomMission 1",
        "role": "V1 基础前置",
        "summary": "负责加载 CustomMissions 目录中的 V1 JSON 任务。启用任何 V1 任务前，应先启用它。",
        "accent": "cyan",
    },
    {
        "id": "plugin|SFM_custom_mission_v2.dll",
        "displayName": "CustomMission 2",
        "role": "V2 基础前置",
        "summary": "负责加载 CustomMissions2 目录中的 .code 脚本包。启用任何 V2 包前，应先启用它。",
        "accent": "violet",
    },
)
V1_MISSION_LOCATIONS = (
    {"name": "0 开头 · 真菜香大冒险", "area": "家中 / Tab", "location": "000 在家里冰箱前；其余任务会自动加入 Tab 任务列表。", "note": "高画质下“在人附近使用假阳具”容易使角色掉出地图。"},
    {"name": "admirer", "area": "住宅区", "location": "家门口左边。", "note": ""},
    {"name": "Alice's New Life 1", "area": "住宅区", "location": "家门口右边。", "note": ""},
    {"name": "alleyway_gambit", "area": "繁华街", "location": "从繁华街传送点直走，在第一个路口往左。", "note": ""},
    {"name": "Apart_BladderRace", "area": "公寓前", "location": "公寓前传送点右边的院子里。", "note": ""},
    {"name": "Apart_mission", "area": "住宅区", "location": "家门口正对面。", "note": ""},
    {"name": "ApartmentFun", "area": "公寓前", "location": "公寓前传送点左前方。", "note": ""},
    {"name": "blackmail 1–3", "area": "购物中心", "location": "1：一层传送点右边；2：二层上行自动扶梯出口；3：三层上行自动扶梯出口。", "note": ""},
    {"name": "Brat", "area": "住宅区", "location": "出家门后左边一排。", "note": ""},
    {"name": "cc 系列", "area": "家中 / Tab", "location": "起点在家里正中间；便利店任务从 Tab 任务列表查看。", "note": ""},
    {"name": "challenges", "area": "家中", "location": "家里沙发旁。", "note": "需要 BepInEx 插件 SFMCMextender。"},
    {"name": "City Center Tour", "area": "繁华街", "location": "繁华街传送点右边的货车旁。", "note": ""},
    {"name": "Condom shopping blackmail", "area": "住宅区", "location": "出家门后右边。", "note": ""},
    {"name": "Exorcist Maiden 1–2", "area": "购物中心 / 繁华街", "location": "1：购物中心一层传送点左前方；2：繁华街前往购物中心的入口处。", "note": ""},
    {"name": "ExtremeItemSearch", "area": "家中 / 全地图", "location": "从家里床边开始；之后要在各场景寻找并捡起掉落物品。", "note": ""},
    {"name": "floor-presentation", "area": "公寓前", "location": "公寓前传送点正前方。", "note": ""},
    {"name": "forgottenwallet", "area": "繁华街", "location": "蓝色招牌的海鲜酒场前。", "note": ""},
    {"name": "Go to a male classmate's house", "area": "住宅区", "location": "出家门时触发提示。", "note": ""},
    {"name": "Late Night Store Run", "area": "家中", "location": "电脑右后方的柜子。", "note": "需要 BepInEx 插件 SFM_EdgingPatch。"},
    {"name": "lockedout", "area": "住宅区", "location": "家门左边自动售货机背后那栋建筑的院子里。", "note": "两个 lockedout 版本不能同时启用。"},
    {"name": "manakasbathroomstreak", "area": "公园", "location": "公园厕所右边的路灯处。", "note": ""},
    {"name": "Mas marathon", "area": "家中", "location": "家里电脑后方。", "note": "第三个任务存在较严重的流程问题，建议谨慎启用。"},
    {"name": "Missing persons", "area": "住宅区", "location": "家门口左边。", "note": "如果提示不明确，可等待角色达到高潮继续流程。"},
    {"name": "modifications [randomEventMistress]", "area": "家中", "location": "家里床边。", "note": ""},
    {"name": "Nocturnal Summons", "area": "家中", "location": "家里电脑右后方的柜子前。", "note": ""},
    {"name": "octo 系列", "area": "住宅区", "location": "lost_bet、little_gift：出家门右边；grocery_shopping 1：出家门右边，之后跟随提示，第三段也可在住宅区前往便利店的入口处触发。", "note": ""},
    {"name": "Park Accident", "area": "公园", "location": "公园传送点左边。", "note": ""},
    {"name": "park_stroll", "area": "公园", "location": "公园女厕所入口处。", "note": "剧情似乎承接 octo_lost_bet，但原说明提示人物设定可能不一致。"},
    {"name": "pdd 系列", "area": "住宅区 / Tab", "location": "出家门触发提示；住宅区任务从 Tab 任务列表查看。", "note": ""},
    {"name": "school_adventure_combined", "area": "住宅区", "location": "家门口。", "note": ""},
    {"name": "SekiMission 系列", "area": "多地点 / Tab", "location": "大部分任务自动加入 Tab 任务列表；住宅区、繁华街、购物中心传送点附近各有一组全裸爬行任务。00AllMaps ClimacticFinale 在家门口正对面。", "note": ""},
    {"name": "slaveplayapartment", "area": "公寓前", "location": "公寓前传送点右前方。", "note": ""},
    {"name": "SlaveToFate 1", "area": "住宅区", "location": "家门口正对面。", "note": ""},
    {"name": "Stealth Ninja Action", "area": "家中", "location": "家里沙发旁。", "note": ""},
    {"name": "the curse of obscene book 1–4", "area": "住宅区 / 购物中心 / 家中", "location": "1–3：出家门左边；3-2：购物中心前往服装店传送点对面的自动售货机附近；4：家里冰箱旁。", "note": ""},
    {"name": "The Final Key", "area": "服装店", "location": "进入服装店时触发提示。", "note": ""},
    {"name": "UnknownPact", "area": "住宅区", "location": "家门口左边的石碑处。", "note": ""},
    {"name": "Warp 传送点", "area": "多地点", "location": "普通 Warp 点用于连接原本不相连的地图；WarpDT 会前往正常情况下无法到达的区域。", "note": "属于地图连接工具，不是普通剧情起点。"},
    {"name": "Working hours of the guards", "area": "住宅区", "location": "出家门时触发提示。", "note": ""},
    {"name": "Xposure 0–3", "area": "多地点", "location": "0：家里电脑右后方柜子前；1：出家门沿街道一直左转；2：家里床边；3-1：住宅区大马路旁红色邮箱附近；3-2：住宅区前往便利店入口处；3-3：公寓前传送点右边院子里。", "note": "不建议一次启用所有章节，否则罗盘会出现大量指针。"},
    {"name": "Yakuza's Punishment", "area": "繁华街", "location": "蓝色招牌的海鲜酒场前。", "note": ""},
)
V1_LOCATION_RULES = (
    (r"^基础地点任务包$", ("0 开头 · 真菜香大冒险",)),
    (r"^admirer$", ("admirer",)),
    (r"^alice's new life", ("Alice's New Life 1",)),
    (r"^alleyway", ("alleyway_gambit",)),
    (r"^apart$", ("Apart_BladderRace", "Apart_mission")),
    (r"^apartmentfun", ("ApartmentFun",)),
    (r"^blackmail", ("blackmail 1–3",)),
    (r"^brat$", ("Brat",)),
    (r"^cc$", ("cc 系列",)),
    (r"^challenges$", ("challenges",)),
    (r"^city center tour$", ("City Center Tour",)),
    (r"^condom shopping blackmail$", ("Condom shopping blackmail",)),
    (r"^exorcist maiden", ("Exorcist Maiden 1–2",)),
    (r"^extremeitemsearch", ("ExtremeItemSearch",)),
    (r"^floor-presentation$", ("floor-presentation",)),
    (r"^forgottenwallet$", ("forgottenwallet",)),
    (r"^go to a male classmate's house$", ("Go to a male classmate's house",)),
    (r"^late night store run$", ("Late Night Store Run",)),
    (r"^lockedout$", ("lockedout",)),
    (r"^manakasbathroomstreak$", ("manakasbathroomstreak",)),
    (r"^mas marathon$", ("Mas marathon",)),
    (r"^missing persons$", ("Missing persons",)),
    (r"^modifications \[randomeventmistress\]$", ("modifications [randomEventMistress]",)),
    (r"^nocturnal summons$", ("Nocturnal Summons",)),
    (r"^octo$", ("octo 系列",)),
    (r"^park$", ("park_stroll",)),
    (r"^park accident$", ("Park Accident",)),
    (r"^pdd$", ("pdd 系列",)),
    (r"^school$", ("school_adventure_combined",)),
    (r"^sekimission", ("SekiMission 系列",)),
    (r"^slaveplayapartment$", ("slaveplayapartment",)),
    (r"^slavetofate", ("SlaveToFate 1",)),
    (r"^stealth ninja action$", ("Stealth Ninja Action",)),
    (r"^the curse of obscene book", ("the curse of obscene book 1–4",)),
    (r"^the final key", ("The Final Key",)),
    (r"^unknownpact$", ("UnknownPact",)),
    (r"^warp", ("Warp 传送点",)),
    (r"^working hours of the guards$", ("Working hours of the guards",)),
    (r"^xposure$", ("Xposure 0–3",)),
    (r"^yakuza's punishment$", ("Yakuza's Punishment",)),
)
F95_CUSTOM_MISSIONS_THREAD = (
    "https://f95zone.to/threads/"
    "secret-flasher-manaka-custom-missions-1-2-1-version-2-4-0.263276/"
)
MOD_SOURCE_LINKS = (
    {
        "group": "内置任务来源",
        "name": "Custom Missions 原帖索引",
        "author": "F95Zone 社区作者",
        "reference": "主帖",
        "url": F95_CUSTOM_MISSIONS_THREAD,
        "summary": "CustomMission 1/2、任务与功能包的原始发布讨论入口。需要登录 F95Zone。",
    },
    {
        "group": "内置任务来源",
        "name": "Park Accident / admirer",
        "author": "请以原帖署名为准",
        "reference": "原帖索引",
        "url": F95_CUSTOM_MISSIONS_THREAD,
        "summary": "整理清单没有给出这两项的可靠作者链接，因此只提供原帖索引，不擅自署名。",
    },
    {
        "group": "内置任务来源",
        "name": "Slave To Fate",
        "author": "Tghyt",
        "reference": "F95 #147",
        "url": F95_CUSTOM_MISSIONS_THREAD + "page-8",
        "summary": "当前内置 V1 文件名为 SlaveToFate1；链接打开原帖对应页附近。",
    },
    {
        "group": "内置任务来源",
        "name": "Auto Brightness",
        "author": "Suzutsuki117",
        "reference": "F95 #2014",
        "url": F95_CUSTOM_MISSIONS_THREAD + "page-101",
        "summary": "按地图调整亮度的 V2 功能包。",
    },
    {
        "group": "内置任务来源",
        "name": "Exposure Urges",
        "author": "raptorr64",
        "reference": "F95 #2279",
        "url": F95_CUSTOM_MISSIONS_THREAD + "page-114",
        "summary": "当前内置目录名为 ExhibUrges；链接打开原始任务条目附近。",
    },
    {
        "group": "中文用户资源",
        "name": "user9527 中文汉化整合",
        "author": "user9527",
        "reference": "仅在 F95Zone 发布",
        "url": F95_CUSTOM_MISSIONS_THREAD + "post-20360819",
        "summary": "请登录原帖查找 user9527 的发布内容；本软件不转载、不镜像该整合包。",
    },
    {
        "group": "中文用户资源",
        "name": "user9527 作者下载目录",
        "author": "user9527",
        "reference": "Mega",
        "url": "https://mega.nz/folder/QAEiCThB#V3T3H3c60jmQ_Pqm2R2eRA",
        "summary": "作者在原帖说明中提供的目录；使用与更新规则仍以 F95Zone 原帖为准。",
    },
    {
        "group": "扩展入口",
        "name": "地图导入器",
        "author": "F95Zone 作者",
        "reference": "原帖",
        "url": "https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-2-1.263276/post-20766048",
        "summary": "第三方地图导入工具；请在原帖确认版本与依赖。",
    },
    {
        "group": "扩展入口",
        "name": "lrlVIbe",
        "author": "F95Zone 作者",
        "reference": "原帖",
        "url": "https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-1-1.263276/post-20537701",
        "summary": "成人玩具外设插件；本软件仅提供作者页面入口。",
    },
    {
        "group": "扩展入口",
        "name": "SecretFlasherManakaVR",
        "author": "F95Zone 作者",
        "reference": "原帖",
        "url": "https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-1-1.263276/post-20565081",
        "summary": "VR 外设插件；本软件仅提供作者页面入口。",
    },
    {
        "group": "扩展入口",
        "name": "任务管理 / 提示器",
        "author": "F95Zone 作者",
        "reference": "原帖",
        "url": "https://f95zone.to/threads/secret-flasher-manaka-custom-missions-1-2-1-version-2-2-1.263276/post-20924939",
        "summary": "任务管理与提示工具；请在原帖查看最新兼容信息。",
    },
    {
        "group": "扩展入口",
        "name": "PeanutsZheng ModManager",
        "author": "PeanutsZheng",
        "reference": "GitHub",
        "url": "https://github.com/PeanutsZheng/ModManager/releases",
        "summary": "另一款开源插件管理器；适合希望比较不同管理方案的用户。",
    },
    {
        "group": "扩展入口",
        "name": "中文开发者 Telegram 群组",
        "author": "社区",
        "reference": "Telegram",
        "url": "https://t.me/+jpMci4Z4pdRjZGE1",
        "summary": "原说明中列出的第三方开发讨论群组。",
    },
)
ALLOWED_EXTERNAL_HOSTS = {
    "f95zone.to",
    "github.com",
    "mega.nz",
    "t.me",
}
SUPPORTED_GAME_HASHES = {
    "GameAssembly.dll": "6003033049ac32e8712dc4101382534e21d65b97100c167ebec6bbca1462c18d",
    "SecretFlasherManaka_Data/il2cpp_data/Metadata/global-metadata.dat": "457203754abe77b346fd98086a5c787bd41088d808cc81b1d4e2cae5b85c72c8",
}
USER_AGREEMENT = """Manaka × DG-LAB 使用协议与风险知情确认

1. 本软件仅供具有完全民事行为能力的成年人自愿使用，用于把游戏事件转换为第三方电刺激设备控制指令。它不是医疗器械，也不提供医疗建议。

2. 电刺激可能造成疼痛、皮肤刺激或灼伤、肌肉不自主收缩、惊吓、跌倒及其他已知或未知伤害。无线网络、蓝牙、游戏插件、操作系统或第三方 App 可能出现延迟、重复、丢包、错误识别或停止按钮失效。

3. 使用前必须阅读并遵守 DG-LAB 主机、电极与 App 的官方说明。存在心脏或神经系统疾病、植入式电子设备、妊娠、感觉障碍、皮肤破损，或对自身健康状况不确定时，请勿使用，除非已经获得合格医疗专业人员的明确许可。

4. 从低强度开始，确保随时能够接触实体主机和断开电源。不要在驾驶、站立、洗浴、睡眠、意识不清、饮酒或服用影响判断能力的物质后使用；不要把电极放在设备说明禁止的位置。

5. “安全硬上限”只是软件命令的上限，不代表医学安全值，也不能替代设备实体保护。提高上限、使用自定义波形或让他人控制前，应重新进行低强度确认。出现疼痛、麻木、灼热、眩晕、心悸或其他不适，应立即停止并断开设备，必要时寻求医疗帮助。

6. 本软件按现状提供。在适用法律允许的范围内，开发者不对因用户设置、第三方硬件或软件、网络、游戏修改、错误操作或违反说明而产生的损失承担责任。

7. 点击“我已阅读并同意”表示你已理解上述风险并自愿承担在正确使用范围内仍可能存在的风险。不同意请直接退出应用，软件不会启动遥测监听或 DG-LAB Socket 服务。"""

USER_AGREEMENT_EN = """Manaka × DG-LAB User Agreement and Risk Acknowledgement

1. This software is intended only for consenting adults with full legal capacity. It converts game events into control commands for a third-party electrical stimulation device. It is not a medical device and does not provide medical advice.

2. Electrical stimulation may cause pain, skin irritation or burns, involuntary muscle contraction, shock, falls, and other known or unknown injury. Wireless networks, Bluetooth, game plugins, the operating system, or third-party apps may introduce latency, duplicated or lost packets, incorrect detection, or failure of a stop command.

3. Before use, read and follow the official instructions for the DG-LAB controller, electrodes, and app. Do not use if you have a cardiac or neurological condition, an implanted electronic device, are pregnant, have impaired sensation or broken skin, or are unsure about your health, unless a qualified medical professional has explicitly approved use.

4. Start at low strength and keep the physical controller and power disconnect within immediate reach. Do not use while driving, standing, bathing, sleeping, unconscious, intoxicated, or after taking substances that impair judgment. Do not place electrodes in locations prohibited by the device instructions.

5. The “safety hard cap” only limits software commands. It is not a medically safe value and does not replace physical device protections. Re-test at low strength after raising the cap, using a custom waveform, or allowing another person to control the device. Stop and disconnect immediately if you experience pain, numbness, burning, dizziness, palpitations, or other discomfort, and seek medical help when appropriate.

6. This software is provided as-is. To the maximum extent permitted by applicable law, the developer is not liable for loss arising from user settings, third-party hardware or software, networks, game modifications, misuse, or failure to follow instructions.

7. Clicking “I Have Read and Agree” confirms that you understand these risks and voluntarily accept risks that may remain during proper use. If you disagree, exit the application. Telemetry listening and DG-LAB Socket services will not start."""


def app_data_dir() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "ManakaDGLab"


def config_path() -> Path:
    return app_data_dir() / "config.json"


def waveform_library_dir() -> Path:
    return app_data_dir() / "waveforms"


def waveform_file_stem(name: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(name)).strip().strip(".")
    clean = re.sub(r"\s+", " ", clean)[:48].strip()
    return clean or "未命名波形"


def load_config() -> dict:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def update_config(values: dict) -> None:
    current = load_config()
    current.update(values)
    target = config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")


def build_hud_packet(
    sequence: int,
    *,
    visible: bool,
    connected: bool,
    active: bool,
    strength_a: float,
    strength_b: float,
    pulse_a: float,
    pulse_b: float,
) -> bytes:
    """Build the small local-only packet consumed by the in-game HUD plugin."""

    values = (
        "MANAKA_HUD_V1",
        str(max(0, int(sequence))),
        "1" if visible else "0",
        "1" if connected else "0",
        "1" if active else "0",
        f"{clamp(float(strength_a), 0, 100):.2f}",
        f"{clamp(float(strength_b), 0, 100):.2f}",
        f"{clamp(float(pulse_a), 0, 1):.3f}",
        f"{clamp(float(pulse_b), 0, 1):.3f}",
        "END",
    )
    return "|".join(values).encode("ascii")


def bundled_plugin_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "assets" / "ManakaDGLabTelemetry.dll"
    return Path(__file__).resolve().parents[2] / "manaka_telemetry" / "bin" / "ManakaDGLabTelemetry.dll"


def bundled_bepinex_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "assets" / "bepinex_v113"
    return Path(__file__).resolve().parents[2] / "installer_payload" / "bepinex_v113"


def bundled_guide_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "assets" / "dglab_guide"
    return Path(__file__).resolve().parents[1] / "assets" / "dglab_guide"


def dropin_mods_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "dropin_mods"
    return Path(__file__).resolve().parents[2] / "dropin_mods"


def validate_game_folder(folder: Path) -> tuple[bool, str]:
    if not (folder / "SecretFlasherManaka.exe").is_file():
        return False, "请选择能直接看到 SecretFlasherManaka.exe 的游戏根目录"
    if not (folder / "GameAssembly.dll").is_file():
        return False, "缺少 GameAssembly.dll，这不是完整的游戏根目录"
    if not (folder / "BepInEx" / "core" / "BepInEx.Core.dll").is_file():
        return True, "已检测到纯原版；点击安装即可自动配置 BepInEx 6 与遥测插件"
    return True, "游戏与 BepInEx 已就绪（遥测插件无需任务 Mod）"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_supported_game_build(folder: Path) -> tuple[bool, str]:
    for relative, expected in SUPPORTED_GAME_HASHES.items():
        target = folder / Path(relative)
        if not target.is_file():
            return False, f"缺少游戏文件：{relative}"
        if sha256_file(target).lower() != expected:
            return False, "当前只验证了 SecretFlasherManaka v1.1.3；该副本文件版本不匹配"
    return True, "SecretFlasherManaka v1.1.3"


class TelemetryWorker(threading.Thread):
    def __init__(self, messages: queue.Queue) -> None:
        super().__init__(name="manaka-qml-telemetry", daemon=True)
        self.messages = messages
        self.stop_event = threading.Event()
        self.receiver: socket.socket | None = None

    def run(self) -> None:
        try:
            self.receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.receiver.bind((UDP_HOST, UDP_PORT))
            self.receiver.settimeout(0.2)
            self.messages.put(("listener", "ready"))
            while not self.stop_event.is_set():
                try:
                    payload, _ = self.receiver.recvfrom(65535)
                except socket.timeout:
                    continue
                try:
                    decoded = json.loads(payload.decode("utf-8"))
                    packet_type = decoded.get("type")
                    if packet_type == "progressResult":
                        kind = "progress_result"
                    else:
                        kind = "telemetry"
                    self.messages.put((kind, decoded))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    self.messages.put(("listener", f"遥测数据格式错误：{error}"))
        except Exception as error:  # socket ownership and shutdown failures are surfaced in the UI
            if not self.stop_event.is_set():
                self.messages.put(("listener", f"监听启动失败：{error}"))
        finally:
            if self.receiver is not None:
                self.receiver.close()

    def stop(self) -> None:
        self.stop_event.set()
        if self.receiver is not None:
            try:
                self.receiver.close()
            except OSError:
                pass


class ControlCenterBackend(QObject):
    stateChanged = Signal()
    statusChanged = Signal()
    vitalsChanged = Signal()
    contextChanged = Signal()
    outputChanged = Signal()
    connectionChanged = Signal()
    progressChanged = Signal()
    waveChanged = Signal()
    configChanged = Signal()
    logsChanged = Signal()
    toastRequested = Signal(str, str)
    exitRequested = Signal()

    def __init__(self, *, demo: bool = False, language: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.demo_mode = bool(demo)
        self.messages: queue.Queue = queue.Queue()
        self.saved = load_config()
        self.theme_name = "light" if self.saved.get("theme") == "light" else "dark"
        saved_language = str(language or self.saved.get("language", "")).lower()
        if saved_language not in {"zh", "en"}:
            saved_language = "zh" if QLocale.system().name().lower().startswith("zh") else "en"
        self.language_name = saved_language
        self.agreement_accepted_value = bool(
            demo or self.saved.get("agreement_version") == AGREEMENT_VERSION
        )

        self.engine = ManakaTriggerEngine(
            max_strength=float(self.saved.get("hard_cap", 30)),
            min_strength=float(self.saved.get("min_strength", 5)),
            output_max=float(self.saved.get("output_max", 30)),
            trigger_bpm=float(self.saved.get("trigger_bpm", 90)),
            full_bpm=float(self.saved.get("full_bpm", 160)),
        )
        self.trigger_bpm_value = int(self.engine.trigger_bpm)
        self.full_bpm_value = int(self.engine.full_bpm)
        self.min_strength_value = int(self.engine.min_strength)
        self.output_max_value = int(self.engine.output_max)
        self.hard_cap_value = int(self.engine.hard_cap)
        # HUD is enabled by default for the first run; the visible control-center
        # switch persists an explicit opt-out.
        self.game_hud_enabled_value = bool(self.saved.get("game_hud_enabled", True))
        self.hud_sequence = 0
        self.hud_last_sent = 0.0
        self.ui_last_telemetry_emit = 0.0
        self.ui_page_index = 0
        try:
            self.hud_socket: socket.socket | None = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except OSError:
            self.hud_socket = None

        self.wave_mode_value = "fixed" if self.saved.get("wave_mode") == "fixed" else "smart"
        fixed = str(self.saved.get("fixed_wave", "official_heartbeat"))
        self.fixed_wave_value = fixed if fixed in PRESETS or fixed == "custom" else "official_heartbeat"
        saved_map = self.saved.get("wave_map", DEFAULT_WAVE_MAP)
        if saved_map == LEGACY_DEFAULT_WAVE_MAP:
            saved_map = DEFAULT_WAVE_MAP
        self.wave_map_value = sanitize_wave_map(saved_map)
        if self.wave_map_value.get("peak") == "burst":
            self.wave_map_value["peak"] = "climax"
        points = self.saved.get("custom_wave_points")
        if not isinstance(points, list) or len(points) != 16:
            points = DEFAULT_CUSTOM_POINTS
        self.custom_name_value = str(self.saved.get("custom_wave_name", "我的波形")).strip() or "我的波形"
        self.custom_points_value = [int(clamp(float(value), 0, 100)) for value in points]
        self.custom_frequency_value = int(clamp(float(self.saved.get("custom_wave_frequency", 92)), 10, 240))
        self.custom_wave_library_value = self._read_custom_wave_library()
        saved_actions = self.saved.get("known_actions", [])
        if not isinstance(saved_actions, list):
            saved_actions = []
        self.known_actions_value = list(
            dict.fromkeys(
                list(GAME_ACTION_TYPES)
                + [str(value).strip() for value in saved_actions if str(value).strip() not in {"", "None"}]
            )
        )
        saved_action_map = self.saved.get("action_wave_map", {})
        if not isinstance(saved_action_map, dict):
            saved_action_map = {}
        self.action_wave_map_value = {
            str(action): str(wave_key)
            for action, wave_key in saved_action_map.items()
            if str(action).strip()
            and self._is_assignable_wave_key(str(wave_key))
        }
        self.wave_selector = WaveformSelector(hold_seconds=0.8)
        self.peak_limiter = RollingPeakLimiter(window_ms=5000, maximum_rise=15)

        saved_folder = str(self.saved.get("game_folder", ""))
        self.game_folder_value = saved_folder if Path(saved_folder).is_dir() else ""
        self.game_status_value = "尚未检查"
        # The manager now has one clear scope: the selected game's installed
        # and disabled files. External packs enter through Drop-in or a guided
        # importer instead of becoming a second scan source.
        self.mod_source_folder_value = self.game_folder_value
        self.mod_inventory_value: list[dict] = []
        self.loaded_mod_inventory_value: list[dict] = []
        self.recommended_mod_inventory_value: list[dict] = self._recommended_mods([])
        self.mod_status_value = "选择游戏目录后即可管理本地 Mod"
        self.mod_summary_value = "尚未扫描"
        self.mod_manager: ManakaModManager | None = None
        self.pack9527_importer = Pack9527Importer()
        self.pack9527_folder_value = ""
        self.pack9527_status_value = "尚未选择 9527 整合包"
        self.pack9527_analysis_value: dict = {}
        self.pack9527_backup_value = ""
        self.dropin_importer = DropInModImporter(dropin_mods_path())
        self.dropin_status_value = "把 Mod 放进 incoming，然后点击导入"
        try:
            self.dropin_importer.ensure_layout()
        except OSError as error:
            self.dropin_status_value = f"Drop-in 目录不可写：{error}"
        self.telemetry_status_value = "演示模式" if demo else "正在准备监听…"
        self.device_status_value = "演示设备已连接" if demo else "等待手机扫码"
        self.device_connected_value = bool(demo)
        self.auto_output_enabled = bool(demo)
        self.server_ready_value = bool(demo)
        self.lan_address_value = "192.168.x.x:9999" if demo else "正在准备…"
        self.lan_addresses_value = ["192.168.x.x"] if demo else []
        self.qr_source_value = ""

        self.heart_rate_value = 128.0 if demo else 0.0
        self.alert_level_value = 32.0 if demo else 0.0
        self.excitement_value = 67.0 if demo else 0.0
        self.current_rp_value = 12540.0 if demo else 0.0
        self.expose_exp_value = 3280 if demo else 0
        self.current_save_slot_value = 1 if demo else -1
        self.progress_editor_status_value = "演示模式" if demo else "等待游戏载入存档"
        self.pending_progress_id = ""
        self.pending_progress_deadline = 0.0
        self.stage_value = "Stage02" if demo else "—"
        self.action_value = "Walking" if demo else "None"
        self.last_packet: dict = {}
        self.last_receive = time.monotonic() if demo else 0.0
        self.last_game_ms: int | None = None
        self.last_action = "None"
        self.stale_reported = False
        self.safety_wait_reason = ""
        self.current_frame = self.engine.force_safe_cut("startup")
        self.current_wave_a: WaveformPreset | None = PRESETS["official_heartbeat"] if demo else None
        self.current_wave_b: WaveformPreset | None = PRESETS["official_tide"] if demo else None
        self.current_output_a = 18.0 if demo else 0.0
        self.current_output_b = 7.0 if demo else 0.0
        self.log_lines: list[str] = []

        self.worker: TelemetryWorker | None = None
        self.bridge: DGLabBridge | None = None
        self.runtime_started = False
        if not demo and self.agreement_accepted_value:
            self._start_runtime()
        elif not demo:
            self.telemetry_status_value = "等待协议确认"
            self.device_status_value = "同意使用协议后才会启动连接"
            self._log("等待用户阅读并同意风险协议；网络和设备服务未启动")
        else:
            self._log("视觉演示模式：不会连接游戏、Socket 或设备")

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(50)
        self.poll_timer.timeout.connect(self._poll)
        self.poll_timer.start()
        self.demo_phase = 0.0
        self.check_game()
        if self.mod_source_folder_value:
            self.scan_mods(show_error=False)

    def _read_custom_wave_library(self) -> list[dict]:
        directory = waveform_library_dir()
        try:
            files = sorted(directory.glob("*.json"), key=lambda value: value.name.casefold())
        except OSError:
            return []
        entries: list[dict] = []
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                points = data.get("points")
                if not isinstance(points, list) or len(points) != 16:
                    continue
                clean_points = [int(clamp(float(value), 0, 100)) for value in points]
                frequency = int(clamp(float(data.get("frequency", 92)), 10, 240))
                name = str(data.get("name", path.stem)).strip() or path.stem
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
            entries.append(
                {
                    "id": path.name,
                    "key": "library:" + path.stem,
                    "name": name,
                    "description": self._t("保存的 16 点自定义包络"),
                    "bestFor": self._t("载入后可编辑并用于固定或智能策略"),
                    "color": "#59DCE7",
                    "points": clean_points,
                    "frequency": frequency,
                    "source": "我的波形库",
                    "group": "custom",
                    "feelScale": 100,
                }
            )
        return entries

    def _library_entry(self, file_id: str) -> dict | None:
        return next((entry for entry in self.custom_wave_library_value if entry.get("id") == file_id), None)

    def _library_entry_by_key(self, wave_key: str) -> dict | None:
        return next((entry for entry in self.custom_wave_library_value if entry.get("key") == wave_key), None)

    def _is_assignable_wave_key(self, wave_key: str) -> bool:
        return wave_key == "off" or wave_key in PRESETS or self._library_entry_by_key(wave_key) is not None

    def _waveform_from_key(self, wave_key: str) -> WaveformPreset | None:
        if wave_key == "off":
            return None
        if wave_key in PRESETS:
            return PRESETS[wave_key]
        entry = self._library_entry_by_key(wave_key)
        if entry is None:
            return None
        return WaveformPreset(
            str(entry["key"]),
            str(entry["name"]),
            "保存的自定义包络",
            "由用户分配的动作类型",
            str(entry["color"]),
            tuple(int(value) for value in entry["points"]),
            (int(entry["frequency"]),),
            source="我的波形库",
        )

    def _next_custom_waveform_name(self) -> str:
        prefix = self._t("自定义波形")
        used_numbers: set[int] = set()
        for entry in self.custom_wave_library_value:
            match = re.fullmatch(
                r"(?:自定义波形|Custom Wave)\s+(\d+)",
                str(entry.get("name", "")).strip(),
                flags=re.IGNORECASE,
            )
            if match:
                used_numbers.add(int(match.group(1)))
        number = 1
        while number in used_numbers:
            number += 1
        return f"{prefix} {number}"

    def _selected_action_wave_key(self, action: str) -> str:
        selected = self.action_wave_map_value.get(action, recommended_wave_for_action(action))
        return selected if self._is_assignable_wave_key(selected) else recommended_wave_for_action(action)

    def _display_custom_wave_name(self) -> str:
        if self.custom_name_value in {"我的波形", "My Wave"}:
            return self._t("我的波形")
        return self.custom_name_value

    # ----- Generic properties -------------------------------------------------
    @Property(str, constant=True)
    def version(self) -> str:
        return APP_VERSION

    @Property(bool, constant=True)
    def demoMode(self) -> bool:
        return self.demo_mode

    @Property(bool, notify=configChanged)
    def agreementAccepted(self) -> bool:
        return self.agreement_accepted_value

    @Property(str, notify=configChanged)
    def agreementText(self) -> str:
        return USER_AGREEMENT_EN if self.language_name == "en" else USER_AGREEMENT

    @Property(str, notify=configChanged)
    def theme(self) -> str:
        return self.theme_name

    @Property(str, notify=configChanged)
    def language(self) -> str:
        return self.language_name

    @Property(bool, notify=statusChanged)
    def telemetryOnline(self) -> bool:
        return self.demo_mode or (self.last_receive > 0 and time.monotonic() - self.last_receive < STALE_SECONDS)

    @Property(str, notify=statusChanged)
    def telemetryStatus(self) -> str:
        return self._t(self.telemetry_status_value)

    @Property(bool, notify=statusChanged)
    def deviceConnected(self) -> bool:
        return self.device_connected_value

    @Property(bool, notify=statusChanged)
    def outputPaused(self) -> bool:
        return self.device_connected_value and not self.auto_output_enabled

    @Property(bool, notify=statusChanged)
    def safetyIdle(self) -> bool:
        return bool(self.safety_wait_reason)

    @Property(str, notify=statusChanged)
    def deviceStatus(self) -> str:
        return self._t(self.device_status_value)

    @Property(bool, notify=connectionChanged)
    def serverReady(self) -> bool:
        return self.server_ready_value

    @Property(str, notify=connectionChanged)
    def lanAddress(self) -> str:
        return self.lan_address_value

    @Property("QVariantList", notify=connectionChanged)
    def lanAddresses(self) -> list[str]:
        return list(self.lan_addresses_value)

    @Property(str, notify=connectionChanged)
    def qrSource(self) -> str:
        return self.qr_source_value

    @Property(float, notify=vitalsChanged)
    def heartRate(self) -> float:
        return self.heart_rate_value

    @Property(float, notify=vitalsChanged)
    def alertLevel(self) -> float:
        return self.alert_level_value

    @Property(float, notify=vitalsChanged)
    def excitement(self) -> float:
        return self.excitement_value

    @Property(str, notify=contextChanged)
    def stage(self) -> str:
        return self.stage_value

    @Property(str, notify=contextChanged)
    def action(self) -> str:
        return self.action_value

    @Property(str, notify=contextChanged)
    def actionDisplay(self) -> str:
        return action_label(self.action_value, self.language_name)

    @Property(float, notify=progressChanged)
    def currentRp(self) -> float:
        return self.current_rp_value

    @Property(int, notify=progressChanged)
    def exposeExp(self) -> int:
        return self.expose_exp_value

    @Property(int, notify=progressChanged)
    def currentSaveSlot(self) -> int:
        return self.current_save_slot_value

    @Property(str, notify=progressChanged)
    def progressEditorStatus(self) -> str:
        return self._t(self.progress_editor_status_value)

    @Property(bool, notify=progressChanged)
    def canEditProgress(self) -> bool:
        if self.demo_mode:
            return True
        return self.telemetryOnline and bool(self.last_packet.get("paused", False)) and self.current_save_slot_value >= 0

    @Property(str, constant=True)
    def saveBackupFolder(self) -> str:
        return str(app_data_dir() / "save_backups")

    @Property(float, notify=outputChanged)
    def outputA(self) -> float:
        return self.current_output_a if self.auto_output_enabled and not self.safety_wait_reason else 0.0

    @Property(float, notify=outputChanged)
    def outputB(self) -> float:
        return self.current_output_b if self.auto_output_enabled and not self.safety_wait_reason else 0.0

    @Property(str, notify=waveChanged)
    def waveAName(self) -> str:
        return self._t(self.current_wave_a.name if self.current_wave_a else "待机")

    @Property(str, notify=waveChanged)
    def waveBName(self) -> str:
        return self._t(self.current_wave_b.name if self.current_wave_b else "待机")

    @Property("QVariantList", notify=waveChanged)
    def waveAPoints(self) -> list[int]:
        return list(self.current_wave_a.amplitudes) if self.current_wave_a else [0, 0, 0, 0]

    @Property("QVariantList", notify=waveChanged)
    def waveBPoints(self) -> list[int]:
        return list(self.current_wave_b.amplitudes) if self.current_wave_b else [0, 0, 0, 0]

    @Property(bool, notify=configChanged)
    def gameHudEnabled(self) -> bool:
        return self.game_hud_enabled_value

    # ----- Settings properties ------------------------------------------------
    @Property(str, notify=configChanged)
    def gameFolder(self) -> str:
        return self.game_folder_value

    @Property(str, notify=configChanged)
    def gameStatus(self) -> str:
        return self._t(self.game_status_value)

    @Property(str, notify=configChanged)
    def modSourceFolder(self) -> str:
        return self.mod_source_folder_value

    @Property("QVariantList", notify=configChanged)
    def modInventory(self) -> list[dict]:
        return list(self.mod_inventory_value)

    @Property("QVariantList", notify=configChanged)
    def loadedModInventory(self) -> list[dict]:
        return list(self.loaded_mod_inventory_value)

    @Property("QVariantList", notify=configChanged)
    def recommendedModInventory(self) -> list[dict]:
        return list(self.recommended_mod_inventory_value)

    @Property("QVariantList", notify=configChanged)
    def modSourceLinks(self) -> list[dict]:
        return build_mod_catalog(self.language_name)

    @Property("QVariantList", constant=True)
    def v1MissionLocations(self) -> list[dict]:
        return [dict(item) for item in V1_MISSION_LOCATIONS]

    @Property(str, notify=configChanged)
    def modStatus(self) -> str:
        return self._t(self.mod_status_value)

    @Property(str, notify=configChanged)
    def modSummary(self) -> str:
        return self._t(self.mod_summary_value)

    @Property(str, constant=True)
    def dropInFolder(self) -> str:
        return str(self.dropin_importer.incoming)

    @Property(str, notify=configChanged)
    def dropInStatus(self) -> str:
        return self._t(self.dropin_status_value)

    @Property(str, notify=configChanged)
    def pack9527Folder(self) -> str:
        return self.pack9527_folder_value

    @Property(str, notify=configChanged)
    def pack9527Status(self) -> str:
        return self._t(self.pack9527_status_value)

    @Property("QVariantMap", notify=configChanged)
    def pack9527Analysis(self) -> dict:
        return dict(self.pack9527_analysis_value)

    @Property(bool, notify=configChanged)
    def pack9527Ready(self) -> bool:
        return bool(self.pack9527_analysis_value.get("ready"))

    @Property(str, notify=configChanged)
    def pack9527Backup(self) -> str:
        return self.pack9527_backup_value

    @Property(int, notify=configChanged)
    def triggerBpm(self) -> int:
        return self.trigger_bpm_value

    @Property(int, notify=configChanged)
    def fullBpm(self) -> int:
        return self.full_bpm_value

    @Property(int, notify=configChanged)
    def minStrength(self) -> int:
        return self.min_strength_value

    @Property(int, notify=configChanged)
    def outputMax(self) -> int:
        return self.output_max_value

    @Property(int, notify=configChanged)
    def hardCap(self) -> int:
        return self.hard_cap_value

    @Property(str, notify=configChanged)
    def waveMode(self) -> str:
        return self.wave_mode_value

    @Property(str, notify=configChanged)
    def fixedWave(self) -> str:
        return self.fixed_wave_value

    @Property("QVariantMap", notify=configChanged)
    def waveMap(self) -> dict[str, str]:
        return dict(self.wave_map_value)

    @Property("QVariantList", notify=configChanged)
    def customPoints(self) -> list[int]:
        return list(self.custom_points_value)

    @Property(str, notify=configChanged)
    def customName(self) -> str:
        return self._display_custom_wave_name()

    @Property(int, notify=configChanged)
    def customFrequency(self) -> int:
        return self.custom_frequency_value

    @Property("QVariantList", notify=configChanged)
    def presets(self) -> list[dict]:
        values = [
            {
                "key": preset.key,
                "name": self._t(preset.name),
                "description": self._t(preset.description),
                "bestFor": self._t(preset.best_for),
                "color": preset.color,
                "points": list(preset.amplitudes),
                "frequency": int(round(sum(preset.frequency_codes) / len(preset.frequency_codes))),
                "source": self._t(preset.source),
                "group": "official" if preset.key.startswith("official_") else "builtin",
                "feelScale": int(round(preset.feel_scale * 100)),
            }
            for preset in PRESETS.values()
        ]
        values.append(
            {
                "key": "custom",
                "name": self._display_custom_wave_name(),
                "description": self._t("自定义 16 点包络"),
                "bestFor": self._t("由用户自行分配"),
                "color": "#59DCE7",
                "points": list(self.custom_points_value),
                "frequency": self.custom_frequency_value,
                "source": self._t("用户自定义"),
                "group": "custom",
                "feelScale": 100,
            }
        )
        return values

    @Property("QVariantList", notify=configChanged)
    def officialPresets(self) -> list[dict]:
        return [value for value in self.presets if str(value.get("key", "")).startswith("official_")]

    @Property("QVariantList", notify=configChanged)
    def waveformCatalog(self) -> list[dict]:
        return [value for value in self.presets if value.get("key") != "custom"] + list(
            self.custom_wave_library_value
        )

    @Property("QVariantList", notify=configChanged)
    def savedCustomWaveforms(self) -> list[dict]:
        return list(self.custom_wave_library_value)

    @Property(str, notify=configChanged)
    def nextCustomWaveformName(self) -> str:
        return self._next_custom_waveform_name()

    @Property("QVariantList", notify=configChanged)
    def assignableWaveforms(self) -> list[dict]:
        values = [
            {
                "key": "off",
                "name": self._t("关闭 B 通道"),
                "description": self._t("这个动作不产生动作通道输出"),
                "color": "#667389",
                "points": [0, 0, 0, 0],
                "frequency": 0,
                "group": "off",
            }
        ]
        values.extend(value for value in self.presets if value.get("key") != "custom")
        values.extend(self.custom_wave_library_value)
        return values

    @Property("QVariantList", notify=configChanged)
    def actionWaveMappings(self) -> list[dict]:
        options = {str(item["key"]): item for item in self.assignableWaveforms}
        result: list[dict] = []
        for action in self.known_actions_value:
            selected = self._selected_action_wave_key(action)
            option = options.get(selected, options["off"])
            style = action_style(action)
            style_label = {"off": "普通交互", "static": "静态姿势", "rhythmic": "规律动作"}[style]
            result.append(
                {
                    "action": action,
                    "actionLabel": action_label(action, self.language_name),
                    "waveKey": selected,
                    "waveName": str(option.get("name", selected)),
                    "style": style,
                    "styleLabel": self._t(style_label),
                    "points": list(option.get("points", [0, 0, 0, 0])),
                    "color": str(option.get("color", "#667389")),
                    "isOverride": action in self.action_wave_map_value,
                }
            )
        return result

    @Property(str, constant=True)
    def waveformLibraryFolder(self) -> str:
        return str(waveform_library_dir())

    @Property("QVariantList", constant=True)
    def guideSources(self) -> list[str]:
        directory = bundled_guide_dir()
        names = ["step1_socket.png", "step2_initialize.png", "step3_connect_server.png", "step4_camera_scan.png"]
        return [QUrl.fromLocalFile(str(directory / name)).toString() for name in names]

    @Property("QVariantList", notify=logsChanged)
    def logs(self) -> list[str]:
        values: list[str] = []
        for line in self.log_lines:
            if "  " in line:
                stamp, message = line.split("  ", 1)
                values.append(f"{stamp}  {self._t(message)}")
            else:
                values.append(self._t(line))
        return values

    # ----- QML actions ---------------------------------------------------------
    def _t(self, source: str) -> str:
        return translate(str(source), self.language_name)

    @Slot(str, result=str)
    def translate(self, source: str) -> str:
        return self._t(source)

    @staticmethod
    def _is_allowed_external_url(value: str) -> bool:
        url = QUrl(str(value).strip())
        host = url.host().lower().rstrip(".")
        return (
            url.isValid()
            and url.scheme().lower() == "https"
            and any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_EXTERNAL_HOSTS)
        )

    @Slot(str, result=bool)
    def openExternalUrl(self, value: str) -> bool:
        if not self._is_allowed_external_url(value):
            self.toastRequested.emit(self._t("无法打开链接"), self._t("这个地址不在允许的作者来源列表中。"))
            return False
        return bool(QDesktopServices.openUrl(QUrl(value)))

    @Slot(str)
    def setLanguage(self, value: str) -> None:
        value = "en" if value == "en" else "zh"
        if value == self.language_name:
            return
        self.language_name = value
        self.custom_wave_library_value = self._read_custom_wave_library()
        self.recommended_mod_inventory_value = self._recommended_mods(self.mod_inventory_value)
        update_config({"language": value})
        self.configChanged.emit()
        self.statusChanged.emit()
        self.vitalsChanged.emit()
        self.contextChanged.emit()
        self.outputChanged.emit()
        self.connectionChanged.emit()
        self.progressChanged.emit()
        self.waveChanged.emit()
        self.logsChanged.emit()

    @Slot(str)
    def setTheme(self, value: str) -> None:
        value = "light" if value == "light" else "dark"
        if value == self.theme_name:
            return
        self.theme_name = value
        update_config({"theme": value})
        self.configChanged.emit()

    @Slot(bool)
    def setGameHudEnabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self.game_hud_enabled_value:
            return
        self.game_hud_enabled_value = enabled
        update_config({"game_hud_enabled": enabled})
        self._publish_game_hud(force=True)
        self.configChanged.emit()
        self._log("游戏内 A/B HUD 已开启" if enabled else "游戏内 A/B HUD 已关闭")

    @Slot()
    def acceptAgreement(self) -> None:
        if self.agreement_accepted_value:
            return
        self.agreement_accepted_value = True
        update_config({"agreement_version": AGREEMENT_VERSION})
        self.configChanged.emit()
        self._log("用户已确认使用协议与风险提示")
        self._start_runtime()

    @Slot()
    def declineAgreement(self) -> None:
        self._log("用户不同意使用协议；应用即将退出")
        self.exitRequested.emit()

    def _start_runtime(self) -> None:
        if self.demo_mode or self.runtime_started:
            return
        self.runtime_started = True
        self.telemetry_status_value = "正在准备监听…"
        self.device_status_value = "等待手机扫码"
        self.worker = TelemetryWorker(self.messages)
        self.bridge = DGLabBridge(
            self.messages,
            port=int(self.saved.get("socket_port", DEFAULT_PORT)),
            lan_ip=str(self.saved.get("socket_lan_ip", "")),
        )
        self.worker.start()
        self.bridge.start()
        self.statusChanged.emit()
        self.connectionChanged.emit()

    @Slot(int)
    def setActivePage(self, index: int) -> None:
        self.ui_page_index = max(0, min(8, int(index)))
        # Values continue updating while a page is hidden. Emit one snapshot on
        # entry so the newly visible page catches up without background churn.
        self.statusChanged.emit()
        self.connectionChanged.emit()
        if self.ui_page_index == 0:
            self.vitalsChanged.emit()
            self.contextChanged.emit()
            self.outputChanged.emit()
            self.waveChanged.emit()
        elif self.ui_page_index == 3:
            self.contextChanged.emit()
            self.waveChanged.emit()
        elif self.ui_page_index == 4:
            self.outputChanged.emit()
            self.waveChanged.emit()
        elif self.ui_page_index == 5:
            self.progressChanged.emit()

    @Slot(str, result=bool)
    def selectLanAddress(self, address: str) -> bool:
        if self.demo_mode:
            return True
        if self.bridge is None or not self.bridge.set_lan_ip(address):
            self._toast("无法切换地址", "所选地址已失效，请重新连接网络后重启软件")
            return False
        update_config({"socket_lan_ip": str(address)})
        self._log(f"二维码已切换到局域网地址：{address}:{self.bridge.port}")
        self._toast("二维码已更新", "请使用 DG-LAB App 扫描新的二维码")
        return True

    @Slot(result=bool)
    def repairNetworkAccess(self) -> bool:
        if os.name != "nt":
            self._toast("当前系统不支持", "自动网络修复仅适用于 Windows")
            return False
        if self.bridge is None or not self.server_ready_value:
            self._toast("Socket 尚未就绪", "请等待二维码和局域网地址显示后再试")
            return False
        try:
            script = windows_network_repair_script(self.bridge.lan_ip, self.bridge.port)
            parameters = subprocess.list2cmdline(["-NoProfile", "-Command", script])
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                "powershell.exe",
                parameters,
                None,
                1,
            )
        except (OSError, ValueError) as error:
            self._toast("无法启动网络修复", str(error))
            return False
        if int(result) <= 32:
            self._toast("未执行网络修复", "管理员授权已取消或 PowerShell 无法启动")
            return False
        self._log(f"已请求管理员修复网络：{self.bridge.lan_ip}:{self.bridge.port}")
        self._toast("请确认管理员授权", "修复完成后回到 DG-LAB App 重新扫码")
        return True

    @Slot(str)
    def setGameFolder(self, value: str) -> None:
        url = QUrl(value)
        path = url.toLocalFile() if url.isLocalFile() else value
        self.game_folder_value = str(Path(path)) if path else ""
        self.mod_source_folder_value = self.game_folder_value
        update_config({
            "game_folder": self.game_folder_value,
            "mod_source_folder": self.game_folder_value,
            "mod_source_mode": "game",
        })
        self.check_game()
        if self.mod_source_folder_value:
            self.scan_mods(show_error=False)

    @Slot()
    def reset9527Import(self) -> None:
        self.pack9527_folder_value = ""
        self.pack9527_status_value = "尚未选择 9527 整合包"
        self.pack9527_analysis_value = {}
        self.pack9527_backup_value = ""
        self.configChanged.emit()

    @Slot(str, result=bool)
    def inspect9527Pack(self, value: str) -> bool:
        url = QUrl(value)
        path = url.toLocalFile() if url.isLocalFile() else value
        self.pack9527_folder_value = str(Path(path)) if path else ""
        self.pack9527_analysis_value = {}
        self.pack9527_backup_value = ""
        try:
            analysis = self.pack9527_importer.inspect(Path(self.pack9527_folder_value))
        except (Pack9527Error, OSError) as error:
            self.pack9527_status_value = str(error)
            self._toast("9527 整合包校验失败", str(error))
            self.configChanged.emit()
            return False
        self.pack9527_folder_value = analysis.root
        self.pack9527_analysis_value = analysis.as_dict()
        size_mib = analysis.total_bytes / (1024 * 1024)
        self.pack9527_status_value = (
            f"校验通过：插件 {analysis.plugins} · V1 {analysis.v1_missions} · "
            f"V2 {analysis.v2_packages} · {size_mib:.1f} MiB"
        )
        self._log(f"9527 整合包：{self.pack9527_status_value}")
        self.configChanged.emit()
        return analysis.ready

    @Slot(result=bool)
    def install9527Pack(self) -> bool:
        if not self.pack9527_folder_value:
            self._toast("尚未选择整合包", "请先选择解压后的 9527 整合包目录")
            return False
        self.pack9527_status_value = "正在备份并应用精简启动预设…"
        self.configChanged.emit()
        try:
            result = self.pack9527_importer.install(
                Path(self.pack9527_folder_value),
                Path(self.game_folder_value.strip()),
            )
        except (Pack9527Error, OSError, shutil.Error) as error:
            self.pack9527_status_value = str(error)
            self._toast("9527 整合包导入失败", str(error))
            self._log(f"9527 整合包导入失败：{error}")
            self.configChanged.emit()
            return False

        self.pack9527_backup_value = str(result["backup"])
        self.pack9527_analysis_value = dict(result)
        self.pack9527_status_value = (
            f"导入完成：仅启用 CustomMission 1/2；已停用插件 {result['disabled_plugins']}、"
            f"V1 任务 {result['disabled_v1']}、V2 包 {result['disabled_v2']}"
        )
        self.mod_source_folder_value = self.game_folder_value
        update_config({
            "mod_source_folder": self.mod_source_folder_value,
            "mod_source_mode": "game",
        })
        self.scan_mods(show_error=False)
        self._log(f"9527 整合包：{self.pack9527_status_value}")
        self._toast("9527 整合包导入完成", "精简启动预设已应用；可到本地 Mod 逐项开启任务")
        self.configChanged.emit()
        return True

    @Slot()
    def open9527Backup(self) -> None:
        if self.pack9527_backup_value and Path(self.pack9527_backup_value).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.pack9527_backup_value))

    @Slot(result=bool)
    def scanMods(self) -> bool:
        return self.scan_mods(show_error=True)

    def scan_mods(
        self,
        *,
        show_error: bool,
        retained_loaded_ids: tuple[str, ...] = (),
    ) -> bool:
        game = Path(self.game_folder_value.strip())
        source = Path(self.mod_source_folder_value.strip())
        try:
            extra_roots = []
            if self.dropin_importer.repository.is_dir():
                extra_roots.append(self.dropin_importer.repository)
            manager = ManakaModManager(game, source, extra_roots)
            inventory = manager.scan()
            self._annotate_v1_locations(inventory)
        except (ModManagerError, OSError) as error:
            self.mod_manager = None
            self.mod_inventory_value = []
            self.loaded_mod_inventory_value = []
            self.recommended_mod_inventory_value = self._recommended_mods([])
            self.mod_status_value = str(error)
            self.mod_summary_value = "扫描不可用"
            self.configChanged.emit()
            if show_error:
                self._toast("无法扫描 Mod", str(error))
            return False
        self.mod_manager = manager
        self.mod_inventory_value = inventory
        # "当前加载" is intentionally a file-state filter, not a runtime-log
        # claim. Items disabled from that tab remain as a grey session snapshot
        # until the user explicitly rescans (or restarts the application).
        self.loaded_mod_inventory_value = self._loaded_mods(inventory, retained_loaded_ids)
        self.recommended_mod_inventory_value = self._recommended_mods(inventory)
        counts = {
            kind: sum(1 for item in inventory if item.get("kind") == kind)
            for kind in ("plugin", "v1", "v2")
        }
        active = sum(1 for item in inventory if item.get("enabled"))
        self.mod_summary_value = (
            f"{counts['plugin']} 插件 · {counts['v1']} V1 任务组 · "
            f"{counts['v2']} V2 包 · {active} 项启用"
        )
        self.mod_status_value = "扫描完成；修改前请完全退出游戏"
        self.configChanged.emit()
        return True

    @staticmethod
    def _enabled_mods(inventory: list[dict]) -> list[dict]:
        """Return the file-state view used by the Current Enabled tab."""
        return [dict(item) for item in inventory if item.get("enabled")]

    @staticmethod
    def _loaded_mods(
        inventory: list[dict],
        retained_ids: tuple[str, ...] = (),
    ) -> list[dict]:
        """Build the Current Loaded snapshot, retaining just-toggled cards."""
        retained = set(retained_ids)
        return [
            dict(item, sessionDisabled=not bool(item.get("enabled")))
            for item in inventory
            if item.get("enabled") or item.get("id") in retained
        ]

    @staticmethod
    def _annotate_v1_locations(inventory: list[dict]) -> None:
        guide = {item["name"]: item for item in V1_MISSION_LOCATIONS}
        for mod in inventory:
            mod.update({
                "hasLocationGuide": False,
                "locationArea": "",
                "location": "",
                "locationNote": "",
            })
            if mod.get("kind") != "v1":
                continue
            name = str(mod.get("name", "")).casefold()
            guide_names: tuple[str, ...] = ()
            for pattern, candidates in V1_LOCATION_RULES:
                if re.search(pattern, name, flags=re.IGNORECASE):
                    guide_names = candidates
                    break
            matches = [guide[value] for value in guide_names if value in guide]
            if not matches:
                continue
            mod["hasLocationGuide"] = True
            mod["locationArea"] = " / ".join(dict.fromkeys(item["area"] for item in matches))
            if len(matches) == 1:
                mod["location"] = matches[0]["location"]
            else:
                mod["location"] = "　".join(f"{item['name']}：{item['location']}" for item in matches)
            mod["locationNote"] = "　".join(item["note"] for item in matches if item["note"])

    def _recommended_mods(self, inventory: list[dict]) -> list[dict]:
        by_id = {str(item.get("id", "")).casefold(): item for item in inventory}
        result: list[dict] = []
        for definition in RECOMMENDED_MODS:
            item = dict(by_id.get(definition["id"].casefold(), {}))
            localized_definition = dict(definition)
            localized_definition["role"] = self._t(str(definition["role"]))
            localized_definition["summary"] = self._t(str(definition["summary"]))
            item.update(localized_definition)
            if not item.get("kind"):
                item.update({
                    "kind": "plugin" if definition["id"].startswith("plugin|") else "v2",
                    "kindLabel": self._t("插件" if definition["id"].startswith("plugin|") else "V2 包"),
                    "enabled": False,
                    "available": False,
                    "status": self._t("当前来源库中未找到"),
                    "warning": "",
                    "requiredPluginName": "",
                    "dependencyReady": True,
                    "dependencyAvailable": True,
                })
            result.append(item)
        return result

    @Slot()
    def openDropInFolder(self) -> None:
        try:
            self.dropin_importer.ensure_layout()
        except OSError as error:
            self._toast("无法创建 Drop-in 目录", str(error))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.dropin_importer.incoming)))

    @Slot()
    def openDropInArchive(self) -> None:
        try:
            self.dropin_importer.ensure_layout()
        except OSError as error:
            self._toast("无法创建 Drop-in 目录", str(error))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.dropin_importer.archive)))

    @Slot(result=bool)
    def importDropIns(self) -> bool:
        try:
            result = self.dropin_importer.import_all()
        except OSError as error:
            self._toast("Drop-in 导入失败", str(error))
            return False
        errors = result["errors"]
        summary = (
            f"插件 {result['plugins']} · V1 {result['v1']} · V2 {result['v2']}"
        )
        self.scan_mods(show_error=False)
        refreshed = 0
        refresh_error = ""
        if self.mod_manager is not None:
            try:
                refreshed = self.mod_manager.refresh_enabled_from_sources()
            except (ModManagerError, OSError, shutil.Error) as error:
                refresh_error = str(error)
        if refreshed:
            summary += f" · 已替换 {refreshed} 个启用项"
        if errors:
            self.dropin_status_value = f"{summary} · {len(errors)} 个文件未导入"
            self._toast("部分 Drop-in 未导入", errors[0])
        elif refresh_error:
            self.dropin_status_value = f"导入完成；{refresh_error}"
            self._toast("仓库已更新", refresh_error)
        else:
            self.dropin_status_value = f"导入完成：{summary}"
            self._toast("Drop-in 导入完成", summary)
        self._log(f"Drop-in：{self.dropin_status_value}")
        self.scan_mods(show_error=False)
        self.configChanged.emit()
        return not errors and not refresh_error

    @Slot(str, result=bool)
    def deleteDropInMod(self, entry_id: str) -> bool:
        if self.mod_manager is None and not self.scan_mods(show_error=True):
            return False
        assert self.mod_manager is not None
        try:
            status = self.mod_manager.delete_dropin(entry_id)
        except (ModManagerError, OSError, shutil.Error) as error:
            self._toast("无法删除 Mod", str(error))
            self.mod_status_value = str(error)
            self.configChanged.emit()
            return False
        self._log(f"Drop-in 删除：{entry_id} · {status}")
        self.scan_mods(show_error=False)
        self._toast("Mod 已删除", entry_id.split("|", 1)[-1])
        return True

    @Slot(str, bool, result=bool)
    def setModEnabled(self, entry_id: str, enabled: bool) -> bool:
        return self._set_mod_enabled(entry_id, enabled)

    @Slot(str, bool, result=bool)
    def setLoadedModEnabled(self, entry_id: str, enabled: bool) -> bool:
        retained_ids = tuple(
            str(item.get("id", ""))
            for item in self.loaded_mod_inventory_value
            if item.get("id")
        )
        return self._set_mod_enabled(entry_id, enabled, retained_loaded_ids=retained_ids)

    def _set_mod_enabled(
        self,
        entry_id: str,
        enabled: bool,
        *,
        retained_loaded_ids: tuple[str, ...] = (),
    ) -> bool:
        if self.mod_manager is None and not self.scan_mods(show_error=True):
            return False
        assert self.mod_manager is not None
        try:
            status = self.mod_manager.set_enabled(entry_id, enabled)
        except (ModManagerError, OSError, shutil.Error) as error:
            self._toast("Mod 修改失败", str(error))
            self.mod_status_value = str(error)
            self.configChanged.emit()
            return False
        self._log(f"Mod 管理器：{entry_id} -> {status}")
        self.scan_mods(
            show_error=False,
            retained_loaded_ids=retained_loaded_ids,
        )
        self._toast("Mod 状态已更新", f"{entry_id.split('|', 1)[-1]}：{status}")
        return True

    @Slot(result=bool)
    def checkGame(self) -> bool:
        return self.check_game()

    def check_game(self) -> bool:
        folder = Path(self.game_folder_value.strip())
        valid, detail = validate_game_folder(folder)
        if valid:
            target = folder / "BepInEx" / "plugins" / "ManakaDGLabTelemetry" / "ManakaDGLabTelemetry.dll"
            has_bepinex = (folder / "BepInEx" / "core" / "BepInEx.Core.dll").is_file()
            if target.is_file() and has_bepinex:
                detail = "游戏、BepInEx 和独立遥测插件均已就绪"
            elif has_bepinex:
                detail = "已检测到 BepInEx；独立遥测插件尚未安装"
        self.game_status_value = detail
        self.configChanged.emit()
        return valid

    @Slot(result=bool)
    def installPlugin(self) -> bool:
        folder = Path(self.game_folder_value.strip())
        valid, detail = validate_game_folder(folder)
        if not valid:
            self._toast("无法安装", detail)
            return False
        supported, build_detail = validate_supported_game_build(folder)
        if not supported:
            self._toast("版本不匹配", build_detail)
            return False
        source = bundled_plugin_path()
        if not source.is_file():
            self._toast("缺少文件", f"找不到遥测插件：{source}")
            return False

        runtime_installed = False
        runtime_core = folder / "BepInEx" / "core" / "BepInEx.Core.dll"
        if not runtime_core.is_file():
            runtime_source = bundled_bepinex_path()
            required_runtime_files = (
                runtime_source / ".doorstop_version",
                runtime_source / "doorstop_config.ini",
                runtime_source / "winhttp.dll",
                runtime_source / "BEPINEX_LICENSE.txt",
                runtime_source / "dotnet",
                runtime_source / "BepInEx" / "core",
                runtime_source / "BepInEx" / "interop",
                runtime_source / "BepInEx" / "unity-libs",
            )
            missing = [str(path) for path in required_runtime_files if not path.exists()]
            if missing:
                self._toast("安装包不完整", f"缺少 BepInEx 文件：{missing[0]}")
                return False
            try:
                (folder / "BepInEx").mkdir(parents=True, exist_ok=True)
                for root_file in (".doorstop_version", "doorstop_config.ini", "winhttp.dll"):
                    shutil.copy2(runtime_source / root_file, folder / root_file)
                shutil.copy2(
                    runtime_source / "BEPINEX_LICENSE.txt",
                    folder / "BepInEx" / "BEPINEX_LICENSE.txt",
                )
                shutil.copytree(runtime_source / "dotnet", folder / "dotnet", dirs_exist_ok=True)
                for child in ("core", "interop", "unity-libs", "config"):
                    shutil.copytree(
                        runtime_source / "BepInEx" / child,
                        folder / "BepInEx" / child,
                        dirs_exist_ok=True,
                    )
                (folder / "BepInEx" / "patchers").mkdir(parents=True, exist_ok=True)
                (folder / "BepInEx" / "plugins").mkdir(parents=True, exist_ok=True)
                runtime_installed = True
            except (OSError, shutil.Error) as error:
                self._toast("运行环境安装失败", str(error))
                return False

        target_dir = folder / "BepInEx" / "plugins" / "ManakaDGLabTelemetry"
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            plugin_target = target_dir / source.name
            shutil.copy2(source, plugin_target)
            manifest_path = folder / ".manaka-dglab-install.json"
            try:
                previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                previous_manifest = {}
            runtime_owned = runtime_installed or bool(previous_manifest.get("runtimeInstalledByApp", False))
            manifest = {
                "schema": 1,
                "appVersion": APP_VERSION,
                "gameBuild": build_detail,
                "bepInExVersion": "6.0.0-be.735+5fef357",
                "telemetryVersion": "0.4.2-hud-compact",
                "runtimeInstalledByApp": runtime_owned,
                "pluginSha256": sha256_file(plugin_target),
                "ownedRootItems": [
                    ".doorstop_version",
                    "doorstop_config.ini",
                    "winhttp.dll",
                    "dotnet",
                    "BepInEx",
                ] if runtime_owned else [
                    "BepInEx/plugins/ManakaDGLabTelemetry/ManakaDGLabTelemetry.dll"
                ],
            }
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except PermissionError:
            self._toast("文件正在使用", "请完全退出游戏后再安装或更新")
            return False
        except OSError as error:
            self._toast("插件安装失败", str(error))
            return False
        update_config({"game_folder": str(folder)})
        self._log("BepInEx 与独立遥测插件安装完成" if runtime_installed else "独立遥测插件安装/更新完成")
        self.check_game()
        self._toast(
            "一键安装完成" if runtime_installed else "插件更新完成",
            "已安装 BepInEx 6 与独立遥测插件" if runtime_installed else "独立遥测插件已复制到游戏目录",
        )
        return True

    @Slot()
    def installAndLaunch(self) -> None:
        if not self.installPlugin():
            return
        executable = Path(self.game_folder_value.strip()) / "SecretFlasherManaka.exe"
        try:
            subprocess.Popen([str(executable)], cwd=str(executable.parent))
            self._log("游戏已启动，等待进入可操作场景")
            self._toast("游戏已启动", "进入可操作场景后会自动接收心率")
        except OSError as error:
            self._toast("启动失败", str(error))

    @Slot()
    def toggleOutput(self) -> None:
        if self.demo_mode:
            self.auto_output_enabled = not self.auto_output_enabled
            self.device_status_value = "演示输出已暂停" if not self.auto_output_enabled else "演示输出中"
            self.statusChanged.emit()
            self.outputChanged.emit()
            return
        if not self.device_connected_value:
            self._toast("尚未连接", "请先使用 DG-LAB App 扫描二维码")
            return
        assert self.bridge is not None
        if self.auto_output_enabled:
            self.auto_output_enabled = False
            self.safety_wait_reason = ""
            self.bridge.emergency_stop()
            self.device_status_value = "输出已暂停 · A/B 已归零 · 设备保持连接"
            self._log("手动暂停输出：A/B 已归零并清空队列")
        else:
            self.auto_output_enabled = True
            self.bridge.set_auto_enabled(True)
            self.device_status_value = "已继续 · 等待有效游戏数据" if self.current_frame.safe_cut else "A/B 通道输出中"
            self.safety_wait_reason = self.current_frame.reason if self.current_frame.safe_cut else ""
            self._show_frame(self.current_frame)
            self._log("继续输出：已恢复 A 心率与 B 动作驱动")
        self.statusChanged.emit()
        self.outputChanged.emit()

    @Slot(int, int, int, int, int, bool, result=bool)
    def savePersonalSettings(
        self,
        trigger_bpm: int,
        full_bpm: int,
        min_strength: int,
        output_max: int,
        hard_cap: int,
        confirmed_high_cap: bool,
    ) -> bool:
        if not 60 <= trigger_bpm < full_bpm <= 160:
            self._toast("心率范围无效", "开始 BPM 必须低于满幅 BPM，最高为 160")
            return False
        if not 0 <= min_strength <= output_max <= 100 or not 1 <= hard_cap <= 100:
            self._toast("强度范围无效", "必须满足：最低强度 ≤ 日常最高 ≤ 100，安全硬上限为 1–100")
            return False
        if hard_cap > 30 and hard_cap > self.hard_cap_value and not confirmed_high_cap:
            self._toast("需要确认", "提高到 30 以上前，请确认个人可承受范围")
            return False
        self.engine.configure(
            min_strength=min_strength,
            output_max=output_max,
            hard_cap=hard_cap,
            trigger_bpm=trigger_bpm,
            full_bpm=full_bpm,
        )
        self.trigger_bpm_value = trigger_bpm
        self.full_bpm_value = full_bpm
        self.min_strength_value = min_strength
        self.output_max_value = output_max
        self.hard_cap_value = hard_cap
        update_config(
            {
                "trigger_bpm": trigger_bpm,
                "full_bpm": full_bpm,
                "min_strength": min_strength,
                "output_max": output_max,
                "hard_cap": hard_cap,
            }
        )
        self.configChanged.emit()
        self._log(f"个性化范围已保存：BPM {trigger_bpm}–{full_bpm}，强度 {min_strength}–{output_max}，上限 {hard_cap}")
        self._toast("设置已保存", "新的范围会立即用于心率输出")
        return True

    @Slot(str, "QVariantList", int, result=bool)
    def saveCustomWaveform(self, name: str, points: list, frequency: int) -> bool:
        name = str(name).strip()
        if not name:
            name = self._next_custom_waveform_name()
        if len(points) != 16:
            self._toast("自定义波形无效", "波形必须包含 16 个控制点")
            return False
        clean_points = [int(clamp(float(value), 0, 100)) for value in points]
        clean_frequency = int(clamp(float(frequency), 10, 240))
        directory = waveform_library_dir()
        target = directory / f"{waveform_file_stem(name)}.json"
        existed = target.is_file()
        payload = {
            "format": "ManakaDGLabWaveform/1",
            "name": name[:64],
            "points": clean_points,
            "frequency": clean_frequency,
            "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        try:
            directory.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(target)
        except OSError as error:
            self._toast("保存失败", str(error))
            return False
        self.custom_name_value = payload["name"]
        self.custom_points_value = clean_points
        self.custom_frequency_value = clean_frequency
        self.custom_wave_library_value = self._read_custom_wave_library()
        update_config(
            {
                "custom_wave_name": self.custom_name_value,
                "custom_wave_points": self.custom_points_value,
                "custom_wave_frequency": self.custom_frequency_value,
            }
        )
        self.configChanged.emit()
        self._log(f"自定义波形已{'更新' if existed else '保存'}：{self.custom_name_value}")
        self._toast("波形库已更新", f"{self.custom_name_value} 已保存到固定目录")
        return True

    @Slot(str, str, result=bool)
    def setActionWaveform(self, action: str, wave_key: str) -> bool:
        action = str(action).strip()
        wave_key = str(wave_key).strip()
        if not action or action == "None" or not self._is_assignable_wave_key(wave_key):
            self._toast("动作映射无效", "请选择有效的动作与波形")
            return False
        recommended = recommended_wave_for_action(action)
        if wave_key == recommended:
            self.action_wave_map_value.pop(action, None)
        else:
            self.action_wave_map_value[action] = wave_key
        if action not in self.known_actions_value:
            self.known_actions_value.append(action)
        self.wave_selector.reset()
        update_config(
            {
                "action_wave_map": self.action_wave_map_value,
                "known_actions": self.known_actions_value,
            }
        )
        self.configChanged.emit()
        self._log(f"动作波形：{action} → {wave_key}")
        return True

    @Slot()
    def resetActionWaveforms(self) -> None:
        self.action_wave_map_value = {}
        self.wave_selector.reset()
        update_config({"action_wave_map": {}})
        self.configChanged.emit()
        self._log("动作波形已恢复推荐配置")
        self._toast("已恢复推荐", "静态姿势、规律动作与普通交互已重新自动匹配")

    @Slot(str, result=bool)
    def loadCustomWaveform(self, file_id: str) -> bool:
        entry = self._library_entry(file_id)
        if entry is None:
            self._toast("载入失败", "找不到这个波形文件，可能已被移动或删除")
            return False
        self.custom_name_value = entry["name"]
        self.custom_points_value = list(entry["points"])
        self.custom_frequency_value = int(entry["frequency"])
        self.wave_selector.reset()
        update_config(
            {
                "custom_wave_name": self.custom_name_value,
                "custom_wave_points": self.custom_points_value,
                "custom_wave_frequency": self.custom_frequency_value,
            }
        )
        self.configChanged.emit()
        self._log(f"已载入自定义波形：{self.custom_name_value}")
        self._toast("已载入波形", "可继续编辑，或在策略中选择这个自定义波形")
        return True

    @Slot(str, result=bool)
    def deleteCustomWaveform(self, file_id: str) -> bool:
        entry = self._library_entry(file_id)
        if entry is None:
            self._toast("删除失败", "找不到这个波形文件")
            return False
        target = waveform_library_dir() / file_id
        try:
            if target.parent.resolve() != waveform_library_dir().resolve() or target.suffix.lower() != ".json":
                raise OSError("波形文件路径无效")
            target.unlink()
        except OSError as error:
            self._toast("删除失败", str(error))
            return False
        deleted_key = str(entry.get("key", ""))
        self.action_wave_map_value = {
            action: key for action, key in self.action_wave_map_value.items() if key != deleted_key
        }
        self.custom_wave_library_value = self._read_custom_wave_library()
        update_config({"action_wave_map": self.action_wave_map_value})
        self.configChanged.emit()
        self._log(f"已从波形库删除：{entry['name']}")
        self._toast("已删除", entry["name"])
        return True

    @Slot()
    def openWaveformLibraryFolder(self) -> None:
        directory = waveform_library_dir()
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self._toast("无法打开目录", str(error))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory)))

    @Slot(str, str, str, str, str, str, str, str, "QVariantList", int, result=bool)
    def saveWaveSettings(
        self,
        mode: str,
        fixed: str,
        low: str,
        mid: str,
        high: str,
        action: str,
        peak: str,
        custom_name: str,
        custom_points: list,
        custom_frequency: int,
    ) -> bool:
        allowed = set(PRESETS) | {"custom"}
        fixed = fixed if fixed in allowed else "official_heartbeat"
        clean_map = sanitize_wave_map({"low": low, "mid": mid, "high": high, "action": action, "peak": peak})
        if len(custom_points) != 16:
            self._toast("自定义波形无效", "波形必须包含 16 个控制点")
            return False
        self.wave_mode_value = "fixed" if mode == "fixed" else "smart"
        self.fixed_wave_value = fixed
        self.wave_map_value = clean_map
        self.custom_name_value = str(custom_name).strip()[:64] or "我的波形"
        self.custom_points_value = [int(clamp(float(value), 0, 100)) for value in custom_points]
        self.custom_frequency_value = int(clamp(float(custom_frequency), 10, 240))
        self.wave_selector.reset()
        update_config(
            {
                "wave_mode": self.wave_mode_value,
                "fixed_wave": fixed,
                "wave_map": clean_map,
                "custom_wave_name": self.custom_name_value,
                "custom_wave_points": self.custom_points_value,
                "custom_wave_frequency": self.custom_frequency_value,
            }
        )
        self.configChanged.emit()
        self._log("波形策略已保存")
        self._toast("波形已保存", "新的预设将在下一次输出更新时生效")
        return True

    @Slot()
    def resetWaveSettings(self) -> None:
        self.wave_mode_value = "smart"
        self.fixed_wave_value = "official_heartbeat"
        self.wave_map_value = dict(DEFAULT_WAVE_MAP)
        self.custom_name_value = "我的波形"
        self.custom_points_value = list(DEFAULT_CUSTOM_POINTS)
        self.custom_frequency_value = 92
        self.wave_selector.reset()
        update_config(
            {
                "wave_mode": self.wave_mode_value,
                "fixed_wave": self.fixed_wave_value,
                "wave_map": self.wave_map_value,
                "custom_wave_name": self.custom_name_value,
                "custom_wave_points": self.custom_points_value,
                "custom_wave_frequency": self.custom_frequency_value,
            }
        )
        self.configChanged.emit()
        self._log("波形策略已恢复默认：智能分段 + Climax 双击峰值")
        self._toast("已恢复默认", "当前编辑器已重置；波形库中的已保存文件会保留")

    @Slot()
    def clearLogs(self) -> None:
        self.log_lines.clear()
        self.logsChanged.emit()

    @Slot(str, str, result=bool)
    def applyProgressValues(self, rp_text: str, exp_text: str) -> bool:
        try:
            rp = float(str(rp_text).strip().replace(",", ""))
            exp_number = float(str(exp_text).strip().replace(",", ""))
            exp = int(exp_number)
        except (TypeError, ValueError):
            self._toast("数值无效", "货币与经验必须是数字")
            return False
        if not math.isfinite(rp) or rp < 0 or rp > 999_999_999 or exp_number != exp or exp < 0 or exp > 999_999_999:
            self._toast("数值超出范围", "请输入 0–999999999 之间的非负数；经验值必须是整数")
            return False
        if self.demo_mode:
            self.current_rp_value = rp
            self.expose_exp_value = exp
            self.progress_editor_status_value = "演示修改完成（未写入真实存档）"
            self.progressChanged.emit()
            self._toast("演示修改完成", "演示模式不会接触真实游戏存档")
            return True
        if not self.telemetryOnline:
            self._toast("游戏尚未连接", "请先载入一个存档并进入可操作场景")
            return False
        if not bool(self.last_packet.get("paused", False)):
            self._toast("请先暂停游戏", "按 Esc 打开游戏菜单，看到“游戏已暂停”后再写入")
            return False
        if self.current_save_slot_value < 0:
            self._toast("没有可用存档", "当前游戏没有有效的手动存档槽位")
            return False
        try:
            backup = self._create_save_backup("before-edit")
        except OSError as error:
            self._toast("备份失败，已取消修改", str(error))
            return False

        command_id = str(time.time_ns())
        payload = (
            f"MANAKA_PROGRESS_V1|{command_id}|{rp:.2f}|{exp}|1|END"
        ).encode("utf-8")
        try:
            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sender.sendto(payload, (UDP_HOST, COMMAND_PORT))
            finally:
                sender.close()
        except OSError as error:
            self._toast("发送修改命令失败", str(error))
            return False
        self.pending_progress_id = command_id
        self.pending_progress_deadline = time.monotonic() + 5.0
        self.progress_editor_status_value = "正在由游戏写入并保存…"
        self._log(f"修改前存档已备份：{backup.name}")
        self._log(f"已请求写入 RP={rp:.0f}，经验={exp}，槽位={self.current_save_slot_value}")
        self.progressChanged.emit()
        return True

    @Slot(result=bool)
    def createSaveBackup(self) -> bool:
        try:
            backup = self._create_save_backup("manual")
        except OSError as error:
            self._toast("备份失败", str(error))
            return False
        self._log(f"手动存档备份已创建：{backup.name}")
        self._toast("备份完成", str(backup))
        return True

    def _game_save_root(self) -> Path:
        return Path.home() / "AppData" / "LocalLow" / "SheableSoft" / "SecretFlasherManaka"

    def _create_save_backup(self, reason: str) -> Path:
        source_root = self._game_save_root()
        save_data = source_root / "SaveData"
        if not save_data.is_dir() or not any(save_data.glob("*.sd")):
            raise OSError("找不到游戏存档；请至少在游戏中保存一次")
        timestamp = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() % 1_000_000_000:09d}"
        destination = app_data_dir() / "save_backups" / f"{timestamp}-{reason}"
        destination.mkdir(parents=True, exist_ok=False)
        shutil.copytree(save_data, destination / "SaveData")
        game_backup = source_root / "SaveDataBackup"
        if game_backup.is_dir():
            shutil.copytree(game_backup, destination / "SaveDataBackup")
        (destination / "backup.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "createdAt": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "reason": reason,
                    "appVersion": APP_VERSION,
                    "saveSlot": self.current_save_slot_value,
                    "currentRp": self.current_rp_value,
                    "exposeExp": self.expose_exp_value,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        backup_root = destination.parent
        backups = sorted((path for path in backup_root.iterdir() if path.is_dir()), reverse=True)
        for old in backups[20:]:
            shutil.rmtree(old, ignore_errors=True)
        return destination

    # ----- Runtime -------------------------------------------------------------
    def _poll(self) -> None:
        status_changed = False
        vitals_changed = False
        context_changed = False
        output_changed = False
        connection_changed = False
        progress_changed = False
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "listener":
                    status_changed = True
                    if payload == "ready":
                        self.telemetry_status_value = "等待游戏数据"
                        self._log("遥测监听已启动；设备输出保持锁定")
                    else:
                        self.telemetry_status_value = str(payload)
                        self._log(str(payload))
                elif kind == "telemetry":
                    previous_status = (
                        bool(self.last_receive),
                        self.telemetry_status_value,
                        self.device_connected_value,
                        self.auto_output_enabled,
                        self.safety_wait_reason,
                        self.device_status_value,
                    )
                    previous_vitals = (self.heart_rate_value, self.alert_level_value, self.excitement_value)
                    previous_context = (self.stage_value, self.action_value)
                    previous_output = (self.current_output_a, self.current_output_b)
                    previous_progress = (
                        self.current_rp_value,
                        self.expose_exp_value,
                        self.current_save_slot_value,
                        self.progress_editor_status_value,
                        bool(self.last_packet.get("paused", False)),
                    )
                    self._on_telemetry(payload)
                    status_changed |= previous_status != (
                        bool(self.last_receive),
                        self.telemetry_status_value,
                        self.device_connected_value,
                        self.auto_output_enabled,
                        self.safety_wait_reason,
                        self.device_status_value,
                    )
                    vitals_changed |= previous_vitals != (
                        self.heart_rate_value,
                        self.alert_level_value,
                        self.excitement_value,
                    )
                    context_changed |= previous_context != (self.stage_value, self.action_value)
                    output_changed |= previous_output != (self.current_output_a, self.current_output_b)
                    progress_changed |= previous_progress != (
                        self.current_rp_value,
                        self.expose_exp_value,
                        self.current_save_slot_value,
                        self.progress_editor_status_value,
                        bool(self.last_packet.get("paused", False)),
                    )
                elif kind == "progress_result":
                    self._on_progress_result(payload)
                    progress_changed = True
                elif kind == "dglab":
                    self._handle_dglab_event(payload)
                    status_changed = True
                    output_changed = True
                    connection_changed = True
        except queue.Empty:
            pass

        if self.demo_mode:
            self.demo_phase += 0.05
            self.heart_rate_value = 128 + math.sin(self.demo_phase * 0.8) * 6
            self.alert_level_value = 34 + math.sin(self.demo_phase * 0.43) * 13
            self.excitement_value = 67 + math.sin(self.demo_phase * 0.31) * 7
            if self.auto_output_enabled:
                self.current_output_a = 18 + math.sin(self.demo_phase * 0.67) * 4
                self.current_output_b = 7 + math.sin(self.demo_phase * 0.49) * 3
            vitals_changed = True
            output_changed = True
        elif self.last_receive and time.monotonic() - self.last_receive >= STALE_SECONDS and not self.stale_reported:
            self.stale_reported = True
            self.telemetry_status_value = "等待游戏数据"
            self._enter_safety_idle("telemetry-stale")
            self._show_frame(self.engine.force_safe_cut("telemetry-stale"))
            self._log("安全归零：遥测中断")
            status_changed = True
            output_changed = True
            progress_changed = True
        if self.pending_progress_id and time.monotonic() >= self.pending_progress_deadline:
            self.pending_progress_id = ""
            self.progress_editor_status_value = "写入超时；未确认存档是否变化"
            self._log("存档修改响应超时，请检查插件版本并重新读取数值")
            self._toast("写入超时", "游戏插件没有在 5 秒内确认，请勿连续点击")
            progress_changed = True
        self._publish_game_hud()
        if status_changed:
            self.statusChanged.emit()
        if connection_changed:
            self.connectionChanged.emit()
        if progress_changed and self.ui_page_index == 5:
            self.progressChanged.emit()

        now = time.monotonic()
        live_due = now - self.ui_last_telemetry_emit >= 0.2
        emitted_live = False
        if self.ui_page_index == 0 and live_due:
            if vitals_changed:
                self.vitalsChanged.emit()
                emitted_live = True
            if context_changed:
                self.contextChanged.emit()
                emitted_live = True
            if output_changed:
                self.outputChanged.emit()
                emitted_live = True
        elif self.ui_page_index == 3 and context_changed:
            self.contextChanged.emit()
        elif self.ui_page_index == 4 and output_changed and live_due:
            self.outputChanged.emit()
            emitted_live = True
        if emitted_live:
            self.ui_last_telemetry_emit = now

    @staticmethod
    def _wave_pulse(wave: WaveformPreset | None, output: float, now: float) -> float:
        if wave is None or output <= 0 or not wave.amplitudes:
            return 0.0
        index = int(now * 10.0) % len(wave.amplitudes)
        return clamp(float(wave.amplitudes[index]) / 100.0, 0.0, 1.0)

    def _publish_game_hud(self, *, force: bool = False) -> None:
        if self.hud_socket is None:
            return
        now = time.monotonic()
        if not force and now - self.hud_last_sent < 0.1:
            return
        self.hud_last_sent = now
        self.hud_sequence += 1
        active = bool(
            self.auto_output_enabled
            and self.device_connected_value
            and not self.safety_wait_reason
        )
        strength_a = self.current_output_a if active else 0.0
        strength_b = self.current_output_b if active else 0.0
        packet = build_hud_packet(
            self.hud_sequence,
            visible=self.game_hud_enabled_value,
            connected=self.device_connected_value,
            active=active,
            strength_a=strength_a,
            strength_b=strength_b,
            pulse_a=self._wave_pulse(self.current_wave_a, strength_a, now),
            pulse_b=self._wave_pulse(self.current_wave_b, strength_b, now),
        )
        try:
            self.hud_socket.sendto(packet, (UDP_HOST, HUD_PORT))
        except OSError:
            # HUD is optional and must never interrupt output or telemetry.
            pass

    def _handle_dglab_event(self, payload: dict) -> None:
        event = str(payload.get("event", ""))
        if event == "ready":
            self.server_ready_value = True
            address = f"{payload.get('lan_ip')}:{payload.get('port')}"
            self.lan_address_value = address
            if self.bridge is not None:
                self.lan_addresses_value = list(self.bridge.available_lan_ips)
            self.device_status_value = "Socket 已就绪 · 等待手机扫码"
            if self.bridge is not None:
                snapshot = self.bridge.snapshot()
                self.qr_source_value = self._qr_data_url(snapshot.qr_url)
            self._log(f"DG-LAB Socket 已就绪：{address}")
        elif event == "connected":
            self.device_connected_value = True
            self.auto_output_enabled = True
            self.safety_wait_reason = self.current_frame.reason if self.current_frame.safe_cut else ""
            assert self.bridge is not None
            self.bridge.set_auto_enabled(True)
            self.device_status_value = "设备已连接 · 安全待机" if self.current_frame.safe_cut else "设备已连接 · A/B 通道输出中"
            self._log("DG-LAB 手机端绑定成功；已自动启用 A/B 输出")
            self._show_frame(self.current_frame)
        elif event == "disconnected":
            self.device_connected_value = False
            self.auto_output_enabled = False
            self.safety_wait_reason = ""
            self.device_status_value = "设备已断开 · 输出已归零"
            self._log("DG-LAB 连接断开；自动输出已关闭")
        elif event == "feedback":
            message = str(payload.get("message", ""))
            if message.startswith("strength-"):
                self._log(f"设备强度反馈：{message}")
        elif event == "error":
            self.device_status_value = "Socket 连接不可用"
            self._log(str(payload.get("detail", "未知 Socket 错误")))

    def _on_telemetry(self, packet: dict) -> None:
        now = time.monotonic()
        game_ms = int(packet.get("monotonicMs", 0) or 0)
        dt = 0.1 if self.last_game_ms is None else max(0.0, min(0.5, (game_ms - self.last_game_ms) / 1000.0))
        self.last_game_ms = game_ms
        self.last_receive = now
        self.last_packet = packet
        self.stale_reported = False
        frame = self.engine.evaluate(packet, dt)
        self.telemetry_status_value = "游戏已暂停" if frame.reason == "game-paused" else "实时连接"
        self.heart_rate_value = float(packet.get("heartRate", 0) or 0)
        self.alert_level_value = max(0.0, min(100.0, float(packet.get("maxNpcAlert", 0) or 0) * 100))
        self.excitement_value = max(0.0, min(100.0, float(packet.get("ecstasy", 0) or 0) * 100))
        self.stage_value = str(packet.get("stage", "None"))
        self.action_value = str(packet.get("action", "None") or "None")
        if self.action_value not in {"", "None"} and self.action_value not in self.known_actions_value:
            self.known_actions_value.append(self.action_value)
            update_config({"known_actions": self.known_actions_value})
            self.configChanged.emit()
        self.current_rp_value = float(packet.get("currentRp", self.current_rp_value) or 0)
        self.expose_exp_value = int(packet.get("exposeExp", self.expose_exp_value) or 0)
        self.current_save_slot_value = int(packet.get("currentSaveSlot", self.current_save_slot_value))
        if not self.pending_progress_id:
            self.progress_editor_status_value = (
                f"已读取手动存档槽位 {self.current_save_slot_value}"
                if self.current_save_slot_value >= 0
                else "当前没有可写入的手动存档槽位"
            )
        if frame.safe_cut:
            self._enter_safety_idle(frame.reason)
        else:
            self._leave_safety_idle()
        self._show_frame(frame)
        if self.action_value != self.last_action:
            action_title = "Action" if self.language_name == "en" else "动作"
            previous_label = action_label(self.last_action, self.language_name)
            current_label = action_label(self.action_value, self.language_name)
            self._log(f"{action_title}：{previous_label} → {current_label}")
            self.last_action = self.action_value
        for event in frame.events:
            self._log(f"事件：{event}")

    def _on_progress_result(self, packet: dict) -> None:
        response_id = str(packet.get("id", ""))
        if self.pending_progress_id and response_id != self.pending_progress_id:
            return
        ok = bool(packet.get("ok", False))
        message = str(packet.get("message", "未知响应"))
        self.pending_progress_id = ""
        self.pending_progress_deadline = 0.0
        if ok:
            self.current_rp_value = float(packet.get("currentRp", self.current_rp_value) or 0)
            self.expose_exp_value = int(packet.get("exposeExp", self.expose_exp_value) or 0)
            self.current_save_slot_value = int(packet.get("currentSaveSlot", self.current_save_slot_value))
            self.progress_editor_status_value = message
            self._log(f"存档修改成功：RP={self.current_rp_value:.0f}，经验={self.expose_exp_value}")
            self._toast("修改并保存成功", f"RP {self.current_rp_value:.0f} · 经验 {self.expose_exp_value}")
        else:
            self.progress_editor_status_value = "写入失败：" + message
            self._log("存档修改失败：" + message)
            self._toast("修改失败", message)

    def _show_frame(self, frame: TriggerFrame) -> None:
        self.current_frame = frame
        previous_wave_a = self.current_wave_a.key if self.current_wave_a else ""
        previous_wave_b = self.current_wave_b.key if self.current_wave_b else ""
        custom = self._custom_waveform()
        wave_a = self.wave_selector.select(
            "A", frame.pattern_a, self.wave_mode_value, self.fixed_wave_value, self.wave_map_value, custom
        )
        if self.wave_mode_value == "smart" and frame.pattern_b == "action-ramp":
            wave_b = self._waveform_from_key(self._selected_action_wave_key(self.action_value))
            self.wave_selector.current["B"] = wave_b
            self.wave_selector.pending["B"] = None
        else:
            wave_b = self.wave_selector.select(
                "B", frame.pattern_b, self.wave_mode_value, self.fixed_wave_value, self.wave_map_value, custom
            )
        self.current_wave_a = wave_a
        self.current_wave_b = wave_b
        if previous_wave_a != (wave_a.key if wave_a else "") or previous_wave_b != (wave_b.key if wave_b else ""):
            self.waveChanged.emit()
        self.current_output_a = frame.strength_a * wave_a.feel_scale if wave_a else 0.0
        self.current_output_b = frame.strength_b * wave_b.feel_scale if wave_b else 0.0
        if frame.safe_cut:
            self.peak_limiter.reset()
            self.current_output_a = 0.0
            self.current_output_b = 0.0
        elif self.auto_output_enabled and self.device_connected_value:
            previous_peak_limit = self.peak_limiter.active_limit
            self.current_output_a, self.current_output_b, peak_limit = self.peak_limiter.apply(
                self.current_output_a,
                self.current_output_b,
                peak_active=frame.pattern_a == "peak" or frame.pattern_b == "peak",
                now_ms=self.last_game_ms if self.last_game_ms is not None else int(time.monotonic() * 1000),
                hard_cap=self.hard_cap_value,
            )
            if peak_limit is not None and previous_peak_limit is None:
                self._log(f"Climax 动态上限：前 5 秒实际最高 + 15 = {peak_limit:.1f}")
        else:
            # Do not count theoretical values while the device is disconnected
            # or manual output pause is active; the limiter follows real output.
            self.peak_limiter.reset()
        if self.auto_output_enabled and self.bridge is not None:
            self.bridge.update_auto_outputs(
                self.current_output_a if wave_a else 0,
                wave_a.v3_frames() if wave_a and self.current_output_a > 0 else (),
                wave_key_a=wave_a.key if wave_a and self.current_output_a > 0 else "idle",
                strength_b=self.current_output_b if wave_b else 0,
                frames_b=wave_b.v3_frames() if wave_b and self.current_output_b > 0 else (),
                wave_key_b=wave_b.key if wave_b and self.current_output_b > 0 else "idle",
                hard_cap=self.hard_cap_value,
            )

    def _custom_waveform(self) -> WaveformPreset:
        return WaveformPreset(
            "custom",
            self.custom_name_value,
            "用户绘制的自定义包络",
            "由用户分配的心率区间",
            "#59DCE7",
            tuple(self.custom_points_value),
            (self.custom_frequency_value,),
            source="我的波形",
        )

    def _enter_safety_idle(self, reason: str) -> None:
        if not self.auto_output_enabled:
            return
        if self.safety_wait_reason != reason:
            self._log(f"安全待机并归零：{reason}")
        self.safety_wait_reason = reason
        self.device_status_value = "安全待机 · 输出归零，等待有效游戏数据"

    def _leave_safety_idle(self) -> None:
        if not self.auto_output_enabled or not self.device_connected_value:
            return
        if self.safety_wait_reason:
            self._log("有效游戏数据已恢复；自动继续心率输出")
        self.safety_wait_reason = ""
        self.device_status_value = "设备已连接 · A/B 通道输出中"

    def _qr_data_url(self, value: str) -> str:
        if not value:
            return ""
        qr = qrcode.QRCode(version=None, box_size=5, border=2)
        qr.add_data(value)
        qr.make(fit=True)
        image = qr.make_image(fill_color="#111522", back_color="#FFFFFF")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    def _toast(self, title: str, message: str) -> None:
        self.toastRequested.emit(self._t(title), self._t(message))

    def _log(self, text: str) -> None:
        self.log_lines.append(f"{time.strftime('%H:%M:%S')}  {text}")
        self.log_lines = self.log_lines[-300:]
        self.logsChanged.emit()

    @Slot()
    def shutdown(self) -> None:
        self.poll_timer.stop()
        self.auto_output_enabled = False
        self.game_hud_enabled_value = False
        self._publish_game_hud(force=True)
        if self.hud_socket is not None:
            try:
                self.hud_socket.close()
            except OSError:
                pass
            self.hud_socket = None
        if self.worker is not None:
            self.worker.stop()
        if self.bridge is not None:
            self.bridge.stop()

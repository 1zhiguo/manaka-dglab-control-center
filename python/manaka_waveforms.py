"""Waveform presets and selection policy for the Manaka control center.

The module is device-independent.  It describes normalized envelopes for UI
preview and future DG-LAB V3 encoding, but never opens a socket or sends data.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
import time

from dglab_official_waveforms import OFFICIAL_WAVEFORMS


@dataclass(frozen=True)
class WaveformPreset:
    key: str
    name: str
    description: str
    best_for: str
    color: str
    amplitudes: tuple[int, ...]
    frequency_codes: tuple[int, ...]
    caution: str = "首次使用请从低强度开始标定"
    raw_frames: tuple[str, ...] = ()
    source: str = "Manaka 内置"
    feel_scale: float = 1.0

    def __post_init__(self) -> None:
        if not self.amplitudes:
            raise ValueError("waveform requires amplitude samples")
        if len(self.frequency_codes) not in {1, len(self.amplitudes)}:
            raise ValueError("frequency_codes must contain one value or match amplitudes")
        if any(not 0 <= value <= 100 for value in self.amplitudes):
            raise ValueError("amplitude samples must be within 0..100")
        if any(not 10 <= value <= 240 for value in self.frequency_codes):
            raise ValueError("DG-LAB V3 frequency codes must be within 10..240")
        if not 0.1 <= float(self.feel_scale) <= 1.0:
            raise ValueError("feel_scale must be within 0.1..1.0")
        for frame in self.raw_frames:
            if len(frame) != 16 or any(char not in "0123456789ABCDEF" for char in frame.upper()):
                raise ValueError("raw V3 frames must contain 16 hexadecimal characters")
            values = bytes.fromhex(frame)
            if any(not 10 <= value <= 240 for value in values[:4]) or any(value > 100 for value in values[4:]):
                raise ValueError("Invalid V3 frequency code or amplitude")

    def frequency_at(self, index: int) -> int:
        return self.frequency_codes[0] if len(self.frequency_codes) == 1 else self.frequency_codes[index % len(self.frequency_codes)]

    @lru_cache(maxsize=128)
    def v3_frames(self) -> tuple[str, ...]:
        """Return preview-ready V3 100ms frames (8-byte uppercase HEX)."""
        if self.raw_frames:
            return tuple(frame.upper() for frame in self.raw_frames)
        frames = []
        for index, amplitude in enumerate(self.amplitudes):
            frequency = self.frequency_at(index)
            frames.append((f"{frequency:02X}" * 4) + (f"{amplitude:02X}" * 4))
        return tuple(frames)


def _official_preset(
    key: str,
    name: str,
    description: str,
    best_for: str,
    color: str,
    feel_scale: float,
    caution: str = "官方波形也请从低强度开始适应",
) -> WaveformPreset:
    frames = OFFICIAL_WAVEFORMS[key]
    amplitudes = tuple(
        round(sum(int(frame[index : index + 2], 16) for index in range(8, 16, 2)) / 4)
        for frame in frames
    )
    frequencies = tuple(
        round(sum(int(frame[index : index + 2], 16) for index in range(0, 8, 2)) / 4)
        for frame in frames
    )
    return WaveformPreset(
        key,
        name,
        description,
        best_for,
        color,
        amplitudes,
        frequencies,
        caution,
        frames,
        "DG-LAB 官方",
        feel_scale,
    )


PRESETS: dict[str, WaveformPreset] = {
    "official_breath": _official_preset(
        "official_breath", "官方·呼吸", "缓慢抬升后留出充分休止", "低心率、初次适应", "#62D6E8", 0.90
    ),
    "official_heartbeat": _official_preset(
        "official_heartbeat", "官方·心跳节奏", "重拍与两次渐强回拍组合", "中心率段、强调心跳存在感", "#FF82B5", 0.80
    ),
    "official_ripple": _official_preset(
        "official_ripple", "官方·波浪涟漪", "四拍起伏中持续提高频率", "中心率到高心率的连续推进", "#78A7FF", 0.80
    ),
    "official_tide": _official_preset(
        "official_tide", "官方·潮汐", "频率与包络共同缓慢推进", "较长的持续输出段", "#9D8CFF", 0.85
    ),
    "official_pulsating": _official_preset(
        "official_pulsating", "官方·连击", "三组清晰的强弱连击", "高心率段、节奏反馈明显", "#FFC857", 0.75
    ),
    "official_gradual": _official_preset(
        "official_gradual", "官方·按捏渐强", "脉冲分段逐级加强并回落", "心率快速上升时的推进感", "#FF9671", 0.75
    ),
    "official_bouncy": _official_preset(
        "official_bouncy", "官方·渐变弹跳", "重复弹跳并逐步提高频率", "持续高心率、变化感较强", "#55E0A3", 0.75
    ),
    "official_tease2": _official_preset(
        "official_tease2", "官方·挑逗 2", "长渐强后进入逐频点按", "低到中心率的偶尔变化", "#DFA7FF", 0.80
    ),
    "breath": WaveformPreset(
        "breath",
        "呼吸",
        "缓慢起伏，留出明显休止段",
        "心率刚超过触发线、适应阶段",
        "#62D6E8",
        (0, 12, 28, 48, 70, 90, 100, 82, 58, 32, 12, 0),
        (95,),
    ),
    "heartbeat": WaveformPreset(
        "heartbeat",
        "双拍心跳",
        "主拍后跟随一次较弱回拍",
        "中段心率，强调心跳同步感",
        "#FF82B5",
        (0, 100, 22, 0, 62, 12, 0, 0),
        (78,),
    ),
    "rush": WaveformPreset(
        "rush",
        "急促心跳",
        "间隔更短、波峰更密集",
        "高心率区；仅改变节奏，不突破强度上限",
        "#FFC857",
        (15, 92, 26, 72, 18, 88, 22, 55),
        (58,),
    ),
    "tide": WaveformPreset(
        "tide",
        "潮汐",
        "连续上升后平滑回落",
        "动作进程或较长的连续段落",
        "#9D8CFF",
        (0, 12, 25, 42, 62, 82, 100, 92, 76, 56, 34, 15),
        (100, 96, 92, 88, 84, 80, 76, 80, 84, 88, 92, 96),
    ),
    "steps": WaveformPreset(
        "steps",
        "阶梯推进",
        "分段抬升，每一级保持片刻",
        "需要清晰进度反馈的动作阶段",
        "#55E0A3",
        (18, 18, 38, 38, 58, 58, 78, 78, 100, 76, 48, 22),
        (92,),
    ),
    "stream": WaveformPreset(
        "stream",
        "细流",
        "稳定、低变化的连续波形",
        "设备检查与个人低强度标定",
        "#78A7FF",
        (42, 48, 44, 50, 43, 47, 45, 49),
        (112,),
    ),
    "burst": WaveformPreset(
        "burst",
        "峰值短促",
        "短时集中波峰，随后立即归零",
        "仅用于峰值边沿，并受冷却时间限制",
        "#FF5C7A",
        (35, 100, 70, 25, 0, 0, 0, 0),
        (70,),
        "只允许短时触发；不得循环播放",
    ),
    "climax": WaveformPreset(
        "climax",
        "Climax 双击",
        "一次峰值事件内给出两下清晰高潮脉冲",
        "仅供 A/B 通道在峰值边沿同步使用",
        "#FF4778",
        (0, 35, 100, 58, 12, 0, 38, 100, 62, 0),
        (72,),
        "峰值会达到用户安全硬上限；只允许单次短时触发",
        source="Manaka 插件",
        feel_scale=1.0,
    ),
}


WAVE_ZONES = ("low", "mid", "high", "action", "peak")

DEFAULT_WAVE_MAP: dict[str, str] = {
    "low": "official_breath",
    "mid": "official_heartbeat",
    "high": "official_pulsating",
    "action": "official_tide",
    "peak": "climax",
}

LEGACY_DEFAULT_WAVE_MAP: dict[str, str] = {
    "low": "breath",
    "mid": "heartbeat",
    "high": "rush",
    "action": "tide",
    "peak": "burst",
}


# Values exposed by ExposureUnnoticed2.Master.Action.ActionType in game 1.1.3.
# Keeping the list in the desktop app makes the mapping editor useful before a
# player has triggered every action once. Unknown values received from newer
# game versions are added by the backend at runtime.
GAME_ACTION_TYPES: tuple[str, ...] = (
    "OldOnaniNormal", "OldGanimataWalk", "Pinpon", "ConbiniTakeGoods", "CrouchCry",
    "EatMedicine", "SadHandcuffAtMap", "SwitchTimeStop", "SwitchPistonMachine",
    "PickingCoat", "Pick", "Drop", "ChangeClothes", "DroppingClothes", "HandOver",
    "InsertAnalPlug", "ExtractAnalPlug", "CommonEquip", "IntoWasher", "TakeFromWasher",
    "UseBuyMachine", "DrinkWater", "PeeNormal", "TakeOffPants", "TakeOnPants",
    "TakeOffBra", "TakeOnBra", "Sad", "AttachHandcuffs", "PutHandcuffsOnMap",
    "HandcuffsAtMap", "UnlockHandcuffsAtMap", "AttachEyeMask", "SwitchVibrator",
    "PickUpItem", "SitDown", "StandUp", "PutDildoFloor", "PutDildoWall",
    "UseDildoFloorPussy1", "UseDildoFloorPussy2", "UseDildoFloorPussy3",
    "UseDildoFloorPussy4", "UseDildoFloorPussy5", "UseDildoFloorAnal1",
    "UseDildoFloorAnal2", "UseDildoFloorAnal3", "UseDildoFloorAnal4",
    "UseDildoFloorAnal5", "UseDildoFloorFella1", "UseDildoFloorFella2",
    "UseDildoFloorFella3", "UseDildoFloorFella4", "UseDildoFloorFella5",
    "UseDildoWallPussy1", "UseDildoWallPussy2", "UseDildoWallPussy3",
    "UseDildoWallPussy4", "UseDildoWallPussy5", "UseDildoWallAnal1",
    "UseDildoWallAnal2", "UseDildoWallAnal3", "UseDildoWallAnal4", "UseDildoWallAnal5",
    "UseDildoWallFella1", "UseDildoWallFella2", "UseDildoWallFella3",
    "UseDildoWallFella4", "UseDildoWallFella5", "UseDildoFloorWaitPussy",
    "UseDildoFloorWaitAnal", "UseDildoFloorWaitFella", "UseDildoWallWaitPussy",
    "UseDildoWallWaitAnal", "UseDildoWallWaitFella", "UseDildoFloorPussyEcstasyA",
    "UseDildoFloorAnalEcstasyA", "UseDildoFloorFellaEcstasyA",
    "UseDildoWallPussyEcstasyA", "UseDildoWallAnalEcstasyA",
    "UseDildoWallFellaEcstasyA", "PickDildo", "SitDildo", "SitDildoPut",
    "SitDildoPick", "SitDildoMoveAnal", "SitDildoMovePussy", "PickDildoWall",
    "GanimataWalk", "AhegaoDoublePiece", "HipShake", "GanimataHip", "KaikyakuFella",
    "Dogeza", "DogTintin", "IBalance", "WakimiseCrouch", "MituasiOnani", "Tebura",
    "PeeKaikyaku", "PeeDog", "ChikubiRotate", "OnaniYotuashi", "OnaniNeGanimata",
    "OnaniNormal", "NeKataashiage", "OnaniArmKuri", "OnaniSikoru",
    "GanimataKoshiHeko", "Haigure", "PeeStand", "DogezaUpHead", "PoseEnd",
    "SexStandBack", "SexKijoui",
)


# The game sends compact enum keys.  Keep those keys for configuration and
# matching, while presenting a readable name in the UI.
_ACTION_LABELS_ZH: dict[str, str] = {
    "None": "无动作",
    "Walking": "行走",
    "OldOnaniNormal": "旧版 · 普通自慰",
    "OldGanimataWalk": "旧版 · 岔腿行走",
    "Pinpon": "按门铃",
    "ConbiniTakeGoods": "便利店取商品",
    "CrouchCry": "蹲下哭泣",
    "EatMedicine": "服药",
    "SadHandcuffAtMap": "地图手铐 · 悲伤",
    "SwitchTimeStop": "切换时间停止",
    "SwitchPistonMachine": "切换活塞机",
    "PickingCoat": "选择外套",
    "Pick": "拾取",
    "Drop": "放下",
    "ChangeClothes": "更换服装",
    "DroppingClothes": "脱下服装",
    "HandOver": "递交物品",
    "InsertAnalPlug": "塞入肛塞",
    "ExtractAnalPlug": "取出肛塞",
    "CommonEquip": "装备道具",
    "IntoWasher": "放入洗衣机",
    "TakeFromWasher": "从洗衣机取出",
    "UseBuyMachine": "使用自动贩卖机",
    "DrinkWater": "喝水",
    "PeeNormal": "普通排尿",
    "TakeOffPants": "脱下下装",
    "TakeOnPants": "穿上下装",
    "TakeOffBra": "脱下内衣",
    "TakeOnBra": "穿上内衣",
    "Sad": "悲伤",
    "AttachHandcuffs": "戴上手铐",
    "PutHandcuffsOnMap": "把手铐放到地图",
    "HandcuffsAtMap": "使用地图手铐",
    "UnlockHandcuffsAtMap": "解开地图手铐",
    "AttachEyeMask": "戴上眼罩",
    "SwitchVibrator": "切换跳蛋",
    "PickUpItem": "拾取物品",
    "SitDown": "坐下",
    "StandUp": "起身",
    "PutDildoFloor": "放置地面假阳具",
    "PutDildoWall": "放置墙面假阳具",
    "PickDildo": "拾取假阳具",
    "SitDildo": "骑坐假阳具",
    "SitDildoPut": "放置骑坐假阳具",
    "SitDildoPick": "收起骑坐假阳具",
    "SitDildoMoveAnal": "骑坐移动 · 肛门",
    "SitDildoMovePussy": "骑坐移动 · 阴道",
    "PickDildoWall": "拾取墙面假阳具",
    "GanimataWalk": "岔腿行走",
    "AhegaoDoublePiece": "阿黑颜双 V 手势",
    "HipShake": "摇臀",
    "GanimataHip": "岔腿挺胯",
    "KaikyakuFella": "劈腿口交",
    "Dogeza": "土下座",
    "DogTintin": "小狗姿势",
    "IBalance": "I 字平衡",
    "WakimiseCrouch": "露腋蹲姿",
    "MituasiOnani": "足部自慰",
    "Tebura": "托胸姿势",
    "PeeKaikyaku": "劈腿排尿",
    "PeeDog": "小狗姿势排尿",
    "ChikubiRotate": "旋转乳头",
    "OnaniYotuashi": "四足自慰",
    "OnaniNeGanimata": "躺姿岔腿自慰",
    "OnaniNormal": "普通自慰",
    "NeKataashiage": "躺姿单腿抬起",
    "OnaniArmKuri": "手臂动作自慰",
    "OnaniSikoru": "套弄自慰",
    "GanimataKoshiHeko": "岔腿摆腰",
    "Haigure": "高衩姿势",
    "PeeStand": "站立排尿",
    "DogezaUpHead": "抬头土下座",
    "PoseEnd": "结束姿势",
    "SexStandBack": "站立后入",
    "SexKijoui": "骑乘位",
}

_ACTION_TOKEN_EN: dict[str, str] = {
    "Onani": "Masturbation",
    "Ganimata": "Wide-legged",
    "Pee": "Urination",
    "Kaikyaku": "Spread-legged",
    "Fella": "Oral",
    "Pussy": "Vaginal",
    "Anal": "Anal",
    "Dogeza": "Dogeza",
    "Chikubi": "Nipple",
    "Kijoui": "Cowgirl",
}


# Exact reference-project default frames; MIT attribution in THIRD_PARTY_NOTICES.
DONOR_WAVEFORMS = [
    ('donor_vibrator', '官方示例 - 呼吸', (
        '0A0A0A0A00000000', '0A0A0A0A14141414', '0A0A0A0A28282828', '0A0A0A0A3C3C3C3C',
        '0A0A0A0A50505050', '0A0A0A0A64646464', '0A0A0A0A64646464', '0A0A0A0A64646464',
        '0A0A0A0A00000000', '0A0A0A0A00000000', '0A0A0A0A00000000', '0A0A0A0A00000000',
    )),
    ('donor_piston', '默认 - 活塞机', (
        '2A2A2A2A64461450', '3030303014506428', '37373737001E5A64', '303030304614003C',
    )),
    ('donor_climax', '默认 - 高潮', (
        'B4B4B4B4001E5064', 'C8C8C8C814466428', 'DCDCDCDC46641E00', 'C8C8C8C8643C0A28',
    )),
]
for _key, _name, _frames in DONOR_WAVEFORMS:
    PRESETS[_key] = WaveformPreset(_key, _name, "参考项目完整默认波形", "振动器 / 活塞机 / 高潮", "#59DCE7",
        tuple(round(sum(bytes.fromhex(frame)[4:])/4) for frame in _frames), (int(_frames[0][:2],16),),
        raw_frames=_frames, source="SecretFlasherManaka2_X_DGLAB")


def _humanize_action_name(action: str) -> str:
    value = str(action or "None").strip() or "None"
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", words)
    for source, target in _ACTION_TOKEN_EN.items():
        words = re.sub(rf"\b{re.escape(source)}\b", target, words)
    return words


def action_label(action: str, language: str = "zh") -> str:
    """Return a localized display label without changing the enum key."""

    value = str(action or "None").strip() or "None"
    if language != "zh":
        return _humanize_action_name(value)

    fixed = _ACTION_LABELS_ZH.get(value)
    if fixed:
        return fixed

    dildo_action = re.fullmatch(r"UseDildo(Floor|Wall)(Pussy|Anal|Fella)([1-5])", value)
    if dildo_action:
        location, action_type, number = dildo_action.groups()
        location_label = {"Floor": "地面", "Wall": "墙面"}[location]
        type_label = {"Pussy": "阴道", "Anal": "肛门", "Fella": "口交"}[action_type]
        return f"{location_label}假阳具 · {type_label}动作 {number}"

    dildo_wait = re.fullmatch(r"UseDildo(Floor|Wall)Wait(Pussy|Anal|Fella)", value)
    if dildo_wait:
        location, action_type = dildo_wait.groups()
        location_label = {"Floor": "地面", "Wall": "墙面"}[location]
        type_label = {"Pussy": "阴道", "Anal": "肛门", "Fella": "口交"}[action_type]
        return f"{location_label}假阳具 · {type_label}待机"

    dildo_peak = re.fullmatch(r"UseDildo(Floor|Wall)(Pussy|Anal|Fella)EcstasyA", value)
    if dildo_peak:
        location, action_type = dildo_peak.groups()
        location_label = {"Floor": "地面", "Wall": "墙面"}[location]
        type_label = {"Pussy": "阴道", "Anal": "肛门", "Fella": "口交"}[action_type]
        return f"{location_label}假阳具 · {type_label}高潮"

    # Newer game/plugin versions may introduce enums unknown to this release.
    # A spaced fallback remains searchable and is much easier to read than the
    # original compact identifier.
    return _humanize_action_name(value)

_ACTION_OFF = {
    "None", "Pinpon", "ConbiniTakeGoods", "CrouchCry", "EatMedicine",
    "SadHandcuffAtMap", "SwitchTimeStop", "SwitchPistonMachine", "PickingCoat",
    "Pick", "Drop", "ChangeClothes", "DroppingClothes", "HandOver",
    "InsertAnalPlug", "ExtractAnalPlug", "CommonEquip", "IntoWasher", "TakeFromWasher",
    "UseBuyMachine", "DrinkWater", "PeeNormal", "TakeOffPants", "TakeOnPants",
    "TakeOffBra", "TakeOnBra", "Sad", "AttachHandcuffs", "PutHandcuffsOnMap",
    "HandcuffsAtMap", "UnlockHandcuffsAtMap", "AttachEyeMask", "SwitchVibrator",
    "PickUpItem", "SitDown", "StandUp", "PutDildoFloor", "PutDildoWall", "PickDildo",
    "SitDildoPut", "SitDildoPick", "PickDildoWall", "PeeKaikyaku", "PeeDog",
    "PeeStand", "PoseEnd",
}

_ACTION_STATIC = {
    "UseDildoFloorWaitPussy", "UseDildoFloorWaitAnal", "UseDildoFloorWaitFella",
    "UseDildoWallWaitPussy", "UseDildoWallWaitAnal", "UseDildoWallWaitFella",
    "SitDildo", "AhegaoDoublePiece", "Dogeza", "DogTintin", "IBalance",
    "WakimiseCrouch", "Tebura", "NeKataashiage", "Haigure", "DogezaUpHead",
}


def action_style(action: str) -> str:
    """Classify an action for UI labels and safe default waveform selection."""

    value = str(action or "None")
    if value in _ACTION_OFF:
        return "off"
    if value in _ACTION_STATIC:
        return "static"
    return "rhythmic"


def recommended_wave_for_action(action: str) -> str:
    """Return a conservative default based only on the game's action type."""

    style = action_style(action)
    if style == "off":
        return "off"
    if style == "static":
        return "official_breath"
    value = str(action or "")
    if "Onani" in value or "Chikubi" in value:
        return "official_heartbeat"
    if value in {"OldGanimataWalk", "GanimataWalk"}:
        return "official_tide"
    return "official_pulsating"

ZONE_LABELS: dict[str, str] = {
    "low": "低心率段",
    "mid": "中心率段",
    "high": "高心率段",
    "action": "动作进程",
    "peak": "峰值边沿",
}

ZONE_REASONS: dict[str, str] = {
    "low": "刚超过触发 BPM，使用留白较多的柔和节奏",
    "mid": "心率处于个性化范围中段，使用清晰双拍",
    "high": "接近满幅 BPM，缩短间隔但不提高安全上限",
    "action": "B 通道跟随动作进程，使用连续起伏",
    "peak": "只在峰值边沿短时触发，之后回到动作波形",
}


def pattern_zone(pattern: str) -> str | None:
    return {
        "heartbeat-soft": "low",
        "heartbeat": "mid",
        "heartbeat-fast": "high",
        "action-ramp": "action",
        "peak": "peak",
    }.get(pattern)


def sanitize_wave_map(value: object) -> dict[str, str]:
    result = dict(DEFAULT_WAVE_MAP)
    if isinstance(value, dict):
        for zone in WAVE_ZONES:
            preset = value.get(zone)
            if preset in PRESETS or preset == "custom":
                result[zone] = preset
    return result


def resolve_waveform(
    pattern: str,
    mode: str,
    fixed_preset: str,
    wave_map: dict[str, str],
    custom_preset: WaveformPreset | None = None,
    library: dict | None = None,
) -> WaveformPreset | None:
    zone = pattern_zone(pattern)
    if zone is None:
        return None
    available = dict(PRESETS)
    available.update(library or {})
    if custom_preset is not None:
        available["custom"] = custom_preset
    # Peak edges always use their dedicated synchronized A/B mapping. A fixed
    # preset still applies to every non-peak state.
    if mode == "fixed" and zone != "peak" and fixed_preset in available:
        return available[fixed_preset]
    mapping = sanitize_wave_map(wave_map)
    if library:
        mapping.update({zone:key for zone,key in wave_map.items() if zone in WAVE_ZONES and key in library})
    return available.get(mapping[zone], PRESETS[DEFAULT_WAVE_MAP[zone]])


class WaveformSelector:
    """Stateful anti-jitter selector for future device queue switching.

    Heart-rate zone changes on channel A must remain stable briefly before the
    selected waveform changes. Idle cuts and channel-B event changes are
    immediate.
    """

    def __init__(self, hold_seconds: float = 0.8) -> None:
        self.hold_seconds = max(0.0, float(hold_seconds))
        self.current: dict[str, WaveformPreset | None] = {"A": None, "B": None}
        self.pending: dict[str, WaveformPreset | None] = {"A": None, "B": None}
        self.pending_since: dict[str, float] = {"A": 0.0, "B": 0.0}

    def reset(self) -> None:
        self.current = {"A": None, "B": None}
        self.pending = {"A": None, "B": None}
        self.pending_since = {"A": 0.0, "B": 0.0}

    def select(
        self,
        channel: str,
        pattern: str,
        mode: str,
        fixed_preset: str,
        wave_map: dict[str, str],
        custom_preset: WaveformPreset | None = None,
        now: float | None = None,
        library: dict | None = None,
    ) -> WaveformPreset | None:
        channel = "B" if channel == "B" else "A"
        candidate = resolve_waveform(pattern, mode, fixed_preset, wave_map, custom_preset, library)
        timestamp = time.monotonic() if now is None else float(now)
        if candidate is None:
            self.current[channel] = None
            self.pending[channel] = None
            return None

        current = self.current[channel]
        if current is None or channel == "B" or self.hold_seconds == 0:
            self.current[channel] = candidate
            self.pending[channel] = None
            return candidate
        if current.key == candidate.key:
            self.current[channel] = candidate
            self.pending[channel] = None
            return candidate

        pending = self.pending[channel]
        if pending is None or pending.key != candidate.key:
            self.pending[channel] = candidate
            self.pending_since[channel] = timestamp
            return current
        if timestamp - self.pending_since[channel] >= self.hold_seconds:
            self.current[channel] = candidate
            self.pending[channel] = None
            return candidate
        return current

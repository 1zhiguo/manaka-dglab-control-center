"""Waveform presets and selection policy for the Manaka control center.

The module is device-independent.  It describes normalized envelopes for UI
preview and future DG-LAB V3 encoding, but never opens a socket or sends data.
"""

from __future__ import annotations

from dataclasses import dataclass
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

    def frequency_at(self, index: int) -> int:
        return self.frequency_codes[0] if len(self.frequency_codes) == 1 else self.frequency_codes[index % len(self.frequency_codes)]

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
) -> WaveformPreset | None:
    zone = pattern_zone(pattern)
    if zone is None:
        return None
    available = dict(PRESETS)
    if custom_preset is not None:
        available["custom"] = custom_preset
    # Peak edges always use their dedicated synchronized A/B mapping. A fixed
    # preset still applies to every non-peak state.
    if mode == "fixed" and zone != "peak" and fixed_preset in available:
        return available[fixed_preset]
    mapping = sanitize_wave_map(wave_map)
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
    ) -> WaveformPreset | None:
        channel = "B" if channel == "B" else "A"
        candidate = resolve_waveform(pattern, mode, fixed_preset, wave_map, custom_preset)
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

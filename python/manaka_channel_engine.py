"""Independent channel mapping, with no Qt, files, network or device side effects."""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field, replace
import math

from manaka_trigger_engine import ManakaTriggerEngine, TriggerFrame
from manaka_telemetry_schema import detections

SCHEMA_VERSION = 4
SOURCES = ("heart", "action", "action_active", "ecstasy", "vibrator", "piston", "npc_alert", "device")


def number(value, low=0.0, high=100.0):
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f"Value must be finite and in {low}..{high}")
    return result


@dataclass(frozen=True)
class Binding:
    source: str = "heart"
    weight: float = 1.0
    low: float = 90.0
    high: float = 160.0
    weak: float = 30.0
    medium: float = 50.0
    strong: float = 70.0
    wave: str = "auto"
    phase_ms: int = 0
    input_start: float = 0.0
    input_full: float = 100.0
    curve: str = "linear"

    @classmethod
    def parse(cls, raw):
        binding = cls(**raw)
        if binding.source not in SOURCES:
            raise ValueError("Unknown detection source")
        number(binding.weight, 0, 10)
        number(binding.low, 0, 300)
        number(binding.high, 0, 300)
        if binding.low >= binding.high:
            raise ValueError("Detection start must be below full scale")
        for value in (binding.weak, binding.medium, binding.strong):
            number(value)
        if binding.source in {"piston", "device"} and not binding.weak <= binding.medium <= binding.strong:
            raise ValueError("Weak/medium/strong percentages must be ordered")
        if binding.source == "vibrator" and binding.weak > binding.strong:
            raise ValueError("Weak percentage must not exceed strong percentage")
        if not isinstance(binding.wave, str):
            raise ValueError("Invalid waveform key")
        number(binding.phase_ms, 0, 8000)
        number(binding.input_start)
        number(binding.input_full, binding.input_start, 100)
        if binding.input_full <= binding.input_start or binding.curve not in {"linear","ease_in","ease_out"}:
            raise ValueError("Invalid input range or mapping curve")
        return binding


@dataclass(frozen=True)
class EventSettings:
    enabled: bool = True
    percent: float = 90.0
    duration_ms: int = 1300
    cooldown_ms: int = 5000

    @classmethod
    def parse(cls, raw):
        event = cls(**raw)
        if type(event.enabled) is not bool:
            raise ValueError("Event enabled must be boolean")
        number(event.percent)
        number(event.duration_ms, 100, 5000)
        number(event.cooldown_ms, event.duration_ms, 60000)
        return event


@dataclass(frozen=True)
class ChannelSettings:
    enabled: bool = True
    device: str = "none"
    minimum: float = 0.0
    maximum: float = 20.0
    hard_cap: float = 30.0
    attack: float = 12.0
    release: float = 24.0
    combine: str = "max"
    bindings: tuple[Binding, ...] = field(default_factory=lambda: (Binding(),))
    climax: EventSettings = field(default_factory=EventSettings)
    failure: EventSettings = field(default_factory=lambda: EventSettings(enabled=False))

    @classmethod
    def parse(cls, raw):
        raw = dict(raw)
        raw["bindings"] = tuple(Binding.parse(item) for item in raw.get("bindings", [{}]))
        raw["climax"] = EventSettings.parse(raw.get("climax", {}))
        raw["failure"] = EventSettings.parse(raw.get("failure", {"enabled": False}))
        channel = cls(**raw)
        if type(channel.enabled) is not bool:
            raise ValueError("Channel enabled must be boolean")
        if channel.device not in {"none", "vibrator", "piston"}:
            raise ValueError("Unknown channel device")
        if channel.device == "none" and any(x.source == "device" for x in channel.bindings):
            raise ValueError("设备档位强度需要先绑定振动器或活塞机 / Bind a device before selecting its level")
        number(channel.minimum, 0, 200)
        number(channel.maximum, channel.minimum, 200)
        number(channel.hard_cap, 0, 200)
        number(channel.attack, .1, 100)
        number(channel.release, .1, 100)
        if channel.combine not in {"max", "weighted"} or not 1 <= len(channel.bindings) <= 6:
            raise ValueError("Choose max/weighted and 1..6 bindings")
        return channel


@dataclass(frozen=True)
class MappingSettings:
    schema: int = SCHEMA_VERSION
    mode: str = "independent"
    # Compatibility field for old programmatic callers. Persisted schema 4
    # uses only A/B limits; this field stays at the protocol bound of 200.
    global_cap: float = 200.0
    intensity_sync: str = "off"
    A: ChannelSettings = field(default_factory=ChannelSettings)
    B: ChannelSettings = field(default_factory=lambda: ChannelSettings(bindings=(Binding(source="action", low=0, high=100),)))

    def to_dict(self):
        result = asdict(self)
        # QVariantMap must contain actual lists, not opaque Python tuples.
        for key in "AB":
            result[key]["bindings"] = list(result[key]["bindings"])
        return result

    @classmethod
    def parse(cls, raw):
        if raw.get("schema") not in {2, 3, SCHEMA_VERSION} or raw.get("mode") not in {"independent", "legacy_v1"}:
            raise ValueError("Unsupported channel configuration")
        channels = {key:ChannelSettings.parse(raw[key]) for key in "AB"}
        if raw["schema"] == 2:
            old_cap = number(raw.get("global_cap", 30))
            channels = {key:replace(value, hard_cap=min(old_cap,value.hard_cap)) for key,value in channels.items()}
        sync = raw.get("intensity_sync", "off")
        if sync not in {"off", "A_to_B", "B_to_A"}:
            raise ValueError("Invalid intensity sync direction")
        return cls(mode=raw["mode"], intensity_sync=sync, **channels)


def migrate_settings(saved):
    """Old settings retain the old engine until the user explicitly switches."""
    if "channel_mapping" in saved:
        return MappingSettings.parse(saved["channel_mapping"])
    if not any(key in saved for key in ("hard_cap", "min_strength", "output_max", "trigger_bpm", "full_bpm", "pulse_channel_sources")):
        return MappingSettings(
            A=ChannelSettings(device="vibrator", bindings=(Binding(source="device"),)),
            B=ChannelSettings(device="piston", bindings=(Binding(source="device"),)))
    cap = number(saved.get("hard_cap", 30), 0, 200)
    ordinary = dict(minimum=number(saved.get("min_strength", 5), 0, 200),
                    maximum=number(saved.get("output_max", 30), 0, 200), hard_cap=cap)
    return MappingSettings(mode="legacy_v1",
        A=ChannelSettings(**ordinary, bindings=(Binding(low=number(saved.get("trigger_bpm", 90), 0, 300),
                                                       high=number(saved.get("full_bpm", 160), 0, 300)),)),
        B=ChannelSettings(**ordinary, bindings=(Binding(source="action", low=0, high=100),)))


class ChannelPeakLimiter:
    """Separate histories; final limiting is applied after waveform gain."""
    def __init__(self):
        self.history = {key: deque(maxlen=512) for key in "AB"}
        self.active = {key: None for key in "AB"}

    def reset(self):
        for key in "AB":
            self.history[key].clear()
            self.active[key] = None

    def apply(self, channel, value, *, peak, now, cap, record=True, observed=None):
        history = self.history[channel]
        while history and history[0][0] < now - 5:
            history.popleft()
        value = max(0, min(float(value), float(cap), 200))
        if peak:
            if self.active[channel] is None:
                self.active[channel] = max((sample for _, sample in history), default=0) + 15
            return min(value, self.active[channel])
        self.active[channel] = None
        if record:
            history.append((now, value if observed is None else max(0,min(float(observed),cap))))
        return value


class ChannelEngine:
    def __init__(self, settings=None):
        self.settings = settings or MappingSettings()
        self.output = {key: 0.0 for key in "AB"}
        self.event_until = {key: 0 for key in "AB"}
        self.event_kind = {key: "" for key in "AB"}
        self.last_event = {(key, event): -100000 for key in "AB" for event in ("climax", "failure")}
        self.previous_orgasm = False
        self.previous_failure = False
        self.baseline = False
        self.selected = {key: None for key in "AB"}
        self.components = {key: () for key in "AB"}
        self.unavailable = {key: () for key in "AB"}

    def force_safe_cut(self, reason):
        self.output = {key: 0.0 for key in "AB"}
        self.event_until = {key: 0 for key in "AB"}
        self.selected = {key: None for key in "AB"}
        self.components = {key: () for key in "AB"}
        return TriggerFrame(0, 0, "idle", "idle", reason, (), True)

    def source_level(self, binding, packet, state=None):
        state = state or detections(packet)[binding.source]
        if not state.available:
            return 0, False, False
        if binding.source == "heart":
            bpm = state.level
            return self._curve(max(0, min(1, (bpm-binding.low)/(binding.high-binding.low))),binding), bpm >= binding.low, True
        if binding.source == "action_active":
            return 1.0 if state.active else 0.0, state.active, True
        if binding.source in {"action", "ecstasy"}:
            value = state.level*100
            level = max(0,min(1,(value-binding.input_start)/(binding.input_full-binding.input_start)))
            return self._curve(level,binding), state.active and value >= binding.input_start, True
        if binding.source == "vibrator":
            return (binding.strong if state.mode == "high" else binding.weak) / 100, state.active, True
        if binding.source == "piston":
            value = {"0": 0, "1": binding.weak, "2": binding.medium, "3": binding.strong}[state.mode]
            return value / 100, state.active, True
        if binding.source == "npc_alert":
            value = state.level*100
            level = max(0,min(1,(value-binding.input_start)/(binding.input_full-binding.input_start)))
            return self._curve(level,binding), state.active and value >= binding.input_start, True
        return 0, False, False

    @staticmethod
    def _curve(level, binding):
        return level**2 if binding.curve == "ease_in" else level**.5 if binding.curve == "ease_out" else level

    def evaluate(self, packet, dt=.1, event_states=None):
        paused = (packet.get("paused") or packet.get("systemMenuOpen") or
                  float(packet.get("timeScale", 1)) <= .001 or float(packet.get("managedTimeScale", 1)) <= .001)
        failure = bool(packet.get("gameOver"))
        orgasm = bool(packet.get("orgasm", packet.get("climaxActive", False)))
        now = int(packet.get("monotonicMs", 0))
        edges = dict(climax=self.baseline and orgasm and not self.previous_orgasm,
                     failure=self.baseline and failure and not self.previous_failure)
        self.previous_orgasm, self.previous_failure = orgasm, failure
        self.baseline = True
        if paused or packet.get("stage", "None") in {"", "None"} or packet.get("panic") or packet.get("armed") is False:
            return self.force_safe_cut("game-paused" if paused else "not-in-playable-scene")
        events = []
        patterns = {}
        states = detections(packet)
        for key in "AB":
            config = getattr(self.settings, key)
            missing, contributions = [], []
            for binding in config.bindings:
                effective = replace(binding,source=config.device) if binding.source == "device" else binding
                level, active, available = self.source_level(effective, packet, states[effective.source])
                if not available:
                    missing.append(binding.source)
                if available and active and binding.wave != "off":
                    target = (level * config.maximum if effective.source in {"vibrator", "piston"}
                              else config.minimum + level * (config.maximum-config.minimum))
                    contributions.append((target * binding.weight, binding))
            self.unavailable[key] = tuple(missing)
            self.components[key] = tuple(contributions)
            winner = max(contributions, key=lambda item: item[0], default=(0, None))
            self.selected[key] = winner[1]
            if config.combine == "weighted":
                # Keep inactive/unavailable sources in the denominator: losing
                # one source must not amplify the remaining sources. Preserve
                # the persisted weights and the existing "weighted" key.
                total_weight = sum(binding.weight for binding in config.bindings)
                target = sum(item[0] for item in contributions) / total_weight if total_weight > 0 else 0
            else:
                target = winner[0]
            target = max(0, min(config.maximum, target))
            pattern = "action-ramp" if winner[1] and winner[1].source == "action" else "heartbeat" if winner[1] and winner[1].source == "heart" else "source"
            if winner[1] and winner[1].source == "heart":
                heart_level, _, _ = self.source_level(winner[1],packet,states["heart"])
                pattern = "heartbeat-soft" if heart_level < .3 else "heartbeat" if heart_level < .7 else "heartbeat-fast"
            if not target:
                pattern = "idle"
            if config.device != "none":
                device = states[config.device]
                if not device.available:
                    missing.append(config.device)
                if not device.available or not device.active:
                    target, pattern = 0, "idle"
                self.unavailable[key] = tuple(dict.fromkeys(missing))
            for kind in ("climax", "failure"):
                event = getattr(config, kind)
                if event_states is None and config.enabled and event.enabled and edges[kind] and now-self.last_event[key, kind] >= event.cooldown_ms:
                    self.last_event[key, kind] = now
                    self.event_until[key] = now + event.duration_ms
                    self.event_kind[key] = kind
                    events.append(f"{key}:{kind}")
                    break
            event_active = now < self.event_until[key]
            if event_states is not None:
                selected_event = event_states.get(key)
                event_active = selected_event in {"climax", "failure"} and config.enabled
                if event_active:
                    if self.event_kind[key] != selected_event:
                        events.append(f"{key}:{selected_event}")
                    self.event_kind[key] = selected_event
                else:
                    self.event_kind[key] = ""
            if event_active:
                target = config.maximum * getattr(config, self.event_kind[key]).percent / 100
                pattern = "peak"
            if failure and not event_active:
                target, pattern = 0, "idle"
            cap = min(config.hard_cap, self.settings.global_cap)
            target = max(0, min(cap, target))
            immediate = not config.enabled or failure or event_active or target == 0
            if immediate:
                self.output[key] = target if config.enabled else 0
            else:
                step = max(0, min(.5, dt)) * (config.attack if target > self.output[key] else config.release)
                self.output[key] += max(-step, min(step, target-self.output[key]))
                self.output[key] = min(self.output[key], cap)
            patterns[key] = pattern if self.output[key] else "idle"
        return TriggerFrame(round(self.output["A"], 3), round(self.output["B"], 3), patterns["A"], patterns["B"],
                            "independent-mapping", tuple(events), failure and not any(self.output.values()))

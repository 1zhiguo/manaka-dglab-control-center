"""One deterministic waveform owner per channel; independent of intensity math."""
from dataclasses import dataclass, field
import math

from manaka_telemetry_schema import detections
from manaka_waveforms import DEFAULT_WAVE_MAP, GAME_ACTION_TYPES, recommended_wave_for_action

SOURCES = ("always", "action", "heart", "ecstasy", "vibrator", "piston", "npc_alert", "climax", "failure")


def bounded(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Expected a number in {low}..{high}")
    return value


@dataclass(frozen=True)
class WaveRule:
    id: str
    source: str = "always"
    wave: str = "official_breath"
    value: str = ""
    minimum: float = 0
    maximum: float = 300
    priority: int = 10
    stable_ms: int = 300
    hold_ms: int = 800
    transition: str = "immediate"
    playback: str = "loop"
    duration_ms: int = 1300
    cooldown_ms: int = 5000
    enabled: bool = True

    @classmethod
    def parse(cls, raw):
        rule = cls(**raw)
        if not rule.id or len(rule.id) > 120 or rule.source not in SOURCES:
            raise ValueError("Invalid rule ID or detection source")
        if not isinstance(rule.wave, str) or not isinstance(rule.value, str) or type(rule.enabled) is not bool:
            raise ValueError("Invalid rule fields")
        bounded(rule.minimum, 0, 300); bounded(rule.maximum, rule.minimum, 300)
        bounded(rule.priority, 0, 1000)
        for value in (rule.stable_ms, rule.hold_ms):
            bounded(value, 0, 10000)
        bounded(rule.duration_ms, 100, 60000)
        bounded(rule.cooldown_ms, rule.duration_ms, 120000)
        if rule.transition not in {"immediate", "cycle"} or rule.playback not in {"loop", "once"}:
            raise ValueError("Invalid playback/transition mode")
        return rule


@dataclass(frozen=True)
class ChannelRules:
    default_wave: str = "official_breath"
    default_playback: str = "loop"
    rules: tuple[WaveRule, ...] = ()

    @classmethod
    def parse(cls, raw):
        value = cls(raw["default_wave"], raw.get("default_playback", "loop"), tuple(WaveRule.parse(x) for x in raw.get("rules", [])))
        if not isinstance(value.default_wave, str) or value.default_playback not in {"loop", "once"}:
            raise ValueError("Invalid default waveform")
        if len(value.rules) > 128 or len({x.id for x in value.rules}) != len(value.rules):
            raise ValueError("Rules need unique IDs (at most 128 per channel)")
        return value


@dataclass(frozen=True)
class WavePolicy:
    A: ChannelRules = field(default_factory=ChannelRules)
    B: ChannelRules = field(default_factory=lambda: ChannelRules("official_tide"))
    schema: int = 1

    def to_dict(self):
        from dataclasses import asdict
        return {"schema": 1, **{key: {**asdict(getattr(self, key)), "rules": [asdict(x) for x in getattr(self, key).rules]} for key in "AB"}}

    @classmethod
    def parse(cls, raw):
        if raw.get("schema") != 1:
            raise ValueError("Unsupported waveform policy")
        return cls(ChannelRules.parse(raw["A"]), ChannelRules.parse(raw["B"]))


def migrate_policy(saved, mapping):
    if "wave_workbench" in saved:
        return WavePolicy.parse(saved["wave_workbench"])
    waves = dict(DEFAULT_WAVE_MAP, **saved.get("wave_map", {}))
    fixed = saved.get("wave_mode") == "fixed"
    channels = {}
    for key in "AB":
        config = getattr(mapping, key)
        rules = []
        migrated_actions = False
        for index, binding in enumerate(config.bindings):
            if binding.wave == "off":
                continue
            prefix = f"migrated-{key}-{index}"
            if binding.wave != "auto":
                rules.append(WaveRule(prefix, binding.source, binding.wave, priority=30-index))
            elif not fixed and binding.source == "action":
                if migrated_actions:
                    continue
                migrated_actions = True
                actions = dict((action, recommended_wave_for_action(action)) for action in GAME_ACTION_TYPES)
                actions.update(saved.get("action_wave_map", {}))
                grouped = {}
                for action, wave in actions.items():
                    grouped.setdefault(wave, []).append(action)
                for number, (wave, actions) in enumerate(grouped.items()):
                    rules.append(WaveRule(f"{prefix}-{number}", "action", wave, value="|".join(actions), priority=20))
            elif not fixed and binding.source == "heart":
                span = binding.high-binding.low
                for number, (zone, start, end) in enumerate((("low", binding.low, binding.low+.3*span), ("mid", binding.low+.3*span, binding.low+.7*span), ("high", binding.low+.7*span, 300))):
                    rules.append(WaveRule(f"{prefix}-{number}", "heart", waves[zone], minimum=start, maximum=end, priority=20+number))
        for event_name in ("climax", "failure"):
            event = getattr(config, event_name)
            rules.append(WaveRule(f"event-{key}-{event_name}", event_name, waves.get("peak", "climax"),
                priority=100, stable_ms=0, hold_ms=0, playback="once", duration_ms=event.duration_ms,
                cooldown_ms=event.cooldown_ms, enabled=event.enabled))
        default_wave = saved.get("fixed_wave", "official_heartbeat") if fixed else waves["mid" if key == "A" else "action"]
        if not any(name in saved for name in ("wave_mode", "wave_map", "channel_mapping")) and config.device != "none":
            default_wave = "donor_"+config.device
            from dataclasses import replace
            rules = [replace(rule, wave="donor_climax") if rule.source == "climax" else rule for rule in rules]
        channels[key] = ChannelRules(default_wave, rules=tuple(rules))
    return WavePolicy(**channels)


@dataclass(frozen=True)
class Selection:
    wave: str
    token: str
    loop: bool
    reason: str
    transition: str = "immediate"


class WaveRouter:
    def __init__(self, policy):
        self.policy = policy
        self.reset()

    def reset(self):
        self.current = {key: None for key in "AB"}
        self.entered = {key: 0. for key in "AB"}
        self.pending = {key: (None, 0.) for key in "AB"}
        self.cycle_after = {key: 0. for key in "AB"}
        self.serial = {key: 0 for key in "AB"}
        self.previous = None
        self.events = {}
        self.last_event = {}

    def evaluate(self, packet, now, period):
        states = detections(packet)
        edges = {"climax": bool(packet.get("orgasm", packet.get("climaxActive", False))), "failure": bool(packet.get("gameOver"))}
        result = {}
        for key in "AB":
            config = getattr(self.policy, key)
            candidates = []
            for index, rule in enumerate(config.rules):
                if not rule.enabled:
                    continue
                if rule.source in edges:
                    event_key = (key, rule.id)
                    if self.previous is not None and edges[rule.source] and not self.previous[rule.source] and now-self.last_event.get(event_key, -1e9) >= rule.cooldown_ms/1000:
                        self.last_event[event_key] = now
                        self.events[event_key] = now+rule.duration_ms/1000
                    matched = now < self.events.get(event_key, -1)
                elif rule.source == "always":
                    matched = True
                else:
                    state = states["action_active" if rule.source == "action" else rule.source]
                    value = state.level if rule.source == "heart" else state.level*100
                    matched = state.available and state.active and (rule.source == "action" or rule.minimum <= value <= rule.maximum)
                    if rule.source == "action" and rule.value:
                        matched = matched and str(packet.get("action", "")) in rule.value.split("|")
                    elif rule.source in {"vibrator", "piston"} and rule.value:
                        mode = {"1":"low", "2":"medium", "3":"high"}.get(state.mode, state.mode)
                        matched = matched and mode == rule.value.lower()
                if matched:
                    rank = 2 if rule.source == "climax" else 1 if rule.source == "failure" else 0
                    candidates.append((rank*10000+rule.priority, -index, rule))
            candidate = max(candidates, default=(0, 0, None), key=lambda x: x[:2])[2]
            old = self.current[key]
            identity = candidate.id if candidate else "default"
            old_identity = old.id if old else "default"
            first = self.serial[key] == 0
            event_change = (candidate and candidate.source in edges) or (old and old.source in edges)
            if first or identity != old_identity:
                duration = max(.1, period(key, old.wave if old else config.default_wave))
                if self.pending[key][0] != identity:
                    self.pending[key] = (identity, now)
                    elapsed = max(0, now-self.entered[key])
                    self.cycle_after[key] = self.entered[key]+(math.floor(elapsed/duration)+1)*duration
                stable = candidate.stable_ms/1000 if candidate else 0
                held = old.hold_ms/1000 if old else 0
                elapsed = max(0, now-self.entered[key])
                boundary = now >= self.cycle_after[key] or (old and old.playback == "once" and elapsed >= duration)
                cycle = candidate and candidate.transition == "cycle"
                if first or event_change or (now-self.pending[key][1] >= stable and elapsed >= held and (not cycle or boundary)):
                    self.current[key] = candidate
                    self.entered[key] = now
                    self.serial[key] += 1
            else:
                self.pending[key] = (identity, now)
            selected = self.current[key]
            result[key] = Selection(selected.wave if selected else config.default_wave,
                f"{key}:{self.serial[key]}", (selected.playback if selected else config.default_playback) == "loop",
                f"{selected.id} · {selected.source}" if selected else "default",
                selected.transition if selected and selected.source not in edges else "immediate")
        self.previous = edges
        return result

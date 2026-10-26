"""Qt-free realtime processor. The GUI consumes immutable display snapshots."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
import queue
import threading
import time

from manaka_channel_engine import ChannelEngine, ChannelPeakLimiter, MappingSettings
from manaka_trigger_engine import ManakaTriggerEngine, RollingPeakLimiter, TriggerFrame
from manaka_waveforms import PRESETS, WaveformPreset, WaveformSelector, recommended_wave_for_action
from manaka_wave_rules import WavePolicy, WaveRouter, migrate_policy, Selection
from manaka_telemetry_schema import detections
from manaka_pulse_routing import route_frame


class DisplayMailbox:
    """One latest state plus bounded discrete UI events; output never uses this."""
    def __init__(self, capacity=256):
        self.events = deque(maxlen=capacity)
        self.latest = {}
        self.critical = {}
        self.lock = threading.Lock()
        self.coalesced = 0
        self.dropped_events = 0

    def put(self, item):
        with self.lock:
            kind, payload = item
            if kind == "progress_result":
                key = "progress:"+str(payload.get("id",""))
                if key not in self.critical and len(self.critical) >= 64:
                    self.critical.pop(next(iter(self.critical)))
                self.critical[key] = item
            elif kind == "listener" or (kind == "dglab" and payload.get("event") != "feedback"):
                key = "listener" if kind == "listener" else "ready" if payload.get("event") == "ready" else "connection"
                self.critical[key] = item
            elif kind in {"telemetry", "runtime_snapshot"}:
                self.coalesced += kind in self.latest
                self.latest[kind] = item
            else:
                if len(self.events) == self.events.maxlen:
                    self.dropped_events += 1
                self.events.append(item)

    def get_nowait(self):
        with self.lock:
            if self.critical:
                return self.critical.pop(next(iter(self.critical)))
            if self.events:
                return self.events.popleft()
            if self.latest:
                key = next(iter(self.latest))
                return self.latest.pop(key)
            raise queue.Empty

    def qsize(self):
        with self.lock:
            return len(self.events) + len(self.latest) + len(self.critical)


@dataclass(frozen=True)
class RuntimeConfig:
    mapping: MappingSettings = field(default_factory=MappingSettings)
    legacy: tuple = (("max_strength", 30), ("min_strength", 5), ("output_max", 30), ("trigger_bpm", 90), ("full_bpm", 160))
    wave_mode: str = "smart"
    fixed_wave: str = "official_heartbeat"
    wave_map: tuple = ()
    custom: WaveformPreset = PRESETS["heartbeat"]
    action_map: tuple = ()
    library: tuple = ()
    wave_policy: WavePolicy | None = None
    pulse_sources: tuple = (("A", "heart"), ("B", "action"))


@dataclass(frozen=True)
class OutputSnapshot:
    packet: dict
    received_at: float
    frame: TriggerFrame
    wave_a: WaveformPreset | None
    wave_b: WaveformPreset | None
    output_a: float
    output_b: float
    missing_a: tuple = ()
    missing_b: tuple = ()
    reason_a: str = ""
    reason_b: str = ""


class RealtimeProcessor:
    def __init__(self, config, bridge, messages, *, clock=time.monotonic):
        self.lock = threading.RLock()
        self.bridge = bridge
        self.messages = messages
        self.clock = clock
        self.config = config
        self.latest = None
        self.last_sequence = None
        self.last_game_ms = None
        self.session = None
        self.retired_sessions = deque(maxlen=16)
        self.last_received = 0
        self.active_state = bool(bridge.connected and bridge.auto_enabled)
        self.rejected = 0
        self.durations_ms = deque(maxlen=4096)
        self._reset()

    def _reset(self):
        mapping = self.config.mapping
        independent = mapping.mode == "independent"
        self.bridge.configure_limits(mapping.global_cap,mapping.A.hard_cap, mapping.B.hard_cap)
        self.library = dict(self.config.library)
        effective = self.config.mapping
        for key in "AB":
            channel = getattr(effective, key)
            effective = replace(effective, **{key: replace(channel, bindings=tuple(
                replace(binding, wave="auto", phase_ms=0, weight=0 if binding.wave == "off" else binding.weight)
                for binding in channel.bindings))})
        self.engine = (ChannelEngine(effective) if self.config.mapping.mode == "independent"
                       else ManakaTriggerEngine(**dict(self.config.legacy)))
        if not independent:
            self.engine.channel_caps = (min(mapping.global_cap,mapping.A.hard_cap), min(mapping.global_cap,mapping.B.hard_cap))
        self.legacy_selector = WaveformSelector(hold_seconds=.8)
        self.legacy_wave_keys = {key:None for key in "AB"}
        self.legacy_wave_serial = {key:0 for key in "AB"}
        policy = self.config.wave_policy or migrate_policy(dict(wave_mode=self.config.wave_mode,
            fixed_wave=self.config.fixed_wave, wave_map=dict(self.config.wave_map), action_wave_map=dict(self.config.action_map)), self.config.mapping)
        self.router = WaveRouter(policy)
        self.limiter = ChannelPeakLimiter()
        self.legacy_limiter = RollingPeakLimiter()

    def configure(self, config):
        with self.lock:
            if config == self.config:
                return
            self.config = config
            self._reset()
            self.last_game_ms = None
            self.latest = None
            self.bridge.zero_output()

    def set_bridge(self, bridge):
        """Retire the old transport under the same lock as packet processing."""
        with self.lock:
            self.bridge.zero_output()
            self.bridge = bridge
            self.latest = None
            self.active_state = False
            self._reset()

    def _wave(self, key):
        if key == "off":
            return None
        if key == "custom":
            return self.config.custom
        return PRESETS.get(key) or self.library.get(key)

    def _legacy_selections(self, frame, packet, now):
        config = self.config
        waves = {}
        for key, source in config.pulse_sources:
            pattern = getattr(frame, "pattern_"+key.lower())
            if config.wave_mode == "smart" and source == "action" and pattern == "action-ramp":
                action = str(packet.get("action", "None"))
                waves[key] = self._wave(dict(config.action_map).get(action, recommended_wave_for_action(action)))
                self.legacy_selector.current[key] = waves[key]
                self.legacy_selector.pending[key] = None
            else:
                waves[key] = self.legacy_selector.select(key, pattern, config.wave_mode,
                    config.fixed_wave, dict(config.wave_map), config.custom, now=now,
                    library=self.library, hold_changes=source == "heart")
        result = {}
        for key, wave in waves.items():
            identity = (wave.key if wave else "off", self.engine.peak_active_until_ms if wave and wave.key == "climax" else 0)
            if identity != self.legacy_wave_keys[key]:
                self.legacy_wave_keys[key] = identity
                self.legacy_wave_serial[key] += 1
            result[key] = Selection(identity[0], f"legacy-{key}:{self.legacy_wave_serial[key]}",
                not wave or wave.key != "climax", "legacy:"+getattr(frame,"pattern_"+key.lower()))
        return result

    def process(self, packet, received_at=None):
        started = time.perf_counter_ns()
        received_at = self.clock() if received_at is None else received_at
        with self.lock:
            try:
                return self._process(packet, received_at)
            except (ValueError, TypeError, KeyError, OverflowError):
                self.rejected += 1
                self.bridge.zero_output()
                self.engine.force_safe_cut("invalid-telemetry")
                self.router.reset()
                return None
            finally:
                self.durations_ms.append((time.perf_counter_ns()-started)/1e6)

    def _process(self, packet, received_at):
        if not isinstance(packet, dict) or packet.get("version", 1) not in {1, 2}:
            raise ValueError("Unsupported telemetry")
        if self.clock()-received_at >= 1 or received_at < self.last_received:
            self.rejected += 1
            return None
        game_ms = int(packet["monotonicMs"])
        sequence = int(packet["sequence"])
        if game_ms < 0 or sequence < 0:
            raise ValueError("Negative telemetry clock")
        session = str(packet.get("sessionId", "v1"))
        if self.last_received and received_at-self.last_received >= 1:
            self._reset()
        if session != self.session:
            if session in self.retired_sessions:
                self.rejected += 1
                return None
            if self.session is not None:
                self.retired_sessions.append(self.session)
            self.session = session
            self.last_sequence = self.last_game_ms = None
            self._reset()
        if self.last_sequence is not None and (sequence <= self.last_sequence or
                                               (self.last_game_ms is not None and game_ms < self.last_game_ms)):
            # Old plugins lack session IDs. Accept a restart only after a real gap.
            if session == "v1" and received_at-self.last_received >= 1 and sequence < self.last_sequence:
                self._reset()
                self.last_game_ms = None
            else:
                self.rejected += 1
                return None
        dt = .1 if self.last_game_ms is None else max(0, min(.5, (game_ms-self.last_game_ms)/1000))
        self.last_sequence, self.last_game_ms, self.last_received = sequence, game_ms, received_at
        active_now = bool(self.bridge.connected and self.bridge.auto_enabled)
        if active_now != self.active_state:
            self._reset()
            self.active_state = active_now
        independent = self.config.mapping.mode == "independent"
        if independent:
            selections = self.router.evaluate(packet, received_at,
                lambda channel, name: len(self._wave(name).v3_frames())*.1 if self._wave(name) else .1)
            event_states = {key: (self.router.current[key].source if self.router.current[key]
                and self.router.current[key].source in {"climax", "failure"} else None) for key in "AB"}
            frame = self.engine.evaluate(packet, dt, event_states=event_states if self.config.wave_policy else None)
        else:
            # Original gameplay: unchanged ordinary curves, original event
            # timing/cooldown and waveform selector, with separate final caps.
            frame = route_frame(self.engine.evaluate(packet, dt), dict(self.config.pulse_sources))
            selections = self._legacy_selections(frame, packet, received_at)
        if frame.safe_cut:
            self.router.reset()
            selections = {key: Selection("off", "idle", True, "stopped") for key in "AB"}
        a, b = self._wave(selections["A"].wave), self._wave(selections["B"].wave)
        self.invalid_waves = {key: ([(self.engine.selected[key].source if independent and self.engine.selected[key] else "wave")+":wave-unavailable"]
            if selections[key].wave != "off" and self._wave(selections[key].wave) is None else []) for key in "AB"}
        values = {"A": frame.strength_a * (1 if independent else a.feel_scale) if a else 0,
                  "B": frame.strength_b * (1 if independent else b.feel_scale) if b else 0}
        active = self.bridge.connected and self.bridge.auto_enabled
        if not active:
            self.limiter.reset()
            self.legacy_limiter.reset()
        sync = self.config.mapping.intensity_sync
        for key in "AB":
            if not getattr(self.config.mapping, key).enabled:
                values[key] = 0
        if sync != "off":
            master, follower = ("A", "B") if sync == "A_to_B" else ("B", "A")
            # Synchronization changes the intensity source, not device activation.
            device = getattr(self.config.mapping, follower).device
            state = detections(packet).get(device)
            event = independent and event_states.get(follower) in {"climax", "failure"}
            gated = independent and state is not None and not (state.available and state.active) and not event
            values[follower] = values[master] if self._wave(selections[follower].wave) and not gated else 0
        if frame.safe_cut:
            self.limiter.reset()
            self.legacy_limiter.reset()
            values = dict(A=0, B=0)
            self.bridge.zero_output()
        elif independent:
            for key in "AB":
                config = getattr(self.config.mapping, key)
                values[key] = self.limiter.apply(key, values[key], peak=getattr(frame, "pattern_"+key.lower()) == "peak",
                    now=received_at, cap=min(config.hard_cap, self.config.mapping.global_cap, self.bridge.channel_limit(key)),
                    record=active, observed=self.bridge.channel_output(key))
        elif active:
            values["A"], values["B"], _ = self.legacy_limiter.apply(values["A"], values["B"],
                peak_active=frame.pattern_a == "peak" or frame.pattern_b == "peak", now_ms=game_ms,
                hard_cap=self.config.mapping.global_cap)
        else:
            self.limiter.reset()
            self.legacy_limiter.reset()
        for key in "AB":
            channel = getattr(self.config.mapping,key)
            values[key] = min(values[key], self.bridge.channel_limit(key), channel.hard_cap, self.config.mapping.global_cap) if channel.enabled else 0
        if not frame.safe_cut:
            self.bridge.update_auto_outputs(values["A"], a.v3_frames() if a and values["A"] > 0 else (),
                wave_key_a=(a.key+"|"+selections["A"].token) if a else "idle", strength_b=values["B"],
                frames_b=b.v3_frames() if b and values["B"] > 0 else (), wave_key_b=(b.key+"|"+selections["B"].token) if b else "idle",
                hard_cap=self.config.mapping.global_cap, received_at=received_at,
                cap_a=self.config.mapping.A.hard_cap,
                cap_b=self.config.mapping.B.hard_cap,
                loop_a=selections["A"].loop, loop_b=selections["B"].loop,
                transition_a=selections["A"].transition, transition_b=selections["B"].transition)
        snapshot = OutputSnapshot(dict(packet), received_at, frame, a, b, values["A"], values["B"],
            tuple(self.engine.unavailable["A"])+tuple(self.invalid_waves["A"]) if independent else (),
            tuple(self.engine.unavailable["B"])+tuple(self.invalid_waves["B"]) if independent else (),
            selections["A"].reason, selections["B"].reason)
        self.latest = snapshot
        self.messages.put(("runtime_snapshot", snapshot))
        for event in frame.events:
            self.messages.put(("runtime_event", event))
        return snapshot

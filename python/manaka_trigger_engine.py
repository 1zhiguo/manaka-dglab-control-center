"""SecretFlasherManaka telemetry-to-trigger pilot.

This program is deliberately DRY RUN ONLY.  It receives the BepInEx telemetry
stream and prints proposed channel strengths/patterns, but contains no
WebSocket client and cannot send commands to a DG-LAB device.
"""

from __future__ import annotations

import argparse
import json
import socket
import time
from dataclasses import dataclass


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class TriggerFrame:
    strength_a: float
    strength_b: float
    pattern_a: str
    pattern_b: str
    reason: str
    events: tuple[str, ...]
    safe_cut: bool = False
    pulse_interval_ms: int = 0


class RollingPeakLimiter:
    """Limit a peak to the highest real output in the preceding window plus a step."""

    def __init__(self, window_ms: int = 5000, maximum_rise: float = 15.0) -> None:
        self.window_ms = max(1, int(window_ms))
        self.maximum_rise = max(0.0, float(maximum_rise))
        self.history: list[tuple[int, float, float]] = []
        self.active_limit: float | None = None

    def apply(
        self,
        output_a: float,
        output_b: float,
        *,
        peak_active: bool,
        now_ms: int,
        hard_cap: float,
    ) -> tuple[float, float, float | None]:
        cutoff = int(now_ms) - self.window_ms
        self.history = [sample for sample in self.history if sample[0] >= cutoff]
        hard_cap = clamp(float(hard_cap), 0.0, 200.0)
        output_a = clamp(float(output_a), 0.0, hard_cap)
        output_b = clamp(float(output_b), 0.0, hard_cap)
        if peak_active:
            if self.active_limit is None:
                previous_max = max(
                    (max(sample_a, sample_b) for _, sample_a, sample_b in self.history),
                    default=0.0,
                )
                self.active_limit = min(hard_cap, previous_max + self.maximum_rise)
            return (
                min(output_a, self.active_limit),
                min(output_b, self.active_limit),
                self.active_limit,
            )

        self.active_limit = None
        self.history.append((int(now_ms), output_a, output_b))
        return output_a, output_b, None

    def reset(self) -> None:
        self.history.clear()
        self.active_limit = None


class ManakaTriggerEngine:
    """Stateful, conservative mapping from game state to proposed output."""

    def __init__(
        self,
        max_strength: float = 30.0,
        min_strength: float = 5.0,
        output_max: float | None = None,
        trigger_bpm: float = 90.0,
        full_bpm: float = 160.0,
    ) -> None:
        self.hard_cap = clamp(max_strength, 1.0, 200.0)
        self.min_strength = 0.0
        self.output_max = self.hard_cap
        self.trigger_bpm = 90.0
        self.full_bpm = 160.0
        self.configure(
            min_strength=min_strength,
            output_max=self.hard_cap if output_max is None else output_max,
            hard_cap=self.hard_cap,
            trigger_bpm=trigger_bpm,
            full_bpm=full_bpm,
        )
        self.channel_caps = None
        self.output_a = 0.0
        self.output_b = 0.0
        self.has_baseline = False
        self.previous_orgasm = False
        self.previous_game_over = False
        self.previous_action = "None"
        self.last_peak_event_ms = -10_000_000
        self.last_failure_event_ms = -10_000_000
        self.peak_active_until_ms = -1
        self.was_peak_active = False

    @property
    def max_strength(self) -> float:
        """Backward-compatible name for the absolute device hard cap."""
        return self.hard_cap

    @max_strength.setter
    def max_strength(self, value: float) -> None:
        self.hard_cap = clamp(float(value), 1.0, 200.0)
        self.min_strength = min(self.min_strength, self.output_max)

    def configure(
        self,
        *,
        min_strength: float,
        output_max: float,
        hard_cap: float,
        trigger_bpm: float,
        full_bpm: float,
    ) -> None:
        hard_cap = clamp(float(hard_cap), 1.0, 200.0)
        output_max = clamp(float(output_max), 0.0, 200.0)
        min_strength = clamp(float(min_strength), 0.0, output_max)
        trigger_bpm = clamp(float(trigger_bpm), 40.0, 159.0)
        full_bpm = clamp(float(full_bpm), trigger_bpm + 1.0, 160.0)
        self.hard_cap = hard_cap
        self.output_max = output_max
        self.min_strength = min_strength
        self.trigger_bpm = trigger_bpm
        self.full_bpm = full_bpm
        if hasattr(self, "output_a"):
            self.output_a = clamp(self.output_a, 0.0, hard_cap)
            self.output_b = clamp(self.output_b, 0.0, hard_cap)

    @staticmethod
    def _action_name(packet: dict) -> str:
        value = str(packet.get("action", "None") or "None")
        return value

    @staticmethod
    def _is_action_active(packet: dict, action: str) -> bool:
        return bool(packet.get("playingAction")) or action not in {"", "None"}

    @staticmethod
    def _slew(current: float, target: float, dt: float) -> float:
        # Faster release than attack. A real device adapter must still enforce
        # an immediate zero for stale telemetry and disconnects. Game-over has
        # one explicitly bounded failure pulse before entering safe idle.
        rate = 12.0 if target > current else 24.0
        step = max(0.0, dt) * rate
        if target > current:
            return min(target, current + step)
        return max(target, current - step)

    def evaluate(self, packet: dict, dt: float = 0.1) -> TriggerFrame:
        cap_a, cap_b = self.channel_caps or (self.hard_cap, self.hard_cap)
        action = self._action_name(packet)
        action_active = self._is_action_active(packet, action)
        stage = str(packet.get("stage", "None") or "None")
        game_over = bool(packet.get("gameOver"))
        system_menu_open = bool(packet.get("systemMenuOpen"))
        now_ms = int(packet.get("monotonicMs", 0) or 0)
        paused = (
            bool(packet.get("paused"))
            or system_menu_open
            or float(packet.get("timeScale", 1.0) or 0.0) <= 0.001
            or float(packet.get("managedTimeScale", 1.0) or 0.0) <= 0.001
        )

        # The game's GameOverEvent opens MissionFailedPanel, making the rising
        # edge a reliable evacuation-failure signal.  It deliberately shares
        # the normal two-hit climax path, so the UI's rolling +15 limiter and
        # absolute hard cap still apply.  ESC/menu pause always wins.
        failure_edge = (
            self.has_baseline
            and game_over
            and not self.previous_game_over
            and not system_menu_open
            and stage not in {"", "None"}
            and now_ms - self.last_failure_event_ms >= 5000
        )
        if failure_edge:
            self.last_failure_event_ms = now_ms
            self.peak_active_until_ms = max(self.peak_active_until_ms, now_ms + 1300)

        failure_peak_active = game_over and now_ms < self.peak_active_until_ms
        if failure_peak_active and not system_menu_open:
            self.output_a = cap_a
            self.output_b = cap_b
            self.was_peak_active = True
            self.previous_game_over = True
            self.previous_orgasm = False
            self.previous_action = action
            events = ("evacuation-failed", "failure-climax") if failure_edge else ()
            return TriggerFrame(
                round(self.output_a, 1),
                round(self.output_b, 1),
                "peak",
                "peak",
                "evacuation-failed-punishment",
                events,
            )

        if paused or game_over or stage in {"", "None"}:
            self.output_a = 0.0
            self.output_b = 0.0
            self.previous_orgasm = False
            self.previous_game_over = game_over
            self.previous_action = action
            self.peak_active_until_ms = -1
            self.was_peak_active = False
            self.has_baseline = True
            if paused:
                why = "game-paused"
            elif game_over:
                why = "game-over"
            else:
                why = "not-in-playable-scene"
            return TriggerFrame(0.0, 0.0, "idle", "idle", why, (), True)

        bpm = float(packet.get("heartRate", 0.0) or 0.0)
        heart = clamp((bpm - self.trigger_bpm) / (self.full_bpm - self.trigger_bpm), 0.0, 1.0)
        alert = clamp(float(packet.get("maxNpcAlert", 0.0) or 0.0), 0.0, 1.0)
        ecstasy = clamp(float(packet.get("ecstasy", 0.0) or 0.0), 0.0, 1.0)
        rising_count = max(0, int(packet.get("risingNpcCount", 0) or 0))
        watching_count = max(0, int(packet.get("watchingNpcCount", 0) or 0))
        orgasm = bool(packet.get("orgasm"))
        events: list[str] = []
        if not self.has_baseline:
            # Starting the controller in the middle of an encounter/action must
            # never manufacture edge events from the current level state.
            self.has_baseline = True
        else:
            if action_active and self.previous_action in {"", "None"}:
                events.append(f"action-start:{action}")
            if orgasm and not self.previous_orgasm and now_ms - self.last_peak_event_ms >= 5000:
                events.append("peak-edge")
                self.last_peak_event_ms = now_ms
                # Keep both channels at the cap long enough for the complete
                # two-hit envelope. The bridge treats `climax` as one-shot.
                self.peak_active_until_ms = now_ms + 1300

        # Channel A: authoritative in-game heart rate. NPC alert is displayed
        # by the UI but never changes either output channel.
        target_a = 0.0
        pattern_a = "idle"
        pulse_interval_ms = 0
        if bpm >= self.trigger_bpm:
            heart_level = clamp(
                (bpm - self.trigger_bpm) / (self.full_bpm - self.trigger_bpm),
                0.0,
                1.0,
            )
            target_a = self.min_strength + heart_level * (self.output_max - self.min_strength)
            pulse_interval_ms = int(round(60000.0 / max(1.0, bpm)))
            low_mid = self.trigger_bpm + (self.full_bpm - self.trigger_bpm) * 0.30
            high_mid = self.trigger_bpm + (self.full_bpm - self.trigger_bpm) * 0.70
            if bpm < low_mid:
                pattern_a = "heartbeat-soft"
            elif bpm < high_mid:
                pattern_a = "heartbeat"
            else:
                pattern_a = "heartbeat-fast"

        # Channel B: action progression. Ecstasy is authoritative and gives a
        # stable 0..1 ramp. The peak flag is an edge, not a continuously queued
        # command.
        target_b = 0.0
        pattern_b = "idle"
        if action_active:
            progress = clamp(ecstasy * 0.85 + heart * 0.15, 0.0, 1.0)
            # Ordinary action feedback is intentionally gentler than the A
            # channel. Only a peak edge may reach the absolute safety cap.
            action_max = max(self.min_strength, self.output_max * 0.55)
            target_b = self.min_strength + progress * (action_max - self.min_strength)
            pattern_b = "action-ramp"

        peak_active = now_ms < self.peak_active_until_ms
        if peak_active:
            target_a = cap_a
            target_b = cap_b
            pattern_a = "peak"
            pattern_b = "peak"

        target_a = clamp(target_a, 0.0, cap_a)
        target_b = clamp(target_b, 0.0, cap_b)
        if peak_active:
            self.output_a = cap_a
            self.output_b = cap_b
            self.was_peak_active = True
        elif self.was_peak_active:
            # Do not let the hard-cap climax level bleed into the ordinary
            # heart/action mappings after the one-shot window ends.
            self.output_a = target_a
            self.output_b = target_b
            self.was_peak_active = False
        else:
            self.output_a = self._slew(self.output_a, target_a, dt)
            self.output_b = self._slew(self.output_b, target_b, dt)

        if action_active:
            reason = (
                f"bpm={bpm:.1f} pulse={pulse_interval_ms}ms "
                f"action={action} ecstasy={ecstasy:.3f}"
            )
        elif pulse_interval_ms:
            reason = f"bpm={bpm:.1f} pulse={pulse_interval_ms}ms"
        else:
            reason = f"heart-below-threshold bpm={bpm:.1f}"

        self.previous_orgasm = orgasm
        self.previous_game_over = game_over
        self.previous_action = action
        return TriggerFrame(
            round(self.output_a, 1),
            round(self.output_b, 1),
            pattern_a,
            pattern_b,
            reason,
            tuple(events),
            pulse_interval_ms=pulse_interval_ms,
        )

    def force_safe_cut(self, reason: str) -> TriggerFrame:
        self.output_a = 0.0
        self.output_b = 0.0
        self.peak_active_until_ms = -1
        self.was_peak_active = False
        return TriggerFrame(0.0, 0.0, "idle", "idle", reason, (), True)


def render(packet: dict, frame: TriggerFrame) -> str:
    event_text = ",".join(frame.events) if frame.events else "-"
    prefix = "SAFE-CUT" if frame.safe_cut else "DRY-RUN"
    return (
        f"[{prefix}] seq={int(packet.get('sequence', 0)):>7} "
        f"A={frame.strength_a:>4.1f}/{frame.pattern_a:<12} "
        f"B={frame.strength_b:>4.1f}/{frame.pattern_b:<11} "
        f"event={event_text:<28} reason={frame.reason}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manaka trigger engine (dry run only)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=45678, type=int)
    parser.add_argument("--stale-after", default=0.75, type=float)
    parser.add_argument("--max-strength", default=30.0, type=float)
    parser.add_argument("--print-every", default=0.5, type=float)
    args = parser.parse_args()

    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind((args.host, args.port))
    receiver.settimeout(0.1)
    engine = ManakaTriggerEngine(args.max_strength)

    print(f"Manaka trigger pilot listening on udp://{args.host}:{args.port}")
    print("DRY RUN ONLY: no WebSocket client, no DG-LAB connection, no device output")
    print(f"Safety: hard cap={engine.hard_cap:.0f}, stale cut={args.stale_after:.2f}s")

    last_receive = 0.0
    last_print = 0.0
    last_game_ms: int | None = None
    stale_reported = False
    latest_packet: dict = {"sequence": 0}

    try:
        while True:
            try:
                payload, _ = receiver.recvfrom(65535)
            except socket.timeout:
                now = time.monotonic()
                if last_receive and not stale_reported and now - last_receive >= args.stale_after:
                    frame = engine.force_safe_cut("telemetry-stale")
                    print(render(latest_packet, frame), flush=True)
                    stale_reported = True
                continue

            now = time.monotonic()
            latest_packet = json.loads(payload.decode("utf-8"))
            game_ms = int(latest_packet.get("monotonicMs", 0) or 0)
            dt = 0.1 if last_game_ms is None else clamp((game_ms - last_game_ms) / 1000.0, 0.0, 0.5)
            last_game_ms = game_ms
            last_receive = now
            stale_reported = False

            frame = engine.evaluate(latest_packet, dt)
            if frame.events or frame.safe_cut or now - last_print >= args.print_every:
                print(render(latest_packet, frame), flush=True)
                last_print = now
    except KeyboardInterrupt:
        print(render(latest_packet, engine.force_safe_cut("operator-stop")), flush=True)
    finally:
        receiver.close()


if __name__ == "__main__":
    main()

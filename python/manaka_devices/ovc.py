"""Manaka vibrator-mode mapping. No Ricca events or electrical profiles.

The steady envelope is authored here, not copied from DG-LAB's GPL waveform
library. Protocol framing is performed by DG-LAB 4 App (100 ms per frame).
"""
from __future__ import annotations

import math
import random
from copy import deepcopy

DEFAULT_PROFILE = {
    "mode": "sync",
    "hard_cap": 30,
    "low": 10, "medium": 20, "high": 30,
    "channel_a": True, "channel_b": False,
    "custom_waves": [],
}

# Original vibration envelopes; no electrical frequencies or GPL tables.
WAVES = {
    "ovc_steady": ("恒定", "Steady", [100] * 16),
    "ovc_breathe": ("呼吸", "Breathe", [0, 10, 20, 40, 65, 80, 95, 100, 95, 80, 65, 40, 20, 10, 0, 0]),
    "ovc_pulse": ("轻敲", "Tap", [100, 100, 0, 0] * 4),
    "ovc_ramp": ("渐强", "Ramp", [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 80, 60, 40, 20, 0]),
}


def clean_points(raw):
    if not isinstance(raw, (list, tuple)) or not 2 <= len(raw) <= 100:
        return None
    try:
        values = [float(v) for v in raw]
        if any(not math.isfinite(v) for v in values):
            return None
        return [round(max(0, min(100, v))) for v in values]
    except (TypeError, ValueError, OverflowError):
        return None


def waveform_catalog(profile, shared=(), language="zh"):
    result = [{"key": key, "name": wave[1] if language == "en" else wave[0], "points": wave[2], "group": "built_in"}
              for key, wave in WAVES.items()]
    result.extend(deepcopy(profile.get("custom_waves", [])))
    for item in shared:
        points = clean_points(item.get("points"))
        if points is not None:
            result.append({"key": "ovc_shared:" + str(item["id"]), "name": str(item["name"]) + (" · Shared" if language == "en" else " · 共用曲线"), "points": points, "group": "shared"})
    return result


def wave_frames(key, catalog):
    item = next((item for item in catalog if item.get("key") == key), None)
    points = clean_points(item.get("points")) if item else None
    return tuple("0A0A0A0A" + f"{point:02X}" * 4 for point in points) if points else ()


def default_policy(enabled):
    return {"enabled": enabled, "mode": "sync", "wave": "ovc_breathe", "strength": 20,
            "random_waves": list(WAVES), "random_seconds": 4, "actions": {}}


def _clean_policy(raw, enabled, allowed):
    result = default_policy(enabled)
    if not isinstance(raw, dict):
        return result
    result["enabled"] = raw.get("enabled", enabled) is True
    if raw.get("mode") in {"sync", "fixed", "random", "action", "off"}:
        result["mode"] = raw["mode"]
    result["strength"] = step_strength(raw.get("strength", 20))
    wave = str(raw.get("wave", result["wave"]))
    result["wave"] = wave if wave in allowed or wave.startswith("ovc_shared:") else ""
    pool = raw.get("random_waves", list(WAVES))
    result["random_waves"] = list(dict.fromkeys(str(v) for v in pool if str(v) in allowed or str(v).startswith("ovc_shared:")))[:64] if isinstance(pool, list) else []
    try:
        seconds = float(raw.get("random_seconds", 4))
        result["random_seconds"] = max(1, min(60, seconds)) if math.isfinite(seconds) else 4
    except (TypeError, ValueError):
        pass
    actions = raw.get("actions", {})
    if isinstance(actions, dict):
        for action, rule in list(actions.items())[:512]:
            if isinstance(rule, dict) and rule.get("mode") in {"sync", "wave", "random", "off"}:
                key = str(rule.get("wave", ""))
                result["actions"][str(action)[:128]] = {"mode": rule["mode"], "wave": key if key in allowed or key.startswith("ovc_shared:") else "",
                                                        "strength": step_strength(rule.get("strength", result["strength"]))}
    return result


def step_strength(value, cap=200):
    try:
        number, limit = float(value), float(cap)
        if not math.isfinite(number) or not math.isfinite(limit):
            return 0
        return int(max(0, min(200, limit, number)) // 10) * 10
    except (TypeError, ValueError, OverflowError):
        return 0


def sanitize_profile(raw):
    result = deepcopy(DEFAULT_PROFILE)
    if not isinstance(raw, dict):
        raw = {}
    result["hard_cap"] = step_strength(raw.get("hard_cap", result["hard_cap"]))
    for key in ("low", "medium", "high"):
        result[key] = step_strength(raw.get(key, result[key]), result["hard_cap"])
    for key in ("channel_a", "channel_b"):
        result[key] = raw.get(key, result[key]) is True
    result["mode"] = "independent" if raw.get("mode") == "independent" else "sync"
    custom = raw.get("custom_waves", [])
    if isinstance(custom, list):
        used = set()
        for wave in custom[:64]:
            if not isinstance(wave, dict):
                continue
            key, points = str(wave.get("key", "")), clean_points(wave.get("points"))
            if key.startswith("ovc_custom:") and key not in used and points is not None:
                result["custom_waves"].append({"key": key[:96], "name": str(wave.get("name", key))[:64], "points": points, "group": "custom"})
                used.add(key)
    allowed = set(WAVES) | {wave["key"] for wave in result["custom_waves"]}
    policies = raw.get("channels", {})
    if not isinstance(policies, dict):
        policies = {}
    result["channels"] = {ch: _clean_policy(policies.get(ch), result["channel_" + ch.lower()], allowed) for ch in ("A", "B")}
    return result


def vibration_mode(raw):
    # Strict allowlist: unknown modded enums do not silently become high.
    # Verified against v1.1.3 Assembly-CSharp: Off, Low, High, Random.
    # Telemetry resolves Random via CommonVibratorController.currentMode.
    # Older plugins that only send Random must not produce a made-up output.
    return {"none": "off", "off": "off", "low": "low", "medium": "medium", "middle": "medium", "random": "random",
            "high": "high"}.get(str(raw).strip().lower(), "unknown")


def plan(packet, profile, *, fresh, authorized):
    """Return requested A/B; never inherit failure/climax electrical pulses."""
    mode = vibration_mode(packet.get("vibration", "None"))
    if not authorized:
        return mode, 0, 0, "not-authorized"
    if not fresh:
        return mode, 0, 0, "telemetry-stale"
    if (packet.get("paused") or packet.get("systemMenuOpen") or packet.get("gameOver")
            or str(packet.get("stage", "None")) in {"", "None"}):
        return mode, 0, 0, "game-safety-idle"
    try:
        scales = [float(packet.get(key, 1)) for key in ("timeScale", "managedTimeScale")]
        if any(not math.isfinite(scale) or scale <= 0.001 for scale in scales):
            return mode, 0, 0, "game-safety-idle"
    except (TypeError, ValueError):
        return mode, 0, 0, "invalid-telemetry"
    if mode == "random":
        return mode, 0, 0, "vibrator-random-wait"
    if mode not in {"low", "medium", "high"}:
        return mode, 0, 0, "vibrator-off" if mode == "off" else "unknown-vibrator-mode"
    strength = step_strength(profile[mode], profile["hard_cap"])
    return mode, strength if profile["channel_a"] else 0, strength if profile["channel_b"] else 0, ""


STEADY_FRAMES = ("0A0A0A0A64646464",)


class OvcPlanner:
    """State is per device/channel, with no dependency on electrical output."""
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.reset()

    def reset(self):
        self.state = {}
        self.sequence = {"A": 0, "B": 0}

    def evaluate(self, packet, profile, catalog, *, now, fresh, authorized):
        # Reuse the existing game-safety gates even when vibrator mode is Off.
        mode, _, _, gate = plan(packet, profile, fresh=fresh, authorized=authorized)
        blocked = gate not in {"", "vibrator-off", "unknown-vibrator-mode", "vibrator-random-wait"}
        outputs = {}
        for ch in ("A", "B"):
            policy = profile["channels"][ch]
            behavior = "sync" if profile["mode"] == "sync" else policy["mode"]
            key, strength = "ovc_steady", 0
            action = str(packet.get("action", "None"))
            token = (behavior, action if behavior == "action" else "")
            rule = policy["actions"].get(action, {"mode": "sync"}) if behavior == "action" else {}
            if behavior == "action":
                behavior = {"wave": "fixed"}.get(rule["mode"], rule["mode"])
            if not blocked and policy["enabled"] and behavior != "off":
                if behavior == "sync":
                    strength = profile.get(mode, 0) if mode in {"low", "medium", "high"} else 0
                elif behavior == "fixed":
                    key = rule.get("wave", policy["wave"])
                    strength = rule.get("strength", policy["strength"])
                elif behavior == "random":
                    available = {item["key"] for item in catalog}
                    pool = [key for key in policy["random_waves"] if key in available]
                    previous = self.state.get(ch, {})
                    if pool:
                        if previous.get("token") != token or now >= previous.get("until", 0) or previous.get("key") not in pool:
                            key = self.rng.choice(pool)
                            self.sequence[ch] += 1
                            self.state[ch] = {"token": token, "key": key, "until": now + policy["random_seconds"]}
                        else:
                            key = previous["key"]
                        strength = rule.get("strength", policy["strength"])
            strength = step_strength(strength, profile["hard_cap"])
            frames = wave_frames(key, catalog) if strength else ()
            if not frames:
                strength = 0
            outputs[ch] = {"strength": strength, "frames": frames, "wave": key,
                           "token": key + ":" + str(self.sequence[ch]) + (":" + action if policy["mode"] == "action" else ""), "behavior": behavior}
        if blocked:
            self.reset()
        return {"mode": mode, "gate": gate if blocked else ("" if any(v["strength"] for v in outputs.values()) else gate or "no-channel-output"), **outputs}

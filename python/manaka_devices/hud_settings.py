"""Display-only preferences and the bounded, local Unity HUD V2 protocol."""
from copy import deepcopy
import math

ANCHORS = ("game_safe", "top_left", "top_center", "top_right", "bottom_left", "bottom_center", "bottom_right", "custom")
DEFAULTS = {"scale": 100, "opacity": 35, "anchor": "game_safe", "x": 30, "y": 96,
            "show_pulse": True, "show_ovc": True, "show_a": True, "show_b": True,
            "show_numbers": True, "show_status": True, "show_waveforms": True}
FLAGS = ("show_pulse", "show_ovc", "show_a", "show_b", "show_numbers", "show_status", "show_waveforms")


def finite(value, low, high, fallback=0):
    try:
        value = float(value)
        return max(low, min(high, value)) if math.isfinite(value) else fallback
    except (TypeError, ValueError, OverflowError):
        return fallback


def sanitize_settings(raw):
    result = deepcopy(DEFAULTS)
    if not isinstance(raw, dict):
        return result
    for key, low, high in (("scale", 60, 180), ("opacity", 0, 100), ("x", 0, 100), ("y", 0, 100)):
        result[key] = round(finite(raw.get(key, result[key]), low, high, result[key]))
    if raw.get("anchor") in ANCHORS:
        result["anchor"] = raw["anchor"]
    for key in FLAGS:
        if type(raw.get(key)) is bool:
            result[key] = raw[key]
    if not (result["show_pulse"] or result["show_ovc"]):
        result["show_pulse"] = True
    if not (result["show_a"] or result["show_b"]):
        result["show_a"] = True
    return result


def build_packet(sequence, options, *, visible, connected, active, strengths, caps, pulses):
    options = sanitize_settings(options)
    flags = sum((1 << index) for index, key in enumerate(FLAGS) if options[key])
    connection = int(bool(connected[0])) | (int(bool(connected[1])) << 1)
    activity = int(bool(active[0])) | (int(bool(active[1])) << 1)
    values = ["MANAKA_HUD_V2", str(max(0, int(sequence))), str(int(bool(visible))), str(flags),
              str(options["scale"]), str(options["opacity"]), str(ANCHORS.index(options["anchor"])),
              str(options["x"]), str(options["y"]), str(connection), str(activity)]
    values.extend(f"{finite(value, 0, 200):.2f}" for value in strengths)
    values.extend(f"{finite(value, 0, 200):.2f}" for value in caps)
    values.extend(f"{finite(value, 0, 1):.3f}" for value in pulses)
    values.append("END")
    if len(values) != 24:
        raise ValueError("HUD requires exactly four channel values")
    return "|".join(values).encode("ascii")

"""Display-only preferences and the bounded, local Unity HUD V2/V3 protocols."""
from copy import deepcopy
import math

ANCHORS = ("game_safe", "top_left", "top_center", "top_right", "bottom_left", "bottom_center", "bottom_right", "custom")
DEFAULTS = {"scale": 100, "opacity": 35, "anchor": "game_safe", "x": 30, "y": 96,
            "show_pulse": True, "show_ovc": True, "show_a": True, "show_b": True,
            "show_numbers": True, "show_status": True, "show_waveforms": True, "show_booboop": True}
FLAGS = ("show_pulse", "show_ovc", "show_a", "show_b", "show_numbers", "show_status", "show_waveforms", "show_booboop")


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
    if not has_visible_cells(result):
        result["show_pulse"] = result["show_a"] = True
    return result


def has_visible_cells(options):
    return bool(options.get("show_booboop") or
                ((options.get("show_pulse") or options.get("show_ovc")) and
                 (options.get("show_a") or options.get("show_b"))))


def build_packet(sequence, options, *, visible, connected, active, strengths, caps, pulses, booboop=None):
    options = sanitize_settings(options)
    flags = sum((1 << index) for index, key in enumerate(FLAGS) if options[key])
    version = 3 if booboop is not None else 2
    connection = int(bool(connected[0])) | (int(bool(connected[1])) << 1)
    activity = int(bool(active[0])) | (int(bool(active[1])) << 1)
    if version == 3:
        connection |= int(bool(booboop.get("connected"))) << 2
        activity |= int(bool(booboop.get("active") and booboop.get("connected"))) << 2
    else:
        flags &= 127
        visible = visible and bool((options["show_pulse"] or options["show_ovc"]) and
                                    (options["show_a"] or options["show_b"]))
    values = [f"MANAKA_HUD_V{version}", str(max(0, int(sequence))), str(int(bool(visible))), str(flags),
              str(options["scale"]), str(options["opacity"]), str(ANCHORS.index(options["anchor"])),
              str(options["x"]), str(options["y"]), str(connection), str(activity)]
    values.extend(f"{finite(value, 0, 100 if index < 2 else 200):.2f}" for index, value in enumerate(strengths))
    values.extend(f"{finite(value, 0, 100 if index < 2 else 200):.2f}" for index, value in enumerate(caps))
    values.extend(f"{finite(value, 0, 1):.3f}" for value in pulses)
    if len(values) != 23:
        raise ValueError("HUD requires exactly four channel values")
    if version == 3:
        cap = finite(booboop.get("cap"), 0, 9)
        enabled = bool(activity & 4)
        values.extend(f"{finite(booboop.get(key), 0, cap):.2f}" if enabled else "0.00"
                      for key in ("stretch", "vibration"))
        values.extend([f"{cap:.2f}", f"{cap:.2f}", "0.000", "0.000"])
    values.append("END")
    if len(values) != (30 if version == 3 else 24):
        raise ValueError("HUD requires exactly four channel values")
    return "|".join(values).encode("ascii")

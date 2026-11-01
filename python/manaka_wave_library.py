"""Lossless V3 waveform interchange and bounded Dungeonlab .pulse conversion.

Text format and Dungeonlab section layout informed by SecretFlasherManaka2_X_DGLAB
(MIT, kusadact); see THIRD_PARTY_NOTICES. Period encoding follows DG-LAB V3.
"""
import json
import math
import re

MAX_FRAMES = 6000
MAX_BYTES = 2 * 1024 * 1024


def frames_valid(frames):
    if not isinstance(frames, (list, tuple)) or not 1 <= len(frames) <= MAX_FRAMES:
        raise ValueError(f"Waveform must contain 1..{MAX_FRAMES} frames")
    result = []
    for index, frame in enumerate(frames):
        if isinstance(frame, (list, tuple)):
            if len(frame) == 2:
                frame = [frame[0]]*4+[frame[1]]*4
            if len(frame) != 8 or any(type(x) is not int for x in frame):
                raise ValueError(f"Frame {index+1}: expected 2 or 8 integers")
            values = list(frame)
        elif isinstance(frame, str) and re.fullmatch(r"[0-9a-fA-F]{16}", frame):
            values = list(bytes.fromhex(frame))
        else:
            raise ValueError(f"Frame {index+1}: expected 16 hexadecimal characters")
        if any(not 10 <= x <= 240 for x in values[:4]) or any(not 0 <= x <= 100 for x in values[4:]):
            raise ValueError(f"Frame {index+1}: frequency codes 10..240, amplitudes 0..100")
        result.append(bytes(values).hex().upper())
    return tuple(result)


def encode_period(period_ms):
    if not math.isfinite(period_ms) or not 10 <= period_ms <= 1000:
        raise ValueError("Pulse period outside V3 range (10..1000 ms)")
    value = period_ms if period_ms <= 100 else (period_ms-100)/5+100 if period_ms <= 600 else (period_ms-600)/10+200
    return int(round(value))


def decode_period(code):
    return code if code <= 100 else (code-100)*5+100 if code <= 200 else (code-200)*10+600


def parse_text(text):
    frames = []
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if re.fullmatch(r"[0-9a-fA-F]{16}", line):
            frames.append(line)
        else:
            try:
                frames.append([int(x) for x in re.split(r"[,;，\s]+", line)])
            except ValueError as error:
                raise ValueError(f"Line {line_number}: invalid waveform data") from error
    return frames_valid(frames)


def dungeonlab_frames(text):
    sections = text.removeprefix("Dungeonlab+pulse:").split("+section+")
    metadata, sections[0] = sections[0].split("=", 1) if "=" in sections[0] else ("0,1", sections[0])
    rest, speed = map(float, metadata.split(","))
    if not math.isfinite(rest) or not 0 <= rest <= 600000 or not math.isfinite(speed) or not .01 <= speed <= 100:
        raise ValueError("Invalid Dungeonlab timing")
    frames = ["0A0A0A0A00000000"] * math.ceil(rest/100)
    for section in sections:
        header, body = section.split("/", 1)
        lower, upper, duration, mode, enabled = map(int, header.split(","))
        if enabled not in (0, 1) or mode not in (0, 1, 2, 3, 4) or not 0 <= lower <= upper < len(PERIODS) or not 0 <= duration < len(DURATIONS):
            raise ValueError("Invalid Dungeonlab section parameters")
        if not enabled:
            continue
        points = [float(x.split("-", 1)[0]) for x in body.split(",") if x.strip()]
        if not points or any(not math.isfinite(x) or not 0 <= x <= 100 for x in points):
            raise ValueError("Invalid Dungeonlab amplitude")
        count = max(1, round(DURATIONS[duration]*10))
        if len(frames)+count > MAX_FRAMES:
            raise ValueError("Waveform exceeds 10 minutes; nothing was imported")
        repeats = math.ceil(count/len(points))
        for i in range(count):
            ratio = i/max(1,count-1) if mode == 2 else (i%len(points))/max(1,len(points)-1) if mode == 3 else (i//len(points))/max(1,repeats-1) if mode == 4 else 0
            period = PERIODS[math.floor(lower+(upper-lower)*ratio)]/speed
            code = encode_period(period)
            frames.append(bytes([code]*4+[round(points[i%len(points)])]*4).hex().upper())
    return frames_valid(frames)


def parse_import(text, name="Imported waveform"):
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Waveform file exceeds 2 MiB")
    text = text.lstrip("\ufeff").strip()
    if text.startswith("Dungeonlab+pulse:"):
        return [dict(name=name, frames=dungeonlab_frames(text), source="Dungeonlab .pulse")]
    if not text.startswith(("{", "[")):
        return [dict(name=name, frames=parse_text(text), source="V3 text")]
    raw = json.loads(text)
    records = raw.get("waveforms", [raw]) if isinstance(raw, dict) else [dict(name=name, frames=raw)]
    if not isinstance(records, list) or not 1 <= len(records) <= 128:
        raise ValueError("Invalid waveform collection")
    result = []
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("Each waveform must be a JSON object")
        if item.get("frame_ms", 100) != 100:
            raise ValueError("Only V3 100 ms frames are supported")
        if "points" in item:
            frames = [[int(item.get("frequency",92)), x] for x in item["points"]]
        else:
            frames = item.get("frames", item.get("raw"))
        result.append(dict(name=str(item.get("name",name))[:120], frames=frames_valid(frames), source="Imported JSON",
            category=str(item.get("category", "Imported"))[:60]))
    return result


def preview_samples(frames):
    decoded = [bytes.fromhex(frame) for frame in frames_valid(frames)]
    return {"amplitudes": [x for frame in decoded for x in frame[4:]],
            "frequencyCodes": [x for frame in decoded for x in frame[:4]],
            "periodsMs": [decode_period(x) for frame in decoded for x in frame[:4]],
            "durationMs": len(decoded)*100}


PERIODS = (10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 78, 80, 85, 90, 95, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 233, 266, 300, 333, 366, 400, 450, 500, 550, 600, 700, 800, 900, 1000)
DURATIONS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 5, 5.2, 5.4, 5.6, 5.8, 6, 6.2, 6.4, 6.6, 6.8, 7, 7.2, 7.4, 7.6, 7.8, 8, 8.5, 9, 9.5, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23.4, 26.6, 30, 33.4, 36.6, 40, 45, 50, 55, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200, 250, 300)

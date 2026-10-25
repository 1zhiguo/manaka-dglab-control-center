"""Offline mapping benchmark. Never opens sockets or sends device commands."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from manaka_trigger_engine import ManakaTriggerEngine
from manaka_channel_engine import ChannelEngine, MappingSettings


def replay(path, repeats=1000, settings=None):
    if repeats < 1:
        raise ValueError("repeats must be positive")
    packets = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    durations = []
    cpu_start = time.process_time()
    wall_start = time.perf_counter()
    frames = []
    for _ in range(repeats):
        engine = ChannelEngine(settings) if settings is not None and settings.mode == "independent" else ManakaTriggerEngine()
        frames = []
        for packet in packets:
            start = time.perf_counter_ns()
            frame = engine.evaluate(packet, dt=0.1)
            durations.append((time.perf_counter_ns() - start) / 1e6)
            frames.append(asdict(frame))
    ordered = sorted(durations)
    return dict(packets=len(packets), repeats=repeats, samples=len(durations),
                mapping_ms_median=statistics.median(durations),
                mapping_ms_p95=ordered[int((len(ordered)-1)*.95)],
                mapping_ms_max=max(durations), cpu_seconds=time.process_time()-cpu_start,
                wall_seconds=time.perf_counter()-wall_start, frames=frames,
                scope="offline engine only; excludes GUI, transport and hardware")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parents[1] / "python/fixtures/channel_replay.jsonl")
    parser.add_argument("--repeats", type=int, default=1000)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--settings", type=Path, help="A channel mapping JSON file or exported application config")
    args = parser.parse_args()
    settings = None
    if args.settings:
        raw = json.loads(args.settings.read_text(encoding="utf-8"))
        settings = MappingSettings.parse(raw.get("channel_mapping", raw))
    result = json.dumps(replay(args.input, args.repeats, settings), indent=2)
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result)

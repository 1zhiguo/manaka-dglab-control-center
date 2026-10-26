"""Local, bounded, non-blocking JSONL diagnostics. No device authorization here."""
from __future__ import annotations

import atexit
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from logging import LogRecord
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import queue
import re
import threading
import time
import uuid


class AuditLog:
    def __init__(self, path: Path, *, max_bytes=4 * 1024 * 1024, backups=3, capacity=4096):
        self.path = Path(path)
        self.session = uuid.uuid4().hex[:12]
        self.error = ""
        self.dropped = 0
        self._sequence = itertools.count(1)
        self._queue = queue.Queue(maxsize=capacity)
        self._stop = threading.Event()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handler = RotatingFileHandler(self.path, maxBytes=max_bytes,
                                           backupCount=backups, encoding="utf-8")
        self._thread = threading.Thread(target=self._run, name="RiccaAuditWriter", daemon=True)
        self._thread.start()

    def record(self, event: str, **fields) -> None:
        if self._stop.is_set():
            return
        entry = {"time": datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds"),
                 "monotonic": round(time.monotonic(), 6), "session": self.session,
                 "pid": os.getpid(), "sequence": next(self._sequence), "event": event, **fields}
        try:
            self._queue.put_nowait(entry)
        except queue.Full:
            self.dropped += 1

    def _run(self):
        while not self._stop.is_set() or not self._queue.empty():
            try:
                entry = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                entry["dropped_total"] = self.dropped
                line = json.dumps(entry, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
                # Write directly so failures are observable rather than swallowed
                # by logging.Handler.handleError. emit still rotates and flushes.
                row = LogRecord("ricca.audit", 20, "", 0, line, (), None)
                if self._handler.shouldRollover(row):
                    self._handler.doRollover()
                self._handler.stream.write(line + "\n")
                self._handler.flush()
            except Exception as error:
                self.error = type(error).__name__
            finally:
                self._queue.task_done()

    def close(self):
        self._stop.set()
        self._thread.join(timeout=2)
        if not self._thread.is_alive():
            self._handler.close()


_sink: AuditLog | None = None
_startup_error = ""


def configure(path: Path):
    global _sink, _startup_error
    if _sink is not None:
        return
    try:
        _sink = AuditLog(path)
        atexit.register(close)
    except Exception as error:
        _startup_error = type(error).__name__


def record(event: str, **fields):
    if _sink is not None:
        _sink.record(event, **fields)


def status():
    return {"enabled": _sink is not None,
            "path": str(_sink.path) if _sink else "",
            "session": _sink.session if _sink else "",
            "error": _sink.error if _sink else _startup_error,
            "dropped": _sink.dropped if _sink else 0}


def close():
    global _sink
    if _sink:
        _sink.close()
        _sink = None


def state_fields(state):
    # No dialogue text, audio samples, QR URLs, pairing IDs or contact details.
    keys = ("process_id", "status", "scene", "current_hp", "max_hp", "pause_mask",
            "player_address", "action_trigger_hash", "build_supported")
    return {key: None if isinstance(state.get(key), float) and not math.isfinite(state[key])
            else state.get(key) for key in keys}


def command_fields(message: str):
    """Only retain well-formed output commands; never dump an arbitrary packet."""
    result = {"kind": "other"}
    if re.fullmatch(r"strength-[12]\+2\+\d{1,3}", message):
        channel, _, strength = message.split("-")[1].split("+")
        result = {"kind": "strength", "channel": "A" if channel == "1" else "B",
                  "strength": int(strength), "command": message}
    elif message in {"clear-1", "clear-2", "heartbeat"}:
        result = {"kind": "heartbeat" if message == "heartbeat" else "clear", "command": message}
    elif message.startswith(("pulse-A:", "pulse-B:")):
        try:
            frames = json.loads(message.split(":", 1)[1])
            if (isinstance(frames, list) and 1 <= len(frames) <= 100
                    and all(isinstance(frame, str) and re.fullmatch(r"[0-9A-Fa-f]{16}", frame) for frame in frames)):
                result = {"kind": "pulse", "channel": message[6], "frames": frames,
                          "frame_count": len(frames), "sha256": hashlib.sha256(message.encode()).hexdigest()}
        except (ValueError, TypeError):
            pass
    return result

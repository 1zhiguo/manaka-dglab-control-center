"""Validate versioned raw telemetry and expose source availability explicitly."""
from dataclasses import dataclass
import math


def finite(value, low=0., high=100.):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and low <= parsed <= high else None


@dataclass(frozen=True)
class Detection:
    available: bool
    active: bool = False
    level: float = 0.
    mode: str = "unavailable"


def detections(packet):
    bpm = finite(packet.get("heartRate"), 0, 300)
    ecstasy = finite(packet.get("ecstasy"), 0, 1)
    npc = finite(packet.get("maxNpcAlert"), 0, 1)
    result = dict(heart=Detection(bpm is not None, bool(bpm), bpm or 0),
        action_active=Detection("action" in packet, bool(packet.get("playingAction")) or packet.get("action", "None") not in {"", "None"}),
        ecstasy=Detection(ecstasy is not None, bool(ecstasy), ecstasy or 0),
        action=Detection(ecstasy is not None and "action" in packet,
            bool(packet.get("playingAction")) or packet.get("action", "None") not in {"", "None"}, ecstasy or 0),
        npc_alert=Detection(npc is not None, bool(npc), npc or 0),
        vibrator=Detection(False), piston=Detection(False))
    # V1 only reports configured modes. Never guess random modes from them.
    if packet.get("version") == 2:
        if packet.get("hasVibratorData") is True:
            mode = str(packet.get("vibratorEffectiveMode", "unknown")).lower()
            if mode in {"off", "none", "low", "high"}:
                result["vibrator"] = Detection(True, mode in {"low", "high"}, 0, mode)
        if packet.get("hasPistonData") is True:
            mode = finite(packet.get("pistonEffectiveMode"), 0, 3)
            if mode is not None and mode == int(mode):
                result["piston"] = Detection(True, mode > 0, 0, str(int(mode)))
    return result

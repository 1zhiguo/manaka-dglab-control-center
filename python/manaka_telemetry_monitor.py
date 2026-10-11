"""Read-only pilot monitor for the Manaka BepInEx telemetry plugin.

This program never connects to DG-LAB and cannot send device commands.
"""

from __future__ import annotations

import argparse
import json
import socket
import time


def bool_mark(value: object) -> str:
    return "Y" if value else "-"


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor Manaka game telemetry (dry run)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=45678, type=int)
    parser.add_argument("--stale-after", default=1.0, type=float)
    args = parser.parse_args()

    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind((args.host, args.port))
    receiver.settimeout(0.25)

    print(f"Manaka telemetry pilot listening on udp://{args.host}:{args.port}")
    print("DRY RUN: no DG-LAB connection and no device output")
    print("Enter the playable game scene, then compare BPM below with the top-left HUD.")

    last_packet_at: float | None = None
    stale_reported = False

    try:
        while True:
            try:
                payload, _ = receiver.recvfrom(65535)
            except socket.timeout:
                if (
                    last_packet_at is not None
                    and not stale_reported
                    and time.monotonic() - last_packet_at >= args.stale_after
                ):
                    print("\n[STALE] Telemetry stopped; a future controller would force output to zero.")
                    stale_reported = True
                continue

            packet = json.loads(payload.decode("utf-8"))
            last_packet_at = time.monotonic()
            stale_reported = False

            line = (
                f"seq={packet.get('sequence', 0):>7} "
                f"BPM={packet.get('heartRate', 0):>6.2f} "
                f"detect={packet.get('detection', 0):>5.3f} "
                f"watch={bool_mark(packet.get('watched'))} "
                f"show={bool_mark(packet.get('showingOff'))} "
                f"rise={bool_mark(packet.get('detectionRising'))} "
                f"found={bool_mark(packet.get('found'))} "
                f"npcAlert={packet.get('maxNpcAlert', 0):>5.3f} "
                f"watchN={packet.get('watchingNpcCount', 0):>2} "
                f"riseN={packet.get('risingNpcCount', 0):>2} "
                f"ecst={packet.get('ecstasy', 0):>5.3f} "
                f"org={bool_mark(packet.get('orgasm'))} "
                f"vib={str(packet.get('vibration', 'None')):<10} "
                f"piston={packet.get('piston', 0):>3} "
                f"move={bool_mark(packet.get('moving'))} "
                f"dash={bool_mark(packet.get('dashing'))} "
                f"stage={packet.get('stage', 'None'):<14} "
                f"action={packet.get('action', 'None')}"
            )
            print("\r" + line[:240].ljust(240), end="", flush=True)
    except KeyboardInterrupt:
        print("\nPilot monitor stopped.")
    finally:
        receiver.close()


if __name__ == "__main__":
    main()

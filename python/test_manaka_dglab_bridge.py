import asyncio
import json
import queue
import time
import unittest

import websockets

from manaka_dglab_bridge import DGLabBridge, clamp_strength, pulse_message, strength_message


class ProtocolEncodingTests(unittest.TestCase):
    def test_strength_is_clamped_to_user_hard_cap(self):
        self.assertEqual(strength_message("A", 90, 30), "strength-1+2+30")
        self.assertEqual(strength_message("B", -2, 30), "strength-2+2+0")
        self.assertEqual(clamp_strength(250, 200), 100)

    def test_wave_frames_are_validated(self):
        self.assertEqual(
            pulse_message("A", ["0A0A0A0A14141414"]),
            'pulse-A:["0A0A0A0A14141414"]',
        )
        with self.assertRaises(ValueError):
            pulse_message("A", ["not-a-frame"])

    def test_lan_address_can_refresh_the_qr_without_restarting(self):
        events: queue.Queue = queue.Queue()
        bridge = DGLabBridge(events, port=9999)
        bridge.available_lan_ips = ("192.168.1.20", "192.168.50.20")
        bridge.controller_id = "controller-id"

        self.assertTrue(bridge.set_lan_ip("192.168.50.20"))
        self.assertIn("ws://192.168.50.20:9999/controller-id", bridge.qr_url)
        self.assertFalse(bridge.set_lan_ip("203.0.113.5"))


class LocalSocketIntegrationTests(unittest.TestCase):
    def test_bind_output_and_emergency_zero(self):
        events: queue.Queue = queue.Queue()
        bridge = DGLabBridge(events, port=0)
        bridge.start()
        deadline = time.monotonic() + 3
        ready = None
        while time.monotonic() < deadline:
            kind, payload = events.get(timeout=3)
            if kind == "dglab" and payload.get("event") == "ready":
                ready = payload
                break
        self.assertIsNotNone(ready)

        async def fake_phone():
            uri = f"ws://127.0.0.1:{ready['port']}/"
            async with websockets.connect(uri) as websocket:
                hello = json.loads(await websocket.recv())
                phone_id = hello["clientId"]
                await websocket.send(
                    json.dumps(
                        {
                            "type": "bind",
                            "clientId": ready["controller_id"],
                            "targetId": phone_id,
                            "message": "DGLAB",
                        }
                    )
                )
                bind = json.loads(await asyncio.wait_for(websocket.recv(), timeout=2))
                self.assertEqual(bind["message"], "200")
                await asyncio.sleep(0.15)
                bridge.set_auto_enabled(True)
                bridge.update_auto_outputs(
                    18,
                    ("4E4E4E4E64646464",),
                    wave_key_a="test-a",
                    strength_b=9,
                    frames_b=("4646464650505050",),
                    wave_key_b="test-b",
                    hard_cap=20,
                )
                received = []
                deadline_loop = asyncio.get_running_loop().time() + 2
                while asyncio.get_running_loop().time() < deadline_loop:
                    packet = json.loads(await asyncio.wait_for(websocket.recv(), timeout=2))
                    received.append(packet.get("message"))
                    if (
                        "strength-1+2+18" in received
                        and "strength-2+2+9" in received
                        and any(str(value).startswith("pulse-A:") for value in received)
                        and any(str(value).startswith("pulse-B:") for value in received)
                    ):
                        break
                self.assertIn("strength-1+2+18", received)
                self.assertIn("strength-2+2+9", received)
                self.assertTrue(any(str(value).startswith("pulse-A:") for value in received))
                self.assertTrue(any(str(value).startswith("pulse-B:") for value in received))

                bridge.emergency_stop()
                emergency = []
                deadline_loop = asyncio.get_running_loop().time() + 2
                while asyncio.get_running_loop().time() < deadline_loop and "clear-2" not in emergency:
                    packet = json.loads(await asyncio.wait_for(websocket.recv(), timeout=2))
                    emergency.append(packet.get("message"))
                self.assertIn("strength-1+2+0", emergency)
                self.assertIn("strength-2+2+0", emergency)
                self.assertIn("clear-1", emergency)
                self.assertIn("clear-2", emergency)

        try:
            asyncio.run(fake_phone())
        finally:
            bridge.stop()


if __name__ == "__main__":
    unittest.main()


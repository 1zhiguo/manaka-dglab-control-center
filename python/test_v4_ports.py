"""Port collisions/reservations and restart recovery, without device output."""
import asyncio
import errno
import queue
import unittest
from unittest.mock import patch
from urllib.parse import unquote

from manaka_devices.dglab_v4 import DGLabV4Bridge
from manaka_devices.dglab_v4_hub import DGLabV4Hub
import manaka_devices.dglab_v4 as module


class V4PortTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, cls, port, check=None):
        bridge = cls(queue.Queue(), port=port, lan_ip="127.0.0.1")
        bridge.lan_ip = "127.0.0.1"  # Bypass production LAN-interface selection.
        task = asyncio.create_task(bridge._run())
        try:
            async with asyncio.timeout(3):
                while not bridge.server_ready:
                    if task.done():
                        await task
                        self.fail("V4 listener did not start")
                    await asyncio.sleep(.01)
            self.assertGreater(bridge.port, 0)
            self.assertIn(f"127.0.0.1:{bridge.port}", unquote(bridge.qr_url))
            self.assertFalse(bridge.auto_enabled)
            if check:
                check(bridge)
            # The advertised port really accepts connections.
            async with module.websockets.connect(f"ws://127.0.0.1:{bridge.port}/?tid={bridge.controller_id}") as phone:
                self.assertIn('"hello"', await phone.recv())
            return bridge
        finally:
            bridge._stop_event.set()
            await asyncio.wait_for(task, 3)

    async def test_occupied_port_falls_back_for_bridge_and_shared_hub(self):
        occupied = await asyncio.start_server(lambda r, w: w.close(), "0.0.0.0", 0)
        port = occupied.sockets[0].getsockname()[1]
        try:
            for cls in (DGLabV4Bridge, DGLabV4Hub):
                with self.subTest(cls=cls.__name__):
                    bridge = await self.exercise(cls, port, lambda b: self.assertNotEqual(b.port, port))
                    self.assertFalse(bridge.server_ready)
                    self.assertEqual(bridge.qr_url, "")
        finally:
            occupied.close()
            await occupied.wait_closed()

    async def test_windows_reserved_port_uses_actual_port_for_both_routes(self):
        serve = module.websockets.serve
        attempts = []
        def reserved(handler, host, port, **kwargs):
            attempts.append(port)
            if port == 9998:
                raise PermissionError(errno.EACCES, "simulated Windows port exclusion")
            return serve(handler, host, port, **kwargs)
        def check(hub):
            for role in ("coyote", "ovc"):
                route = hub.channel(role)
                self.assertEqual((route.port, route.qr_url), (hub.port, hub.qr_url))
                self.assertTrue(route.server_ready)
                self.assertFalse(route.auto_enabled)
        with patch.object(module.websockets, "serve", side_effect=reserved):
            await self.exercise(DGLabV4Hub, 9998, check)
        self.assertEqual(attempts, [9998, 0])

    async def test_failed_listen_clears_old_qr_and_same_hub_can_retry(self):
        hub = DGLabV4Hub(queue.Queue(), port=9998, lan_ip="127.0.0.1")
        hub.server_ready, hub.qr_url = True, "obsolete-qr"
        with patch.object(module.websockets, "serve", side_effect=PermissionError(errno.EACCES, "blocked")):
            await hub._run()
        for route in (hub, hub.channel("coyote"), hub.channel("ovc")):
            self.assertFalse(route.server_ready)
            self.assertEqual(route.qr_url, "")
        events = []
        while not hub.events.empty():
            events.append(hub.events.get_nowait()[1])
        self.assertEqual(sum(e["event"] == "server_error" for e in events), 1)
        hub.requested_port = 0
        task = asyncio.create_task(hub._run())
        try:
            async with asyncio.timeout(3):
                while not hub.server_ready:
                    await asyncio.sleep(.01)
            self.assertTrue(hub.channel("ovc").server_ready)
            self.assertNotIn("obsolete", hub.qr_url)
        finally:
            hub._stop_event.set()
            await asyncio.wait_for(task, 3)


if __name__ == "__main__":
    unittest.main()

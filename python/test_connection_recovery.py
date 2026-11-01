"""Real local server startup, including blocked ports and proxy environments."""
import asyncio
import base64
import json
from pathlib import Path
import queue
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QImage
from manaka_dglab_bridge import DGLabBridge
from qml_dashboard_prototype import backend as module


class ConnectionRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_blocked_port_recovers_and_gui_receives_valid_qr_without_proxy(self):
        async def scenario():
            with tempfile.TemporaryDirectory() as directory, patch.object(module, "app_data_dir", return_value=Path(directory)), patch.object(module, "load_config", return_value={}):
                backend = module.ControlCenterBackend(demo=True)
                backend.poll_timer.stop()
                backend.demo_mode = False
                bridge = DGLabBridge(backend.messages, port=9999)
                backend.bridge = bridge
                bridge.available_lan_ips = ("127.0.0.1",)
                bridge.lan_ip = "127.0.0.1"
                import manaka_dglab_bridge as transport
                serve = transport.websockets.serve
                calls = []

                async def blocked_once(handler, host, port, **kwargs):
                    calls.append(port)
                    if port == 9999:
                        raise PermissionError(13, "simulated Windows reserved port")
                    return await serve(handler, host, port, **kwargs)

                with patch.object(transport.websockets, "serve", side_effect=blocked_once), patch.dict("os.environ", {"http_proxy":"http://127.0.0.1:1", "https_proxy":"http://127.0.0.1:1", "all_proxy":"http://127.0.0.1:1", "no_proxy":""}):
                    task = asyncio.create_task(bridge._run())
                    try:
                        for _ in range(200):
                            await asyncio.sleep(.01)
                            backend._poll()
                            if backend.qrSource:
                                break
                        self.assertEqual(calls, [9999, 0])
                        self.assertTrue(backend.serverReady)
                        self.assertNotEqual(backend.socketPort, 9999)
                        self.assertEqual(backend.lanAddresses, ["127.0.0.1"])
                        png = base64.b64decode(backend.qrSource.split(",", 1)[1])
                        self.assertFalse(QImage.fromData(png).isNull())
                        self.assertIn(f":{bridge.port}/", bridge.qr_url)
                        self.assertFalse(bridge.auto_enabled)
                    finally:
                        bridge._stop_event.set()
                        await task
                        backend.shutdown()
        asyncio.run(scenario())

    def test_qr_failure_surfaces_and_address_refresh_recovers(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(module, "app_data_dir", return_value=Path(directory)), patch.object(module, "load_config", return_value={}):
            backend = module.ControlCenterBackend(demo=True)
            backend.demo_mode = False
            backend.bridge = DGLabBridge(queue.Queue(), port=0)
            backend.bridge.controller_id = "test-controller"
            backend.bridge.available_lan_ips = ("192.0.2.1",)
            backend.bridge.lan_ip = "192.0.2.1"
            backend.bridge.qr_url = backend.bridge._build_qr_url()
            try:
                with patch.object(backend, "_qr_data_url", side_effect=RuntimeError("test")):
                    backend._handle_dglab_event(dict(event="ready", lan_ip="192.0.2.1", port=12345))
                self.assertFalse(backend.qrSource)
                self.assertTrue(backend.connection_error_value)
                backend._handle_dglab_event(dict(event="ready", lan_ip="192.0.2.1", port=12345))
                self.assertTrue(backend.qrSource)
                self.assertFalse(backend.connection_error_value)
                with patch.object(module, "discover_lan_ips", return_value=()):
                    backend.refreshConnection()
                self.assertFalse(backend.qrSource)
                self.assertEqual(backend.lanAddresses, [])
            finally:
                backend.shutdown()

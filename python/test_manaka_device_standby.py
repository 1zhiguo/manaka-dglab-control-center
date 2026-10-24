"""Real Qt backend with fake transports: pre-game enable must stay at zero."""
import tempfile
import queue
import json
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QCoreApplication
from qml_dashboard_prototype import backend as module
from test_manaka_device_feedback import device
from test_manaka_trigger_engine import packet


class TelemetryReceiptTests(unittest.TestCase):
    def test_udp_receipt_time_overrides_wire_time_and_reports_real_receive_gap(self):
        messages = queue.Queue()
        worker = module.TelemetryWorker(messages)
        receiver = MagicMock()
        calls = 0
        def receive(_):
            nonlocal calls
            calls += 1
            if calls == 2:
                worker.stop_event.set()
            return json.dumps(packet(_received_monotonic=999999999)).encode(), ("127.0.0.1",1234)
        receiver.recvfrom.side_effect = receive
        with patch.object(module.socket,"socket",return_value=receiver), patch.object(module.time,"monotonic",side_effect=[100.,100.6]), patch.object(module.device_audit,"record") as record:
            worker.run()
        messages.get_nowait()  # listener-ready
        self.assertEqual(messages.get_nowait()[1]["_received_monotonic"],100.)
        self.assertEqual(messages.get_nowait()[1]["_received_monotonic"],100.6)
        record.assert_called_once_with("telemetry.receive_gap",gap_ms=600)
        receiver.close.assert_called_once()


class DeviceStandbyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.clock = time.monotonic()
        clock_patch = patch.object(module.time,"monotonic",side_effect=lambda:self.clock)
        clock_patch.start();self.addCleanup(clock_patch.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        for context in (patch.object(module, "app_data_dir", return_value=Path(directory.name)),
                        patch.object(module, "load_config", return_value={"language":"en"})):
            context.start(); self.addCleanup(context.stop)
        self.b = module.ControlCenterBackend(demo=True, language="en")
        self.b.poll_timer.stop()
        self.b.demo_mode = False
        self.b.socket_protocol = "v4"
        self.b.auto_output_enabled = False
        self.b.device_connected_value = self.b.ovc_connected = True
        self.b.last_receive = 0
        self.b.v4_hub = MagicMock(server_ready=True, app_connected=True)
        self.routes = {}
        for role in ("coyote", "ovc"):
            route = MagicMock(selected_slot_id=role, connected=True, _readiness_failure_latched=False)
            route.devices_snapshot.return_value = [device("COYOTE_030" if role=="coyote" else "OVC_1", role)]
            self.routes[role] = route
        self.b.v4_hub.channel.side_effect = self.routes.__getitem__
        self.b.bridge = self.routes["coyote"]
        self.addCleanup(self.b.shutdown)

    def receive_packet(self, **changes):
        self.clock += .1
        self.b._on_telemetry(packet(**changes))

    def enable_both(self):
        self.b.toggleOutput()
        self.b.toggleOvcOutput()

    def test_enable_before_game_persists_standby_without_arming_any_transport(self):
        self.enable_both()
        self.assertTrue(self.b.auto_output_enabled and self.b.ovc_enabled)
        self.assertTrue(self.b.coyote_waiting_for_game and self.b.ovc_waiting_for_game)
        self.assertIn("waiting for game", self.b.coyoteChannelStatus)
        self.assertIn("waiting for game", self.b.ovcStatus)
        self.assertEqual((self.b.current_output_a,self.b.current_output_b,self.b.ovc_output), (0,0,(0,0)))
        for _ in range(5):
            self.b._sync_ovc(force=True)
        self.assertTrue(self.b.ovc_enabled)
        for route in self.routes.values():
            route.set_auto_enabled.assert_not_called()

    def test_old_nonzero_game_state_is_never_replayed_when_enabling_standby(self):
        self.b.last_packet = packet(heartRate=160, vibration="High")
        self.b.last_receive = time.monotonic()-10
        self.b.current_frame = self.b.engine.evaluate(self.b.last_packet, dt=1)
        self.assertGreater(self.b.current_frame.strength_a,0)
        self.enable_both()
        self.assertEqual((self.b.current_output_a,self.b.current_output_b,self.b.ovc_output), (0,0,(0,0)))
        for route in self.routes.values():
            route.set_auto_enabled.assert_not_called()
        self.routes["ovc"].update_auto_outputs.assert_not_called()

    def test_first_fresh_game_packet_exits_standby_and_follows_game(self):
        self.enable_both()
        self.receive_packet(heartRate=150,vibration="High")
        self.b._sync_ovc(force=True)
        self.assertFalse(self.b.coyote_waiting_for_game or self.b.ovc_waiting_for_game)
        self.assertTrue(self.b.auto_output_enabled and self.b.ovc_enabled)
        self.assertGreater(self.b.current_output_a,0)
        self.assertEqual(self.b.ovc_output,(30,0))
        for route in self.routes.values():
            route.set_auto_enabled.assert_called_with(True)

    def test_manual_stop_cancels_pre_game_enable_and_later_game_cannot_rearm_it(self):
        self.enable_both()
        self.b.toggleOutput(); self.b.toggleOvcOutput()
        for route in self.routes.values():
            route.reset_mock()
        self.receive_packet(heartRate=160,vibration="High")
        self.b._sync_ovc(force=True)
        self.assertFalse(self.b.auto_output_enabled or self.b.ovc_enabled)
        for route in self.routes.values():
            route.set_auto_enabled.assert_not_called()
            route.update_auto_outputs.assert_not_called()

    def test_telemetry_loss_after_live_ovc_enters_zero_standby(self):
        self.enable_both()
        self.receive_packet(heartRate=150,vibration="High")
        self.b._sync_ovc(force=True)
        self.b.last_receive = time.monotonic()-1
        self.b._sync_ovc(force=True)
        self.assertTrue(self.b.ovc_enabled and self.b.ovc_waiting_for_game)
        self.assertEqual(self.b.ovc_output,(0,0))
        self.clock += .1
        self.b.last_receive = time.monotonic()
        self.b._sync_ovc(force=True)
        self.assertTrue(self.b.ovc_enabled)
        self.assertFalse(self.b.ovc_waiting_for_game)

    def test_producer_timeouts_keep_enable_but_require_data_received_after_the_fault(self):
        self.enable_both()
        self.receive_packet(heartRate=150,vibration="High")
        self.b._sync_ovc(force=True)
        for route in self.routes.values():
            route.reset_mock()
        cutoff = time.monotonic()
        for role in ("coyote","ovc"):
            self.b.v4_messages.put(("dglab",{"role":role,"event":"output_timeout","reason":"producer-stale","producer_stalled_at":cutoff}))
        self.b._poll_device_support()
        self.assertTrue(self.b.auto_output_enabled and self.b.ovc_enabled)
        self.assertTrue(self.b.coyote_waiting_for_game and self.b.ovc_waiting_for_game)
        self.assertEqual((self.b.current_output_a,self.b.current_output_b,self.b.ovc_output),(0,0,(0,0)))
        self.receive_packet(heartRate=160,vibration="High",_received_monotonic=cutoff-.05)
        self.b._sync_ovc(force=True)
        self.assertTrue(self.b.coyote_waiting_for_game and self.b.ovc_waiting_for_game)
        self.assertEqual((self.b.current_output_a,self.b.current_output_b,self.b.ovc_output),(0,0,(0,0)))
        for route in self.routes.values():
            route.set_auto_enabled.assert_not_called()
        self.receive_packet(heartRate=150,vibration="High")
        self.b._sync_ovc(force=True)
        self.assertFalse(self.b.coyote_waiting_for_game or self.b.ovc_waiting_for_game)
        self.assertEqual(self.b.ovc_output,(30,0))
        for route in self.routes.values():
            route.set_auto_enabled.assert_called_with(True)

    def test_app_confirmation_timeout_still_cancels_enable_and_never_auto_resumes(self):
        self.enable_both()
        self.receive_packet(heartRate=150,vibration="High")
        self.b._sync_ovc(force=True)
        for role in ("coyote","ovc"):
            self.b.v4_messages.put(("dglab",{"role":role,"event":"output_timeout","reason":"response-timeout"}))
        self.b._poll_device_support()
        self.assertFalse(self.b.auto_output_enabled or self.b.ovc_enabled)
        for route in self.routes.values():
            route.reset_mock()
        self.receive_packet(heartRate=150,vibration="High")
        self.b._sync_ovc(force=True)
        for route in self.routes.values():
            route.set_auto_enabled.assert_not_called()

    def test_queued_old_udp_packet_does_not_become_fresh_on_ui_processing(self):
        self.enable_both()
        old = time.monotonic()-1
        self.receive_packet(heartRate=160,vibration="High",_received_monotonic=old)
        self.b._sync_ovc(force=True)
        self.assertEqual(self.b.last_receive,old)
        self.assertTrue(self.b.coyote_waiting_for_game and self.b.ovc_waiting_for_game)
        self.assertEqual((self.b.current_output_a,self.b.current_output_b,self.b.ovc_output),(0,0,(0,0)))
        for route in self.routes.values():
            route.set_auto_enabled.assert_not_called()

    def test_delayed_timeout_event_cannot_undo_manual_stop(self):
        self.enable_both()
        self.b.toggleOutput();self.b.toggleOvcOutput()
        for role in ("coyote","ovc"):
            self.b.v4_messages.put(("dglab",{"role":role,"event":"output_timeout","reason":"producer-stale"}))
        self.b._poll_device_support()
        self.assertFalse(self.b.auto_output_enabled or self.b.ovc_enabled)
        for route in self.routes.values():
            route.reset_mock()
        self.receive_packet(heartRate=160,vibration="High")
        self.b._sync_ovc(force=True)
        for route in self.routes.values():
            route.set_auto_enabled.assert_not_called()

    def test_switching_to_single_device_v3_cancels_hidden_ovc_standby(self):
        self.b._device_persist = MagicMock()
        self.enable_both()
        self.b.selectSocketProtocol("v3")
        self.assertFalse(self.b.ovc_enabled or self.b.ovc_waiting_for_game)
        self.assertFalse(self.b.auto_output_enabled or self.b.coyote_waiting_for_game)
        self.routes["ovc"].emergency_stop.assert_called()


if __name__ == "__main__":
    unittest.main()

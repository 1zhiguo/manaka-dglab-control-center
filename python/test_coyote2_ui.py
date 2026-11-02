"""Coyote 2.0 discovery and UI diagnostics with fake transports only."""
import math
import unittest
from unittest.mock import patch

from test_manaka_device_feedback import device, harness


class Coyote2UiTests(unittest.TestCase):
    def ready(self):
        b, routes = harness()
        raw = device("COYOTE_020", "pulse")
        raw["props"].pop("channelAStatus", None)
        raw["props"].pop("channelBStatus", None)
        route = routes["coyote"]
        route.selected_slot_id = "pulse"
        route.selected_client_id = "app"
        route.connected = True
        route.devices_snapshot.return_value = [raw]
        b.v4_hub.devices_snapshot.return_value = [raw, device()]
        return b, route, raw

    def test_autoselects_020_for_pulse_and_never_authorizes_output(self):
        b, routes = harness()
        b.auto_output_enabled = b.ovc_enabled = False
        with patch("qml_dashboard_prototype.v4_integration.audit.record"):
            b._auto_select_new_v4_devices([device("COYOTE_020", "pulse"), device()])
        self.assertEqual(routes["coyote"].selected_slot_id, "pulse")
        self.assertEqual(routes["ovc"].selected_slot_id, "ovc")
        self.assertFalse(b.auto_output_enabled or b.ovc_enabled)
        for route in routes.values():
            route.set_auto_enabled.assert_not_called()

    def test_ui_role_filters_and_hardware_names_are_distinct(self):
        b, route, raw = self.ready()
        b.v4_hub.devices_snapshot.return_value += [device("COYOTE_030", "new"), device("OTHER", "other")]
        coyote = b.coyoteDevices[1:]
        ovc = b.ovcDevices[1:]
        self.assertEqual({row["type"] for row in coyote}, {"COYOTE_020", "COYOTE_030"})
        self.assertEqual({row["type"] for row in ovc}, {"OVC_1"})
        self.assertIn("Coyote 2.0", coyote[0]["label"])
        self.assertEqual(b.socket_protocol, "v4")

    def test_020_readiness_does_not_require_030_circuit_status(self):
        b, route, raw = self.ready()
        self.assertEqual(b.deviceBlockReason("coyote"), "")
        self.assertIn("Ready", b.coyoteChannelStatus)
        route.connected = False
        self.assertIn("safe zero", b.deviceBlockReason("coyote"))

    def test_unknown_and_invalid_current_app_limits_block_with_diagnostics(self):
        for bad in (None, True, -1, float("nan"), float("inf"), "60"):
            with self.subTest(limit=bad):
                b, route, raw = self.ready()
                for channel in "AB":
                    raw["slotState"]["channel" + channel]["intensityMax"] = bad
                    raw["slotState"]["channel" + channel]["intensityMaxMax"] = 100
                self.assertIn("current App channel limit", b.deviceBlockReason("coyote"))
                self.assertIn("output blocked", b.coyoteChannelStatus)
                self.assertNotIn("Ready", b.coyoteChannelStatus)

    def test_one_missing_limit_only_blocks_affected_channel(self):
        b, route, raw = self.ready()
        raw["slotState"]["channelA"].pop("intensityMax")
        self.assertEqual(b.deviceBlockReason("coyote"), "")
        self.assertIn("A: Waiting", b.coyoteChannelStatus)
        self.assertIn("B: Ready", b.coyoteChannelStatus)

    def test_zero_limits_block_without_inventing_a_default(self):
        b, route, raw = self.ready()
        for channel in "AB":
            raw["slotState"]["channel" + channel]["intensityMax"] = 0
        self.assertIn("limit is zero", b.deviceBlockReason("coyote"))
        self.assertNotIn("Ready", b.coyoteChannelStatus)

    def test_app_link_does_not_imply_bluetooth_readiness(self):
        b, route, raw = self.ready()
        raw["slotState"]["hasDevice"] = False
        self.assertIn("Bluetooth", b.deviceBlockReason("coyote"))

    def test_new_020_link_cannot_override_manual_pause_or_selection(self):
        b, routes = harness()
        b.auto_output_enabled = False
        routes["coyote"].selected_slot_id = "existing"
        with patch("qml_dashboard_prototype.v4_integration.audit.record"):
            b._auto_select_new_v4_devices([device("COYOTE_020", "pulse")])
        b.v4_hub.select_device.assert_not_called()
        self.assertFalse(b.auto_output_enabled)


if __name__ == "__main__":
    unittest.main()

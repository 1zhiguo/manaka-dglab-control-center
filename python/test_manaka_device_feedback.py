"""Discovery/UI state tests; all transport calls are mocks, no hardware output."""
import time
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

from test_manaka_ovc import Harness
from qml_dashboard_prototype import backend as backend_module
from manaka_devices.ovc import OvcPlanner, sanitize_profile, waveform_catalog


def device(kind="OVC_1", slot="ovc", reason=""):
    return {"type": kind, "clientId": "app", "slotId": slot, "selected": True,
            "props": {"connectState": "connected"},
            "slotState": {"hasDevice": True, "channelA": {"intensityMax": 100}, "channelB": {"intensityMax": 100}},
            "channelAReason": reason, "channelBReason": reason}


def harness():
    b = Harness()
    b.socket_protocol = "v4"
    b.hard_cap_value = 30
    routes = {role: MagicMock(selected_slot_id="", selected_client_id="", connected=False,
                               _readiness_failure_latched=False) for role in ("coyote", "ovc")}
    b.v4_hub.channel.side_effect = routes.__getitem__
    b.v4_hub.app_connected = b.v4_hub.server_ready = True

    def select(role, client, slot):
        routes[role].selected_client_id, routes[role].selected_slot_id = client, slot
        return True
    b.v4_hub.select_device.side_effect = select
    return b, routes


class DeviceDiscoveryTests(unittest.TestCase):
    def test_auto_selects_both_roles_without_authorization_or_persistence(self):
        b, routes = harness()
        b.auto_output_enabled = b.ovc_enabled = False
        with patch("qml_dashboard_prototype.v4_integration.audit.record"):
            b._auto_select_new_v4_devices([device("COYOTE_030", "pulse"), device()])
        self.assertEqual(routes["coyote"].selected_slot_id, "pulse")
        self.assertEqual(routes["ovc"].selected_slot_id, "ovc")
        self.assertFalse(b.auto_output_enabled or b.ovc_enabled)
        for route in routes.values():
            route.set_auto_enabled.assert_not_called()
            route.update_auto_outputs.assert_not_called()
        b.persist.assert_not_called()

    def test_patches_do_not_reselect_after_manual_deselection(self):
        b, routes = harness()
        with patch("qml_dashboard_prototype.v4_integration.audit.record"):
            b._auto_select_new_v4_devices([device()])
            self.assertTrue(b.selectV4Device("ovc", "", ""))
            b.v4_hub.select_device.reset_mock()
            b._auto_select_new_v4_devices([device()])
        self.assertEqual(routes["ovc"].selected_slot_id, "")
        b.v4_hub.select_device.assert_not_called()

    def test_reconnect_can_select_again_but_never_replaces_selected_route(self):
        b, routes = harness()
        routes["ovc"].selected_slot_id = "existing"
        with patch("qml_dashboard_prototype.v4_integration.audit.record"):
            b._auto_select_new_v4_devices([device()])
            b.v4_hub.select_device.assert_not_called()
            routes["ovc"].selected_slot_id = ""
            gone = device(); gone["slotState"]["hasDevice"] = False
            b._auto_select_new_v4_devices([gone])
            b._auto_select_new_v4_devices([device()])
        self.assertEqual(routes["ovc"].selected_slot_id, "ovc")

    def test_v3_coyote_and_unsupported_devices_are_not_selected(self):
        b, _ = harness(); b.socket_protocol = "v3"
        b._auto_select_new_v4_devices([device("COYOTE_030", "pulse"), device("COYOTE_020", "old")])
        b.v4_hub.select_device.assert_not_called()

    def test_real_app_conflicting_state_is_selected_but_not_authorized(self):
        b, routes = harness()
        raw = device("COYOTE_030", "coyote", "bluetooth-not-connected")
        raw["slotState"]["hasDevice"] = False
        b.auto_output_enabled = False
        with patch("qml_dashboard_prototype.v4_integration.audit.record"):
            b._auto_select_new_v4_devices([raw])
        self.assertEqual(routes["coyote"].selected_slot_id, "coyote")
        routes["coyote"].devices_snapshot.return_value = [raw]
        self.assertIn("Bluetooth", b.deviceBlockReason("coyote"))
        self.assertFalse(b.auto_output_enabled)
        routes["coyote"].set_auto_enabled.assert_not_called()
        routes["coyote"].update_auto_outputs.assert_not_called()

    def test_announced_slot_without_bluetooth_state_is_selected_only_once(self):
        b, routes = harness()
        raw = {"clientId":"app", "slotId":"coyote", "type":"COYOTE_030"}
        with patch("qml_dashboard_prototype.v4_integration.audit.record"):
            b._auto_select_new_v4_devices([raw])
            self.assertEqual(routes["coyote"].selected_slot_id, "coyote")
            b.selectV4Device("coyote", "", "")
            b.v4_hub.select_device.reset_mock()
            b._auto_select_new_v4_devices([raw])
        b.v4_hub.select_device.assert_not_called()


class DeviceFeedbackTests(unittest.TestCase):
    def test_v3_cannot_enable_or_save_ovc_even_when_a_hub_is_connected(self):
        b, routes = harness()
        b.socket_protocol = "v3"
        b.ovc_connected = True
        self.assertIn("V4",b.deviceBlockReason("ovc"))
        b.toggleOvcOutput()
        self.assertFalse(b.ovc_enabled)
        self.assertFalse(b.saveOvcProfile(b.ovcProfile))
        self.assertEqual(b.saveOvcWaveform("",[10]*16,""),"")
        b.persist.assert_not_called()
        routes["ovc"].set_auto_enabled.assert_not_called()

    def ready(self, role="ovc", reason=""):
        b, routes = harness()
        routes[role].selected_slot_id = role
        routes[role].connected = True
        routes[role].devices_snapshot.return_value = [device(reason=reason)]
        return b, routes[role]

    def test_blockers_explain_scan_selection_accessories_mute_and_zero(self):
        b, route = self.ready()
        self.assertEqual(b.deviceBlockReason("ovc"), "")
        b.v4_hub.app_connected = False
        self.assertIn("Scan", b.deviceBlockReason("ovc"))
        b.v4_hub.app_connected = True
        for reason, expected in (("accessory-not-inserted", "accessory"), ("channel-muted", "muted"), ("bluetooth-not-connected", "Bluetooth")):
            route.devices_snapshot.return_value = [device(reason=reason)]
            self.assertIn(expected, b.deviceBlockReason("ovc"))
            b.toggleOvcOutput()
            self.assertFalse(b.ovc_enabled)
        route.set_auto_enabled.assert_not_called()
        route.devices_snapshot.return_value = [device()]
        route.connected = False
        self.assertIn("safe zero", b.deviceBlockReason("ovc"))
        route._readiness_failure_latched = True
        self.assertIn("reselect", b.deviceBlockReason("ovc"))
        b.explainDeviceBlock("ovc")
        b._toast.assert_called()

    def test_enabled_channel_is_checked_even_if_unused_other_channel_is_ready(self):
        b, route = self.ready()
        item = device(reason="accessory-not-inserted")
        item["channelBReason"] = ""
        route.devices_snapshot.return_value = [item]
        self.assertIn("accessory", b.deviceBlockReason("ovc"))  # Only A enabled by default.
        b.ovc_profile["channels"]["B"]["enabled"] = True
        self.assertEqual(b.deviceBlockReason("ovc"), "")
        item["slotState"]["channelB"]["intensityMax"] = 0
        self.assertIn("limit is zero", b.deviceBlockReason("ovc"))

    def test_game_data_is_not_an_enable_requirement_but_zero_cap_still_blocks(self):
        b, route = self.ready()
        b.last_receive = time.monotonic() - 1
        self.assertEqual(b.deviceBlockReason("ovc"), "")
        b.last_receive = time.monotonic()
        b.ovc_profile["hard_cap"] = 0
        self.assertIn("cap is zero", b.deviceBlockReason("ovc"))
        route.devices_snapshot.return_value = [{"selected": True, "slotState": None}]
        self.assertIn("state", b.deviceBlockReason("ovc"))

    def test_coyote_backend_itself_checks_blocker_but_always_allows_stop(self):
        b, route = self.ready("coyote", "channel-muted")
        b.auto_output_enabled = False
        backend_module.ControlCenterBackend.toggleOutput(b)
        self.assertFalse(b.auto_output_enabled)
        b.bridge.set_auto_enabled.assert_not_called()
        b.auto_output_enabled = True
        backend_module.ControlCenterBackend.toggleOutput(b)
        self.assertFalse(b.auto_output_enabled)
        b.bridge.emergency_stop.assert_called_once()

    def test_card_states_require_actual_connections_and_explicit_output_enable(self):
        b, _ = harness()
        b.device_connected_value = b.auto_output_enabled = False
        b.ovc_connected = b.ovc_enabled = False
        b.v4_hub.app_connected = False
        self.assertFalse(b.phoneConnected or b.coyoteRunning or b.ovcRunning)
        b.v4_hub.app_connected = True
        self.assertTrue(b.phoneConnected)
        b.device_connected_value = b.ovc_connected = True
        self.assertFalse(b.coyoteRunning or b.ovcRunning)
        b.auto_output_enabled = b.ovc_enabled = True
        self.assertTrue(b.coyoteRunning and b.ovcRunning)
        b.emergencyStopAll()
        self.assertFalse(b.coyoteRunning or b.ovcRunning)
        self.assertTrue(b.phoneConnected)


class GameRandomTests(unittest.TestCase):
    def test_sync_follows_effective_mode_changes_including_off(self):
        planner, profile = OvcPlanner(), sanitize_profile({})
        for i, (mode, strength) in enumerate((("Low", 10), ("High", 30), ("Low", 10), ("Off", 0), ("Random", 0))):
            frame = planner.evaluate({"vibration": mode, "stage": "Stage02"}, profile, waveform_catalog(profile), now=i+1, fresh=True, authorized=True)
            self.assertEqual(frame["A"]["strength"], strength)
            self.assertEqual(frame["B"]["strength"], 0)
        self.assertNotIn("random", profile)


if __name__ == "__main__":
    unittest.main()

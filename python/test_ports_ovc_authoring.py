"""No hardware: port persistence/conflicts and custom action output."""
import queue,socket,time,unittest
from unittest.mock import MagicMock
from test_manaka_ovc import Harness
from manaka_devices.ovc import OvcPlanner,sanitize_profile,waveform_catalog

class PortTests(unittest.TestCase):
    def backend(self):
        b=Harness();b.saved={};b.runtime_started=False
        return b
    def free_port(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0));return sock.getsockname()[1]
    def test_port_conflict_does_not_save_or_stop_running_devices(self):
        b=self.backend()
        with socket.socket() as sock:
            sock.bind(("0.0.0.0",0));sock.listen()
            self.assertFalse(b.saveSocketPorts(sock.getsockname()[1],9998))
        b.persist.assert_not_called();b.bridge.stop.assert_not_called()
        self.assertTrue(b.auto_output_enabled)
    def test_ports_are_validated_and_saved_without_auto_enable(self):
        b=self.backend()
        for values in ((0,9998),(9998,9998),(9999,65536)):
            self.assertFalse(b.saveSocketPorts(*values))
        ports=self.free_port(),self.free_port()
        self.assertTrue(b.saveSocketPorts(*ports))
        self.assertEqual((b.socketPortV3,b.socketPortV4),ports)
        self.assertEqual(b.persist.call_args.args[0],dict(socket_port=ports[0],socket_v4_port=ports[1]))
        self.assertFalse(b.auto_output_enabled or b.ovc_enabled)
        self.assertTrue(b._ports_require_manual_enable)
        self.assertIsNone(b.bridge);self.assertIsNone(b.v4_hub)
        b._init_device_support(b.saved,b.persist)
        self.assertEqual((b.socketPortV3,b.socketPortV4),ports)
    def test_failed_config_write_keeps_connections_and_ports(self):
        b=self.backend();b.persist.side_effect=OSError("disk full")
        self.assertFalse(b.saveSocketPorts(self.free_port(),self.free_port()))
        self.assertEqual((b.socketPortV3,b.socketPortV4),(9999,9998))
        b.bridge.stop.assert_not_called()

class CustomActionTests(unittest.TestCase):
    def test_custom_wave_saved_and_actions_change_actual_frames_independently(self):
        b=Harness()
        key=b.saveOvcWaveform("Mine",[0,100]*8,"")
        profile=b.ovcProfile;profile["mode"]="independent"
        profile["channels"]["A"].update(enabled=True,mode="action",actions={
            "Walking":dict(mode="wave",wave=key,strength=20),
            "SexStandBack":dict(mode="wave",wave="ovc_ramp",strength=30)})
        profile["channels"]["B"].update(enabled=True,mode="fixed",wave="ovc_pulse",strength=20)
        self.assertTrue(b.saveOvcProfile(profile))
        p=OvcPlanner();catalog=b.ovcWaveforms
        def evaluate(action):
            return p.evaluate(dict(stage="Residence",vibration="Off",action=action),b.ovc_profile,catalog,now=1,fresh=True,authorized=True)
        first,second=evaluate("Walking"),evaluate("SexStandBack")
        self.assertEqual(first["A"]["wave"],key)
        self.assertNotEqual(first["A"]["frames"],second["A"]["frames"])
        self.assertEqual(first["B"]["frames"],second["B"]["frames"])
        self.assertGreater(first["A"]["strength"],0)
        self.assertEqual(evaluate("Other")["A"]["strength"],0)
    def test_unused_missing_default_wave_does_not_reject_valid_action_assignment(self):
        b=Harness();p=b.ovcProfile
        p["mode"]="independent";p["channels"]["A"].update(mode="action",wave="",
            actions={"Walking":dict(mode="wave",wave="ovc_breathe",strength=20)})
        self.assertTrue(b.saveOvcProfile(p))

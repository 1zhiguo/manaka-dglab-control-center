"""Source routing never changes the engine's safety decisions or physical caps."""
import itertools
import json
import unittest
from unittest.mock import patch

from manaka_pulse_routing import sanitize_sources, route_frame, heart_rate_bands
from manaka_trigger_engine import ManakaTriggerEngine, TriggerFrame
from manaka_waveforms import WaveformSelector, DEFAULT_WAVE_MAP
from test_manaka_trigger_engine import packet
import test_manaka_device_standby as standby
from qml_dashboard_prototype import backend as module


class PulseRoutingTests(unittest.TestCase):
    def test_every_source_combination_routes_strength_and_pattern_together(self):
        frame = TriggerFrame(24,9,"heartbeat-fast","action-ramp","reason",("event",),pulse_interval_ms=400)
        signals = {"heart":(24,"heartbeat-fast"),"action":(9,"action-ramp")}
        for a,b in itertools.product(signals,repeat=2):
            with self.subTest(a=a,b=b):
                routed = route_frame(frame,{"A":a,"B":b})
                self.assertEqual((routed.strength_a,routed.pattern_a),signals[a])
                self.assertEqual((routed.strength_b,routed.pattern_b),signals[b])
                self.assertEqual((routed.reason,routed.events,routed.pulse_interval_ms),("reason",("event",),400))
        self.assertEqual((frame.strength_a,frame.strength_b),(24,9))

    def test_safety_cut_and_peak_apply_to_all_source_combinations(self):
        for a,b in itertools.product(("heart","action"),repeat=2):
            sources = {"A":a,"B":b}
            safe = route_frame(TriggerFrame(20,12,"heartbeat","action-ramp","paused",(),True),sources)
            self.assertEqual((safe.strength_a,safe.strength_b,safe.pattern_a,safe.pattern_b),(0,0,"idle","idle"))
            self.assertTrue(safe.safe_cut)
            peak = route_frame(TriggerFrame(30,30,"peak","peak","peak",("peak-edge",)),sources)
            self.assertEqual((peak.strength_a,peak.strength_b,peak.pattern_a,peak.pattern_b),(30,30,"peak","peak"))

    def test_missing_and_malformed_saved_sources_keep_legacy_defaults(self):
        for raw in (None,[],"heart",{"A":[],"B":{}},{"A":"bad"}):
            self.assertEqual(sanitize_sources(raw),{"A":"heart","B":"action"})
        self.assertEqual(sanitize_sources({"A":"action"}),{"A":"action","B":"action"})

    def test_displayed_bands_match_actual_engine_boundaries(self):
        for start,full in ((67,150),(90,160)):
            bands = heart_rate_bands(start,full)
            engine = ManakaTriggerEngine(trigger_bpm=start,full_bpm=full)
            for bpm,pattern in ((start-.1,"idle"),(start,"heartbeat-soft"),
                                (bands["lowEnd"]-.01,"heartbeat-soft"),(bands["lowEnd"],"heartbeat"),
                                (bands["highStart"]-.01,"heartbeat"),(bands["highStart"],"heartbeat-fast"),
                                (full,"heartbeat-fast")):
                self.assertEqual(engine.evaluate(packet(heartRate=bpm),dt=.1).pattern_a,pattern)

    def test_debounce_follows_source_not_physical_channel(self):
        for channel,hold in (("A",False),("B",True)):
            selector = WaveformSelector(hold_seconds=.8)
            selector.select(channel,"heartbeat-soft","smart","heartbeat",DEFAULT_WAVE_MAP,now=1,hold_changes=hold)
            changed = selector.select(channel,"heartbeat","smart","heartbeat",DEFAULT_WAVE_MAP,now=1.1,hold_changes=hold)
            self.assertEqual(changed.key,"official_breath" if hold else "official_heartbeat")
            if hold:
                self.assertEqual(selector.select(channel,"heartbeat","smart","heartbeat",DEFAULT_WAVE_MAP,now=2,hold_changes=True).key,"official_heartbeat")
            self.assertIsNone(selector.select(channel,"idle","smart","heartbeat",DEFAULT_WAVE_MAP,now=2.1,hold_changes=hold))


class PulseBackendTests(unittest.TestCase):
    # Same isolated Qt backend and fake transports as the standby regression
    # suite, without inheriting/rerunning its tests.
    setUp = standby.DeviceStandbyTests.setUp
    receive_packet = standby.DeviceStandbyTests.receive_packet
    enable_both = standby.DeviceStandbyTests.enable_both

    @classmethod
    def setUpClass(cls):
        standby.DeviceStandbyTests.setUpClass()

    def save(self,a,b):
        w = self.b.wave_map_value
        return self.b.saveWaveSettings("smart","official_heartbeat",w["low"],w["mid"],w["high"],w["action"],w["peak"],
                                       self.b.custom_name_value,self.b.custom_points_value,self.b.custom_frequency_value,a,b)

    def test_save_pauses_only_pulse_and_preserves_unrelated_configuration(self):
        self.enable_both()
        with patch.object(module,"update_device_config") as persist:
            self.assertTrue(self.save("heart","heart"))
        self.assertEqual(persist.call_args.args[0]["pulse_channel_sources"],{"A":"heart","B":"heart"})
        self.assertFalse(self.b.auto_output_enabled)
        self.assertTrue(self.b.ovc_enabled)
        self.routes["coyote"].emergency_stop.assert_called()
        self.assertEqual((self.b.current_output_a,self.b.current_output_b),(0,0))
        self.receive_packet(heartRate=150)
        self.assertFalse(self.b.auto_output_enabled)

    def test_invalid_or_failed_save_keeps_running_configuration(self):
        self.enable_both()
        with patch.object(module,"update_device_config",side_effect=OSError("disk full")) as persist:
            self.assertFalse(self.save("other","heart"))
            persist.assert_not_called()
            self.assertFalse(self.save("heart","heart"))
        self.assertEqual(self.b.pulseChannelSources,{"A":"heart","B":"action"})
        self.assertTrue(self.b.auto_output_enabled and self.b.ovc_enabled)

    def test_sources_survive_restart_without_overwriting_other_settings(self):
        target = module.config_path()
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps({"language":"en","socket_protocol":"v4","unrelated":{"keep":1}}),encoding="utf-8")
        self.assertTrue(self.save("action","heart"))
        saved = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(saved["unrelated"],{"keep":1})
        self.assertEqual(saved["socket_protocol"],"v4")
        with patch.object(module,"load_config",return_value=saved):
            reloaded = module.ControlCenterBackend(demo=True,language="en")
        try:
            self.assertEqual(reloaded.pulseChannelSources,{"A":"action","B":"heart"})
        finally:
            reloaded.shutdown()

    def test_actual_backend_output_and_waveforms_follow_all_four_source_combinations(self):
        for a,b in itertools.product(("heart","action"),repeat=2):
            with self.subTest(a=a,b=b), patch.object(module,"update_device_config"):
                self.assertTrue(self.save(a,b))
                self.b.toggleOutput() if not self.b.auto_output_enabled else None
                self.receive_packet(heartRate=150,action="OnaniNormal",playingAction=True,ecstasy=.5)
                source = self.b.current_source_frame
                expected = route_frame(source,{"A":a,"B":b})
                self.assertEqual(self.b.current_frame,expected)
                for channel,kind in (("a",a),("b",b)):
                    wave = getattr(self.b,"current_wave_"+channel)
                    self.assertEqual(wave.key,"official_pulsating" if kind=="heart" else "official_heartbeat")
                    actual = getattr(self.b,"current_output_"+channel)
                    self.assertAlmostEqual(actual,getattr(expected,"strength_"+channel)*wave.feel_scale)
                    self.assertLessEqual(actual,self.b.hard_cap_value)
                # A reconnect/re-enable replays canonical data, never swaps a
                # previously routed frame a second time.
                self.b._show_frame(self.b.current_source_frame)
                self.assertEqual(self.b.current_frame,expected)

    def test_two_action_channels_are_quiet_without_action_even_with_high_heart_rate(self):
        with patch.object(module,"update_device_config"):
            self.save("action","action")
        self.b.toggleOutput()
        self.receive_packet(heartRate=150)
        self.assertEqual((self.b.current_output_a,self.b.current_output_b),(0,0))
        self.assertIsNone(self.b.current_wave_a)
        self.assertIsNone(self.b.current_wave_b)

    def test_two_heart_channels_play_without_action_and_still_zero_on_pause(self):
        with patch.object(module,"update_device_config"):
            self.save("heart","heart")
        self.b.toggleOutput()
        self.receive_packet(heartRate=150)
        self.assertGreater(self.b.current_output_b,0)
        self.assertEqual(self.b.current_output_a,self.b.current_output_b)
        self.receive_packet(heartRate=150,paused=True)
        self.assertEqual((self.b.current_output_a,self.b.current_output_b),(0,0))


if __name__ == "__main__":
    unittest.main()

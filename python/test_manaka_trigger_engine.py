import unittest

from manaka_trigger_engine import ManakaTriggerEngine, RollingPeakLimiter


def packet(**changes):
    base = {
        "sequence": 1,
        "monotonicMs": 10000,
        "heartRate": 95.0,
        "stage": "Residence",
        "action": "None",
        "playingAction": False,
        "maxNpcAlert": 0.0,
        "risingNpcCount": 0,
        "watchingNpcCount": 0,
        "ecstasy": 0.0,
        "orgasm": False,
        "gameOver": False,
    }
    base.update(changes)
    return base


class TriggerEngineTests(unittest.TestCase):
    def test_climax_is_previous_five_second_max_plus_fifteen(self):
        limiter = RollingPeakLimiter(window_ms=5000, maximum_rise=15)
        limiter.apply(18, 22, peak_active=False, now_ms=10000, hard_cap=90)
        output_a, output_b, limit = limiter.apply(
            90, 90, peak_active=True, now_ms=12000, hard_cap=90
        )
        self.assertEqual(limit, 37.0)
        self.assertEqual((output_a, output_b), (37.0, 37.0))

    def test_climax_dynamic_limit_still_obeys_hard_cap(self):
        limiter = RollingPeakLimiter(window_ms=5000, maximum_rise=15)
        limiter.apply(28, 20, peak_active=False, now_ms=10000, hard_cap=30)
        output_a, output_b, limit = limiter.apply(
            90, 90, peak_active=True, now_ms=10100, hard_cap=30
        )
        self.assertEqual(limit, 30.0)
        self.assertEqual((output_a, output_b), (30.0, 30.0))

    def test_climax_ignores_outputs_older_than_five_seconds(self):
        limiter = RollingPeakLimiter(window_ms=5000, maximum_rise=15)
        limiter.apply(70, 70, peak_active=False, now_ms=1000, hard_cap=100)
        limiter.apply(8, 6, peak_active=False, now_ms=6100, hard_cap=100)
        output_a, output_b, limit = limiter.apply(
            100, 100, peak_active=True, now_ms=6200, hard_cap=100
        )
        self.assertEqual(limit, 23.0)
        self.assertEqual((output_a, output_b), (23.0, 23.0))

    def test_high_bpm_alone_activates_heartbeat(self):
        frame = ManakaTriggerEngine().evaluate(packet(heartRate=160.0), dt=1.0)
        self.assertGreater(frame.strength_a, 0.0)
        self.assertEqual(frame.strength_b, 0.0)
        self.assertEqual(frame.pattern_a, "heartbeat-fast")
        self.assertGreater(frame.pulse_interval_ms, 0)

    def test_low_heart_rate_and_alert_do_not_activate(self):
        frame = ManakaTriggerEngine().evaluate(
            packet(heartRate=80.0, maxNpcAlert=0.5, risingNpcCount=1), dt=1.0
        )
        self.assertEqual((frame.strength_a, frame.strength_b), (0.0, 0.0))
        self.assertEqual(frame.pattern_a, "idle")

    def test_npc_alert_never_changes_heartbeat_output(self):
        engine = ManakaTriggerEngine()
        baseline = engine.evaluate(packet(heartRate=125.0), dt=2.0)
        alerted = engine.evaluate(
            packet(heartRate=125.0, maxNpcAlert=1.0, watchingNpcCount=3, risingNpcCount=3),
            dt=2.0,
        )
        self.assertEqual(alerted.strength_a, baseline.strength_a)
        self.assertEqual(alerted.pattern_a, baseline.pattern_a)
        self.assertEqual(alerted.events, ())

    def test_action_uses_ecstasy_ramp(self):
        frame = ManakaTriggerEngine().evaluate(
            packet(action="SexStandBack", playingAction=True, ecstasy=0.5, heartRate=140),
            dt=2.0,
        )
        self.assertGreater(frame.strength_a, 0.0)
        self.assertGreater(frame.strength_b, 0.0)
        self.assertEqual(frame.pattern_a, "heartbeat-fast")
        self.assertEqual(frame.pattern_b, "action-ramp")

    def test_peak_edge_has_cooldown(self):
        engine = ManakaTriggerEngine()
        engine.evaluate(packet(), dt=1.0)
        first = engine.evaluate(packet(action="Test", orgasm=True), dt=2.0)
        second = engine.evaluate(packet(action="Test", orgasm=True, monotonicMs=10100), dt=2.0)
        self.assertIn("peak-edge", first.events)
        self.assertNotIn("peak-edge", second.events)
        self.assertEqual(first.pattern_b, "peak")
        self.assertGreater(first.strength_b, 0.0)
        self.assertLessEqual(first.strength_b, 30.0)

    def test_starting_mid_encounter_emits_no_edges(self):
        engine = ManakaTriggerEngine()
        frame = engine.evaluate(
            packet(
                action="SexKijoui",
                playingAction=True,
                maxNpcAlert=1.0,
                watchingNpcCount=1,
                orgasm=True,
            ),
            dt=1.0,
        )
        self.assertEqual(frame.events, ())

    def test_game_over_is_immediate_safe_cut(self):
        engine = ManakaTriggerEngine()
        engine.evaluate(packet(action="Test", ecstasy=1.0), dt=2.0)
        frame = engine.evaluate(packet(gameOver=True), dt=0.1)
        self.assertTrue(frame.safe_cut)
        self.assertEqual((frame.strength_a, frame.strength_b), (0.0, 0.0))

    def test_system_menu_is_immediate_safe_cut(self):
        engine = ManakaTriggerEngine()
        engine.evaluate(packet(heartRate=160.0), dt=2.0)
        frame = engine.evaluate(packet(heartRate=160.0, systemMenuOpen=True), dt=0.1)
        self.assertTrue(frame.safe_cut)
        self.assertEqual(frame.reason, "game-paused")
        self.assertEqual((frame.strength_a, frame.strength_b), (0.0, 0.0))

    def test_game_time_scale_is_immediate_safe_cut(self):
        engine = ManakaTriggerEngine()
        frame = engine.evaluate(packet(heartRate=160.0, managedTimeScale=0.0), dt=0.1)
        self.assertTrue(frame.safe_cut)
        self.assertEqual(frame.reason, "game-paused")

    def test_personal_thresholds_map_minimum_to_maximum(self):
        engine = ManakaTriggerEngine(
            max_strength=30,
            min_strength=5,
            output_max=20,
            trigger_bpm=110,
            full_bpm=150,
        )
        at_start = engine.evaluate(packet(heartRate=110), dt=10.0)
        self.assertEqual(at_start.strength_a, 5.0)
        engine.output_a = 0.0
        at_full = engine.evaluate(packet(heartRate=150), dt=10.0)
        self.assertEqual(at_full.strength_a, 20.0)

    def test_hard_cap_cannot_exceed_device_range(self):
        engine = ManakaTriggerEngine(
            max_strength=200,
            min_strength=10,
            output_max=150,
            trigger_bpm=100,
            full_bpm=150,
        )
        frame = engine.evaluate(packet(heartRate=180), dt=10.0)
        self.assertEqual(engine.hard_cap, 100.0)
        self.assertLessEqual(frame.strength_a, 100.0)


if __name__ == "__main__":
    unittest.main()

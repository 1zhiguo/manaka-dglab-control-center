import json
from pathlib import Path
import unittest

from manaka_trigger_engine import ManakaTriggerEngine


class ReplayBaselineTests(unittest.TestCase):
    def test_replay_is_deterministic_and_pause_cuts_immediately(self):
        packets = [json.loads(line) for line in (Path(__file__).parent / "fixtures/channel_replay.jsonl").read_text().splitlines()]
        def replay():
            engine = ManakaTriggerEngine()
            return [engine.evaluate(packet, .1) for packet in packets]
        frames = replay()
        self.assertEqual(frames, replay())
        self.assertEqual((frames[4].strength_a, frames[4].strength_b), (0, 0))
        self.assertTrue(frames[4].safe_cut)
        self.assertTrue(frames[-1].safe_cut)
        self.assertIn("peak-edge", frames[3].events)

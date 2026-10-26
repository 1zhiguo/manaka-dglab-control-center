from dataclasses import replace
import queue
import time
import unittest

from manaka_channel_engine import Binding, ChannelSettings, MappingSettings
from manaka_runtime import DisplayMailbox, RealtimeProcessor, RuntimeConfig


class FakeBridge:
    connected = True
    auto_enabled = True
    def __init__(self):
        self.sent = []
        self.zeros = 0
    def channel_limit(self, key):
        return 100
    def channel_output(self,key):
        return 0
    def configure_limits(self,*args):
        pass
    def update_auto_outputs(self, *args, **kwargs):
        self.sent.append((args, kwargs))
    def zero_output(self):
        self.zeros += 1


def packet(sequence=1, **changes):
    result = dict(sequence=sequence, monotonicMs=sequence*100, sessionId="first", version=2,
                  stage="Residence", heartRate=160, ecstasy=1, action="Test", orgasm=False)
    result.update(changes)
    return result


class RealtimeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.mail = DisplayMailbox()
        self.processor = RealtimeProcessor(RuntimeConfig(), self.bridge, self.mail)

    def test_output_and_event_edges_continue_without_gui_consumption(self):
        for sequence in range(1, 200):
            self.processor.process(packet(sequence, orgasm=sequence == 100))
        self.assertEqual(len(self.bridge.sent), 199)
        self.assertGreater(self.bridge.sent[-1][0][0], 0)
        self.assertLessEqual(self.mail.qsize(), 3)
        events = []
        while self.mail.qsize():
            kind, value = self.mail.get_nowait()
            if kind == "runtime_event":
                events.append(value)
        self.assertEqual(events, ["A:climax", "B:climax"])
        self.assertGreater(self.mail.coalesced, 190)

    def test_sequence_rejection_and_session_restart_do_not_make_false_edges(self):
        first = self.processor.process(packet(10))
        self.assertIsNone(self.processor.process(packet(9, orgasm=True)))
        self.assertIs(self.processor.latest, first)
        restarted = self.processor.process(packet(1, sessionId="second", orgasm=True))
        self.assertEqual(restarted.frame.events, ())
        self.assertIsNone(self.processor.process(packet(11)))

    def test_receive_timestamp_is_not_refreshed_by_processing_backlog(self):
        self.assertIsNone(self.processor.process(packet(), time.monotonic()-2))
        self.assertEqual(self.bridge.sent, [])

    def test_configuration_change_zeros_and_rebaselines(self):
        self.processor.process(packet())
        self.processor.configure(replace(RuntimeConfig(), mapping=MappingSettings(global_cap=10)))
        self.assertGreater(self.bridge.zeros, 0)
        self.assertIsNone(self.processor.latest)
        self.assertEqual(self.processor.process(packet(2,orgasm=True)).frame.events, ())

    def test_swapped_action_binding_selects_action_wave_on_a(self):
        binding = Binding(source="action", wave="official_tide")
        config = replace(RuntimeConfig(), mapping=MappingSettings(A=ChannelSettings(bindings=(binding,))))
        self.processor.configure(config)
        snapshot = self.processor.process(packet())
        self.assertEqual(snapshot.wave_a.key, "official_tide")

    def test_device_caps_are_final_and_failure_defaults_to_zero(self):
        self.bridge.channel_limit = lambda key: 2 if key == "A" else 3
        for sequence in range(1, 10):
            snapshot = self.processor.process(packet(sequence))
        self.assertLessEqual(snapshot.output_a, 2)
        self.assertLessEqual(snapshot.output_b, 3)
        self.processor.process(packet(10, gameOver=True))
        self.assertGreater(self.bridge.zeros, 0)

    def test_deleted_wave_does_not_inflate_the_other_weighted_source(self):
        a = ChannelSettings(maximum=20,attack=100,combine="weighted",bindings=(
            Binding(source="action",wave="deleted-wave"),Binding(source="ecstasy",wave="official_tide",weight=.1)))
        self.processor.configure(replace(RuntimeConfig(),mapping=MappingSettings(A=a)))
        snapshot = self.processor.process(packet())
        self.assertLessEqual(snapshot.output_a,2)
        self.assertIn("action:wave-unavailable",snapshot.missing_a)

    def test_first_sample_after_real_telemetry_gap_rebaselines_events(self):
        now = [100.]
        processor = RealtimeProcessor(RuntimeConfig(),self.bridge,self.mail,clock=lambda:now[0])
        processor.process(packet())
        now[0] = 102.
        frame = processor.process(packet(2,orgasm=True)).frame
        self.assertEqual(frame.events,())

    def test_mailbox_stays_bounded_under_display_flood(self):
        for index in range(10000):
            self.mail.put(("runtime_snapshot", index))
        self.assertEqual(self.mail.qsize(), 1)
        self.assertEqual(self.mail.get_nowait(), ("runtime_snapshot", 9999))
        with self.assertRaises(queue.Empty):
            self.mail.get_nowait()

    def test_control_response_and_connection_state_survive_log_flood(self):
        response = ("progress_result",{"id":"pending","ok":True})
        self.mail.put(response)
        self.mail.put(("dglab",{"event":"disconnected"}))
        for index in range(1000):
            self.mail.put(("runtime_event",str(index)))
        self.assertEqual(self.mail.get_nowait(),response)
        self.assertEqual(self.mail.get_nowait(),("dglab",{"event":"disconnected"}))

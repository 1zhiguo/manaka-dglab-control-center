"""Native BLE validation with fake radios and GATT only."""
import asyncio
import time
import unittest
from types import SimpleNamespace

from .coyote_ble import CoyoteBleBridge, frames, SILENT
from .opossum_ble import OpossumBleBridge, display_frame, vibration_frame
from .ble_validation import BleTests, BackendBleTests, FakeClient, FakeClient2, Services, RECORDS


class SharedScanner:
    calls = 0
    coyote_name = "47L121000"

    @classmethod
    async def discover(cls, **kwargs):
        cls.calls += 1
        return {
            key: (SimpleNamespace(address=key, name=name), SimpleNamespace(local_name=name))
            for key, name in (
                ("coyote", cls.coyote_name), ("ovc", "47L127000"),
                ("sensor", "47L120100"), ("other", "47L127001")
            )
        }


class SharedScanner2(SharedScanner):
    coyote_name = "D-LAB ESTIM01"


class FakeOpossum(FakeClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_display = False
        self.displays = []
        self.last_wave = vibration_frame()

    async def write_gatt_char(self, uuid, payload, response=True):
        data = bytes(payload)
        self.rows.append({"at": time.monotonic(), "uuid": uuid, "hex": data.hex()})
        if data[0] == 0xB0:
            assert len(data) == 20
            assert not any(data[1:8] + data[12:16])
            assert max(data[8:12] + data[16:20]) <= 100
            self.last_wave = data
        elif data[0] == 0xB3:
            assert len(data) == 3 and max(data[1:]) <= 200
            self.actual = tuple(data[1:])
            if self.hold:
                self.held.append(data)
            elif not self.drop_ack:
                self.notify(None, data)
        elif data[0] == 0xB2:
            if self.fail_display:
                raise RuntimeError("Simulated B2 long-write rejection")
            assert response
            assert data == display_frame(*data[-2:])
            self.displays.append(tuple(data[-2:]))
        else:
            raise AssertionError("Wrong Opossum opcode")


class OpossumBleTests(BleTests):
    async def asyncSetUp(self):
        import queue
        self.events = queue.Queue()
        self.b = OpossumBleBridge(self.events, scanner=SharedScanner, client_factory=FakeOpossum)
        self.worker = asyncio.create_task(self.b._run())
        await self.until(lambda: self.b.server_ready)

    async def connect(self, hold=False):
        self.b.scan()
        await self.until(lambda: len(self.b.devices) == 1)
        self.assertTrue(self.b.select_device("ovc"))
        await self.until(lambda: self.b.client is not None)
        self.client = self.b.client
        if hold:
            self.client.hold = True
        await self.until(lambda: self.b.connected)

    async def test_explicit_scan_and_select_only_coyote3(self):
        await asyncio.sleep(.03)
        self.assertEqual(self.b.devices, [])
        self.b.scan()
        await self.until(lambda: bool(self.b.devices))
        self.assertEqual([d["address"] for d in self.b.devices], ["ovc"])
        self.assertFalse(self.b.select_device("coyote"))
        self.assertFalse(self.b.connected or self.b._auto_enabled)

    async def test_zero_bf_and_matching_b1_precede_ready(self):
        clients = []
        def factory(*args, **kwargs):
            c = FakeOpossum(*args, **kwargs)
            c.hold = True
            clients.append(c)
            return c
        self.b.client_factory = factory
        self.b.scan()
        await self.until(lambda: bool(self.b.devices))
        self.b.select_device("ovc")
        await self.until(lambda: bool(clients) and bool(clients[0].held))
        self.client = clients[0]
        self.assertFalse(self.b.connected)
        self.assertEqual(self.client.actual, (0, 0))
        await self.client.release()
        await self.until(lambda: self.b.connected)
        self.assertFalse(self.b._auto_enabled)
        self.assertEqual(self.client.displays, [(0, 0)])

    async def test_ab_cadence_caps_and_independent_frames(self):
        await self.connect()
        await self.run_frames(.5)
        rows = [p for p in self.commands() if any(p[8:12] + p[16:20])]
        self.assertGreaterEqual(len(rows), 3)
        a = frames(["0A0A0A0A64646464", "1414141428282828"])
        b = frames(["3232323214141414"])[0]
        self.assertEqual({p[8:12] for p in rows}, {p[4:] for p in a})
        self.assertEqual({p[16:] for p in rows}, {b[4:]})
        self.assertEqual(self.client.actual, (30, 30))
        self.assertIn((30, 30), self.client.displays)

    async def test_wrong_notification_cannot_confirm_intensity(self):
        await self.connect()
        self.client.hold = True
        self.plan()
        self.b.set_auto_enabled(True)
        await self.until(lambda: bool(self.client.held))
        pending = self.b._pending
        # Coyote feedback and D0 button packets cannot confirm Opossum strength.
        self.b._notify(self.client, self.b._epoch, bytes([0xB1, 1, 30, 30]))
        self.b._notify(self.client, self.b._epoch, bytes([0xD0]) + bytes(15))
        self.b._notify(self.client, self.b._epoch, bytes([0xB3, 0, 0]))
        self.assertFalse(pending[2].done())
        await self.client.release()

    async def test_disconnection_reselection_clears_old_plan(self):
        await self.connect()
        await self.run_frames(.2)
        await self.client.disconnect()
        await self.until(lambda: not self.b.connected)
        self.b.select_device("ovc")
        await self.until(lambda: self.b.connected)
        self.client = self.b.client
        self.assertFalse(self.b._auto_enabled)
        self.assertEqual(self.b._desired_updated_at, 0)
        self.assertEqual(self.client.actual, (0, 0))

    async def test_encoder_layout_and_invalid_frames(self):
        a, b = bytes([10]*4+[0,25,50,100]), bytes([10]*4+[100,50,25,0])
        self.assertEqual(vibration_frame(a,b).hex(), "b000000000000000001932640000000064321900")
        self.assertEqual(display_frame(10,20).hex(), "b2ffff00ffffffffffffffffffffffffffffffff08090a14")
        for invalid in (bytes(7), bytes([10]*4+[101]*4)):
            with self.assertRaises(ValueError):
                vibration_frame(invalid, SILENT)

    async def test_rescan_keeps_connected_nonadvertising_device(self):
        await self.connect()
        detail = self.b.detail
        class EmptyScan:
            @staticmethod
            async def discover(**kwargs):
                return {}
        self.b.scanner = EmptyScan
        self.b.scan()
        await asyncio.sleep(.08)
        self.assertEqual(self.b.detail, detail)
        self.assertEqual(self.b.devices[0]["address"], "ovc")
        self.assertTrue(self.b.connected)
        self.assertTrue(self.b.select_device("ovc"))

    async def test_ovc_200_range_kept_separate_from_coyote_100(self):
        await self.connect()
        await self.run_frames(.3, a=180, b=140, cap=160)
        self.assertEqual(self.client.actual, (160, 140))
        await self.run_frames(.25, a=200, b=200, cap=110)
        self.assertEqual(self.client.actual, (110, 110))
        self.assertEqual(self.client.displays[-1], (110, 110))

    async def test_display_write_failure_blocks_connection(self):
        def factory(*args, **kwargs):
            c = FakeOpossum(*args, **kwargs)
            c.fail_display = True
            self.client = c
            return c
        self.b.client_factory = factory
        self.b.scan()
        await self.until(lambda: bool(self.b.devices))
        self.b.select_device("ovc")
        await self.until(lambda: "failed" in self.b.detail.lower())
        self.assertFalse(self.b.connected or self.b._auto_enabled)
        self.assertEqual(self.client.actual, (0, 0))

    async def test_unsolicited_button_above_cap_stops_and_updates_display(self):
        await self.connect()
        await self.run_frames(.2)
        self.b._notify(self.client, self.b._epoch, bytes([0xB3, 100, 100]))
        await self.until(lambda: self.client.actual == (0, 0))
        self.assertFalse(self.b._auto_enabled)
        await self.until(lambda:self.client.displays[-1] == (0,0))


class BackendDualBleTests(BackendBleTests):
    scanner = SharedScanner
    coyote_factory = FakeClient

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.ovc = OpossumBleBridge(self.events, client_factory=FakeOpossum)
        self.ovc_worker = asyncio.create_task(self.ovc._run())
        await self.until(lambda: self.ovc.server_ready)
        self.b.scanner = self.scanner
        self.b.client_factory = self.coyote_factory
        self.b.discovery_sink = self.ovc.accept_discovery
        self.backend.ovc_ble = self.ovc

    async def asyncTearDown(self):
        self.ovc._stop_event.set()
        await asyncio.wait_for(self.ovc_worker, 3)
        RECORDS.append({"case": self._testMethodName+" / Opossum", "physical_hardware":False,
                        "writes": self.ovc.client.rows if self.ovc.client else []})
        self.backend.ovc_ble = None
        await super().asyncTearDown()

    async def connect_both(self):
        before = self.scanner.calls
        await self.connect()
        await self.until(lambda: bool(self.ovc.devices))
        self.assertEqual(self.scanner.calls, before+1)
        self.assertFalse(self.ovc.select_device("coyote"))
        self.assertTrue(self.backend.connectBleRole("ovc", "ovc"))
        await self.until(lambda: self.ovc.connected)
        self.backend._poll_device_support()
        self.assertTrue(self.backend.ovc_connected)
        self.assertFalse(self.backend.ovc_enabled)

    async def feed_until(self, predicate, action="SexStandBack"):
        end = time.monotonic()+2
        while time.monotonic()<end:
            self.feed(action)
            await asyncio.sleep(.03)
            if predicate():
                return
        self.fail("Dual BLE output did not resume: "+repr((self.b.detail,self.ovc.detail,self.backend.ovc_gate)))

    async def enabled_both(self):
        await self.connect_both()
        self.feed()
        self.backend.toggleOutput()
        self.backend.toggleOvcOutput()
        for _ in range(14):
            self.feed()
            await asyncio.sleep(.03)
        self.assertTrue(self.b._auto_enabled and self.ovc._auto_enabled)
        self.assertGreater(max(self.client.actual), 0)
        self.assertGreater(max(self.ovc.client.actual), 0)

    async def test_custom_action_waveforms_and_sync_on_dual_ble(self):
        await self.connect_both()
        key = self.backend.saveOvcWaveform("BLE custom", [0,100]*8, "")
        self.assertTrue(key)
        profile = self.backend.ovcProfile
        profile["mode"] = "independent"
        profile["channels"]["A"].update(enabled=True,mode="action",actions={
            "Walking":dict(mode="wave",wave=key,strength=20),
            "SexStandBack":dict(mode="wave",wave="ovc_ramp",strength=30)})
        profile["channels"]["B"].update(enabled=True,mode="fixed",wave="ovc_pulse",strength=20)
        self.assertTrue(self.backend.saveOvcProfile(profile))
        self.feed("Walking")
        self.backend.toggleOutput()
        self.backend.toggleOvcOutput()
        await self.feed_until(lambda:self.ovc.client.actual==(20,20), "Walking")
        first = self.ovc._desired_frames["A"]
        other = self.ovc._desired_frames["B"]
        self.assertEqual(first, frames(self.backend.ovc_frame["A"]["frames"]))
        self.assertEqual(self.ovc.client.actual, (20,20), repr((self.ovc.detail,self.ovc._auto_enabled,self.ovc._generation,self.ovc._desired_updated_at,self.ovc._pause_zero_task,self.backend.ovc_enabled,self.backend.ovc_gate)))
        self.assertTrue(self.b._auto_enabled)
        for _ in range(12):
            self.feed("SexStandBack")
            await asyncio.sleep(.03)
        self.assertNotEqual(first, self.ovc._desired_frames["A"])
        self.assertEqual(other, self.ovc._desired_frames["B"])
        self.assertEqual(self.ovc.client.actual, (30,20))

    async def test_ovc_disconnect_does_not_stop_coyote_or_auto_resume(self):
        await self.enabled_both()
        await self.ovc.client.disconnect()
        for _ in range(8):
            self.feed()
            await asyncio.sleep(.03)
        self.assertFalse(self.backend.ovc_enabled or self.backend.ovc_connected)
        self.assertTrue(self.b._auto_enabled)
        self.assertTrue(self.backend.connectBleRole("ovc","ovc"))
        await self.until(lambda:self.ovc.connected)
        for _ in range(8):
            self.feed()
            await asyncio.sleep(.03)
        self.assertFalse(self.ovc._auto_enabled or self.backend.ovc_enabled)
        self.assertEqual(self.ovc.client.actual,(0,0))

    async def test_global_stop_and_telemetry_standby_cover_both_routes(self):
        await self.enabled_both()
        self.backend._enter_safety_idle("telemetry-stale")
        await self.until(lambda:self.client.actual==self.ovc.client.actual==(0,0))
        self.assertTrue(self.backend.auto_output_enabled and self.backend.ovc_enabled)
        for _ in range(12):
            self.feed()
            await asyncio.sleep(.03)
        self.assertTrue(self.b._auto_enabled and self.ovc._auto_enabled)
        self.backend.emergencyStopAll()
        await self.until(lambda:self.client.actual==self.ovc.client.actual==(0,0))
        for _ in range(8):
            self.feed()
            await asyncio.sleep(.03)
        self.assertFalse(self.backend.auto_output_enabled or self.backend.ovc_enabled)
        self.assertFalse(self.b._auto_enabled or self.ovc._auto_enabled)

    async def test_modes_are_exclusive_and_retired_socket_events_ignored(self):
        await self.enabled_both()
        self.backend.v4_messages.put(("dglab",dict(role="ovc",event="connected")))
        self.backend._poll_device_support()
        self.assertTrue(self.backend.ovc_enabled)
        self.backend.runtime_started=False
        self.backend.selectSocketProtocol("v3")
        await asyncio.wait_for(asyncio.gather(self.worker,self.ovc_worker),3)
        self.assertIsNone(self.backend.ovc_ble)
        self.assertFalse(self.backend.ovc_enabled or self.backend.auto_output_enabled)
        self.assertFalse(self.b.connected or self.ovc.connected)


class BackendDualBle2Tests(BackendDualBleTests):
    scanner = SharedScanner2
    coyote_factory = FakeClient2


class ThreadedDualBleTests(unittest.TestCase):
    """Exercise production worker threads, not a GUI-owned asyncio loop."""
    def test_both_generations_and_ovc_send_on_separate_worker_loops(self):
        import queue
        import threading
        def until(predicate, timeout=2):
            end = time.monotonic()+timeout
            while time.monotonic()<end:
                if predicate():
                    return
                time.sleep(.01)
            self.fail("Threaded BLE mock timed out")
        for scanner,factory in ((SharedScanner,FakeClient),(SharedScanner2,FakeClient2)):
            with self.subTest(scanner=scanner.__name__):
                events=queue.Queue()
                ovc=OpossumBleBridge(events,client_factory=FakeOpossum)
                coyote=CoyoteBleBridge(events,scanner=scanner,client_factory=factory,discovery_sink=ovc.accept_discovery)
                try:
                    ovc.start()
                    coyote.start()
                    until(lambda:ovc.server_ready and coyote.server_ready)
                    before=scanner.calls
                    coyote.scan()
                    until(lambda:bool(coyote.devices) and bool(ovc.devices))
                    self.assertEqual(scanner.calls,before+1)
                    self.assertTrue(coyote.select_device("coyote"))
                    self.assertTrue(ovc.select_device("ovc"))
                    until(lambda:coyote.connected and ovc.connected)
                    self.assertIsNot(coyote._loop,ovc._loop)
                    self.assertIsNot(coyote._thread,threading.current_thread())
                    end=time.monotonic()+.5
                    while time.monotonic()<end:
                        for route,a,b,cap in ((coyote,20,10,30),(ovc,160,120,170)):
                            route.update_auto_outputs(a,["0A0A0A0A64646464"],wave_key_a="one",
                                strength_b=b,frames_b=["1414141428282828"],wave_key_b="two",hard_cap=cap)
                            route.set_auto_enabled(True)
                        time.sleep(.03)
                    self.assertEqual(coyote.client.actual,(20,10))
                    self.assertEqual(ovc.client.actual,(160,120))
                    coyote.latch_global_emergency_stop()
                    ovc.latch_global_emergency_stop()
                    until(lambda:coyote.client.actual==ovc.client.actual==(0,0))
                finally:
                    coyote.stop(timeout=4)
                    ovc.stop(timeout=4)
                self.assertFalse(coyote._thread.is_alive() or ovc._thread.is_alive())
                self.assertFalse(coyote.connected or ovc.connected)
                RECORDS.append({"case":"threaded-dual / "+scanner.__name__,"physical_hardware":False,
                    "coyote_writes":coyote.client.rows if coyote.client else [],
                    "ovc_writes":ovc.client.rows if ovc.client else []})

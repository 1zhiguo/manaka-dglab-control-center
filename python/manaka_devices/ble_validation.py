"""Fake GATT only: no radio scan, pairing or physical output in validation."""
import asyncio,io,json,queue,time,unittest
from types import SimpleNamespace
from pathlib import Path
from .coyote_ble import CoyoteBleBridge,b0,bf,frames,SERVICE,WRITE,NOTIFY,V2_SERVICE,V2_STRENGTH,V2_A,V2_B,v2_strength,v2_wave

RECORDS=[]
class Services:
    def get_service(self,uuid):
        return uuid==SERVICE
    def get_characteristic(self,uuid):
        return SimpleNamespace(properties=["write"]) if uuid in (WRITE,NOTIFY) else None

class FakeScanner:
    @staticmethod
    async def discover(**kwargs):
        return {name:(SimpleNamespace(address=name,name=label),SimpleNamespace(local_name=label))
                for name,label in (("coyote","47L121000"),("sensor","47L120100"),("ovc","OVC"))}

class FakeClient:
    def __init__(self,device,disconnected_callback=None):
        self.device=device;self.callback=disconnected_callback;self.services=Services()
        self.is_connected=False;self.notify=None;self.rows=[]
        self.hold=False;self.drop_ack=False;self.held=[];self.cap=(0,0);self.actual=(0,0)
    async def connect(self):
        self.is_connected=True
    async def start_notify(self,uuid,callback):
        self.notify=callback
    async def read_gatt_char(self,uuid):
        return bytes([81])
    async def write_gatt_char(self,uuid,payload,response=True):
        data=bytes(payload);row={"at":time.monotonic(),"uuid":uuid,"hex":data.hex()}
        self.rows.append(row)
        if data[0]==0xBF:
            self.cap=tuple(data[1:3]);return
        assert data[0]==0xB0 and len(data)==20
        assert all(10<=x<=240 for x in data[4:8]+data[12:16])
        assert all(x<=100 for x in data[8:12]+data[16:20])
        seq,mode=data[1]>>4,data[1]&15
        if mode:
            self.actual=tuple(min(v,c) for v,c in zip(data[2:4],self.cap))
            ack=bytes([0xB1,seq,*self.actual])
            if self.hold:self.held.append(ack)
            elif not self.drop_ack:self.notify(None,ack)
    async def release(self):
        self.hold=False;pending,self.held=self.held,[]
        for ack in pending:self.notify(None,ack)
    async def disconnect(self):
        self.is_connected=False
        if self.callback:self.callback(self)

class BleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.events=queue.Queue()
        self.b=CoyoteBleBridge(self.events,scanner=FakeScanner,client_factory=FakeClient)
        self.worker=asyncio.create_task(self.b._run())
        await self.until(lambda:self.b.server_ready)
    async def asyncTearDown(self):
        self.b._stop_event.set()
        await asyncio.wait_for(self.worker,3)
        RECORDS.append({"case":self._testMethodName,"physical_hardware":False,
                        "writes":self.client.rows if hasattr(self,"client") else []})
    async def until(self,fn,timeout=2):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if fn():return
            await asyncio.sleep(.01)
        self.fail("BLE mock timed out: "+self.b.detail)
    async def connect(self,hold=False):
        self.b.scan()
        await self.until(lambda:len(self.b.devices)==1)
        self.assertTrue(self.b.select_device("coyote"))
        await self.until(lambda:self.b.client is not None)
        self.client=self.b.client
        if hold:self.client.hold=True
        await self.until(lambda:self.b.connected)
    def plan(self,a=70,b=40,cap=30):
        self.b.update_auto_outputs(a,["0A0A0A0A64646464","1414141428282828"],wave_key_a="a",
                strength_b=b,frames_b=["3232323214141414"],wave_key_b="b",hard_cap=cap)
    async def run_frames(self,seconds=.3,**kwargs):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            self.plan(**kwargs);self.b.set_auto_enabled(True);await asyncio.sleep(.025)
    def commands(self):
        return [bytes.fromhex(x["hex"]) for x in self.client.rows if x["hex"].startswith("b0")]
    async def test_explicit_scan_and_select_only_coyote3(self):
        await asyncio.sleep(.05);self.assertEqual(self.b.devices,[])
        self.b.scan();await self.until(lambda:bool(self.b.devices))
        self.assertEqual([r["address"] for r in self.b.devices],["coyote"])
        self.assertFalse(self.b.select_device("ovc"))
        self.assertFalse(self.b.connected or self.b._auto_enabled)
    async def test_zero_bf_and_matching_b1_precede_ready(self):
        # Hold all zero acknowledgements, independent of callback timing.
        clients=[]
        def factory(*args,**kwargs):
            c=FakeClient(*args,**kwargs);c.hold=True;clients.append(c);return c
        self.b.client_factory=factory
        self.b.scan();await self.until(lambda:bool(self.b.devices))
        self.b.select_device("coyote");await self.until(lambda:bool(clients) and bool(clients[0].held))
        self.client=clients[0];self.assertFalse(self.b.connected)
        self.assertEqual(bytes.fromhex(self.client.rows[0]["hex"]),bf(0))
        await self.client.release();await self.until(lambda:self.b.connected)
        self.assertFalse(self.b._auto_enabled)
        self.assertEqual(self.b.battery,81)
    async def test_ab_cadence_caps_and_independent_frames(self):
        await self.connect();await self.run_frames(.5)
        rows=self.commands()[1:];self.assertGreaterEqual(len(rows),3)
        self.assertTrue(all(p[2]<=30 and p[3]<=30 for p in rows if p[1]&15))
        self.assertTrue(any(p[4:12]!=p[12:] for p in rows))
        self.assertEqual({p[12:] for p in rows},{frames(["3232323214141414"])[0]})
        self.assertEqual({p[4:12] for p in rows},set(frames(["0A0A0A0A64646464","1414141428282828"])))
    async def test_dynamic_cap_lower_zero_and_stop_at_stale(self):
        await self.connect();await self.run_frames(.22)
        await self.run_frames(.25,a=80,b=90,cap=10)
        self.assertLessEqual(max(self.client.actual),10)
        await self.run_frames(.2,cap=0);self.assertEqual(self.client.actual,(0,0))
        await self.run_frames(.2)
        await asyncio.sleep(.75)
        self.assertFalse(self.b._auto_enabled);self.assertEqual(self.client.actual,(0,0))
    async def test_ack_timeout_disconnects_no_auto_recovery(self):
        await self.connect();self.client.drop_ack=True
        await self.run_frames(.25)
        await self.until(lambda:not self.b.connected,timeout=2)
        self.assertFalse(self.b._auto_enabled)
    async def test_pause_resume_requires_fresh_plan(self):
        await self.connect();await self.run_frames(.2)
        self.b.set_paused(True);await self.until(lambda:self.b._paused)
        await self.until(lambda:self.client.actual==(0,0))
        self.b.set_paused(False);await self.until(lambda:not self.b._paused)
        self.assertFalse(self.b._auto_enabled)
        await self.run_frames(.2);self.assertTrue(self.b._auto_enabled)
    async def test_global_stop_unlock_does_not_restart(self):
        await self.connect();await self.run_frames(.2)
        self.b.latch_global_emergency_stop();await self.until(lambda:self.client.actual==(0,0))
        self.b.clear_global_emergency_stop();await asyncio.sleep(.15)
        self.assertFalse(self.b._auto_enabled)
    async def test_disconnection_reselection_clears_old_plan(self):
        await self.connect();await self.run_frames(.2)
        await self.client.disconnect();await self.until(lambda:not self.b.connected)
        self.b.select_device("coyote");await self.until(lambda:self.b.connected)
        self.client=self.b.client
        self.assertFalse(self.b._auto_enabled);self.assertEqual(self.b._desired_updated_at,0)
        self.assertEqual(self.client.actual,(0,0))
    async def test_wrong_notification_cannot_confirm_intensity(self):
        await self.connect()
        self.client.hold=True;self.plan()
        self.b.set_auto_enabled(True)
        await self.until(lambda:bool(self.client.held))
        pending=self.b._pending
        self.b._notify(self.client,self.b._epoch,bytes([0xB1,(pending[0]%15)+1,30,30]))
        self.assertFalse(pending[2].done())
        await self.client.release()
    async def test_encoder_layout_and_invalid_frames(self):
        self.assertEqual(b0(1,20,30).hex(),"b01f141e0a0a0a0a000000000a0a0a0a00000000")
        self.assertEqual(bf(250),bytes([0xBF,100,100,0,0,0,0]))
        for value in ("0A0A0A0A65656565","0000000064646464","FFFF","oops"):
            with self.assertRaises(ValueError):frames([value])

class Services2(Services):
    def get_service(self,uuid):return uuid==V2_SERVICE
    def get_characteristic(self,uuid):
        return SimpleNamespace(properties=["read","write","notify"]) if uuid in (V2_STRENGTH,V2_A,V2_B) else None

class FakeScanner2:
    @staticmethod
    async def discover(**kwargs):
        return {"coyote":(SimpleNamespace(address="coyote",name="D-LAB ESTIM01"),SimpleNamespace(local_name="D-LAB ESTIM01"))}

class FakeClient2(FakeClient):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.services=Services2();self.mismatch=False
    async def write_gatt_char(self,uuid,payload,response=True):
        data=bytes(payload)
        self.rows.append({"at":time.monotonic(),"uuid":uuid,"hex":data.hex()})
        assert len(data)==3
        if uuid==V2_STRENGTH:
            value=int.from_bytes(data,"little")
            assert not value>>22
            raw=(value>>11&2047,value&2047)
            assert max(raw)<=700
            self.actual=tuple(v/7 for v in raw)
            if self.notify:self.notify(None,data)
        else:
            value=int.from_bytes(data,"little")
            assert not value>>20 and (value>>15&31)<=20
    async def read_gatt_char(self,uuid):
        if uuid==V2_STRENGTH:
            if self.drop_ack:await asyncio.sleep(2)
            return v2_strength(100,100) if self.mismatch else v2_strength(*self.actual)
        return bytes([81])

class Ble2Tests(BleTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.b.scanner=FakeScanner2;self.b.client_factory=FakeClient2
    async def test_explicit_scan_and_select_only_coyote3(self):
        await asyncio.sleep(.05);self.assertEqual(self.b.devices,[])
        self.b.scan();await self.until(lambda:bool(self.b.devices))
        self.assertIn("2.0",self.b.devices[0]["label"])
        self.assertFalse(self.b.select_device("ovc"))
        self.assertFalse(self.b.connected or self.b._auto_enabled)
    async def test_zero_bf_and_matching_b1_precede_ready(self):
        await self.connect()
        self.assertEqual(self.b.device_type,"COYOTE_020")
        self.assertEqual(self.client.rows[0]["uuid"],V2_STRENGTH)
        self.assertEqual(self.client.rows[0]["hex"],"000000")
        self.assertEqual(self.client.actual,(0,0));self.assertFalse(self.b._auto_enabled)
    async def test_ab_cadence_caps_and_independent_frames(self):
        await self.connect();await self.run_frames(.5)
        a=[bytes.fromhex(r["hex"]) for r in self.client.rows if r["uuid"]==V2_A][1:]
        b=[bytes.fromhex(r["hex"]) for r in self.client.rows if r["uuid"]==V2_B][1:]
        self.assertGreaterEqual(len(a),3)
        self.assertEqual(set(a),set(v2_wave(f) for f in frames(["0A0A0A0A64646464","1414141428282828"])))
        self.assertEqual(set(b),{v2_wave(frames(["3232323214141414"])[0])})
        self.assertLessEqual(max(self.client.actual),30)
    async def test_wrong_notification_cannot_confirm_intensity(self):
        await self.connect();self.client.mismatch=True
        await self.run_frames(.2)
        await self.until(lambda:not self.b.connected)
        self.assertFalse(self.b._auto_enabled)
    async def test_encoder_layout_and_invalid_frames(self):
        self.assertEqual(v2_strength(1,2),((7<<11)|14).to_bytes(3,"little"))
        self.assertEqual(v2_wave(frames(["0A0A0A0A64646464"])[0]),(1|(9<<5)|(20<<15)).to_bytes(3,"little"))
        self.assertEqual(v2_wave(frames(["0A0A0A0A01010101"])[0]),(1|(9<<5)).to_bytes(3,"little"))
        self.assertEqual(v2_strength(float("nan"),-1),bytes(3))


class BackendBleTests(unittest.IsolatedAsyncioTestCase):
    until=BleTests.until
    connect=BleTests.connect
    async def asyncSetUp(self):
        from contextlib import ExitStack
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from PySide6.QtCore import QCoreApplication
        from qml_dashboard_prototype import backend as module
        self.qt=QCoreApplication.instance() or QCoreApplication([])
        self.tmp=TemporaryDirectory()
        self.context=ExitStack()
        for manager in (patch.object(module,"app_data_dir",return_value=Path(self.tmp.name)),
                        patch.object(module,"load_config",return_value={"language":"en","socket_protocol":"ble"}),
                        patch.object(module,"update_config")):self.context.enter_context(manager)
        self.backend=module.ControlCenterBackend(demo=True,language="en")
        self.backend.poll_timer.stop();self.backend.demo_mode=False
        self.backend.auto_output_enabled=False;self.backend.device_connected_value=False
        self.backend.last_receive=0;self.backend.last_packet={}
        await BleTests.asyncSetUp(self)
        self.backend.bridge=self.b
        self.backend._ble_messages=self.events
    async def asyncTearDown(self):
        await BleTests.asyncTearDown(self)
        self.backend.bridge=None;self.backend.shutdown()
        self.context.close();self.tmp.cleanup()
    def feed(self,action="SexStandBack",playing=True):
        self.backend._poll_device_support()
        self.backend._on_telemetry(dict(sequence=1,monotonicMs=int(time.monotonic()*1000),
            heartRate=160,stage="Residence",action=action,playingAction=playing,
            ecstasy=.5,orgasm=False,gameOver=False,vibration="High"))
    async def test_actual_backend_event_mapping_and_manual_enable(self):
        await self.connect()
        self.backend._poll_device_support()
        self.assertTrue(self.backend.device_connected_value)
        self.assertFalse(self.backend.auto_output_enabled or self.b._auto_enabled)
        self.feed()
        self.backend.toggleOutput()
        for _ in range(15):
            self.feed();await asyncio.sleep(.03)
        self.assertTrue(self.b._auto_enabled)
        self.assertGreater(max(self.client.actual),0)
        self.assertEqual(self.b._desired_frames["A"],frames(self.backend.current_wave_a.v3_frames()))
        self.assertEqual(self.b._desired_frames["B"],frames(self.backend.current_wave_b.v3_frames()))
        self.backend.toggleOutput()
        await self.until(lambda:self.client.actual==(0,0))
        self.feed();await asyncio.sleep(.15)
        self.assertFalse(self.b._auto_enabled)
    async def test_old_and_fresh_game_data_resume_rules(self):
        await self.connect();self.backend._poll_device_support()
        self.backend.toggleOutput()
        self.assertTrue(self.backend.coyote_waiting_for_game)
        self.assertFalse(self.b._auto_enabled)
        for _ in range(12):self.feed();await asyncio.sleep(.03)
        self.assertFalse(self.backend.coyote_waiting_for_game)
        self.assertTrue(self.b._auto_enabled)
        self.backend._enter_safety_idle("telemetry-stale")
        # Zero can already be the current level during an enabled plan.
        # Wait for the queued worker stop too, not merely the numeric value.
        await self.until(lambda:not self.b._auto_enabled and self.client.actual==(0,0))
        self.assertTrue(self.backend.auto_output_enabled)
        self.assertFalse(self.b._auto_enabled)
        for _ in range(12):self.feed();await asyncio.sleep(.03)
        self.assertTrue(self.b._auto_enabled)

class BackendBle2Tests(BackendBleTests):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.b.scanner=FakeScanner2;self.b.client_factory=FakeClient2


def run_validation(path):
    # Import the real Windows backend without scanning or opening any radio.
    from bleak.backends.winrt.client import BleakClientWinRT
    from bleak.backends.winrt.scanner import BleakScannerWinRT
    # Static import also includes the dual-device scenarios in the portable EXE.
    from . import ble_dual_validation, ble_scan_validation, booboop_validation
    RECORDS.clear();output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(["manaka_devices.ble_validation.BleTests","manaka_devices.ble_validation.Ble2Tests","manaka_devices.ble_validation.BackendBleTests","manaka_devices.ble_validation.BackendBle2Tests","manaka_devices.ble_dual_validation.OpossumBleTests","manaka_devices.ble_dual_validation.BackendDualBleTests","manaka_devices.ble_dual_validation.BackendDualBle2Tests","manaka_devices.ble_dual_validation.ThreadedDualBleTests","manaka_devices.ble_scan_validation.AutoConnectBleTests","manaka_devices.ble_scan_validation.AutoConnectBle2Tests","manaka_devices.booboop_validation.PolicyTests","manaka_devices.booboop_validation.TransportTests","manaka_devices.booboop_validation.BackendTests"]))
    import sys
    report={"passed":result.wasSuccessful(),"tests_run":result.testsRun,
            "packaged_executable":bool(getattr(sys,"frozen",False)),"physical_hardware_tested":False,
            "protocol":"Coyote 2 GATT / Coyote 3 B0/B1/BF / Opossum B0/B3/B2 / FN010-RX / HUD V3","log":output.getvalue(),"cases":RECORDS}
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(report,indent=2),encoding="utf-8")
    if sys.stdout:
        print(json.dumps({k:report[k] for k in ("passed","tests_run","packaged_executable")}))
        if not result.wasSuccessful():print(output.getvalue())
    return 0 if result.wasSuccessful() else 1

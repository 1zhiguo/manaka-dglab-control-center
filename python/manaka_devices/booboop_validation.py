"""Targeted source checks only; fake GATT and isolated backend, never real radio."""
import asyncio,queue,time,unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from contextlib import ExitStack
from unittest.mock import patch,MagicMock
from manaka_devices.booboop_ble import BooBoopBleBridge,mode_command,SERVICE,WRITE,NOTIFY
from manaka_devices.booboop import sanitize_profile,evaluate

class PolicyTests(unittest.TestCase):
    def test_commands_and_profile_caps(self):
        self.assertEqual(mode_command("A",0).hex(),"ac0300000000")
        self.assertEqual(mode_command("B",0).hex(),"ac0100000000")
        self.assertEqual(mode_command("A",1).hex(),"ac030100011f")
        self.assertEqual(mode_command("B",9).hex(),"ac01010001e7")
        for value in (-1,10,True,"1",1.5):
            with self.assertRaises(ValueError):mode_command("A",value)
        p=sanitize_profile({"hard_cap":2,"fast":9,"actions":{"walk":{"mode":"level","level":8}}})
        self.assertEqual((p["fast"],p["actions"]["walk"]["level"]),(2,2))
    def test_game_guards_overrides_and_companion(self):
        p=sanitize_profile({"hard_cap":4,"vibration_enabled":True,"vibration_level":2,
                            "actions":{"walk":{"mode":"level","level":4}}})
        base={"stage":"Street","piston":1,"action":"walk"}
        self.assertEqual(evaluate(base,p,fresh=True,authorized=True)["stretch"],4)
        self.assertEqual(evaluate(base,p,fresh=True,authorized=True)["vibration"],2)
        for delta in ({"piston":0},{"piston":4},{"piston":True},{"piston":None},{"gameOver":True},
                      {"paused":True},{"stage":"None"},{"timeScale":0},{"managedTimeScale":float("nan")}):
            result=evaluate({**base,**delta},p,fresh=True,authorized=True)
            self.assertEqual((result["stretch"],result["vibration"]),(0,0),delta)
        for fresh,auth in ((False,True),(True,False)):
            self.assertEqual(evaluate(base,p,fresh=fresh,authorized=auth)["stretch"],0)
        p["actions"]["walk"]["mode"]="off"
        self.assertEqual(evaluate(base,p,fresh=True,authorized=True)["vibration"],0)

    def test_random_piston_follows_each_game_effective_speed(self):
        p=sanitize_profile({"slow":1,"medium":2,"fast":3})
        packet={"stage":"Street","piston":4,"pistonRandom":True}
        for mode,expected in ((1,1),(3,3),(2,2),(0,0),(1,1)):
            out=evaluate({**packet,"pistonEffective":mode},p,fresh=True,authorized=True)
            self.assertEqual(out["stretch"],expected)
            self.assertEqual(out["pistonEffective"],mode)
            self.assertTrue(out["pistonRandom"])
        p["hard_cap"]=2
        self.assertEqual(evaluate({**packet,"pistonEffective":3},p,fresh=True,authorized=True)["stretch"],2)

    def test_random_piston_missing_invalid_and_off_never_guess_speed(self):
        p=sanitize_profile({"vibration_enabled":True})
        packet={"stage":"Street","piston":4,"pistonRandom":True}
        for value in (None,-1,4,True,"1",1.0):
            out=evaluate({**packet,"pistonEffective":value},p,fresh=True,authorized=True)
            self.assertEqual((out["stretch"],out["vibration"]),(0,0))
            self.assertEqual(out["reason"],"piston-random-wait")
        for selected in (0,False,None,5):
            out=evaluate({**packet,"piston":selected,"pistonEffective":3},p,fresh=True,authorized=True)
            self.assertEqual((out["stretch"],out["vibration"]),(0,0))

    def test_random_piston_preserves_actions_and_game_stop_guards(self):
        p=sanitize_profile({"actions":{"Walk":{"mode":"level","level":4}}})
        packet={"stage":"Street","piston":4,"pistonEffective":2,"action":"Walk"}
        self.assertEqual(evaluate(packet,p,fresh=True,authorized=True)["stretch"],4)
        for key in ("paused","gameOver","systemMenuOpen"):
            out=evaluate({**packet,key:True},p,fresh=True,authorized=True)
            self.assertEqual(out["stretch"],0)
        p["actions"]["Walk"]["mode"]="off"
        self.assertEqual(evaluate(packet,p,fresh=True,authorized=True)["stretch"],0)
        out=evaluate(packet,p,fresh=False,authorized=True)
        self.assertEqual(out["stretch"],0)

class Services:
    valid=True
    properties=["write-without-response"]
    def get_service(self,uuid):
        return self if self.valid and uuid==SERVICE else None
    def get_characteristic(self,uuid):
        return SimpleNamespace(properties=self.properties if uuid==WRITE else ["notify"]) if uuid in (WRITE,NOTIFY) else None

class Client:
    handshake=True
    valid=True
    def __init__(self,device,disconnected_callback=None):
        self.callback=disconnected_callback;self.services=Services();self.services.valid=self.valid
        self.is_connected=False;self.rows=[];self.fail_stop=False
    async def connect(self):self.is_connected=True
    async def disconnect(self):
        self.is_connected=False
        if self.callback:self.callback(self)
    async def start_notify(self,char,callback):self.notify=callback
    async def write_gatt_char(self,char,payload,response):
        assert response is False
        self.rows.append(bytes(payload))
        if payload==bytes.fromhex("af00") and self.handshake:self.notify(None,bytes.fromhex("af0003010055"))
        if self.fail_stop and payload==mode_command("A",0):raise OSError("fake write failure")

class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.b=BooBoopBleBridge(queue.Queue(),client_factory=Client)
        self.worker=asyncio.create_task(self.b._run())
        await self.until(lambda:self.b.server_ready)
        self.b._apply_discovery({"one":(SimpleNamespace(address="one",name="FN010-RX"),SimpleNamespace(local_name="FN010-RX")),
                                 "wrong":(SimpleNamespace(address="wrong",name="OVC"),SimpleNamespace(local_name="OVC"))})
    async def asyncTearDown(self):
        self.b._stop_event.set();await asyncio.wait_for(self.worker,2)
    async def until(self,predicate,timeout=2):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if predicate():return
            await asyncio.sleep(.01)
        self.fail(self.b.detail)
    async def connect(self):
        self.assertEqual(len(self.b.devices),1)
        self.assertTrue(self.b.select_device("one"));await self.until(lambda:self.b.connected)
        self.c=self.b.client
    async def test_handshake_stops_then_manual_output_watchdog_reconnect(self):
        await self.connect()
        self.assertEqual(self.c.rows,[bytes.fromhex("af00"),mode_command("A",0),mode_command("B",0)])
        self.assertIsNone(self.b.battery);self.assertFalse(self.b._auto_enabled)
        self.b.update_levels(9,3,2);self.b.set_auto_enabled(True)
        await self.until(lambda:self.b.sent_levels=={"A":2,"B":2})
        n=len(self.c.rows)
        self.b.update_levels(9,3,2);await asyncio.sleep(.09)
        self.assertEqual(len(self.c.rows),n) # latched protocol, no redundant movement writes
        self.b.update_levels(0,0,0)
        await self.until(lambda:self.b.sent_levels=={"A":0,"B":0})
        self.b.update_levels(3,2,4);self.b.set_auto_enabled(True)
        await self.until(lambda:self.b.sent_levels["A"]==3)
        await self.until(lambda:not self.b._auto_enabled)
        await self.until(lambda:self.b.sent_levels=={"A":0,"B":0})
        self.b.update_levels(2,2,4);self.b.set_auto_enabled(True)
        await self.until(lambda:self.b.sent_levels["A"]==2)
        self.b.latch_global_emergency_stop()
        await self.until(lambda:self.b.sent_levels=={"A":0,"B":0})
        self.b.clear_global_emergency_stop();await asyncio.sleep(.1)
        self.assertFalse(self.b._auto_enabled)
        await self.c.disconnect()
        self.assertFalse(self.b.connected)
        self.assertTrue(self.b.select_device("one"));await self.until(lambda:self.b.connected)
        self.assertFalse(self.b._auto_enabled)
        self.assertEqual(self.b.sent_levels,{"A":0,"B":0})
    async def test_wrong_profile_and_missing_handshake_block_readiness(self):
        class Wrong(Client):valid=False
        self.b.client_factory=Wrong;self.b.select_device("one")
        await self.until(lambda:"unsupported" in self.b.detail)
        self.assertFalse(self.b.connected)
        class Silent(Client):handshake=False
        self.b.client_factory=Silent;self.b.select_device("one")
        await self.until(lambda:self.b.client is not None)
        client=self.b.client
        # Incorrect notification must not authorize this profile.
        await self.until(lambda:hasattr(client,"notify"))
        client.notify(None,bytes.fromhex("af000301"))
        await self.until(lambda:"failed" in self.b.detail)
        self.assertFalse(self.b.connected)
        self.assertEqual(client.rows,[bytes.fromhex("af00")])
    async def test_stop_attempts_both_motors_even_when_first_write_fails(self):
        await self.connect();self.c.fail_stop=True;n=len(self.c.rows)
        with self.assertRaises(ConnectionError):await self.b._zero(self.c)
        self.assertEqual(self.c.rows[n:],[mode_command("A",0),mode_command("B",0)])
        self.c.fail_stop=False

class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QCoreApplication
        cls.app=QCoreApplication.instance() or QCoreApplication([])
    def setUp(self):
        from qml_dashboard_prototype import backend as module
        self.m=module;self.ctx=ExitStack();self.tmp=self.ctx.enter_context(tempfile.TemporaryDirectory())
        self.ctx.enter_context(patch.object(module,"app_data_dir",return_value=Path(self.tmp)))
        self.ctx.enter_context(patch.object(module,"load_config",return_value={}))
        self.persist=self.ctx.enter_context(patch.object(module,"update_config"))
        self.b=module.ControlCenterBackend(demo=True)
        self.b.poll_timer.stop()
    def tearDown(self):
        self.b.boo_ble=None;self.b.shutdown();self.ctx.close()
    def test_pulse_batch_atomic_persist_and_invalid_rollback(self):
        self.b.demo_mode=False
        key=self.b.assignableWaveforms[-1]["key"]
        self.assertTrue(self.b.setActionWaveforms(["One","Two","One"],key))
        self.assertEqual(self.persist.call_count,1)
        old=dict(self.b.action_wave_map_value)
        self.persist.side_effect=OSError("disk full")
        self.assertFalse(self.b.setActionWaveforms(["Three"],key))
        self.assertEqual(self.b.action_wave_map_value,old)
        self.assertFalse(self.b.setActionWaveforms(["One",""],key))
        self.assertFalse(self.b.setActionWaveforms(["One"],"does-not-exist"))
        self.assertEqual(self.persist.call_count,2)
    def test_boo_profile_validation_and_stop_before_apply(self):
        from copy import deepcopy
        self.b.demo_mode=False;self.b._device_persist=MagicMock()
        self.b.boo_ble=MagicMock();self.b.boo_enabled=True
        raw=deepcopy(self.b.boo_profile);raw["actions"]={"Walk":{"mode":"level","level":2}}
        self.assertTrue(self.b.saveBooProfile(raw));self.assertFalse(self.b.boo_enabled)
        self.b.boo_ble.emergency_stop.assert_called()
        for invalid in ({"mode":"bad","level":1},{"mode":"level","level":9}):
            raw["actions"]["Walk"]=invalid
            self.assertFalse(self.b.saveBooProfile(raw))
        self.assertEqual(self.b._device_persist.call_count,1)
    def test_boo_manual_enable_piston_off_stale_and_global_stop(self):
        from PySide6.QtCore import QMetaObject
        self.b.demo_mode=False;self.b.socket_protocol="ble"
        self.b.boo_ble=MagicMock();self.b.boo_connected=True
        self.b.last_packet={"stage":"Street","piston":2};self.b.last_receive=time.monotonic()
        self.b._sync_extra_devices(force=True)
        self.assertEqual(self.b.booStretch,0)
        self.b.boo_ble.update_levels.assert_not_called()
        self.b.toggleBooOutput();self.assertTrue(self.b.boo_enabled)
        self.assertEqual(self.b.booStretch,2)
        self.b.last_packet["piston"]=0;self.b.last_receive=time.monotonic();self.b._sync_extra_devices(force=True)
        self.b.boo_ble.update_levels.assert_called_with(0,0,4)
        self.b.last_packet["piston"]=3;self.b.last_receive=time.monotonic()-2;self.b._sync_extra_devices(force=True)
        self.assertTrue(self.b.boo_waiting);self.assertEqual(self.b.booStretch,0)
        time.sleep(.02) # Windows monotonic timestamps can share a clock tick.
        self.b.last_receive=time.monotonic();self.b._sync_extra_devices(force=True)
        self.assertEqual(self.b.booStretch,3)
        self.assertTrue(QMetaObject.invokeMethod(self.b,"emergencyStopAll"))
        self.assertFalse(self.b.boo_enabled);self.b.boo_ble.latch_global_emergency_stop.assert_called()
        self.b.socket_protocol="v4";self.b.toggleBooOutput()
        self.assertFalse(self.b.boo_enabled)
    def test_hud_belt_output_tracks_freshness_without_device_side_effects(self):
        self.b.socket_protocol="ble";self.b.boo_connected=True;self.b.boo_enabled=True
        self.b.boo_frame={"stretch":3,"vibration":1,"reason":""};self.b.boo_ble=MagicMock()
        self.b.last_packet={"stage":"Street","hudProtocol":3}
        self.b.last_receive=time.monotonic()
        self.b.hud_socket=MagicMock()
        def packet():
            self.b._publish_game_hud(force=True)
            return self.b.hud_socket.sendto.call_args.args[0].decode().split("|")
        p=packet()
        self.assertEqual((p[0],p[23:25]),("MANAKA_HUD_V3",["3.00","1.00"]))
        self.assertTrue(self.b.saveHudSettings({**self.b.hud_settings,"show_booboop":False}))
        self.assertFalse(int(packet()[3])&128)
        self.assertTrue(self.b.boo_enabled)
        self.b.boo_ble.emergency_stop.assert_not_called()
        self.b.last_receive=time.monotonic()-2
        p=packet()
        self.assertEqual(p[23:25],["0.00","0.00"])
        self.assertFalse(int(p[10])&4)
        self.b.last_packet["hudProtocol"]=2
        self.assertEqual(packet()[0],"MANAKA_HUD_V2")

    def test_generic_scan_does_not_authorize_extra_role(self):
        self.b.demo_mode=False;self.b.socket_protocol="ble"
        self.b.bridge=MagicMock(connected=False,_connection_task=None,_scan_task=None,scan_request_id=None)
        self.b.ovc_ble=MagicMock(connected=False,_connection_task=None)
        self.b.boo_ble=MagicMock(connected=False,_connection_task=None)
        self.b._scan_ble_roles(("coyote","ovc"))
        self.assertEqual(set(self.b._ble_auto_connect),{"coyote","ovc"})
        self.b._ble_scan_reserved=False
        self.b.scanBooDevice()
        self.assertEqual(set(self.b._ble_auto_connect),{"booboop"})
        self.b.bridge=None;self.b.ovc_ble=None

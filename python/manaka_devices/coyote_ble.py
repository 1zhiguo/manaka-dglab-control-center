"""Direct Coyote 2 / 3 BLE. Protocol: dungeonlab-open/dglab-bluetooth-protocol.
No scanning, connection, or output on construction. All BLE I/O is worker-owned.
"""
from __future__ import annotations
import asyncio,math,threading,time,queue
from .ble_session import BleSession

SERVICE="0000180c-0000-1000-8000-00805f9b34fb"
WRITE="0000150a-0000-1000-8000-00805f9b34fb"
NOTIFY="0000150b-0000-1000-8000-00805f9b34fb"
BATTERY="00001500-0000-1000-8000-00805f9b34fb"
V2_SERVICE="955a180b-0fe2-f5aa-a094-84b8d4f3e8ad"
V2_STRENGTH="955a1504-0fe2-f5aa-a094-84b8d4f3e8ad"
# Official table: 1505 is B, 1506 is A; do not infer from A34/B34 names.
V2_A="955a1506-0fe2-f5aa-a094-84b8d4f3e8ad"
V2_B="955a1505-0fe2-f5aa-a094-84b8d4f3e8ad"
V2_BATTERY="955a1500-0fe2-f5aa-a094-84b8d4f3e8ad"

def v2_strength(a,b):
    return ((bounded(a)*7<<11)|(bounded(b)*7)).to_bytes(3,"little")

def v2_wave(frame):
    # V2 has one 100ms sample versus V3's four 25ms samples.
    # Average periods and widths; floor Z so conversion never rounds width up.
    periods=[v if v<=100 else 100+(v-100)*5 if v<=200 else 600+(v-200)*10 for v in frame[:4]]
    period=sum(periods)//4
    x=int(math.sqrt(period/1000)*15)
    y=period-x
    z=sum(frame[4:])//20
    return (x|(y<<5)|(min(20,z)<<15)).to_bytes(3,"little")

SILENT=bytes([10]*4+[0]*4)

def bounded(value,cap=100):
    if type(value) not in (int,float) or not math.isfinite(value):
        return 0
    return int(max(0,min(100,cap,value)))

def frames(values):
    result=tuple(bytes.fromhex(v) for v in values)
    if len(result)>100 or any(len(v)!=8 or any(not 10<=x<=240 for x in v[:4]) or any(x>100 for x in v[4:]) for v in result):
        raise ValueError("Invalid four-sample Coyote 3 frame")
    return result

def b0(seq,a,b,frame_a=SILENT,frame_b=SILENT):
    if not 0<=seq<=15 or len(frame_a)!=8 or len(frame_b)!=8:
        raise ValueError("Invalid BLE command")
    return bytes([0xB0,(seq<<4)|(15 if seq else 0),bounded(a),bounded(b)])+frame_a+frame_b

def bf(cap):
    # Explicit conservative balance parameters (not claimed as App defaults).
    # Soft caps persist in hardware; reapply after every connection and change.
    return bytes([0xBF,bounded(cap),bounded(cap),0,0,0,0])

class CoyoteBleBridge(BleSession):
    role = "coyote"
    strength_max = 100
    advertised_devices = {
        "47L121000": ("COYOTE_030", "Coyote 3.0"),
        "D-LAB ESTIM01": ("COYOTE_020", "Coyote 2.0"),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hard_cap=30
        self.device_type="COYOTE_030"
        self._sequence=0
        self._last_cap=None

    def _reset_protocol(self):
        self._last_cap=None

    async def _prepare_link(self, client, epoch):
        v2=self.device_type=="COYOTE_020"
        if not client.services.get_service(V2_SERVICE if v2 else SERVICE):
            raise ValueError("Wrong Coyote/Opossum GATT service")
        for uuid in ((V2_STRENGTH,V2_A,V2_B) if v2 else (WRITE,NOTIFY)):
            if not client.services.get_characteristic(uuid):
                raise ValueError("Missing device characteristic")
        await client.start_notify(V2_STRENGTH if v2 else NOTIFY,
            lambda sender,data:self._notify(client,epoch,bytes(data)))

    async def _read_battery(self, client):
        raw=await asyncio.wait_for(client.read_gatt_char(V2_BATTERY if self.device_type=="COYOTE_020" else BATTERY),.5)
        return raw[0] if len(raw)==1 and raw[0]<=100 else None

    def _notify(self,client,epoch,data):
        if client is not self.client:return
        if epoch!=self._epoch and not (self._pending and self._pending[1]==(0,0)):return
        if self.device_type=="COYOTE_020":
            if len(data)!=3:return
            raw=int.from_bytes(data,"little")
            self.reported=((raw>>11&2047)/7,(raw&2047)/7)
            if any(v>self._hard_cap for v in self.reported) or (not self._auto_enabled and any(self.reported)):
                self._request_emergency_in_loop()
            self._emit("ble_status")
            return
        if len(data)!=4 or data[0]!=0xB1:return
        self.reported=(data[2],data[3])
        pending=self._pending
        if pending and data[1]==pending[0] and not pending[2].done():
            expected=pending[1]
            if any(actual>wanted for actual,wanted in zip(self.reported,expected)):
                pending[2].set_exception(ValueError("Unexpected intensity feedback"))
            else:pending[2].set_result(self.reported)
        elif data[1]==0 and (not self._auto_enabled and any(self.reported) or any(v>self._hard_cap for v in self.reported)):
            self._request_emergency_in_loop()
        self._emit("ble_status")


    async def _write(self,client,payload,uuid=WRITE):
        characteristic=client.services.get_characteristic(uuid)
        response="write" in characteristic.properties
        await asyncio.wait_for(client.write_gatt_char(uuid,payload,response=response),.4)


    async def _command(self,client,a,b,fa=SILENT,fb=SILENT,*,generation=None,force_confirm=False):
        async with self._write_lock:
            if client is not self.client or not client.is_connected:raise ConnectionError("BLE disconnected")
            if generation is not None and (generation!=self._generation or not self.connected or not self._auto_enabled or self._paused or self._global_emergency_stop.is_set() or time.monotonic()-self._desired_updated_at>.5):
                return
            if generation is not None:
                cap=self._bound(self._hard_cap)
                a,b=bounded(a,cap),bounded(b,cap)
                if not a:fa=SILENT
                if not b:fb=SILENT
                if self.device_type=="COYOTE_030" and self._last_cap!=cap:
                    await self._write(client,bf(cap));self._last_cap=cap
            if self.device_type=="COYOTE_020":
                if force_confirm or (a,b)!=self.reported:
                    await self._write(client,v2_strength(a,b),V2_STRENGTH)
                    await self._read_v2(client,a,b)
                for uuid,frame in ((V2_A,fa),(V2_B,fb)):
                    if generation is not None and generation!=self._generation:return
                    await self._write(client,v2_wave(frame),uuid)
                return
            if not force_confirm and (a,b)==self.reported:
                await self._write(client,b0(0,a,b,fa,fb))
                return
            self._sequence=self._sequence%15+1
            future=asyncio.get_running_loop().create_future()
            self._pending=(self._sequence,(a,b),future)
            try:
                await self._write(client,b0(self._sequence,a,b,fa,fb))
                await asyncio.wait_for(future,.5)
            finally:
                if not future.done():future.cancel()
                self._pending=None


    async def _zero(self,client):
        if not client.is_connected:return
        if self.device_type=="COYOTE_020":
            await self._command(client,0,0,force_confirm=True)
        else:
            async with self._write_lock:
                await self._write(client,bf(0))
                self._last_cap=0
            await self._command(client,0,0,force_confirm=True)


    async def _read_v2(self,client,a,b):
        raw=bytes(await asyncio.wait_for(client.read_gatt_char(V2_STRENGTH),.5))
        if len(raw)!=3:raise ValueError("Invalid Coyote 2 intensity readback")
        value=int.from_bytes(raw,"little")
        actual=(value>>11&2047,value&2047)
        if value>>22 or actual[0]>a*7 or actual[1]>b*7:
            raise ValueError("Coyote 2 intensity readback mismatch")
        self.reported=tuple(v/7 for v in actual)


    def update_auto_outputs(self,strength_a,frames_a,*,wave_key_a,strength_b,frames_b,wave_key_b,hard_cap):
        a,b=frames(frames_a),frames(frames_b)
        cap=self._bound(hard_cap)
        self._queue_output_plan(strength_a,a,wave_key_a,strength_b,b,wave_key_b,cap)

    async def _output_loop(self):
        keys={"A":"","B":""};cursor={"A":0,"B":0};last_generation=-1
        while not self._stop_event.is_set():
            await asyncio.sleep(.1)
            if not self.client or not self.connected:continue
            if self._generation!=last_generation:
                last_generation=self._generation;keys={"A":"","B":""};cursor={"A":0,"B":0}
            if self._auto_enabled and time.monotonic()-self._desired_updated_at>.5:
                self._request_emergency_in_loop()
                self._emit("output_timeout",reason="producer-stale")
            if not self._auto_enabled or self._paused or self._global_emergency_stop.is_set():continue
            generation=self._generation;client=self.client
            try:
                cap=self._bound(self._hard_cap)
                strength={};wave={}
                for ch in ("A","B"):
                    values=self._desired_frames[ch]
                    if self._desired_wave_key[ch]!=keys[ch]:
                        keys[ch]=self._desired_wave_key[ch];cursor[ch]=0
                    strength[ch]=self._bound(self._desired_strength[ch],cap) if values else 0
                    wave[ch]=values[cursor[ch]%len(values)] if values and strength[ch] else SILENT
                    if values:cursor[ch]=(cursor[ch]+1)%len(values)
                await self._command(client,strength["A"],strength["B"],wave["A"],wave["B"],generation=generation)
            except Exception as error:
                self._discard();self.detail="BLE output stopped: "+str(error)
                await self._safe_zero_async()
                self.connected=False
                try:await client.disconnect()
                except Exception:pass
                self._emit("error",detail=self.detail)
                self._emit("disconnected")

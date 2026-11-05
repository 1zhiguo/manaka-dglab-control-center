"""FN010-RX direct BLE adapter.

Framing is independently implemented from the HCI observations in
https://github.com/buttplugio/buttplug/issues/968, not a vendor SDK.
No vendor executable, third-party DLL, product cache or network API is used.
"""
from __future__ import annotations
import asyncio
import time
from .ble_session import BleSession

SERVICE="0000ffee-0000-1000-8000-00805f9b34fb"
WRITE="0000ee01-0000-1000-8000-00805f9b34fb"
NOTIFY="0000ee02-0000-1000-8000-00805f9b34fb"
MOTORS={"A":3,"B":1}  # A: thrust/oscillation, B: vibration; not linear position.


def mode_command(channel, level):
    if channel not in MOTORS or type(level) is not int or not 0<=level<=9:
        raise ValueError("FN010-RX requires channel A/B and a protocol index 0..9")
    motor=MOTORS[channel]
    if level==0:
        return bytes([0xAC,motor,0,0,0,0])
    return bytes([0xAC,motor,1,0,1,0x1F+0x19*(level-1)])


class BooBoopBleBridge(BleSession):
    role="booboop"
    strength_max=9
    advertised_devices={"FN010-RX":("FN010_RX","FN010-RX")}
    ready_suffix="handshake ready · stop commands sent · enable manually"

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._hard_cap=4
        self._write_characteristic=None
        self.sent_levels={"A":None,"B":None}

    def _reset_protocol(self):
        self._write_characteristic=None
        self.sent_levels={"A":None,"B":None}

    async def _prepare_link(self,client,epoch):
        service=client.services.get_service(SERVICE)
        if not service:
            raise ValueError("FN010-RX ffee service is missing; this hardware variant is unsupported")
        writer=service.get_characteristic(WRITE)
        reader=service.get_characteristic(NOTIFY)
        if not writer or "write-without-response" not in writer.properties or not reader or "notify" not in reader.properties:
            raise ValueError("FN010-RX ee01/ee02 capabilities do not match the captured profile")
        self._write_characteristic=writer
        future=asyncio.get_running_loop().create_future()
        self._pending=("handshake",None,future)
        try:
            await client.start_notify(reader,lambda sender,data:self._notify(client,epoch,bytes(data)))
            await self._write(client,bytes([0xAF,0]))
            await asyncio.wait_for(future,1.)
        finally:
            if not future.done():future.cancel()
            self._pending=None

    def _notify(self,client,epoch,data):
        if client is not self.client or epoch!=self._epoch:
            return
        # Tail byte varies; it is NOT presented as battery or position feedback.
        if len(data)==6 and data[:5]==bytes([0xAF,0,3,1,0]):
            if self._pending and self._pending[0]=="handshake" and not self._pending[2].done():
                self._pending[2].set_result(True)

    async def _write(self,client,payload):
        if client is not self.client or not client.is_connected or self._write_characteristic is None:
            raise ConnectionError("FN010-RX BLE link is unavailable")
        await asyncio.wait_for(client.write_gatt_char(self._write_characteristic,payload,response=False),.4)

    async def _zero(self,client):
        if not client.is_connected:return
        errors=[]
        async with self._write_lock:
            for channel in ("A","B"):
                try:
                    await self._write(client,mode_command(channel,0))
                    self.sent_levels[channel]=0
                except Exception as error:
                    errors.append(error)
        if errors:
            raise ConnectionError("One or both FN010-RX stop writes failed") from errors[0]
        self._emit("ble_status")

    def update_levels(self,stretch,vibration,hard_cap):
        cap=self._bound(hard_cap)
        self._queue_output_plan(stretch,(),"stretch",vibration,(),"vibration",cap)

    def _can_send(self,client,generation):
        return (client is self.client and self.connected and client.is_connected
            and generation==self._generation and self._auto_enabled and not self._paused
            and not self._global_emergency_stop.is_set()
            and 0<=time.monotonic()-self._desired_updated_at<=.5)

    async def _output_loop(self):
        while not self._stop_event.is_set():
            await asyncio.sleep(.05)
            if not self.client or not self.connected:continue
            if self._auto_enabled and time.monotonic()-self._desired_updated_at>.5:
                self._request_emergency_in_loop()
                self._emit("output_timeout",reason="producer-stale")
            client,generation=self.client,self._generation
            if not self._can_send(client,generation):continue
            try:
                async with self._write_lock:
                    for channel in ("A","B"):
                        if not self._can_send(client,generation):break
                        level=self._bound(self._desired_strength[channel],self._hard_cap)
                        if self.sent_levels[channel]==level:continue
                        await self._write(client,mode_command(channel,level))
                        self.sent_levels[channel]=level
                        self._emit("ble_status")
            except Exception as error:
                failure="FN010-RX output stopped: "+str(error)
                self._discard()
                await self._safe_zero_async()
                self.connected=False
                try:await client.disconnect()
                except Exception:pass
                self.detail=failure
                self._emit("error",detail=failure)
                self._emit("disconnected")

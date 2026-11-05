"""Shared BLE lifecycle and authorization; no device-specific framing or discovery on startup."""
from __future__ import annotations
import asyncio
import math
import threading
import time
from .dglab_bridge import DGLabBridge, BridgeSnapshot


class BleSession(DGLabBridge):
    protocol = "ble"
    role = "device"
    strength_max = 0
    advertised_devices = {}
    ready_suffix = "ready · enable manually"
    def __init__(self,events,*,scanner=None,client_factory=None,discovery_sink=None):
        # Avoid Socket discovery/network setup for this route.
        self.events=events
        self.port=self.requested_port=0
        self.lan_ip=self.controller_id=self.target_id=self.qr_url=""
        self.available_lan_ips=()
        self.available_lan_interfaces=[]
        self.server_ready=self.connected=False
        self._thread=self._loop=self._stop_event=None
        self._auto_enabled=self._paused=self._pause_requested=False
        self._pause_epoch=self._generation=0
        self._pause_zero_task=None
        self._global_emergency_stop=threading.Event()
        self._desired_strength={"A":0,"B":0}
        self._desired_frames={"A":(),"B":()}
        self._desired_wave_key={"A":"","B":""}
        self._desired_updated_at=0.
        self._hard_cap=0
        self._resume_deferred=""
        self.discovery_sink=discovery_sink
        self.selected_address=""
        self._aux_tasks=set()
        self.scanner=scanner
        self.client_factory=client_factory
        self.client=None
        self._devices={}
        self.devices=[]
        self.detail="Ready to scan"
        self.battery=None
        self.reported=(0,0)
        self.device_type=""
        self._device_kinds={}
        self._epoch=0
        self._pending=None
        self._scan_task=self._connection_task=None
        self.scan_seconds=5.
        self.scan_started_at=0.
        self.scan_state="idle"
        self.scan_request_id=None
        self._write_lock=None


    def _emit(self,event,**data):
        self.events.put(("dglab",{"event":event,"protocol":"ble","role":self.role,"epoch":self._epoch,**data}))


    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._thread_main, name="DGLabBLE-"+self.role, daemon=True)
        self._thread.start()


    def _thread_main(self):
        try:
            asyncio.run(self._run())
        except Exception as error:
            self._emit("error", detail="BLE worker failed: "+str(error))


    def set_lan_ip(self,address):
        return False


    def refresh_lan_ips(self):
        pass


    def snapshot(self):
        return BridgeSnapshot(self.server_ready,self.connected,"","","","",0)


    def scan(self, request_id=None):
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._start_scan, request_id)
            return True
        return False


    def cancel_scan(self):
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._cancel_scan)


    def _cancel_scan(self):
        if self._scan_task and not self._scan_task.done():
            self.scan_state="cancelled"
            self._scan_task.cancel()


    def _start_scan(self, request_id=None):
        if self._scan_task and not self._scan_task.done():return
        self.scan_request_id=request_id
        self.scan_started_at=time.monotonic()
        self.scan_state="scanning"
        self._scan_task=asyncio.create_task(self._scan())


    async def _scan(self):
        try:
            if not self.connected:
                self.detail="Scanning..."
            self._emit("ble_status")
            scanner=self.scanner
            if scanner is None:
                from bleak import BleakScanner
                scanner=BleakScanner
            rows=await scanner.discover(timeout=self.scan_seconds,return_adv=True)
            if self.scan_state == "cancelled":
                return
            self.scan_state="complete"
            self._apply_discovery(rows, self.scan_request_id)
            if self.discovery_sink:
                self.discovery_sink(rows, self.scan_request_id)
        except asyncio.CancelledError:
            self.scan_state="cancelled"
            raise
        except Exception as error:
            self.scan_state="failed"
            self.detail="Bluetooth scan failed: "+str(error)
        finally:
            self._emit("ble_status")


    def accept_discovery(self, rows, request_id=None):
        """Receive one shared radio scan on this device's worker loop."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._apply_discovery, dict(rows), request_id)


    def _apply_discovery(self, rows, request_id=None):
        found, choices, kinds = {}, [], {}
        for device, advertisement in rows.values():
            name = advertisement.local_name or device.name or ""
            if name not in self.advertised_devices:
                continue
            kind, label = self.advertised_devices[name]
            kinds[device.address] = kind
            found[device.address] = device
            choices.append({"address": device.address, "label": label+" · "+device.address})
        # Connected devices commonly stop advertising. A later shared scan
        # must not erase the other device's active selection.
        address = self.selected_address
        if self.connected and address and address not in found and address in self._devices:
            found[address] = self._devices[address]
            kinds[address] = self._device_kinds[address]
            choices.extend(item for item in self.devices if item["address"] == address)
        self._device_kinds, self._devices, self.devices = kinds, found, choices
        if not self.connected:
            self.detail = "Select a device" if choices else "No device found; disconnect it from the phone App"
        self._emit("ble_discovery", request_id=request_id)
        self._emit("ble_status")


    def _bound(self, value, cap=None):
        limit = self.strength_max if cap is None else min(self.strength_max, cap)
        if type(value) not in (int, float) or not math.isfinite(value):
            return 0
        return int(max(0, min(limit, value)))


    def select_device(self,address):
        if address and address not in self._devices:return False
        if not self._loop or not self._loop.is_running():return False
        self._loop.call_soon_threadsafe(self._select,str(address))
        return True


    def _discard(self):
        self._generation+=1;self._auto_enabled=False
        self._desired_strength={"A":0,"B":0};self._desired_frames={"A":(),"B":()}
        self._desired_updated_at=0.


    def _select(self,address):
        self._epoch+=1;self._discard();self.connected=False
        self.selected_address=address
        if self._connection_task:self._connection_task.cancel()
        self._connection_task=asyncio.create_task(self._connect(address,self._epoch))


    async def _connect(self,address,epoch):
        old=self.client
        if old:
            try:await self._zero(old)
            except Exception:pass
            try:await old.disconnect()
            except Exception:pass
        if epoch!=self._epoch:return
        self.client=None;self._reset_protocol()
        if not address:
            self.detail="Bluetooth disconnected";self._emit("disconnected");return
        client=None
        try:
            factory=self.client_factory
            if factory is None:
                from bleak import BleakClient
                factory=BleakClient
            self.device_type=self._device_kinds[address]
            client=factory(self._devices[address],disconnected_callback=lambda c:self._dropped(c,epoch))
            self.client=client;self.detail="Connecting and confirming zero...";self._emit("ble_status")
            await asyncio.wait_for(client.connect(),12)
            if epoch!=self._epoch:raise asyncio.CancelledError()
            await self._prepare_link(client, epoch)
            await self._zero(client)
            if epoch!=self._epoch:raise asyncio.CancelledError()
            try:
                self.battery=await self._read_battery(client)
            except Exception:
                self.battery=None
            self._discard();self.connected=True
            self.detail=next(label for kind,label in self.advertised_devices.values() if kind==self.device_type)+" · "+self.ready_suffix
            self._emit("connected");self._emit("ble_status")
        except asyncio.CancelledError:
            if client:
                try:await self._zero(client)
                except Exception:pass
                try:await client.disconnect()
                except Exception:pass
            if self.client is client:self.client=None
            raise
        except Exception as error:
            self._discard();self.connected=False
            failure_detail="BLE connection failed: "+str(error)
            if client:
                try:await client.disconnect()
                except Exception:pass
            if self.client is client:self.client=None
            self.detail=failure_detail
            self._emit("error",detail=self.detail)


    def _dropped(self,client,epoch):
        if client is not self.client or epoch!=self._epoch:return
        self._discard();self.connected=False;self._reset_protocol()
        if self._pending and not self._pending[2].done():
            self._pending[2].set_exception(ConnectionError("Bluetooth disconnected"))
        self.detail="Bluetooth disconnected; reconnect and enable manually"
        self._emit("disconnected");self._emit("ble_status")


    async def _safe_zero_async(self):
        client=self.client
        if client and client.is_connected:
            try:await self._zero(client)
            except Exception as error:
                self._discard();self.connected=False
                self.detail="Zero confirmation failed: "+str(error)
                try:await client.disconnect()
                except Exception:pass
                self._emit("error",detail=self.detail)


    def _token(self):
        return self._epoch,self._generation,self._pause_epoch


    def set_auto_enabled(self,enabled):
        if not self._loop or not self._loop.is_running():return
        token=self._token();created=time.monotonic()
        def apply():
            if enabled and (token!=self._token() or time.monotonic()-created>.5):return
            self._set_auto_enabled_in_loop(enabled)
        self._loop.call_soon_threadsafe(apply)


    def manual_test(self,*args,**kwargs):
        return False


    async def _run(self):
        self._loop=asyncio.get_running_loop()
        self._stop_event=asyncio.Event();self._write_lock=asyncio.Lock()
        self.server_ready=True
        output=asyncio.create_task(self._output_loop())
        try:await self._stop_event.wait()
        finally:
            self._epoch+=1;self._discard()
            tasks=(self._scan_task,self._connection_task,output,*tuple(self._aux_tasks))
            for task in tasks:
                if task:task.cancel()
            await asyncio.gather(*(task for task in tasks if task),return_exceptions=True)
            await self._safe_zero_async()
            if self.client:
                try:await self.client.disconnect()
                except Exception:pass
            self.connected=self.server_ready=False


    def _queue_output_plan(self, strength_a, frames_a, key_a, strength_b, frames_b, key_b, cap):
        if self._loop and self._loop.is_running():
            token=self._token();created=time.monotonic()
            def apply():
                if token!=self._token() or time.monotonic()-created>.5:return
                self._set_desired_outputs_in_loop(self._bound(strength_a,cap),frames_a,key_a,
                    self._bound(strength_b,cap),frames_b,key_b,cap)
                if not self._paused and not self._global_emergency_stop.is_set():
                    self._desired_updated_at=created
            self._loop.call_soon_threadsafe(apply)

    def _reset_protocol(self):
        pass

    async def _read_battery(self, client):
        return None

    async def _prepare_link(self, client, epoch):
        raise NotImplementedError

    async def _zero(self, client):
        raise NotImplementedError

    async def _output_loop(self):
        raise NotImplementedError

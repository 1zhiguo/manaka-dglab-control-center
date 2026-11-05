"""Native Opossum BLE, using the existing Manaka vibration planner.

Protocol reference: dungeonlab-open/dglab-bluetooth-protocol,
opossum-vibrate-controller/README_CN.md. No App or network API is used.
"""
from __future__ import annotations

import asyncio
import time

from .coyote_ble import CoyoteBleBridge, SILENT, WRITE


def vibration_frame(frame_a=SILENT, frame_b=SILENT):
    """One 100 ms B0: padding, four A amplitudes, padding, four B amplitudes."""
    if any(len(frame) != 8 or any(value > 100 for value in frame[4:]) for frame in (frame_a, frame_b)):
        raise ValueError("Invalid Opossum waveform")
    return bytes([0xB0]) + bytes(7) + frame_a[4:] + bytes(4) + frame_b[4:]


def display_frame(a, b):
    # Send the official literal byte string, not the inconsistent prose count.
    # B2 exceeds 20 bytes: use an acknowledged GATT write, never split commands.
    return bytes([0xB2]) + bytes.fromhex("FFFF00FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF0809") + bytes([a, b])


class OpossumBleBridge(CoyoteBleBridge):
    role = "ovc"
    strength_max = 200
    advertised_devices = {"47L127000": ("OVC_1", "Opossum")}

    def _output_allowed(self, generation):
        return (
            generation is None or (
                generation == self._generation and self.connected and self._auto_enabled
                and not self._paused and not self._global_emergency_stop.is_set()
                and 0 <= time.monotonic() - self._desired_updated_at <= .5
            )
        )

    def _notify(self, client, epoch, data):
        if client is not self.client:
            return
        if epoch != self._epoch and not (self._pending and self._pending[1] == (0, 0)):
            return
        # D0 is a button event, not intensity or accessory readiness.
        if len(data) != 3 or data[0] != 0xB3 or max(data[1:]) > 200:
            return
        self.reported = tuple(data[1:])
        pending = self._pending
        if pending and not pending[2].done():
            if self.reported == pending[1]:
                pending[2].set_result(self.reported)
            elif any(actual > wanted for actual, wanted in zip(self.reported, pending[1])):
                pending[2].set_exception(ValueError("Opossum intensity feedback exceeded request"))
            # A smaller intermediate report cannot confirm the requested value.
        else:
            task = asyncio.create_task(self._refresh_display(client, epoch, self.reported))
            self._aux_tasks.add(task)
            task.add_done_callback(self._aux_tasks.discard)
            if any(v > self._hard_cap for v in self.reported) or (not self._auto_enabled and any(self.reported)):
                self._request_emergency_in_loop()
                self.detail = "Unexpected Opossum intensity; output stopped, enable manually"
                self._emit("error", detail=self.detail)
        self._emit("ble_status")

    async def _write(self, client, payload, uuid=WRITE):
        if payload[0] == 0xB2:
            characteristic = client.services.get_characteristic(uuid)
            if not characteristic or "write" not in characteristic.properties:
                raise ValueError("Opossum B2 display sync requires acknowledged GATT long writes")
            await asyncio.wait_for(client.write_gatt_char(uuid, payload, response=True), .4)
        else:
            await super()._write(client, payload, uuid)

    async def _refresh_display(self, client, epoch, reported):
        try:
            async with self._write_lock:
                if client is self.client and epoch == self._epoch and client.is_connected and reported == self.reported:
                    await self._write(client, display_frame(*reported))
        except Exception as error:
            self._discard()
            self.detail = "Opossum display sync failed: " + str(error)
            await self._safe_zero_async()
            self.connected = False
            try:
                await client.disconnect()
            except Exception:
                pass
            self._emit("error", detail=self.detail)

    async def _command(self, client, a, b, fa=SILENT, fb=SILENT, *, generation=None, force_confirm=False):
        async with self._write_lock:
            if client is not self.client or not client.is_connected:
                raise ConnectionError("Opossum BLE disconnected")
            if not self._output_allowed(generation):
                return
            if generation is not None:
                cap = self._bound(self._hard_cap)
                a, b = self._bound(a, cap), self._bound(b, cap)
            if not a:
                fa = SILENT
            if not b:
                fb = SILENT
            if force_confirm or (a, b) != self.reported:
                # Do not let the previous envelope play at the new strength.
                await self._write(client, vibration_frame())
                if not self._output_allowed(generation):
                    return
                future = asyncio.get_running_loop().create_future()
                self._pending = (0, (a, b), future)
                try:
                    await self._write(client, bytes([0xB3, a, b]))
                    await asyncio.wait_for(future, .5)
                    await self._write(client, display_frame(*self.reported))
                finally:
                    if not future.done():
                        future.cancel()
                    self._pending = None
            if self._output_allowed(generation):
                await self._write(client, vibration_frame(fa, fb))

    async def _zero(self, client):
        if client.is_connected:
            await self._command(client, 0, 0, force_confirm=True)

"""Explicit scan consent, automatic BLE selection and progress; fake GATT only."""
import asyncio
import time
import unittest

from .ble_validation import BleTests, BackendBleTests, FakeClient, FakeClient2, RECORDS
from .ble_dual_validation import SharedScanner, SharedScanner2, FakeOpossum
from .opossum_ble import OpossumBleBridge


class AutoConnectBleTests(unittest.IsolatedAsyncioTestCase):
    scanner = SharedScanner
    coyote_factory = FakeClient
    until = BleTests.until
    feed = BackendBleTests.feed

    async def asyncSetUp(self):
        await BackendBleTests.asyncSetUp(self)
        self.ovc = OpossumBleBridge(self.events, client_factory=FakeOpossum)
        self.ovc_worker = asyncio.create_task(self.ovc._run())
        await self.until(lambda:self.ovc.server_ready)
        self.b.scanner = self.scanner
        self.b.client_factory = self.coyote_factory
        self.b.discovery_sink = self.ovc.accept_discovery
        self.backend.ovc_ble = self.ovc

    async def asyncTearDown(self):
        self.ovc._stop_event.set()
        await asyncio.wait_for(self.ovc_worker,3)
        RECORDS.append({"case":self._testMethodName+" / Opossum","physical_hardware":False,
                        "writes":self.ovc.client.rows if self.ovc.client else []})
        self.backend.ovc_ble = None
        await BackendBleTests.asyncTearDown(self)

    async def pump_until(self, predicate, timeout=2):
        end = time.monotonic()+timeout
        while time.monotonic()<end:
            self.backend._poll_device_support()
            if predicate():
                return
            await asyncio.sleep(.01)
        self.fail("Auto BLE mock timed out: "+repr((self.b.detail,self.ovc.detail)))

    async def test_explicit_scan_connects_both_without_enabling_output(self):
        await asyncio.sleep(.04)
        self.assertIsNone(self.b.client)
        self.assertIsNone(self.ovc.client)
        self.backend.scanBleDevices()
        await self.pump_until(lambda:self.b.connected and self.ovc.connected and self.backend.ovc_connected)
        self.client=self.b.client
        for _ in range(5):
            self.feed()
            await asyncio.sleep(.03)
        self.assertFalse(self.backend.auto_output_enabled or self.backend.ovc_enabled)
        self.assertFalse(self.b._auto_enabled or self.ovc._auto_enabled)
        self.assertEqual(self.b.client.actual,self.ovc.client.actual)
        self.assertEqual(self.b.client.actual,(0,0))
        self.assertEqual(self.backend.bleScanProgress,1)

    async def test_immediate_double_click_is_one_scan_and_still_auto_connects(self):
        before=self.scanner.calls
        self.backend.scanBleDevices()
        self.backend.scanBleDevices()
        await self.pump_until(lambda:self.b.connected and self.ovc.connected)
        self.assertEqual(self.scanner.calls,before+1)
        self.assertFalse(self.backend.auto_output_enabled or self.backend.ovc_enabled)

    async def test_progress_tracks_elapsed_scan_and_then_waits_for_real_connection(self):
        gate=asyncio.Event()
        scanner=self.scanner
        class SlowScanner:
            @staticmethod
            async def discover(**kwargs):
                self.assertAlmostEqual(kwargs["timeout"],.3)
                await gate.wait()
                return await scanner.discover(**kwargs)
        self.b.scanner=SlowScanner
        self.b.scan_seconds=.3
        self.backend.scanBleDevices()
        await self.pump_until(lambda:self.b.scan_state=="scanning")
        await asyncio.sleep(.08)
        self.backend._poll_device_support()
        self.assertTrue(self.backend.bleScanning and self.backend.bleBusy)
        progress=self.backend.bleScanProgress
        self.assertGreater(progress,.05)
        self.assertLess(progress,.98)
        self.assertIn("Scanning",self.backend.bleScanCaption)
        gate.set()
        await self.pump_until(lambda:self.b.connected and self.ovc.connected and not self.backend.bleBusy)
        self.assertEqual(self.backend.bleScanProgress,1)
        self.assertFalse(self.backend.auto_output_enabled or self.backend.ovc_enabled)

    async def test_cancelled_scan_cannot_connect_from_late_results(self):
        started=asyncio.Event()
        scanner=self.scanner
        class CancellationIgnoringScanner:
            @staticmethod
            async def discover(**kwargs):
                started.set()
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    # Prove the application drops even a late discovery result.
                    return await scanner.discover(**kwargs)
        self.b.scanner=CancellationIgnoringScanner
        self.backend.scanBleDevices()
        await started.wait()
        self.backend.cancelBleScan()
        await self.pump_until(lambda:not self.backend.bleScanning)
        self.assertEqual(self.b.scan_state,"cancelled")
        self.assertEqual(self.backend.bleScanProgress,0)
        self.assertIsNone(self.b.client)
        self.assertIsNone(self.ovc.client)

    async def test_multiple_coyotes_require_choice_but_unique_ovc_connects(self):
        scanner=self.scanner
        class MultipleScanner:
            @staticmethod
            async def discover(**kwargs):
                rows=await scanner.discover(**kwargs)
                from types import SimpleNamespace
                rows["second"]=(SimpleNamespace(address="second",name=scanner.coyote_name),
                                SimpleNamespace(local_name=scanner.coyote_name))
                return rows
        self.b.scanner=MultipleScanner
        self.backend.scanBleDevices()
        await self.pump_until(lambda:self.ovc.connected and not self.backend.bleBusy)
        self.assertEqual(len(self.b.devices),2)
        self.assertIsNone(self.b.client)
        self.assertFalse(self.backend.auto_output_enabled or self.backend.ovc_enabled)
        self.assertTrue(self.backend.connectBleRole("coyote","second"))
        await self.pump_until(lambda:self.b.connected)
        self.assertEqual(self.b.selected_address,"second")

    async def test_rescan_does_not_replace_or_pause_connected_devices(self):
        self.backend.scanBleDevices()
        await self.pump_until(lambda:self.b.connected and self.ovc.connected)
        clients=self.b.client,self.ovc.client
        epochs=self.b._epoch,self.ovc._epoch
        self.feed()
        self.backend.toggleOutput()
        self.backend.toggleOvcOutput()
        for _ in range(12):
            self.feed()
            await asyncio.sleep(.03)
        self.assertTrue(self.b._auto_enabled and self.ovc._auto_enabled)
        self.backend.scanBleDevices()
        await self.pump_until(lambda:not self.backend.bleBusy)
        self.assertEqual((self.b.client,self.ovc.client),clients)
        self.assertEqual((self.b._epoch,self.ovc._epoch),epochs)
        self.assertTrue(self.backend.auto_output_enabled and self.backend.ovc_enabled)


class AutoConnectBle2Tests(AutoConnectBleTests):
    scanner = SharedScanner2
    coyote_factory = FakeClient2

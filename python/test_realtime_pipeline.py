"""End-to-end loopback test: UDP -> background engine -> Socket phone emulator."""
import asyncio
import json
import socket
import threading
import time
import unittest

import websockets
from manaka_dglab_bridge import DGLabBridge
from manaka_runtime import DisplayMailbox, RealtimeProcessor, RuntimeConfig
from qml_dashboard_prototype.backend import TelemetryWorker


class BackgroundPipelineTests(unittest.TestCase):
    def test_udp_output_and_stale_zero_while_gui_thread_is_blocked(self):
        mailbox = DisplayMailbox()
        bridge = DGLabBridge(mailbox,port=0)
        processor = RealtimeProcessor(RuntimeConfig(),bridge,mailbox)
        worker = TelemetryWorker(mailbox,processor,port=0)
        bound, stop = threading.Event(), threading.Event()
        received, failures = [], []
        last_sent = []
        bridge.start()
        worker.start()
        deadline = time.monotonic()+4
        while (not bridge.server_ready or not bridge.controller_id or not worker.port) and time.monotonic()<deadline:
            time.sleep(.01)
        self.assertTrue(bridge.server_ready)
        self.assertGreater(worker.port,0)

        async def phone():
            try:
                async with websockets.connect(f"ws://127.0.0.1:{bridge.port}") as connection:
                    hello = json.loads(await connection.recv())
                    await connection.send(json.dumps(dict(type="bind",clientId=bridge.controller_id,
                        targetId=hello["clientId"],message="DGLAB")))
                    await connection.recv()
                    bound.set()
                    while not stop.is_set():
                        try:
                            packet = json.loads(await asyncio.wait_for(connection.recv(),.1))
                            received.append((time.monotonic(),packet.get("message","")))
                        except asyncio.TimeoutError:
                            pass
            except Exception as error:
                failures.append(str(error))
                bound.set()

        phone_thread = threading.Thread(target=lambda:asyncio.run(phone()),daemon=True)
        phone_thread.start()
        try:
            self.assertTrue(bound.wait(3))
            deadline = time.monotonic()+2
            while not bridge.connected and time.monotonic()<deadline:
                time.sleep(.01)
            self.assertTrue(bridge.connected)
            bridge.set_auto_enabled(True)
            def emit():
                with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
                    for sequence in range(1,9):
                        packet = dict(version=2,sessionId="test",sequence=sequence,monotonicMs=sequence*100,
                            stage="Residence",heartRate=160,action="Test",ecstasy=1,orgasm=False)
                        sender.sendto(json.dumps(packet).encode(),("127.0.0.1",worker.port))
                        last_sent[:] = [time.monotonic()]
                        time.sleep(.05)
            emitter = threading.Thread(target=emit,daemon=True)
            emitter.start()
            # Deliberately do not run QCoreApplication.processEvents(), _poll(),
            # or consume display messages. The same thread owns the real GUI.
            time.sleep(1.8)
            emitter.join(1)
            positives = [(stamp,message) for stamp,message in received if message.startswith("strength-1+2+") and message != "strength-1+2+0"]
            self.assertTrue(positives,received)
            zeros = [stamp for stamp,message in received if message == "strength-1+2+0" and stamp > positives[-1][0]]
            self.assertTrue(zeros,received)
            self.assertLess(zeros[0]-last_sent[0],1.45)
            self.assertGreater(zeros[0]-last_sent[0],.8)
            self.assertLessEqual(mailbox.qsize(),8)
            self.assertEqual(failures,[])
        finally:
            stop.set()
            worker.stop()
            worker.join(1)
            phone_thread.join(2)
            bridge.stop()
        self.assertFalse(worker.is_alive())
        self.assertFalse(phone_thread.is_alive())

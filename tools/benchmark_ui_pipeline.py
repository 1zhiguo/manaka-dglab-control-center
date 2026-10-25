"""Compare GUI message-consumption cost under synthetic telemetry overload."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--batch", type=int, default=5000)
args = parser.parse_args()
sys.path.insert(0, str(args.source / "python"))
from PySide6.QtCore import QCoreApplication
from qml_dashboard_prototype import backend as module

app = QCoreApplication([])


def memory():
    if sys.platform != "win32":
        return None
    class Counters(ctypes.Structure):
        _fields_ = [("cb",ctypes.c_ulong),("faults",ctypes.c_ulong)] + [
            (name,ctypes.c_size_t) for name in ("peak_working_set","working_set","peak_paged","paged",
                "peak_nonpaged","nonpaged","pagefile","peak_pagefile","private")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1),ctypes.byref(counters),counters.cb):
        return None
    return {"working_set_mib":counters.working_set/(1024**2),"peak_working_set_mib":counters.peak_working_set/(1024**2),
            "private_mib":counters.private/(1024**2)}


with tempfile.TemporaryDirectory() as directory, patch.object(module, "app_data_dir", return_value=Path(directory)), patch.object(module, "load_config", return_value={}):
    backend = module.ControlCenterBackend(demo=True)
    backend.poll_timer.stop()
    backend.demo_mode = False
    backend.auto_output_enabled = backend.device_connected_value = False
    if backend.hud_socket is not None:
        backend.hud_socket.close()
    backend.hud_socket = None
    if hasattr(module, "RealtimeProcessor"):
        class NullBridge:
            connected = auto_enabled = False
            def channel_limit(self, key): return 100
            def channel_output(self,key): return 0
            def configure_limits(self,*args): pass
            def update_auto_outputs(self, *args, **kwargs): pass
            def zero_output(self): pass
        backend.processor = module.RealtimeProcessor(backend._runtime_config(), NullBridge(), backend.messages)
    durations = []
    worker_ms = []
    memory_before = memory()
    cpu_start = time.process_time()
    for batch in range(10):
        worker_start = time.perf_counter()
        for index in range(args.batch):
            sequence = batch*args.batch+index+1
            packet = dict(version=1,sequence=sequence,monotonicMs=sequence*100,heartRate=120,stage="Residence",action="None",ecstasy=.4)
            if getattr(backend, "processor", None) is not None:
                backend.processor.process(packet)
            else:
                backend.messages.put(("telemetry", packet))
        worker_ms.append((time.perf_counter()-worker_start)*1000)
        start = time.perf_counter()
        backend._poll()
        durations.append((time.perf_counter()-start)*1000)
    result = dict(batch=args.batch,batches=10,gui_poll_ms_median=statistics.median(durations),
        gui_poll_ms_max=max(durations),gui_poll_ms_p95=sorted(durations)[8],
        ingress_ms_median=statistics.median(worker_ms),cpu_seconds=time.process_time()-cpu_start,
        memory_before=memory_before,memory_after=memory(),
        remaining_display_messages=backend.messages.qsize(),
        scope="synthetic 5000-packet batches, offline; excludes real game, rendering and hardware")
    backend.shutdown()
args.output.write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))

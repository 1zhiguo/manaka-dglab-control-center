"""Measure real Qt Quick frame signals, process CPU and hidden preview clocks.

This is software-renderer profiling, not hardware/GPU or physical-device proof.
Run sequentially, outside concurrent screenshot/tests, for comparable timings.
"""
import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE','Basic')
os.environ.setdefault('QT_QUICK_BACKEND','software')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from PySide6.QtCore import QObject, QUrl, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from qml_dashboard_prototype import backend as module
import shiboken6

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--qml-root',type=Path,default=Path(module.__file__).parent)
    parser.add_argument('--seconds',type=int,default=5)
    args=parser.parse_args();args.output.parent.mkdir(parents=True,exist_ok=True)
    warnings=[];app=QGuiApplication([])
    qInstallMessageHandler(lambda kind,ctx,text:warnings.append(text) if 'font directory' not in text and 'fonts are no longer' not in text else None)
    for font in ['msyh.ttc','segoeui.ttf']:QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
    with tempfile.TemporaryDirectory() as directory,patch.object(module,'app_data_dir',return_value=Path(directory)),patch.object(module,'load_config',return_value={'theme':'dark'}),patch.object(module,'update_config'):
        backend=module.ControlCenterBackend(demo=True,language='en');backend.agreement_accepted_value=True
        engine=QQmlApplicationEngine();engine.rootContext().setContextProperty('backend',backend);engine.rootContext().setContextProperty('initialPageIndex',3)
        engine.load(QUrl.fromLocalFile(str(args.qml_root/'ControlCenter.qml')));assert engine.rootObjects(),warnings
        window=engine.rootObjects()[0];preview=window.findChild(QObject,'wavePreview')
        swaps=[];render=[];start=[0.0]
        window.frameSwapped.connect(lambda:swaps.append(time.perf_counter()))
        window.beforeRendering.connect(lambda:start.__setitem__(0,time.perf_counter()),Qt.DirectConnection)
        window.afterRendering.connect(lambda:render.append((time.perf_counter()-start[0])*1000),Qt.DirectConnection)
        def stats(values):
            values=sorted(values)
            return dict(count=len(values),median_ms=round(statistics.median(values),3) if values else None,p95_ms=round(values[min(len(values)-1,int(len(values)*.95))],3) if values else None)
        reports=[]
        try:
            for name,page,shown in [('visible-preview',3,True),('hidden-preview',9,True),('hidden-window',3,False),('live-dashboard',0,True),('live-monitor',4,True)]:
                window.setProperty('pageIndex',page)
                window.show() if shown else window.hide()
                QTest.qWait(600);swaps.clear();render.clear()
                clock=preview.property('elapsedMs');cpu=time.process_time();wall=time.perf_counter()
                QTest.qWait(args.seconds*1000)
                elapsed=time.perf_counter()-wall
                reports.append(dict(case=name,seconds=round(elapsed,3),cpu_one_core_percent=round((time.process_time()-cpu)/elapsed*100,2),frames=len(swaps),frames_per_second=round(len(swaps)/elapsed,2),frame_interval=stats([(b-a)*1000 for a,b in zip(swaps,swaps[1:])]),render_signal_span=stats(render),preview_clock_delta_ms=round(preview.property('elapsedMs')-clock,1)))
        finally:backend.shutdown();shiboken6.delete(engine)
    report=dict(renderer='Qt Quick software, offscreen, 1320x840, demo telemetry; no game/device',measurements=reports,qml_warnings=warnings)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

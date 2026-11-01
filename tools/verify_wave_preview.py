"""Exercise selection, refresh, looping and hidden-page behavior in actual QML."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"python"))
from PySide6.QtCore import QObject, QPointF, QUrl, Qt, QMetaObject, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine, QQmlEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from qml_dashboard_prototype import backend as module
import shiboken6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--theme", default="light")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    errors, checks = [], []
    def message(kind, context, text):
        if any(s in text for s in ("TypeError", "ReferenceError", "Cannot assign", "Binding loop", "is not a type", "failed to load")):
            errors.append(text)
    qInstallMessageHandler(message)
    app = QGuiApplication([])
    for font in ("msyh.ttc", "segoeui.ttf", "seguisym.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/"+font)
    with tempfile.TemporaryDirectory() as directory, patch.object(module, "app_data_dir", return_value=Path(directory)), patch.object(module, "load_config", return_value={"theme": args.theme,"reduced_motion":True}):
        backend = module.ControlCenterBackend(demo=True, language=args.language)
        backend.agreement_accepted_value = True
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend", backend)
        engine.rootContext().setContextProperty("initialPageIndex", 3)
        engine.load(QUrl.fromLocalFile(str(Path(module.__file__).with_name("ControlCenter.qml"))))
        assert engine.rootObjects(), "Failed to load UI"
        window = engine.rootObjects()[0]
        def find(name):
            result = window.findChild(QObject, name)
            if result is None:
                stack = [window.contentItem()]
                while stack:
                    item = stack.pop()
                    if item.objectName() == name:
                        return item
                    stack.extend(item.childItems())
            assert result is not None, name
            return result
        library = find("waveWorkbench")
        preview = find("wavePreview")
        def js(source, target=library):
            expression = QQmlExpression(QQmlEngine.contextForObject(target), target, source)
            result = expression.evaluate()[0]
            assert not expression.hasError(), expression.error().toString()
            return result
        def click(item):
            assert item.isVisible() and item.property("enabled")
            point = item.mapToScene(QPointF(item.width()/2, item.height()/2)).toPoint()
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
            QTest.qWait(60)
        def snapshot(name):
            image = window.grabWindow()
            assert image.save(str(args.output/(name+".png")))
            point = preview.mapToScene(QPointF(0, 0))
            scale = image.width()/window.width()
            crop = image.copy(int(point.x()*scale), int(point.y()*scale), int(preview.width()*scale), int(preview.height()*scale))
            return hashlib.sha256(bytes(crop.constBits())).hexdigest()
        def select(key):
            find("waveSearch").setProperty("text", "")
            view = find("waveLibraryList")
            js(f'positionViewAtIndex(model.findIndex(x => x.key === {json.dumps(key)}), ListView.Center)', view)
            QTest.qWait(80)
            click(find("waveAsset_"+key))
            assert library.property("selectedAsset") == key
            expected = backend.waveAsset(key)
            assert js("asset.name") == expected["name"]
            assert json.loads(js("JSON.stringify(samples)", preview)) == expected["amplitudes"]
            assert preview.property("durationMs") == expected["durationMs"]
            assert preview.property("windowMs") == min(5000,expected["durationMs"]*3)
        try:
            QTest.qWait(200)
            # Reproduce the old binding break before selecting another entry.
            assert backend.favoriteWaveAsset("official_breath", True)["ok"]
            select("official_heartbeat")
            select("official_breath")
            checks.append("mouse selection updates samples, name and duration after a favorite/config signal")
            first = snapshot("preview-start")
            start = preview.property("elapsedMs")
            QTest.qWait(240)
            assert preview.property("elapsedMs") > start+150
            assert snapshot("preview-moving") != first
            loops = preview.property("completedLoops")
            QTest.qWait(int(preview.property("displayCycleMs"))+120)
            assert preview.property("completedLoops") > loops
            assert 0 <= preview.property("positionMs") < preview.property("durationMs")
            checks.append("rendered waveform scrolls at adaptive preview speed and wraps repeatedly")
            window.setProperty("pageIndex", 10)
            QTest.qWait(50)
            assert not preview.property("animating")
            paused = preview.property("elapsedMs")
            QTest.qWait(180)
            assert preview.property("elapsedMs") == paused
            window.setProperty("pageIndex", 3)
            QTest.qWait(140)
            assert preview.property("animating") and preview.property("elapsedMs") > paused
            checks.append("hidden library stops its animation clock and resumes on return")
            with patch.object(module,"update_config") as persist:
                initial_theme=backend.theme
                click(find("themeToggle"))
                persist.assert_called_once_with({"theme":"dark" if initial_theme=="light" else "light"})
                assert preview.property("animating")
                click(find("themeToggle"))
                assert backend.theme==initial_theme and preview.property("animating")
                assert window.findChild(QObject,"appearanceDialog") is None
            checks.append("direct theme toggle persists only theme and keeps adaptive preview running")
            window.hide();QTest.qWait(80);paused=preview.property("elapsedMs")
            QTest.qWait(180);assert preview.property("elapsedMs")==paused and not preview.property("animating")
            window.show();QTest.qWait(100);assert preview.property("animating")
            checks.append("hidden application window stops the preview clock")
            result = backend.saveWaveAsset("", "Preview regression", "Test", "0A0A0A0A00193264\n0A0A0A0A64321900")
            assert result["ok"], result
            key = result["key"]
            select(key)
            assert preview.property("durationMs") == 200
            before = json.loads(js("JSON.stringify(samples)", preview))
            assert backend.saveWaveAsset(key, "Preview regression edited", "Test", "0A0A0A0A64193200\n0A0A0A0A00193264")["ok"]
            QTest.qWait(60)
            assert js("asset.name") == "Preview regression edited"
            assert json.loads(js("JSON.stringify(samples)", preview)) != before
            assert len(json.loads(js("JSON.stringify(samples)", preview))) == len(before)
            assert preview.property("durationMs") == 200
            select("official_breath")
            select(key)
            checks.append("editing a selected waveform refreshes equal-length samples and later selection remains reactive")
            # Open/close the full-frame editor: this formerly broke selection too.
            js("openAssetEditor()")
            QTest.qWait(50)
            frames = find("waveRawFrames")
            frames.setProperty("text", frames.property("text")+"\n0A0A0A0A00000000")
            assert library.property("dirty")
            window.setProperty("pageIndex", 0)
            window.close(); QTest.qWait(40)
            assert window.isVisible() and find("discardWorkbenchChanges").property("visible")
            js("reject()", find("discardWorkbenchChanges"))
            assert not window.property("pendingWindowClose") and library.property("dirty")
            checks.append("unsaved waveform edits keep their close protection after gameplay separation")
            js("close()", find("waveAssetEditor"))
            window.setProperty("pageIndex", 3)
            select("official_heartbeat")
            select("donor_piston")
            QTest.qWait(int(preview.property("displayCycleMs"))+120)
            assert preview.property("completedLoops") >= 1
            checks.append("selection after editor use and short donor waveform looping remain correct")
            # A full screen always takes five seconds to scroll. Short waves
            # show three cycles; long waves retain a five-second real-time view.
            # Check rendered trace pixels against actual source-time samples.
            window.setProperty("pageIndex",0); QTest.qWait(40)
            preview.setProperty("elapsedMs",0)
            window.setProperty("pageIndex",3); QTest.qWait(40)
            for frames in (1,4,12,82,6000):
                data="\n".join("0A0A0A0A001E3C64" if i%2==0 else "0A0A0A0A643C1E00" for i in range(frames))
                created=backend.saveWaveAsset("",f"Time scale {frames}","Test",data)
                assert created["ok"],created
                select(created["key"])
                span=min(5000,frames*100*3)
                speed=preview.property("pixelsPerMs")
                rate=preview.property("playbackRate")
                assert preview.property("windowMs")==span
                assert abs(speed*rate*5000-preview.width()) < 0.01
                assert rate<=1 and preview.property("displayCycleMs")>=5000/3-0.01
                if frames*100*3<5000:
                    assert span/(frames*100)==3
                    assert f'{1/rate:.1f}' in find("wavePreviewStatus").property("text")
                else:
                    assert rate==1 and span==5000
                # Pause only the test clock so the image has an exact time base.
                js("stop()",find("wavePreviewClock"))
                preview.setProperty("elapsedMs",137)
                js("requestPaint()",find("wavePreviewTrace")); QTest.qWait(60)
                image=window.grabWindow();scale=image.width()/window.width()
                origin=preview.mapToScene(QPointF(0,0))
                color=preview.property("lineColor")
                color_hits=0
                for fraction in (0.11,0.29,0.53,0.77,0.91):
                    # Use the center of a 25 ms sample to avoid vertical edges.
                    source_time=137*rate
                    time=int((source_time+span*fraction)/25)*25+12.5
                    x=(time-source_time)*speed
                    amplitude=js(f"sampleAt({time})",preview)
                    y=2+(preview.property("plotHeight")-4)*(1-amplitude/100)
                    px=int((origin.x()+x)*scale);py=int((origin.y()+y)*scale)
                    hit=any(sum(abs(image.pixelColor(px+dx,py+dy).getRgb()[c]-color.getRgb()[c]) for c in range(3))<80 for dx in range(-2,3) for dy in range(-2,3))
                    color_hits+=int(hit)
                assert color_hits==5,(frames,color_hits)
                assert not any(child.inherits('QQuickRectangle') for child in preview.childItems()),'No start marker should remain'
                if frames in (1,6000):snapshot(f"adaptive-window-{frames}-frames")
                assert backend.waveAsset(created["key"])["durationMs"]==frames*100
            checks.append("100 ms to 10 minute waves use three cycles or five real seconds, scroll one screen in five seconds, match rendered source times and have no start dot")
            assert backend.bridge is None, "Preview test must never create a device bridge"
            snapshot("preview-final")
        finally:
            backend.shutdown()
            shiboken6.delete(engine)
    assert not errors, errors
    (args.output/"results.json").write_text(json.dumps(dict(checks=checks,qml_errors=errors,mode="isolated demo; no game or device output"), indent=2), encoding="utf-8")
    print(f"Passed {len(checks)} waveform preview scenarios")


if __name__ == "__main__":
    main()

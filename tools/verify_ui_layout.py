"""Capture every control-center page with isolated offline demo settings."""
import argparse
from dataclasses import replace
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
from PySide6.QtCore import QObject, QPointF, QTimer, QUrl, QMetaObject, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QFontDatabase, QFont
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem
from qml_dashboard_prototype import backend as module
from manaka_channel_engine import MappingSettings, SOURCES
import shiboken6


def items(root):
    yield root
    for child in root.childItems():
        yield from items(child)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--language",default="zh")
    parser.add_argument("--theme",default="dark")
    parser.add_argument("--width",type=int,default=1320)
    parser.add_argument("--height",type=int,default=840)
    parser.add_argument("--independent",action="store_true")
    parser.add_argument("--legacy",action="store_true")
    parser.add_argument("--live-connection",action="store_true")
    parser.add_argument("--stress-text",action="store_true")
    args=parser.parse_args()
    errors=[]
    def message(kind,context,text):
        if any(word in text for word in ("TypeError","ReferenceError","is not a type","Cannot assign","failed to load","Binding loop","recursive rearrange")):
            errors.append(text)
        if "font directory" not in text and "fonts are no longer shipped" not in text:
            print(text,file=sys.stderr)
    qInstallMessageHandler(message)
    app=QGuiApplication([])
    for font in ("msyh.ttc","segoeui.ttf","seguisym.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/"+font)
    app.setFont(QFont("Microsoft YaHei UI",10))
    reports=[]
    args.output.mkdir(parents=True,exist_ok=True)
    config={"theme":args.theme}
    if args.legacy:
        config.update(trigger_bpm=95, full_bpm=150, min_strength=3, output_max=18)
    if args.independent or args.stress_text:
        config["channel_mapping"]=MappingSettings().to_dict()
    if args.stress_text:
        for key in "AB":
            binding=config["channel_mapping"][key]["bindings"][0]
            config["channel_mapping"][key]["bindings"]=[dict(binding,source=source) for source in SOURCES]
    with tempfile.TemporaryDirectory() as directory, patch.object(module,"app_data_dir",return_value=Path(directory)), patch.object(module,"load_config",return_value=config):
        backend=module.ControlCenterBackend(demo=True,language=args.language)
        backend.agreement_accepted_value=True
        if args.live_connection:
            from manaka_dglab_bridge import DGLabBridge
            backend.demo_mode = False
            backend.server_ready_value = False
            backend.device_connected_value = False
            backend.auto_output_enabled = False
            backend.bridge = DGLabBridge(backend.messages)
            backend.bridge.start()
        if args.stress_text:
            backend.poll_timer.stop()
            wave=next(iter(module.PRESETS.values()))
            backend.current_wave_a=backend.current_wave_b=replace(wave,name="Long custom waveform name / 自定义长名称 / "+"Preview "*12)
            backend.game_folder_value="C:/UI-test/"+"Very long sample folder/"*8+"游戏目录"
        engine=QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend",backend)
        engine.rootContext().setContextProperty("initialPageIndex",0)
        engine.load(QUrl.fromLocalFile(str(Path(module.__file__).with_name("ControlCenter.qml"))))
        if not engine.rootObjects():
            return 1
        window=engine.rootObjects()[0]
        window.setWidth(args.width)
        window.setHeight(args.height)
        sequence=list(range(11))+["channels", "channels-B", "channels-events", "workbench-A", "workbench-B", "workbench-bindings", "workbench-legacy", "network-help", "theme-switched"]
        if args.live_connection:
            sequence = [1, "network-help"]
        def capture(index):
            name=str(sequence[index])
            if args.live_connection and name == "1":
                qr = window.findChild(QObject, "connectionQr")
                if not backend.serverReady or not backend.lanAddresses or QQmlExpression(engine.rootContext(),qr,"Number(status)").evaluate()[0] != 1:
                    errors.append("Live address/QR failed to load")
                if backend.bridge.auto_enabled:
                    errors.append("Diagnostic must not enable device output")
            if name == "network-help":
                title = window.findChild(QObject,"networkHelpTitle")
                intro = window.findChild(QObject,"networkHelpIntro")
                if intro.mapToScene(QPointF(0,0)).y() < title.mapToScene(QPointF(0,title.height())).y():
                    errors.append("Network help content overlaps title")
            if name == "8":
                # An entire row may overflow while every label fits its parent.
                # Check complete control bounds through all clipping ancestors.
                for control_name in ("npcMasterSwitch","npcAudioSwitch","npcSubtitleSwitch"):
                    item=window.findChild(QObject,control_name)
                    pos=item.mapToScene(QPointF(0,0)); ancestor=item.parentItem()
                    if pos.x()<0 or pos.x()+item.width()>window.width()+1:
                        errors.append("Control outside window: "+control_name)
                    while ancestor:
                        if ancestor.clip():
                            origin=ancestor.mapToScene(QPointF(0,0))
                            if pos.x()<origin.x()-1 or pos.x()+item.width()>origin.x()+ancestor.width()+1:
                                errors.append("Control clipped by ancestor: "+control_name)
                        ancestor=ancestor.parentItem()
            image=window.grabWindow()
            if image.isNull() or not image.save(str(args.output/(name+".png"))):
                errors.append("Failed to capture "+name)
            overflow=[]
            buttons=[]
            for item in items(window.contentItem()):
                if not item.isVisible() or item.width()<=0 or item.height()<=0:
                    continue
                point=item.mapToScene(QPointF(0,0))
                if point.x()>=window.width() or point.y()>=window.height() or point.x()+item.width()<=0 or point.y()+item.height()<=0:
                    continue
                text=item.property("text")
                if not isinstance(text,str) or not text:
                    continue
                content=item.property("contentWidth")
                no_elide = QQmlExpression(engine.rootContext(),item,"typeof elide === 'undefined' || elide === 3").evaluate()[0]
                parent=item.parentItem()
                outside_parent=parent and (item.x() < -2 or item.x()+item.width()>parent.width()+2)
                scrollable_input=item.inherits("QQuickTextInput") or item.inherits("QQuickTextEdit")
                if (isinstance(content,(int,float)) and content>item.width()+2 and no_elide and not item.clip() and not scrollable_input) or outside_parent:
                    overflow.append(dict(text=text[:130],width=round(item.width(),1),content=round(content,1),x=round(point.x(),1),y=round(point.y(),1),type=item.metaObject().className()))
                if item.objectName().startswith("navLabel"):
                    buttons.append(dict(text=text,x=point.x(),y=point.y()))
            reports.append(dict(page=name,overflow=overflow,nav_labels=buttons))
            if len(buttons)!=11 or max(button["x"] for button in buttons)-min(button["x"] for button in buttons)>1:
                errors.append("Navigation labels are not aligned: "+name)
            gameplay=window.findChild(QObject,"navItem10")
            waveforms=window.findChild(QObject,"navItem3")
            if gameplay.mapToScene(QPointF(0,0)).y() >= waveforms.mapToScene(QPointF(0,0)).y():
                errors.append("Gameplay must precede waveforms in sidebar: "+name)
            if index+1<len(sequence):
                advance(index+1)
            else:
                app.exit(0)
        def advance(index):
            page=sequence[index]
            if isinstance(page,str):
                window.setProperty("pageIndex",2)
                if page=="channels":
                    window.setProperty("pageIndex",2)
                if page.startswith("workbench-"):
                    window.setProperty("pageIndex",10)
                    studio=window.findChild(QObject,"gameplaySettings")
                    studio.setProperty("pendingMode","legacy_v1" if page == "workbench-legacy" else "independent")
                    QMetaObject.invokeMethod(studio,"confirmMode")
                    window.findChild(QObject,"gameplayTabs").setProperty("currentIndex", {"workbench-A":0,"workbench-B":1,"workbench-bindings":2,"workbench-legacy":0}[page])
                    if page in {"workbench-A","workbench-B"}:
                        studio.setProperty("ruleIndex",0)
                if page=="network-help":
                    QMetaObject.invokeMethod(window.findChild(QObject,"networkHelpDialog"),"open")
                if page=="theme-switched":
                    QMetaObject.invokeMethod(window.findChild(QObject,"networkHelpDialog"),"close")
                    backend.setTheme("dark" if backend.theme == "light" else "light")
                if page=="channels-B":
                    window.findChild(QObject,"channelTabs").setProperty("currentIndex",1)
                if page=="channels-events":
                    scroll=window.findChild(QObject,"channelScroll")
                    content=scroll.property("contentItem")
                    content.setProperty("contentY",max(0,content.property("contentHeight")-content.height()))
            else:
                window.setProperty("pageIndex",page)
            QTimer.singleShot(350,lambda:capture(index))
        QTimer.singleShot(1500 if args.live_connection else 150,lambda:advance(0))
        app.exec()
        backend.shutdown()
        shiboken6.delete(engine)
    (args.output/"layout.json").write_text(json.dumps(dict(language=args.language,theme=args.theme,width=args.width,height=args.height,pages=reports,errors=errors),ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Captured {len(reports)} pages; QML errors: {len(errors)}; horizontal overflow candidates: {sum(len(p['overflow']) for p in reports)}")
    return bool(errors or any(p['overflow'] for p in reports))


if __name__=="__main__":
    raise SystemExit(main())

"""Inspect/render all NPC master-switch states without installing a plugin."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE','Basic')
os.environ.setdefault('QT_QUICK_BACKEND','software')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from PySide6.QtCore import QObject, QPointF, QUrl, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from qml_dashboard_prototype import backend as module
import shiboken6


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--qml-root',type=Path)
    parser.add_argument('--language',default='zh')
    parser.add_argument('--theme',default='light')
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    errors=[]; reports=[]
    def message(kind,context,text):
        if any(s in text for s in ('TypeError','ReferenceError','Cannot assign','Binding loop','is not a type','failed to load')):
            errors.append(text)
    qInstallMessageHandler(message)
    app=QGuiApplication([])
    for font in ('msyh.ttc','segoeui.ttf','seguisym.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
    with tempfile.TemporaryDirectory() as directory, patch.object(module,'app_data_dir',return_value=Path(directory)), patch.object(module,'load_config',return_value={'theme':args.theme}):
        backend=module.ControlCenterBackend(demo=True,language=args.language)
        backend.agreement_accepted_value=True
        backend.poll_timer.stop()
        engine=QQmlApplicationEngine()
        engine.rootContext().setContextProperty('backend',backend)
        engine.rootContext().setContextProperty('initialPageIndex',8)
        engine.load(QUrl.fromLocalFile(str((args.qml_root or Path(module.__file__).parent)/'ControlCenter.qml')))
        assert engine.rootObjects()
        window=engine.rootObjects()[0];window.setWidth(1120);window.setHeight(720)
        def find(name):
            result=window.findChild(QObject,name)
            assert result is not None,name
            return result
        switch=find('npcMasterSwitch');label=find('npcMasterSwitchLabel');knob=find('npcMasterSwitchKnob')
        def capture(name,installed,enabled):
            backend.npc_voice_installed_value=installed
            backend.npc_voice_enabled_value=enabled
            backend.configChanged.emit()
            QTest.qWait(280)
            text=label.property('text')
            left=label.x();right=left+label.width()
            separation=right <= knob.x()+0.5 or left >= knob.x()+knob.width()-0.5
            good=(label.isVisible() and label.width()>=label.property('contentWidth') and label.height()>=label.property('contentHeight') and left>=0 and right<=switch.width()+0.5 and separation)
            expected=backend.translate('开启' if installed and enabled else '关闭')
            record=dict(state=name,text=text,expected=expected,text_rect=[left,label.y(),label.width(),label.height()],knob_rect=[knob.x(),knob.y(),knob.width(),knob.height()],switch_width=switch.width(),label_fits_and_does_not_overlap=good)
            reports.append(record)
            assert window.grabWindow().save(str(args.output/(name+'.png')))
            if not args.inspect_only:
                assert text==expected and good,record
        try:
            # Exercise both initial disabled/installed state and repeated on/off.
            capture('uninstalled',False,True)
            capture('installed-off',True,False)
            capture('installed-on',True,True)
            capture('installed-off-again',True,False)
            capture('uninstalled-again',False,False)
            if not args.inspect_only:
                # Stub only persistence. A real mouse click still invokes the
                # production slot, while no game/config files can be touched.
                def save(*unused):
                    backend.configChanged.emit();return True
                with patch.object(backend,'_save_npc_voice_options',side_effect=save) as persist:
                    point=switch.mapToScene(QPointF(switch.width()/2,switch.height()/2)).toPoint()
                    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point);QTest.qWait(40)
                    assert not persist.called,'Uninstalled switch must stay inactive'
                    backend.npc_voice_installed_value=True;backend.configChanged.emit();QTest.qWait(40)
                    for expected in (True,False,True,False):
                        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point);QTest.qWait(250)
                        assert backend.npc_voice_enabled_value is expected
                        assert label.property('text')==backend.translate('开启' if expected else '关闭')
                    switch.forceActiveFocus(Qt.TabFocusReason)
                    QTest.keyClick(window,Qt.Key_Space);QTest.qWait(250)
                    assert backend.npc_voice_enabled_value is True
                    assert switch.property('activeFocus')
                    assert persist.call_count==5
                assert backend.bridge is None
        finally:
            backend.shutdown();shiboken6.delete(engine)
    result=dict(states=reports,qml_errors=errors,mode='isolated simulated installation state; no game files modified')
    (args.output/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.inspect_only:assert not errors,errors
    print(f"Verified {len(reports)} NPC switch states")


if __name__=='__main__':main()

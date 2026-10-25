"""Inspect application dialogs and appearance settings in an isolated demo."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_CONTROLS_STYLE','Basic');os.environ.setdefault('QT_QUICK_BACKEND','software')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from PySide6.QtCore import QObject, QPointF, QUrl, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from qml_dashboard_prototype import backend as module
import shiboken6

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--language',default='en');parser.add_argument('--theme',default='dark');args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    errors=[];checks=[]
    qInstallMessageHandler(lambda kind,ctx,text:errors.append(text) if any(x in text for x in ('TypeError','ReferenceError','Cannot assign','Binding loop','failed to load','recursive')) else None)
    app=QGuiApplication([])
    for font in ['msyh.ttc','segoeui.ttf']:QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
    with tempfile.TemporaryDirectory() as directory,patch.object(module,'app_data_dir',return_value=Path(directory)),patch.object(module,'load_config',return_value={'theme':args.theme}),patch.object(module,'update_config') as persist:
        backend=module.ControlCenterBackend(demo=True,language=args.language);backend.agreement_accepted_value=True
        engine=QQmlApplicationEngine();engine.rootContext().setContextProperty('backend',backend);engine.rootContext().setContextProperty('initialPageIndex',0)
        engine.load(QUrl.fromLocalFile(str(Path(module.__file__).with_name('ControlCenter.qml'))));assert engine.rootObjects(),errors
        window=engine.rootObjects()[0];window.setWidth(1120);window.setHeight(720);window.requestActivate();QTest.qWait(150)
        def js(expression):
            e=QQmlExpression(engine.contextForObject(window),window,expression);v=e.evaluate()[0];assert not e.hasError(),e.error().toString();return v
        def capture(name):
            QTest.qWait(160);assert window.grabWindow().save(str(args.output/(name+'.png')));checks.append(name)
        try:
            # Confirm keyboard-operable pause/resume without touching a device.
            pause=window.findChild(QObject,'pauseOutput');pause.forceActiveFocus(Qt.TabFocusReason)
            before=backend.outputPaused;QTest.keyClick(window,Qt.Key_Space);QTest.qWait(80);assert backend.outputPaused != before
            QTest.keyClick(window,Qt.Key_Space);assert backend.outputPaused == before
            checks.append('keyboard pause/resume in offline demo')
            for dialog in ['networkHelpDialog','npcTextEditorDialog','pack9527Wizard','progressConfirm','modDeleteConfirm','agreementDialog']:
                js(dialog+'.open()');capture(dialog);assert js(dialog+'.visible');js(dialog+'.close()')
            for step in range(7):
                js(f'onboardingDialog.step={step};onboardingDialog.open()');capture('guide-'+str(step));js('onboardingDialog.close()')
            toggle=window.findChild(QObject,'themeToggle')
            assert window.findChild(QObject,'appearanceDialog') is None
            for keyboard in (False,True):
                before=backend.theme
                expected='dark' if before=='light' else 'light'
                expected_label=({'dark':'夜间模式','light':'日间模式'} if args.language=='zh' else {'dark':'Dark mode','light':'Light mode'})[expected]
                assert toggle.property('text')==expected_label
                if keyboard:
                    toggle.forceActiveFocus(Qt.TabFocusReason);QTest.keyClick(window,Qt.Key_Space)
                else:
                    point=toggle.mapToScene(QPointF(toggle.width()/2,toggle.height()/2)).toPoint()
                    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point)
                QTest.qWait(180)
                assert backend.theme==expected and window.property('darkMode')==(expected=='dark')
                assert persist.call_args.args[0]=={'theme':expected}
                capture('theme-keyboard' if keyboard else 'theme-mouse')
            assert backend.bridge is None
        finally:backend.shutdown();shiboken6.delete(engine)
    assert not errors,errors
    (args.output/'results.json').write_text(json.dumps(dict(checks=checks,qml_errors=errors,mode='offline demo; no game files or device output'),indent=2),encoding='utf-8')
    print(f'Passed {len(checks)} dialog and preference scenarios')
if __name__=='__main__':main()

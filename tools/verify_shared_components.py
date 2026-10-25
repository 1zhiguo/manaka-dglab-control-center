"""Render shared control states and exercise real mouse/keyboard/dialog behavior."""
import argparse
import json
import os
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE','Basic')
os.environ.setdefault('QT_QUICK_BACKEND','software')
from PySide6.QtCore import QObject, QPointF, Qt, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
import shiboken6

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    errors=[];checks=[]
    qInstallMessageHandler(lambda kind,ctx,text: errors.append(text) if any(x in text for x in ('TypeError','ReferenceError','Cannot assign','Binding loop','failed to load','is not a type','recursive')) else None)
    app=QGuiApplication([])
    for font in ['msyh.ttc','segoeui.ttf']: QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
    engine=QQmlApplicationEngine();engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('fixtures')/'ComponentGallery.qml')))
    assert engine.rootObjects(),errors
    window=engine.rootObjects()[0]
    window.requestActivate();QTest.qWait(150)
    def find(name):
        result=window.findChild(QObject,name);assert result is not None,name;return result
    def js(obj,expression):
        exp=QQmlExpression(engine.contextForObject(obj),obj,expression);value=exp.evaluate()[0];assert not exp.hasError(),exp.error().toString();return value
    def center(item):return item.mapToScene(QPointF(item.width()/2,item.height()/2)).toPoint()
    def click(item):QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,center(item));QTest.qWait(70)
    def capture(name):
        QTest.qWait(100);assert window.grabWindow().save(str(args.output/(name+'.png')))
    try:
        for lang in ['zh','en']:
            for dark in [False,True]:
                window.setProperty('language',lang);window.setProperty('dark',dark);QTest.qWait(160)
                prefix=lang+('-dark' if dark else '-light')
                capture(prefix+'-normal-disabled-error')
                button=find('primary');QTest.mouseMove(window,center(button));QTest.qWait(80)
                assert button.property('hovered');capture(prefix+'-hover')
                QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,center(button));assert button.property('down');capture(prefix+'-pressed')
                QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,center(button))
                button.setProperty('focus',False);button.forceActiveFocus(Qt.TabFocusReason);QTest.qWait(30)
                assert button.property('visualFocus');capture(prefix+'-focus')
                # Real Tab traversal must reach enabled controls, skip disabled siblings.
                QTest.keyClick(window,Qt.Key_Tab);assert not button.property('activeFocus')
                check=find('check');check.forceActiveFocus(Qt.TabFocusReason)
                before=check.property('checked');QTest.keyClick(window,Qt.Key_Space);assert check.property('checked') != before
                for name in ['toggle','master']:
                    toggle=find(name);toggle.forceActiveFocus(Qt.TabFocusReason);before=toggle.property('checked')
                    QTest.keyClick(window,Qt.Key_Space);assert toggle.property('checked') != before
                    assert js(toggle,'Accessible.name.length')>0
                field=find('search');click(field);[QTest.keyClick(window,c) for c in 'heart'];assert field.property('text')=='heart'
                click(find('searchClear'));assert field.property('text')==''
                choice=find('choice');choice.forceActiveFocus(Qt.TabFocusReason);QTest.keyClick(window,Qt.Key_Down);assert choice.property('currentIndex')==1
                # Reset to also test the popup on every theme.
                choice.setProperty('currentIndex',0);click(choice);assert js(choice,'popup.visible');capture(prefix+'-choice');QTest.keyClick(window,Qt.Key_Escape)
                number=find('numberInput');click(number);QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier);[QTest.keyClick(window,c) for c in '175']
                assert window.property('enteredValue')==175
                click(find('dialogButton'));dialog=find('confirmation');assert dialog.property('visible')
                assert js(dialog,'footer.count')==2
                capture(prefix+'-dialog')
                # Standard buttons must close and emit the acceptance signal once.
                ok=js(dialog,'standardButton(Dialog.Ok)');assert ok is not None
                previous=window.property('acceptedCount');click(ok)
                assert not dialog.property('visible') and window.property('acceptedCount')==previous+1
                checks.append(prefix+' states, keyboard, search, combo, number and standard dialog acceptance')
    finally:shiboken6.delete(engine)
    assert not errors,errors
    (args.output/'results.json').write_text(json.dumps(dict(checks=checks,qml_errors=errors),indent=2),encoding='utf-8')
    print(f'Passed {len(checks)} component suites')
if __name__=='__main__':main()

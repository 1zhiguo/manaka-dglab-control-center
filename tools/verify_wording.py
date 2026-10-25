"""Check finalized labels, live dialog language and unchanged waveform data."""
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
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from qml_dashboard_prototype import backend as module
import shiboken6

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    errors=[];checks=[]
    qInstallMessageHandler(lambda kind,ctx,text:errors.append(text) if any(x in text for x in ('TypeError','ReferenceError','Cannot assign','Binding loop','failed to load','recursive')) else None)
    app=QGuiApplication([])
    for font in ['msyh.ttc','segoeui.ttf']:QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
    with tempfile.TemporaryDirectory() as directory,patch.object(module,'app_data_dir',return_value=Path(directory)),patch.object(module,'load_config',return_value={'theme':'light'}),patch.object(module,'update_config'):
        backend=module.ControlCenterBackend(demo=True,language='zh');backend.agreement_accepted_value=True
        engine=QQmlApplicationEngine();engine.rootContext().setContextProperty('backend',backend);engine.rootContext().setContextProperty('initialPageIndex',10)
        engine.load(QUrl.fromLocalFile(str(Path(module.__file__).with_name('ControlCenter.qml'))));assert engine.rootObjects(),errors
        window=engine.rootObjects()[0];window.setWidth(1120);window.setHeight(720);window.requestActivate();QTest.qWait(150)
        def find(name):
            obj=window.findChild(QObject,name);assert obj is not None,name;return obj
        def js(obj,expr):
            e=QQmlExpression(engine.contextForObject(obj),obj,expr);v=e.evaluate()[0];assert not e.hasError(),e.error().toString();return v
        def click(button):
            point=button.mapToScene(QPointF(button.width()/2,button.height()/2)).toPoint()
            QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,point);QTest.qWait(60)
        def standard(dialog,code):return js(dialog,f'standardButton({js(window,"Dialog."+code)})')
        def capture(name):
            QTest.qWait(150);assert window.grabWindow().save(str(args.output/(name+'.png')))
        try:
            studio=find('gameplaySettings');library=find('waveWorkbench')
            js(studio,'pendingMode="legacy_v1";confirmMode()');QTest.qWait(80)
            assert find('legacyStart').property('label')=='最低心率（BPM）'
            assert find('legacyFull').property('label')=='最高心率（BPM）'
            assert find('legacyWaveMode').property('displayText')=='自动切换波形'
            capture('zh-original');checks.append('final Original heart-rate and mode labels')
            # The actual window-close path must preserve or discard the same draft.
            js(studio,'edit(draft.mapping.legacy,"trigger_bpm",91)')
            before=js(studio,'JSON.stringify(draft)');window.close();QTest.qWait(100)
            discard=find('discardGameplayChanges');assert discard.property('visible')
            for language,keep,drop in [('zh','继续编辑','放弃修改'),('en','Keep editing','Discard changes'),('zh','继续编辑','放弃修改')]:
                backend.setLanguage(language);QTest.qWait(100)
                assert standard(discard,'Cancel').property('text')==keep
                assert standard(discard,'Discard').property('text')==drop
                capture(language+'-unsaved')
            click(standard(discard,'Cancel'))
            assert window.isVisible() and not discard.property('visible')
            assert js(studio,'JSON.stringify(draft)')==before and studio.property('dirty')
            js(studio,'reload()');checks.append('unsaved close prompt translates live; Keep editing retains the draft')
            # Verify the same Cancel/Discard wording in the waveform editor.
            wave_discard=find('discardWorkbenchChanges');js(wave_discard,'open()');QTest.qWait(60)
            assert standard(wave_discard,'Cancel').property('text')=='继续编辑'
            assert standard(wave_discard,'Discard').property('text')=='放弃修改'
            js(wave_discard,'close()')
            # Exercise every requested standard type in a single diagnostic dialog.
            js(window,'progressConfirm.width=1000;progressConfirm.standardButtons=Dialog.Close|Dialog.Ok|Dialog.Yes|Dialog.No|Dialog.Cancel|Dialog.Discard;progressConfirm.open()')
            for language,labels in [('zh',['关闭','确认','确认','取消','取消','放弃修改']),('en',['Close','Confirm','Confirm','Cancel','Cancel','Discard changes']),('zh',['关闭','确认','确认','取消','取消','放弃修改'])]:
                backend.setLanguage(language);QTest.qWait(100)
                for code,label in zip(['Close','Ok','Yes','No','Cancel','Discard'],labels):
                    assert js(window,f'progressConfirm.standardButton(Dialog.{code}).text')==label,(language,code)
                capture(language+'-standard-buttons')
            js(window,'progressConfirm.close()');checks.append('Close/OK/Yes/No/Cancel/Discard follow application language while open')
            # Context-specific delete confirmation must retain its action role.
            delete=find('deleteWaveConfirm');js(delete,'open()');QTest.qWait(60)
            assert standard(delete,'Ok').property('text')=='删除'
            assert standard(delete,'Cancel').property('text')=='取消'
            js(delete,'close()')
            checks.append('destructive confirmation says Delete rather than a generic affirmative')
            # The alias affects only the built-in key, never imported names/frames.
            for language in ['zh','en']:
                backend.setLanguage(language)
                raw=module.PRESETS['climax'];asset=backend.waveAsset('climax')
                assert asset['name']=='Climax' and asset['framesText'].splitlines()==list(raw.v3_frames())
                assert raw.name=='Climax 双击'
                backend.current_wave_a=raw;backend.current_wave_b=raw
                assert backend.waveAName==backend.waveBName=='Climax'
            checks.append('Climax display alias retains the preset key, raw name and every V3 frame')
            exported=Path(directory)/'climax.json'
            assert backend.exportWaveAsset('climax',str(exported))['ok']
            data=json.loads(exported.read_text(encoding='utf-8'))
            assert data['name']==raw.name and data['frames']==list(raw.v3_frames())
            custom=backend.saveWaveAsset('',raw.name,'Test','\n'.join(raw.v3_frames()))
            assert custom['ok']
            assert backend.waveAsset(custom['key'])['name']==raw.name
            checks.append('export retains stored name and frames; imported same-name assets are not renamed')
            assert backend.bridge is None
        finally:backend.shutdown();shiboken6.delete(engine)
    assert not errors,errors
    (args.output/'results.json').write_text(json.dumps(dict(checks=checks,qml_errors=errors),ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Passed {len(checks)} wording and compatibility scenarios')
if __name__=='__main__':main()

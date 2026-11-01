"""Exercise actual QML drafts, keyboard input and save/discard dialogs offline."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE","Basic")
os.environ.setdefault("QT_QUICK_BACKEND","software")
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"python"))
from PySide6.QtCore import QObject, QMetaObject, QUrl, Qt, Q_ARG, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QFontDatabase, QInputMethodEvent
from PySide6.QtQml import QQmlApplicationEngine, QQmlEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from qml_dashboard_prototype import backend as module
import shiboken6


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--language",default="en")
    parser.add_argument("--qml-root",type=Path)
    parser.add_argument("--theme",default="dark")
    args=parser.parse_args()
    errors=[]
    checks=[]
    def message(kind,context,text):
        if any(word in text for word in ("TypeError","ReferenceError","Cannot assign","Binding loop")):
            errors.append(text)
    qInstallMessageHandler(message)
    app=QGuiApplication([])
    for font in ("msyh.ttc","segoeui.ttf","seguisym.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/"+font)
    with tempfile.TemporaryDirectory() as directory, patch.object(module,"app_data_dir",return_value=Path(directory)), patch.object(module,"load_config",return_value={"trigger_bpm":90,"output_max":30,"theme":args.theme}):
        backend=module.ControlCenterBackend(demo=True,language=args.language)
        backend.agreement_accepted_value=True
        engine=QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend",backend)
        engine.rootContext().setContextProperty("initialPageIndex",2)
        engine.load(QUrl.fromLocalFile(str((args.qml_root or Path(module.__file__).parent)/"ControlCenter.qml")))
        assert engine.rootObjects(),"QML failed to load"
        window=engine.rootObjects()[0]
        def find(name):
            found=window.findChild(QObject,name)
            if found is None:
                stack=[window.contentItem()]
                while stack:
                    item=stack.pop()
                    if item.objectName()==name:
                        return item
                    stack.extend(item.childItems())
            assert found is not None,name
            return found
        def invoke(item,method,*args):
            assert QMetaObject.invokeMethod(item,method,*args),method
            QTest.qWait(30)
        find("navItem1").forceActiveFocus()
        QTest.keyClick(window,Qt.Key_Space)
        QTest.qWait(30)
        assert window.property("pageIndex") == 1
        checks.append("sidebar navigation works with keyboard focus and Space")
        window.setProperty("pageIndex",2)
        editor=find("channelEditor")
        def js(source):
            expression=QQmlExpression(QQmlEngine.contextForObject(editor),editor,source)
            result=expression.evaluate()[0]
            assert not expression.hasError(),expression.error().toString()
            QTest.qWait(20)
            return result
        studio=find("gameplaySettings")
        library=find("waveWorkbench")
        def wjs(source, target=None):
            target=target or studio
            expression=QQmlExpression(QQmlEngine.contextForObject(target),target,source)
            result=expression.evaluate()[0]
            assert not expression.hasError(),expression.error().toString()
            QTest.qWait(30)
            return result
        def capture(name):
            target=args.output.parent/(name+".png")
            target.parent.mkdir(parents=True,exist_ok=True)
            QTest.qWait(100)
            assert window.grabWindow().save(str(target))
        try:
            assert not editor.property("dirty")
            assert not find("saveChannels").property("enabled")
            assert window.findChild(QObject,"sourceChoiceA0") is None
            checks.append("intensity editor has no source or waveform selectors")
            window.setProperty("pageIndex",10)
            assert not studio.property("modeConfirmed")
            original_card=find("chooseGameplaylegacy_v1")
            original_name=wjs("modelData.name",original_card)
            assert ("Original" if args.language=="en" else "原版") in original_name
            assert find("gameplayChooser").property("visible")
            assert not find("confirmGameplay").property("enabled")
            invoke(find("chooseGameplayindependent"),"clicked")
            assert backend.channelSettings["mode"] == "legacy_v1"
            invoke(find("confirmGameplay"),"clicked")
            assert studio.property("modeConfirmed")
            tabs=find("gameplayTabs")
            assert tabs.property("visible")
            checks.append("new sidebar page requires explicit choice and confirmation before editing")
            tabs.setProperty("currentIndex",2)
            invoke(find("donorTemplate"),"clicked")
            assert wjs("draft.mapping.mode") == "independent"
            assert backend.channelSettings["mode"] == "legacy_v1"
            capture("workbench-bindings")
            invoke(find("saveWorkbench"),"clicked")
            assert backend.channelSettings["mode"] == "independent"
            assert backend.channelSettings["A"]["bindings"][0]["source"] == "device"
            assert backend.channelSettings["B"]["bindings"][0]["source"] == "device"
            assert backend.channelSettings["A"]["device"] == "vibrator"
            assert backend.channelSettings["B"]["device"] == "piston"
            checks.append("workbench template applies only on save and uses donor channel sources")
            # Use actual control events: mutating the draft in JS would hide
            # detached Repeater modelData and destruction-on-keystroke bugs.
            def choose(name,index):
                control=find(name)
                control.forceActiveFocus()
                QTest.keyClick(window,Qt.Key_Home)
                for _ in range(index): QTest.keyClick(window,Qt.Key_Down)
                QTest.qWait(50)
            choose("intensitySourceA0",2)
            assert wjs("draft.mapping.A.bindings[0].source") == "heart"
            entry=find("sourceFullA0Input").property("contentItem")
            entry.forceActiveFocus()
            QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier)
            for key in (Qt.Key_1,Qt.Key_7,Qt.Key_5): QTest.keyClick(window,key)
            assert wjs("draft.mapping.A.bindings[0].high") == 175
            choose("boundDeviceA",1)
            find("channelEnabledA").forceActiveFocus()
            QTest.keyClick(window,Qt.Key_Space)
            assert wjs("draft.mapping.A.enabled") is False
            assert wjs("draft.mapping.A.bindings[0].high") == 175
            backend.configChanged.emit(); QTest.qWait(50)
            assert wjs("draft.mapping.A.bindings[0].source") == "heart"
            assert wjs("draft.mapping.A.device") == "piston"
            assert studio.property("dirty")
            invoke(find("saveWorkbench"),"clicked")
            assert backend.channelSettings["A"]["bindings"][0]["high"] == 175
            assert backend.channelSettings["A"]["device"] == "piston"
            assert not backend.channelSettings["A"]["enabled"]
            assert not studio.property("dirty") and not studio.property("failed")
            checks.append("actual detection edits survive later controls and config signals and save cleanly")
            invoke(find("donorTemplate"),"clicked")
            wjs("edit(draft.mapping.A,'enabled',true)")
            invoke(find("saveWorkbench"),"clicked")
            choose("boundDeviceA",2)
            invoke(find("saveWorkbench"),"clicked")
            assert studio.property("failed") and studio.property("dirty")
            choose("intensitySourceA0",2)
            invoke(find("saveWorkbench"),"clicked")
            assert not studio.property("failed") and not studio.property("dirty")
            assert backend.channelSettings["A"]["device"] == "none"
            checks.append("correcting an invalid binding clears the error and saves without losing edits")
            invoke(find("donorTemplate"),"clicked")
            invoke(find("saveWorkbench"),"clicked")
            window.setProperty("pageIndex",2)
            assert editor.property("independent")
            spin=find("A-maximumInput")
            entry=spin.property("contentItem")
            entry.forceActiveFocus()
            QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier)
            QTest.keyClick(window,Qt.Key_2)
            QTest.keyClick(window,Qt.Key_4)
            QTest.qWait(30)
            assert js("draft.A.maximum") == 24
            invoke(find("saveChannels"),"clicked")
            assert backend.channelSettings["A"]["maximum"] == 24
            assert not editor.property("dirty")
            capture("strength-only")
            checks.append("typed strength saves on first click without Enter or Tab")
            js("edit(draft.A,'minimum',90)")
            assert editor.property("validationError")
            assert not find("saveChannels").property("enabled")
            invoke(find("reloadChannels"),"clicked")
            checks.append("invalid intensity range cannot be saved")
            js("edit(draft.A,'hard_cap',40)")
            invoke(find("saveChannels"),"clicked")
            confirmation=find("capConfirmation")
            assert confirmation.property("visible")
            invoke(confirmation,"reject")
            assert backend.channelSettings["A"]["hard_cap"] == 30
            invoke(find("saveChannels"),"clicked")
            invoke(confirmation,"accept")
            assert backend.channelSettings["A"]["hard_cap"] == 40
            checks.append("hard cap increase keeps the existing confirmation")
            js("edit(draft.A,'hard_cap',200); edit(draft.B,'hard_cap',160); edit(draft.A,'maximum',180)")
            assert not editor.property("validationError")
            invoke(find("saveChannels"),"clicked")
            invoke(confirmation,"accept")
            assert backend.channelSettings["A"]["hard_cap"] == 200
            assert backend.channelSettings["A"]["maximum"] == 180
            assert backend.channelSettings["B"]["hard_cap"] == 160
            checks.append("independent caps and ordinary strength accept values through 200")
            js("edit(draft.A,'maximum',24)")
            invoke(find("saveChannels"),"clicked")
            window.setProperty("pageIndex",10)
            tabs.setProperty("currentIndex",0)
            invoke(find("addWaveRule"),"clicked")
            wjs("edit(rule,'source','piston'); edit(rule,'value','medium'); edit(rule,'wave','official_tide'); edit(rule,'priority',60)")
            capture("workbench-A-rule")
            invoke(find("saveWorkbench"),"clicked")
            assert backend.wave_policy.A.rules[-1].value == "medium"
            assert backend.wave_policy.A.rules[-1].wave == "official_tide"
            assert backend.channelSettings["A"]["maximum"] == 24
            checks.append("A rule save retains intensity calibration")
            tabs.setProperty("currentIndex",1)
            invoke(find("addWaveRule"),"clicked")
            wjs("edit(rule,'source','climax'); edit(rule,'duration_ms',2000); edit(rule,'enabled',false)")
            capture("workbench-B-event")
            invoke(find("saveWorkbench"),"clicked")
            assert backend.wave_policy.B.rules[-1].enabled is False
            checks.append("B event editor saves independently")
            tabs.setProperty("currentIndex",0)
            invoke(find("addWaveRule"),"clicked")
            wjs("edit(rule,'source','action'); openActions('rule')")
            assert find("actionPicker").property("visible")
            find("actionSearch").setProperty("text","Dogeza")
            QTest.qWait(80)
            check=find("actionChoiceDogeza")
            assert check.property("text")
            if args.language == "zh":
                assert any('\u4e00'<=c<='\u9fff' for c in check.property("text"))
            check.forceActiveFocus()
            QTest.keyClick(window,Qt.Key_Space)
            QTest.qWait(40)
            assert check.property("checked")
            capture("localized-action-picker")
            invoke(find("applyActionChoices"),"clicked")
            invoke(find("saveWorkbench"),"clicked")
            assert backend.wave_policy.A.rules[-1].value == "Dogeza"
            checks.append("localized searchable action picker preserves stable action keys")
            wjs("edit(draft.policy.A,'default_wave','official_tide')")
            independent_rules=wjs("JSON.stringify(draft.policy)")
            invoke(find("reselectGameplay"),"clicked")
            assert find("gameplayChooser").property("visible")
            invoke(find("chooseGameplaylegacy_v1"),"clicked")
            invoke(find("confirmGameplay"),"clicked")
            assert not tabs.property("visible")
            assert find("legacyWaveMode").property("visible")
            assert wjs("JSON.stringify(draft.policy)") == independent_rules
            checks.append("reselect preserves unsaved independent rules and shows only legacy settings")
            capture("legacy-gameplay")
            invoke(find("saveWorkbench"),"clicked")
            assert backend.channelSettings["mode"] == "legacy_v1"
            wjs("edit(draft.legacy_wave,'fixed','donor_piston'); edit(draft.legacy_wave,'mode','fixed')")
            invoke(find("saveWorkbench"),"clicked")
            assert backend.legacyWaveSettings["fixed"] == "donor_piston"
            checks.append("legacy mode and its separate waveform configuration save")
            legacy_entry=find("legacyStartInput").property("contentItem")
            legacy_entry.forceActiveFocus()
            QTest.keyClick(window,Qt.Key_A,Qt.ControlModifier)
            QTest.keyClick(window,Qt.Key_9); QTest.keyClick(window,Qt.Key_8)
            assert wjs("draft.mapping.legacy.trigger_bpm") == 98
            invoke(find("reselectGameplay"),"clicked")
            invoke(find("chooseGameplayindependent"),"clicked")
            invoke(find("confirmGameplay"),"clicked")
            assert wjs("draft.legacy_wave.fixed") == "donor_piston"
            assert wjs("draft.mapping.legacy.trigger_bpm") == 98
            assert wjs("JSON.stringify(draft.policy)") == independent_rules
            window.setProperty("pageIndex",3)
            assert studio.property("dirty")
            assert window.findChild(QObject,"workbenchTabs") is None
            window.setProperty("pageIndex",10)
            assert studio.property("modeConfirmed") and studio.property("independent")
            checks.append("unsaved legacy edits survive changing mode and sidebar navigation")
            tabs.setProperty("currentIndex",2)
            invoke(find("donorTemplate"),"clicked")
            invoke(find("saveWorkbench"),"clicked")
            # A draft on the other page must not silently overwrite the changed routing.
            assert backend.channelSettings["legacy"]["trigger_bpm"] == 98
            js("edit(draft.B,'maximum',18)")
            wjs("edit(draft.mapping.B.bindings[0],'source','heart')")
            invoke(find("saveWorkbench"),"clicked")
            assert not js("applyChanges(false)")
            assert backend.channelSettings["B"]["bindings"][0]["source"] == "heart"
            invoke(find("reloadChannels"),"clicked")
            checks.append("stale intensity draft cannot overwrite a saved routing change")
            # Exercise the full-frame editor and copy, without opening a native file picker.
            window.setProperty("pageIndex",3)
            field=find("waveSearch")
            field.forceActiveFocus()
            event=QInputMethodEvent();event.setCommitString("呼吸")
            QGuiApplication.sendEvent(window,event);QTest.qWait(80)
            assert field.property("text") == "呼吸"
            assert 0 < find("waveLibraryList").property("count") < len(backend.waveAssets)
            capture("search-checkbox-alignment")
            invoke(find("waveSearchClear"),"clicked")
            assert field.property("text") == ""
            assert find("waveLibraryList").property("count") == len(backend.waveAssets)
            favorite=find("waveFavorites");favorite.forceActiveFocus()
            QTest.keyClick(window,Qt.Key_Space);QTest.qWait(30)
            assert favorite.property("checked")
            assert find("waveLibraryList").property("count") == 0
            QTest.keyClick(window,Qt.Key_Space);QTest.qWait(30)
            assert not favorite.property("checked")
            checks.append("Chinese search input, clear button and favorites checkbox filter correctly")
            result=backend.duplicateWaveAsset("official_tease2")
            assert result["ok"],result
            library.setProperty("selectedAsset",result["key"])
            wjs("openAssetEditor()",library)
            capture("workbench-raw-editor")
            assert find("waveAssetEditor").property("visible")
            assert len(find("waveRawFrames").property("text").splitlines()) == 82
            invoke(find("waveAssetEditor"),"reject")
            checks.append("full 82-frame waveform opens without truncation in styled modal")
            wjs("edit(draft.policy.A,'default_wave','official_tide')")
            window.setProperty("pageIndex",0)
            window.close();QTest.qWait(30)
            assert window.isVisible() and find("discardGameplayChanges").property("visible")
            invoke(find("discardGameplayChanges"),"reject")
            assert not window.property("pendingWindowClose")
            checks.append("unsaved workbench draft prevents accidental window close")
            wjs("reload()")
            window.setProperty("pageIndex",2)
            js("edit(draft.B,'maximum',19)")
            invoke(find("closeChannels"),"clicked")
            assert find("discardChannelChanges").property("visible")
            invoke(find("keepChannelEdits"),"clicked")
            assert editor.property("dirty")
            invoke(find("closeChannels"),"clicked")
            invoke(find("discardChannelEdits"),"clicked")
            assert not editor.property("dirty")
            checks.append("strength draft keep/discard behavior is preserved")
        finally:
            backend.shutdown()
            shiboken6.delete(engine)
    assert not errors,errors
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(dict(checks=checks,qml_errors=errors,mode="isolated offline demo"),indent=2),encoding="utf-8")
    print(f"Passed {len(checks)} QML interaction scenarios")


if __name__=="__main__":
    main()

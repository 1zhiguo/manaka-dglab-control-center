"""Isolated QML preview. No Socket servers, telemetry or real config writes."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch, MagicMock
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from PySide6.QtCore import QTimer, QUrl, QObject, QMetaObject, Q_ARG
from PySide6.QtGui import QGuiApplication, QFont, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from qml_dashboard_prototype import backend as module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", type=int, default=4)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--theme", default="dark")
    parser.add_argument("--protocol", default="v3")
    parser.add_argument("--width", type=int, default=1320)
    parser.add_argument("--height", type=int, default=840)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hud", action="store_true")
    parser.add_argument("--independent", action="store_true")
    parser.add_argument("--exercise", action="store_true")
    parser.add_argument("--hud-custom", action="store_true")
    parser.add_argument("--wave-editor", action="store_true")
    parser.add_argument("--wave-picker", action="store_true")
    parser.add_argument("--protocol-picker", action="store_true")
    parser.add_argument("--connected", action="store_true", help="Mock UI success states; polling stopped, no sockets")
    parser.add_argument("--blocked", action="store_true", help="Show an accessory error toast from mock state")
    parser.add_argument("--strategy", choices=("sync", "action", "random", "fixed"))
    parser.add_argument("--game-running", action="store_true", help="Mock a running process without live telemetry")
    parser.add_argument("--standby", action="store_true", help="Mock enabled V4 devices waiting for the game; no output")
    parser.add_argument("--pulse-sources", choices=("heart,heart","action,action","heart,action","action,heart"))
    parser.add_argument("--pulse-dialog", choices=("heart","action"))
    parser.add_argument("--pulse-fixed", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    app = QGuiApplication([])
    # The offscreen platform does not enumerate Windows system fonts.
    font_root = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for font in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf", "seguisym.ttf"):
        QFontDatabase.addApplicationFont(str(font_root / font))
    app.setFont(QFont("Microsoft YaHei UI", 10))
    with tempfile.TemporaryDirectory(prefix="manaka-v4-ui-") as tmp, patch.object(module, "app_data_dir", return_value=Path(tmp)), patch.object(module, "load_config", return_value={"language": args.language, "theme": args.theme}):
        backend = module.ControlCenterBackend(demo=True, language=args.language)
        if backend.hud_socket:
            backend.hud_socket.close()
        backend.hud_socket = None
        backend.socket_protocol = args.protocol
        if args.connected or args.blocked or args.game_running or args.standby:
            # Mock only: constructor used demo=True so no server was started.
            # Stop its timer before changing display state; never call runtime.
            backend.poll_timer.stop()
            backend.demo_mode = False
            backend.socket_protocol = "v4"
            backend.v4_hub = MagicMock(app_connected=True, server_ready=True)
            backend.bridge = MagicMock()
            backend.device_connected_value = backend.ovc_connected = True
            backend.auto_output_enabled = backend.ovc_enabled = not args.blocked
            backend.last_receive = time.monotonic()
            backend.telemetry_status_value = "实时连接"
            backend.game_status_value = "游戏、BepInEx 和独立遥测插件均已就绪"
            if args.standby:
                backend.last_receive = 0
                backend.auto_output_enabled = backend.ovc_enabled = True
                backend.coyote_waiting_for_game = backend.ovc_waiting_for_game = True
                backend.device_status_value = "已启用 · 等待游戏数据 · 输出为 0"
                snapshots, routes = [], {}
                for role, kind, cap in (("coyote","COYOTE_030",60),("ovc","OVC_1",200)):
                    snapshot = {"clientId":"preview", "slotId":role, "name":role.upper(), "type":kind, "selected":True,
                        "props":{"connectState":"connected", "intensityA":0,"intensityB":0},
                        "slotState":{"hasDevice":True,"channelA":{"intensityMax":cap},"channelB":{"intensityMax":cap}},
                        "channelAReason":"", "channelBReason":""}
                    snapshots.append(snapshot)
                    route = MagicMock(selected_slot_id=role,selected_client_id="preview",connected=True)
                    route.devices_snapshot.return_value = [snapshot]
                    routes[role] = route
                backend.v4_hub.devices_snapshot.return_value = snapshots
                backend.v4_hub.channel.side_effect = routes.__getitem__
                backend.bridge = routes["coyote"]
            backend.game_running_value = args.connected or args.game_running
            if args.game_running:
                backend.last_receive = 0
                backend.auto_output_enabled = backend.ovc_enabled = False
                backend.device_connected_value = backend.ovc_connected = False
                backend.v4_hub.app_connected = False
            if args.blocked:
                route = backend.v4_hub.channel.return_value
                route.selected_slot_id = "ovc"
                route.devices_snapshot.return_value = [{"selected": True, "slotState": {}, "channelAReason": "accessory-not-inserted", "channelBReason": "accessory-not-inserted"}]
        if args.independent:
            backend.ovc_profile["mode"] = "independent"
            backend.ovc_profile["channels"]["A"]["mode"] = "action"
        engine = QQmlApplicationEngine()
        warnings = []
        callback_errors = []
        engine.warnings.connect(lambda items: warnings.extend(str(item.toString()) for item in items))
        engine.rootContext().setContextProperty("backend", backend)
        engine.rootContext().setContextProperty("initialPageIndex", args.page)
        engine.load(QUrl.fromLocalFile(str(ROOT / "python/qml_dashboard_prototype/ControlCenter.qml")))
        if not engine.rootObjects():
            raise RuntimeError("QML could not load: " + str(warnings))
        window = engine.rootObjects()[0]
        window.setWidth(args.width)
        window.setHeight(args.height)
        if args.pulse_sources:
            page = window.findChild(QObject,"pulseWorkbenchPage")
            assert page is not None
            def find_visual(item,name):
                if item.objectName()==name:
                    return item
                for child in item.childItems():
                    found = find_visual(child,name)
                    if found is not None:
                        return found
                return None
            for channel,source in zip(("A","B"),args.pulse_sources.split(",")):
                selector = find_visual(QQuickWindow.contentItem(window),"pulseSource"+channel)
                assert selector is not None
                index = 0 if source=="heart" else 1
                selector.setProperty("currentIndex",index)
                assert QMetaObject.invokeMethod(selector,"activated",Q_ARG(int,index))
            assert QMetaObject.invokeMethod(page,"saveStrategy")
            assert backend.pulseChannelSources == dict(zip(("A","B"),args.pulse_sources.split(",")))
            if args.pulse_fixed:
                page.setProperty("draftMode","fixed")
            if args.pulse_dialog:
                channel = "A" if args.pulse_sources.split(",")[0]==args.pulse_dialog else "B"
                QTimer.singleShot(300, lambda: QMetaObject.invokeMethod(page,"openSourceMapping",Q_ARG("QVariant",channel)))
        if args.hud or args.hud_custom:
            dialog = window.findChild(QObject, "hudSettingsDialog")
            if dialog is None:
                raise RuntimeError("HUD dialog not found")
            def open_hud():
                QMetaObject.invokeMethod(dialog, "openSettings")
                if args.hud_custom:
                    for key, value in (("anchor", "custom"), ("x", 75), ("y", 20), ("scale", 80), ("show_a", False)):
                        QMetaObject.invokeMethod(dialog, "change", Q_ARG("QVariant", key), Q_ARG("QVariant", value))
            QTimer.singleShot(300, open_hud)
        if args.exercise:
            page = window.findChild(QObject, "ovcWorkbenchPage")
            assert page is not None
            QMetaObject.invokeMethod(page, "change", Q_ARG("QVariant", "mode"), Q_ARG("QVariant", "independent"))
            QMetaObject.invokeMethod(page, "setPolicy", Q_ARG("QVariant", "mode"), Q_ARG("QVariant", "action"))
            first_action = backend.ovcActions[0]["key"]
            QMetaObject.invokeMethod(page, "setRule", Q_ARG("QVariant", first_action), Q_ARG("QVariant", "mode"), Q_ARG("QVariant", "wave"))
            draft = page.property("draft").toVariant()
            assert draft["channels"]["A"]["actions"][first_action]["mode"] == "wave"
            for category in ("sync", "custom"):
                QMetaObject.invokeMethod(page, "selectCategory", Q_ARG("QVariant", category))
            draft = page.property("draft").toVariant()
            assert draft["channels"]["A"]["mode"] == "action"
            assert draft["channels"]["A"]["actions"][first_action]["mode"] == "wave"
            page.setProperty("channel", "B")
            QMetaObject.invokeMethod(page, "setPolicy", Q_ARG("QVariant", "mode"), Q_ARG("QVariant", "fixed"))
            for category in ("sync", "custom"):
                QMetaObject.invokeMethod(page, "selectCategory", Q_ARG("QVariant", category))
            draft = page.property("draft").toVariant()
            assert draft["channels"]["B"]["mode"] == "fixed"
            assert draft["channels"]["A"]["mode"] == "action"
            page.setProperty("channel", "A")
            QMetaObject.invokeMethod(page, "saveProfile")
            assert page.property("saveFeedback")
            assert not page.property("dirty")
            QMetaObject.invokeMethod(page,"change",Q_ARG("QVariant","low"),Q_ARG("QVariant",0))
            assert page.property("dirty")
            assert page.property("saveFeedback") == ""
            QMetaObject.invokeMethod(page,"saveProfile")
            assert page.property("saveFeedback")
            def verify_feedback_expired():
                if page.property("saveFeedback") != "":
                    callback_errors.append("Save success feedback did not expire")
            QTimer.singleShot(2900, verify_feedback_expired)
            assert not backend.ovc_enabled  # UI/save never auto-arms devices.
        if args.wave_editor:
            editor = window.findChild(QObject, "ovcWaveEditor")
            assert editor is not None
            QTimer.singleShot(300, lambda: QMetaObject.invokeMethod(editor, "openEditor", Q_ARG("QVariant", "ovc_breathe")))
        if args.strategy or args.wave_picker:
            def open_strategy():
                page = window.findChild(QObject, "ovcWorkbenchPage")
                QMetaObject.invokeMethod(page, "change", Q_ARG("QVariant", "mode"), Q_ARG("QVariant", "independent"))
                QMetaObject.invokeMethod(page, "setPolicy", Q_ARG("QVariant", "mode"), Q_ARG("QVariant", args.strategy or "action"))
                QMetaObject.invokeMethod(page, "openChannel", Q_ARG("QVariant", "A"))
            QTimer.singleShot(250, open_strategy)
        if args.wave_picker or args.protocol_picker:
            name = "ovcActionPicker_" + backend.ovcActions[0]["key"] if args.wave_picker else "connectionProtocolChoice"
            def open_picker():
                try:
                    def visual_find(item):
                        if item.objectName() == name:
                            return item
                        for child in item.childItems():
                            found = visual_find(child)
                            if found is not None:
                                return found
                        return None
                    picker = window.findChild(QObject, name)
                    if picker is None:
                        picker = visual_find(QQuickWindow.contentItem(window))
                    assert picker is not None, name
                    assert QMetaObject.invokeMethod(picker, "openChoices")
                except Exception as error:
                    callback_errors.append(str(error))
            QTimer.singleShot(500, open_picker)
        if args.connected:
            def refresh_mock_display():
                backend.last_receive = time.monotonic()
                backend.devicesChanged.emit()
                backend.statusChanged.emit()
            refresh = QTimer()
            refresh.timeout.connect(refresh_mock_display)
            refresh.start(150)
        if args.blocked:
            QTimer.singleShot(500, lambda: backend.explainDeviceBlock("ovc"))
        captures = []

        def capture():
            result = QQuickWindow.contentItem(window).grabToImage()
            captures.append(result)

            def save():
                if not result.saveToFile(str(args.output)):
                    raise RuntimeError("Screenshot failed")
                app.quit()
            result.ready.connect(save)

        QTimer.singleShot(3200 if args.exercise else 1200, capture)
        QTimer.singleShot(10000, app.quit)
        app.exec()
        backend.shutdown()
        if warnings:
            raise RuntimeError("QML warnings: " + "\n".join(warnings))
        if callback_errors:
            raise RuntimeError("Preview interactions failed: " + "\n".join(callback_errors))
        if not args.output.is_file():
            raise RuntimeError("No screenshot")
        print("Preview:", args.output)


if __name__ == "__main__":
    main()

"""PySide6/QML Manaka Control Center entry point."""

from __future__ import annotations

import sys
import os
import subprocess
import ctypes
from pathlib import Path

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import QLockFile, QStandardPaths, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QIcon, QFont
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtQuick import QQuickItem  # noqa: F401 - registers QQuickItem converters

PYTHON_ROOT = Path(__file__).resolve().parent.parent
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from backend import ControlCenterBackend  # noqa: E402


PAGE_SCREENSHOT_NAMES = (
    "dashboard",
    "connection",
    "personalization",
    "waveforms",
    "channels",
    "save-tools",
    "mods",
    "workshop",
    "voice-studio",
    "event-log",
    "gameplay",
    "opossum",
    "settings",
)


def screenshot_output_dir() -> Path | None:
    prefix = "--capture-pages="
    value = next((argument[len(prefix) :] for argument in sys.argv if argument.startswith(prefix)), "")
    return Path(value).expanduser().resolve() if value else None


def option_value(prefix: str) -> str:
    return next((argument[len(prefix) :] for argument in sys.argv if argument.startswith(prefix)), "")


def main() -> int:
    # Native Windows controls retain native sub-items when their indicator or
    # background is replaced. The app draws its own theme, so select the
    # customizable style before any QML is loaded (also in packaged runs).
    QQuickStyle.setStyle("Basic")
    connection_report = option_value("--connection-check=")
    if connection_report:
        return check_connection(Path(connection_report))
    capture_dir = screenshot_output_dir()
    capture_page_value = option_value("--capture-page=")
    capture_file_value = option_value("--capture-file=")
    if capture_dir is not None and not capture_page_value:
        capture_dir.mkdir(parents=True, exist_ok=True)
        launcher = [sys.executable]
        if not getattr(sys, "frozen", False):
            launcher.append(str(Path(__file__).resolve()))
        for index, name in enumerate(PAGE_SCREENSHOT_NAMES):
            subprocess.run(
                launcher
                + ["--demo", f"--capture-page={index}", f"--capture-file={capture_dir / f'{index + 1:02d}-{name}.png'}"],
                check=True,
            )
        return 0

    capture_page = int(capture_page_value) if capture_page_value else -1
    capture_file = Path(capture_file_value).resolve() if capture_file_value else None
    app = QGuiApplication(sys.argv)
    app.setApplicationDisplayName("Manaka × DG-LAB Control Center")
    app.setOrganizationName("ManakaDGLab")
    app.setFont(QFont("Microsoft YaHei UI", 10))

    lock_path = Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation)) / "manaka-dglab-control-center.lock"
    instance_lock = QLockFile(str(lock_path))
    instance_lock.setStaleLockTime(3000)
    if "--demo" not in sys.argv and not instance_lock.tryLock(0):
        if sys.platform == "win32":
            ctypes.windll.user32.MessageBoxW(
                0,
                "Manaka × DG-LAB 控制中心已经在运行。\n请切换到已有窗口，不需要重复启动。",
                "Manaka × DG-LAB",
                0x40,
            )
        else:
            print("Manaka × DG-LAB Control Center is already running.", file=sys.stderr)
        return 0

    if getattr(sys, "frozen", False):
        icon_file = Path(sys._MEIPASS) / "assets" / "app_icon.png"
    else:
        icon_file = Path(__file__).with_name("assets") / "app_icon.png"
    app.setWindowIcon(QIcon(str(icon_file)))

    demo = "--demo" in sys.argv
    language_override = option_value("--language=").lower()
    backend = ControlCenterBackend(
        demo=demo,
        language=language_override if language_override in {"zh", "en"} else None,
    )
    if capture_file is not None or (demo and "--smoke-test" in sys.argv):
        backend.agreement_accepted_value = True
    app.aboutToQuit.connect(backend.shutdown)
    backend.exitRequested.connect(app.quit)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("initialPageIndex", capture_page)
    if getattr(sys, "frozen", False):
        qml_file = Path(sys._MEIPASS) / "qml" / "ControlCenter.qml"
    else:
        qml_file = Path(__file__).with_name("ControlCenter.qml")
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    window.setIcon(QIcon(str(icon_file)))
    if capture_file is not None:
        capture_file.parent.mkdir(parents=True, exist_ok=True)

        def grab_screenshot() -> None:
            # Capture the QML content item directly. A desktop-level grab can
            # include another window when the app is occluded.
            content_item = window.property("contentItem")
            grab_result = content_item.grabToImage()

            def save_screenshot() -> None:
                grab_result.saveToFile(str(capture_file))
                app.quit()

            grab_result.ready.connect(save_screenshot)

        def prepare_screenshot() -> None:
            # Bring the QML window to the foreground before using the Windows
            # screen grabber; otherwise another app can be captured over it.
            window.show()
            window.raise_()
            window.requestActivate()
            QTimer.singleShot(250, grab_screenshot)

        # The dashboard and connection pages need a little longer to finish
        # their first render on Windows. Capturing too early can occasionally
        # return the window that was previously in the same screen region.
        QTimer.singleShot(1800, prepare_screenshot)
    if "--smoke-test" in sys.argv:
        def finish_smoke():
            destination = option_value("--smoke-report=")
            if destination:
                import json
                from PySide6.QtCore import QObject
                window.setProperty("pageIndex",3)
                checkbox = window.findChild(QObject,"waveFavorites")
                types = []
                def visit(item):
                    types.append(item.metaObject().className())
                    for child in item.childItems(): visit(child)
                visit(window.contentItem())
                indicator = checkbox.property("indicator")
                Path(destination).write_text(json.dumps(dict(style=QQuickStyle.name(),
                    native_items=[name for name in types if "NativeStyle" in name],
                    checkbox_indicator=[indicator.width(),indicator.height()]),indent=2),encoding="utf-8")
                window.grabWindow().save(str(Path(destination).with_suffix(".png")))
            app.quit()
        QTimer.singleShot(1500, finish_smoke)
    return app.exec()


def check_connection(destination: Path) -> int:
    """Packaged diagnostic: isolated config and local Socket, no game/device output."""
    import base64
    import json
    import os
    import tempfile
    import time
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtGui import QImage
    from manaka_dglab_bridge import DGLabBridge
    app = QCoreApplication([])
    with tempfile.TemporaryDirectory() as directory:
        os.environ["APPDATA"] = directory
        backend = ControlCenterBackend(demo=True)
        backend.poll_timer.stop()
        backend.demo_mode = False
        backend.auto_output_enabled = False
        protocol = option_value("--protocol=") or "v3"
        backend.socket_protocol = protocol
        if protocol == "v4":
            from manaka_devices.dglab_v4_hub import DGLabV4Hub
            backend.v4_hub = DGLabV4Hub(backend.v4_messages)
            bridge = backend.v4_hub.channel("coyote")
        else:
            bridge = DGLabBridge(backend.messages)
        backend.bridge = bridge
        from manaka_runtime import RealtimeProcessor
        backend.processor = RealtimeProcessor(backend._runtime_config(), bridge, backend.messages)
        # Only our internal controller connects. Output remains disabled.
        bridge.start()
        deadline = time.monotonic() + 8
        try:
            while time.monotonic() < deadline:
                backend._poll()
                if backend.qrSource or backend.connection_error_value:
                    break
                app.processEvents()
                time.sleep(.02)
            png = base64.b64decode(backend.qrSource.split(",", 1)[1]) if backend.qrSource else b""
            report = dict(protocol=protocol, server_ready=backend.serverReady, address_count=len(backend.lanAddresses),
                qr_png_valid=not QImage.fromData(png).isNull(),
                fallback_used=bridge.port != bridge.requested_port,
                output_enabled=bridge.auto_enabled,
                error=backend.connection_error_value)
        finally:
            backend.shutdown()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 0 if report["server_ready"] and report["qr_png_valid"] and not report["output_enabled"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

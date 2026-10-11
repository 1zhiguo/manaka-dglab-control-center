"""PySide6/QML Manaka Control Center entry point."""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

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
    "event-log",
)


def screenshot_output_dir() -> Path | None:
    prefix = "--capture-pages="
    value = next((argument[len(prefix) :] for argument in sys.argv if argument.startswith(prefix)), "")
    return Path(value).expanduser().resolve() if value else None


def option_value(prefix: str) -> str:
    return next((argument[len(prefix) :] for argument in sys.argv if argument.startswith(prefix)), "")


def main() -> int:
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
    app.setApplicationDisplayName("Manaka DG-LAB 控制中心")
    app.setOrganizationName("ManakaDGLab")

    if getattr(sys, "frozen", False):
        icon_file = Path(sys._MEIPASS) / "assets" / "app_icon.png"
    else:
        icon_file = Path(__file__).with_name("assets") / "app_icon.png"
    app.setWindowIcon(QIcon(str(icon_file)))

    demo = "--demo" in sys.argv
    backend = ControlCenterBackend(demo=demo)
    if capture_file is not None:
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

        def save_screenshot() -> None:
            window.screen().grabWindow(int(window.winId())).save(str(capture_file))
            app.quit()

        QTimer.singleShot(900, save_screenshot)
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(1500, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

"""PySide6/QML Manaka Control Center entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

PYTHON_ROOT = Path(__file__).resolve().parent.parent
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from backend import ControlCenterBackend  # noqa: E402


def main() -> int:
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
    app.aboutToQuit.connect(backend.shutdown)
    backend.exitRequested.connect(app.quit)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    if getattr(sys, "frozen", False):
        qml_file = Path(sys._MEIPASS) / "qml" / "ControlCenter.qml"
    else:
        qml_file = Path(__file__).with_name("ControlCenter.qml")
    engine.load(QUrl.fromLocalFile(str(qml_file)))
    if not engine.rootObjects():
        return 1
    engine.rootObjects()[0].setIcon(QIcon(str(icon_file)))
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(1500, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

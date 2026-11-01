"""Render this application's QML offscreen using an isolated demo backend."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from PySide6.QtCore import QObject, QMetaObject, QTimer, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QFontDatabase, QFont
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from qml_dashboard_prototype import backend as module
import shiboken6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="zh")
    args = parser.parse_args()
    errors = []
    def message(kind, context, text):
        if any(word in text for word in ("TypeError", "ReferenceError", "is not a type", "Cannot assign", "failed to load")):
            errors.append(text)
        print(text, file=sys.stderr)
    qInstallMessageHandler(message)
    app = QGuiApplication([])
    for font in ("msyh.ttc", "segoeui.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + font)
    app.setFont(QFont("Microsoft YaHei", 10))
    with tempfile.TemporaryDirectory() as directory, patch.object(module, "app_data_dir", return_value=Path(directory)), patch.object(module, "load_config", return_value={}):
        backend = module.ControlCenterBackend(demo=True, language=args.language)
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("backend", backend)
        engine.rootContext().setContextProperty("initialPageIndex", 2)
        engine.load(QUrl.fromLocalFile(str(Path(module.__file__).with_name("ControlCenter.qml"))))
        if not engine.rootObjects():
            return 1
        window = engine.rootObjects()[0]
        def capture():
            try:
                stack = [window.findChild(QObject,"channelEditor")]
                bindings = []
                while stack:
                    item = stack.pop()
                    if item.objectName() == "sourceBinding":
                        bindings.append(item)
                    if hasattr(item,"childItems"):
                        stack.extend(item.childItems())
                if len(bindings) != 2:
                    errors.append(f"Expected 2 visible source editors, found {len(bindings)}")
                args.output.parent.mkdir(parents=True, exist_ok=True)
                image = window.grabWindow()
                if image.isNull() or not image.save(str(args.output)):
                    errors.append("Rendering failed")
            finally:
                app.quit()
        def open_editor():
            window.setProperty("pageIndex",2)
            QTimer.singleShot(400, capture)
        QTimer.singleShot(200, open_editor)
        app.exec()
        backend.shutdown()
        shiboken6.delete(engine)
    for error in errors:
        print("VERIFICATION ERROR:",error,file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

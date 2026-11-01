"""Check packaged UI and a real local Socket/QR, without game/device output."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--output",type=Path,required=True)
parser.add_argument("--build-dir",type=Path,default=root/"build/development")
args = parser.parse_args()
build = args.build_dir.resolve()/"dist/ManakaQmlControlCenter-AB-dev"
checks = {}
for source,relative in ((root/"manaka_telemetry/bin/ManakaDGLabTelemetry.dll","assets/ManakaDGLabTelemetry.dll"),
    (root/"python/qml_dashboard_prototype/ChannelSettingsEditor.qml","qml/ChannelSettingsEditor.qml"),
    (root/"python/qml_dashboard_prototype/ControlCenter.qml","qml/ControlCenter.qml"),
    (root/"python/qml_dashboard_prototype/WaveWorkbench.qml","qml/WaveWorkbench.qml"),
    (root/"python/qml_dashboard_prototype/GameplaySettings.qml","qml/GameplaySettings.qml"),
    (root/"python/qml_dashboard_prototype/WavePreview.qml","qml/WavePreview.qml")):
    packaged = build/"_internal"/relative
    digest = lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    if digest(source) != digest(packaged):
        raise RuntimeError("Packaged asset differs from source: "+relative)
    checks[relative] = digest(source)
for folder in ("components", "icons"):
    for source in sorted((root/"python/qml_dashboard_prototype"/folder).rglob("*")):
        if source.is_file():
            relative="qml/"+source.relative_to(root/"python/qml_dashboard_prototype").as_posix()
            packaged=build/"_internal"/relative
            if digest(source) != digest(packaged):
                raise RuntimeError("Packaged component differs: "+relative)
            checks[relative]=digest(source)
with tempfile.TemporaryDirectory() as directory:
    # Deliberately request Windows: the production entrypoint must select Basic
    # itself, otherwise a test-only Basic override conceals native sub-controls.
    env = dict(os.environ,APPDATA=directory,QT_QPA_PLATFORM="offscreen",QT_QUICK_CONTROLS_STYLE="Windows",QT_QUICK_BACKEND="software")
    if sys.platform == "win32":
        env["QT_QPA_FONTDIR"] = str(Path(os.environ["SystemRoot"])/"Fonts")
    options = {}
    if sys.platform == "win32":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        options = dict(startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        ui_report=Path(directory)/"ui.json"
        result = subprocess.run([str(build/"ManakaQmlControlCenter-AB-dev.exe"),"--demo","--smoke-test","--smoke-report="+str(ui_report)],
            env=env,cwd=build,capture_output=True,timeout=30,**options)
        exit_code, stdout, stderr = result.returncode, result.stdout, result.stderr
        if exit_code == 0:
            ui=json.loads(ui_report.read_text())
            assert ui["style"] == "Basic" and not ui["native_items"],ui
            assert ui["checkbox_indicator"] == [20,20],ui
            args.output.with_suffix(".png").write_bytes(ui_report.with_suffix(".png").read_bytes())
    except subprocess.TimeoutExpired as error:
        exit_code, stdout, stderr = 124, error.stdout or b"", error.stderr or b""
    report = dict(exit_code=exit_code,packaged_assets=checks,
        stdout=stdout.decode("utf-8",errors="replace"),stderr=stderr.decode("utf-8",errors="replace"),
        mode="isolated offline demo; no game or device connection")
    if exit_code == 0: report["ui"] = ui
    if exit_code == 0:
        connection_path = Path(directory)/"connection.json"
        # An unreachable proxy must never intercept the internal local client.
        env.update(http_proxy="http://127.0.0.1:1", https_proxy="http://127.0.0.1:1",
                   all_proxy="http://127.0.0.1:1", no_proxy="")
        try:
            connection = subprocess.run([str(build/"ManakaQmlControlCenter-AB-dev.exe"),
                "--connection-check="+str(connection_path)], env=env, cwd=build,
                capture_output=True, timeout=20, **options)
            exit_code = connection.returncode
            report["connection"] = json.loads(connection_path.read_text()) if connection_path.exists() else {"error":"No connection report"}
            if not connection_path.exists():
                exit_code = 1
        except subprocess.TimeoutExpired:
            exit_code = 124
        report["exit_code"] = exit_code
        report["mode"] = "isolated UI plus local Socket and QR; game listener disabled; no device output"
args.output.write_text(json.dumps(report,indent=2),encoding="utf-8")
print("Packaged development smoke exit:",exit_code)
raise SystemExit(exit_code)

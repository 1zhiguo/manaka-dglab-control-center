"""Build a local review client, excluding game files and BepInEx interop."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--build-dir", type=Path, default=root/"build/development")
args = parser.parse_args()
build = args.build_dir.resolve()
if not build.is_relative_to(root/"build"):
    raise ValueError("Development output must stay inside this repository's build directory")
payload = build/"npc-payload"
source = root/"manaka_npc_voices"
payload.mkdir(parents=True,exist_ok=True)
for name in ("ManakaNpcVoices.dll","ManakaNpcVoices.CustomMissions2.dll"):
    target = payload/"bin"/name
    target.parent.mkdir(exist_ok=True)
    shutil.copy2(source/"bin"/name,target)
shutil.copytree(source/"VoicePacks/ja",payload/"VoicePacks/ja",dirs_exist_ok=True)
shutil.copy2(source/"VOICE_PACK_README.txt",payload/"VOICE_PACK_README.txt")
for language in ("zh","ja","en"):
    for text in (source/"SubtitleLines"/language).glob("*.txt"):
        target = payload/"VoicePacks"/language/text.stem/"lines.txt"
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(text,target)
    shutil.copy2(source/"SubtitleProfiles"/(language+".txt"),payload/"VoicePacks"/language/"profiles.txt")
qml = root/"python/qml_dashboard_prototype"
data = [(qml/"ControlCenter.qml","qml"),(qml/"ChannelSettingsEditor.qml","qml"),(qml/"WaveWorkbench.qml","qml"),(qml/"GameplaySettings.qml","qml"),(qml/"WavePreview.qml","qml"),
        (qml/"components","qml/components"), (qml/"icons","qml/icons"),(qml/"assets","qml/assets"),(qml/"assets/app_icon.png","assets"),(qml/"VERSION","assets"),
        (root/"manaka_telemetry/bin/ManakaDGLabTelemetry.dll","assets"),
        (root/"python/assets/dglab_guide","assets/dglab_guide"),(payload,"assets/ManakaNpcVoices")]
command = [sys.executable,"-m","PyInstaller","--noconfirm","--windowed","--onedir",
    "--name","ManakaQmlControlCenter-AB-dev","--icon",str(qml/"assets/app_icon.ico"),
    "--distpath",str(build/"dist"),"--workpath",str(build/"work"),"--specpath",str(build),
    "--paths",str(root/"python"),"--hidden-import","PySide6.QtQuick",
    "--exclude-module","PySide6.QtWebEngineCore","--exclude-module","PySide6.QtWebEngineWidgets"]
for path,destination in data:
    command += ["--add-data",str(path)+";"+destination]
command.append(str(qml/"main.py"))
env = dict(os.environ)
if sys.platform == "win32":
    # PyInstaller searches PATH for dependent DLLs before applying the Windows
    # system-library exclusions. An unrelated Poppler ICU can have the same
    # filename as the OS library while exposing incompatible symbols.
    windows = Path(os.environ["SystemRoot"])
    env["PATH"] = os.pathsep.join(map(str, (
        Path(sys.executable).parent, Path(sys.base_prefix),
        windows/"System32", windows,
    )))
subprocess.run(command,check=True,cwd=root,env=env)
output = build/"dist/ManakaQmlControlCenter-AB-dev"
if sys.platform == "win32":
    # Match the runtime selected by the bootloader to the one shipped with Qt.
    internal = output/"_internal"
    for name in ("VCRUNTIME140.dll", "VCRUNTIME140_1.dll", "MSVCP140.dll",
                 "MSVCP140_1.dll", "MSVCP140_2.dll"):
        shutil.copy2(internal/"PySide6"/name, internal/name)
shutil.copy2(root/"docs/WAVE_WORKBENCH.md",output/"WAVE_WORKBENCH.md")
for name in ("LICENSE.md","THIRD_PARTY_NOTICES.md"):
    shutil.copy2(root/name,output/name)
(output/"DEVELOPMENT.txt").write_text(
    "Local review build. Not a full BepInEx installer package.\n"
    "No game files or generated interop assemblies are included.\n"
    "For the new vibrator/piston sources, use the separately built telemetry plugin\n"
    "with an existing BepInEx installation. Source running and tests are described\n"
    "in the repository README. Old game builds await manual verification.\n",encoding="utf-8")
print(output)

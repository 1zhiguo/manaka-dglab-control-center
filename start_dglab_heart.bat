@echo off
setlocal
cd /d "%~dp0"

rem Compatibility launcher: the old OCR/HUD pair has been replaced by the
rem integrated PySide6/QML controller and direct game telemetry plugin.
call "%~dp0start_manaka_qml_control_center.bat"
endlocal

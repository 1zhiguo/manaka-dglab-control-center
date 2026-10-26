@echo off
setlocal
cd /d "%~dp0"
start "Manaka Control Center" ".\python\.venv\Scripts\pythonw.exe" ".\python\qml_dashboard_prototype\main.py"
endlocal

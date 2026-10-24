@echo off
setlocal
cd /d "%~dp0"
start "Manaka UI Preview" ".\python\.venv\Scripts\pythonw.exe" ".\python\qml_dashboard_prototype\main.py" --demo
endlocal

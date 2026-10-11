# Manaka PySide6/QML Control Center

This folder contains the fully migrated PySide6/QML user interface. It reuses
the existing telemetry, trigger, waveform and DG-LAB Socket backend modules.

Start the real controller from the repository root with:

```powershell
.\start_manaka_qml_control_center.bat
```

For visual review without opening UDP/WebSocket or sending device output, use:

```powershell
.\start_qml_dashboard_prototype.bat
```

The legacy Tkinter controller remains available through
`start_manaka_control_center.bat` as a temporary fallback.

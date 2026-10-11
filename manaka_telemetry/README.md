# Manaka DG-LAB Telemetry Pilot

This plugin reads authoritative game state through BepInEx and broadcasts it only
to `127.0.0.1:45678` as JSON over UDP. It also accepts a strictly bounded local
progress-edit command on `127.0.0.1:45679`; the game applies `CurrentRp` and
`ExposeExp` on its main thread and saves through its own `SaveManager`. It does
not connect to DG-LAB and does not contain any device-output code.

## Build and deploy

Run from PowerShell:

```powershell
.\manaka_telemetry\build_plugin.ps1 -Deploy
```

Restart the game after deployment. BepInEx should log:

```text
Loading [Manaka DG-LAB Telemetry 0.3.1-standalone]
Pilot telemetry enabled: UDP 127.0.0.1:45678
Progress editor enabled: local-only UDP 127.0.0.1:45679
```

Then run `start_manaka_telemetry_pilot.bat` and compare its BPM with the game's
top-left heart-rate HUD.

Closing the monitor has no effect on the game. Since UDP is fire-and-forget, the
game plugin also does not wait for the monitor.

## Trigger-engine pilot

`start_manaka_trigger_pilot.bat` runs the conservative trigger mapper. It is a
dry-run program: it has no WebSocket client and cannot send commands to a
DG-LAB device. Channel A follows the authoritative in-game heart rate; channel
B represents action/ecstasy progression. NPC alert is telemetry-only and does
not affect either output. The UI exposes personal BPM thresholds, minimum and
maximum working strength, plus an independent 0..100 hard cap that defaults to
30. Missing telemetry and non-playable scenes force both proposed outputs to
zero. A game-over rising edge may produce one bounded two-hit failure climax;
after that one-shot finishes, both channels return to zero.

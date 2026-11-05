# Manaka DG-LAB Telemetry Pilot

This plugin reads authoritative game state through BepInEx and broadcasts it only
to `127.0.0.1:45678` as JSON over UDP. It also accepts a strictly bounded local
progress-edit command on `127.0.0.1:45679`; the game applies `CurrentRp` and
`ExposeExp` on its main thread and saves through its own `SaveManager`. It does
not connect to DG-LAB and does not contain any device-output code. The optional
transparent A/B HUD receives display-only state from the control center on
`127.0.0.1:45680` and hides itself if that state is disabled or becomes stale.

## Build and deploy

Run from PowerShell:

```powershell
.\manaka_telemetry\build_plugin.ps1 -GameDir "C:\Path\To\SecretFlasherManaka" -Deploy
```

Restart the game after deployment. BepInEx should log:

```text
Loading [Manaka DG-LAB Telemetry 0.5.2]
Pilot telemetry enabled: UDP 127.0.0.1:45678
Progress editor enabled: local-only UDP 127.0.0.1:45679
In-game A/B HUD listener enabled: local-only UDP 127.0.0.1:45680
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

## Piston random speed (0.5.1)

The original piston integer remains the selected mode (0 off, 1 slow, 2 medium, 3 fast, 4 random). The pistonRandom boolean marks random mode and pistonEffective reports the live player controller CurrentSpeedType (0..3, or -1 when unavailable). The control center follows this effective mode instead of generating its own random timing. Older telemetry without an effective random speed cannot drive the device in random mode; update the DLL and restart the game. Fixed-mode mapping remains available. These fields are read-only and do not change game settings.

## Belt Knight HUD (0.5.2 / HUD V3)

The game advertises hudProtocol=3. MANAKA_HUD_V3 retains V2 fields and appends Belt Knight move/vibration requested indices, caps and display pulses (six extra numeric fields before END). A separate show_booboop bit (128) controls both cells independently of Pulse/Opossum and their A/B filters. The new receiver accepts V1/V2/V3; the control center continues sending V2 to a game reporting V2. Belt Knight indices are 0..9, bounded by the configured cap, and are not physical feedback. Hiding its HUD cells does not change device authorization or output. Install the updated DLL with the game closed, then restart the game and source control center to see the new cells.

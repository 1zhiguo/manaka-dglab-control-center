# FN010-RX direct BLE integration

Status (2026-11-03): experimental source implementation; fake GATT/backend/QML checks passed. No physical device was scanned, connected or driven during implementation. The implementation is now included in v1.2.0; release validation uses fake GATT and loopback scenarios.

## Sources and implementation boundary

- [BooBoop official site](https://www.booboop.com/en/) provides user-facing software/manual/tutorial entry points. This research did not find a public official BLE SDK or protocol sample.
- [BooBoopControl](https://github.com/LuMianJun/BooBoopControl) and [Manaka bridge](https://github.com/LuMianJun/SecretFlasherManaka-BooBoopBridge) were reviewed for supported model, lifecycle and game mapping. They use the vendor Native Host and its product cache, not direct GATT. Their aa01/bb01 commands are host messages and must not be written directly to BLE.
- [Community HCI capture and live-test report](https://github.com/buttplugio/buttplug/issues/968) supplies the experimental direct BLE framing. It is not an official vendor specification. A shared advertising name does not establish compatibility across hardware variants.

The implementation is original Python in this repository. No third-party C# source, DLL, vendor executable, cache or activation data was copied into the application. The existing game backend and Pulse/Opossum planners remain separate.

## Layers

- manaka_devices/ble_session.py: refactored common lifecycle from our existing Coyote BLE implementation; explicit discovery, per-role worker, epochs, stop and stale-plan barriers.
- manaka_devices/booboop_ble.py: FN010-RX-only GATT handshake, discrete motor indices and stop writes.
- manaka_devices/booboop.py: pure piston/action policy.
- qml_dashboard_prototype/booboop_integration.py: authorization, persistence and telemetry adapter.
- qml_dashboard_prototype/BooBoopWorkbench.qml: independent connection, piston-level and action-rule UI.
- qml_dashboard_prototype/BleActivity.qml: shared scan progress and animated SVG hourglass.

Only an explicit scan in this device's tab authorizes its one-time automatic connection attempt. Generic Coyote/Opossum scan does not authorize this role. Multiple matching candidates require selection. All roles use direct BLE when selected; Socket/BLE are not mixed. Output always requires manual enable.

## Profile guard and transport

Advertising name FN010-RX is only the first filter. The adapter requires service 0000ffee-0000-1000-8000-00805f9b34fb, write-without-response characteristic 0000ee01-0000-1000-8000-00805f9b34fb, and notify characteristic 0000ee02-0000-1000-8000-00805f9b34fb within that service.

Subscribe, send AF00, require the six-byte AF00030100xx handshake response, then write stops for both motors before marking ready. The variable final handshake byte is not interpreted as battery.

Run: AC [motor] 01 00 01 [speed]. Vibration motor=01, thrust motor=03. Speed=1F+19*(index-1), indices 1..9. Stop=AC [motor] 00 00 00 00.

These are protocol indices, not verified linear intensity, physical position or stroke. No action/stop acknowledgement is available. The UI reports requested and last-written indices only. Writes are serialized and unchanged levels are not repeatedly sent.

## Game policy

Existing telemetry already includes PistonMachineModeType as piston; no additional Unity bridge is required. Modes 0/1/2/3 are treated as off/slow/medium/fast. Mode 4 (random), or pistonRandom=true, uses pistonEffective reported by telemetry 0.5.1 from the player piston controller CurrentSpeedType. Unknown/missing effective speed stops both motors and the UI requests a telemetry update; no independent software random choice is made. Selected off always stops, even if a previous effective speed remains.

Default slow/medium/fast indices are 1/2/3, user cap 4 (adjustable 0..9). Optional companion vibration defaults off. Action rules choose game sync, a fixed thrust index, or both motors off. An action rule cannot override piston-off. User cap applies to both motors.

Pause, system menu, failure, invalid stage/time scale, stale telemetry or revoked authorization produce zero. Saving settings stops authorization. New fresh telemetry can resume stale-data standby while the user's enable remains; disconnect, device error or global stop require manual re-enable.

A 500 ms producer watchdog attempts both stops. Each stop is attempted even if the other fails. The profile is latched: a process kill, radio failure or lost stop packet cannot guarantee physical stopping. It does not have a device-side short lease, position readback or confirmed stop.

## Local validation

Targeted checks live in python/test_booboop.py. They use fake discovery/GATT only: strict profile and handshake, dual stop, independent motors, cap reduction/zero, stale plans, disconnect/reselection, emergency-stop unlock, authorization, profile validation and atomic Pulse batch persistence. Three representative existing Coyote 3/Coyote 2/Opossum cases passed after common lifecycle extraction.

tools/verify_v4_preview.py --batch-actions pulse|ovc|boo exercises current-filter select-all, inversion, search reset and batch assignment. Opossum edits remain confined to the selected channel and to its draft until save. Chinese and English pages render offline without QML warnings.

Physical compatibility and the game's effective piston mode still need user testing before claiming hardware support.


## 2026-11-05 random piston update

Telemetry 0.5.1 adds pistonEffective and pistonRandom while retaining the original piston selection. PistonStateReader reads the live controller on the main thread; selected off and unknown controller values do not authorize motion. The workbench displays Random -> current speed, and its mapping header now has a Save button sharing the bottom Save action. Saving still revokes output until explicitly re-enabled. Six targeted policy/backend cases passed and the DLL compiled against the local v1.1.3 Interop. The running game was not modified or restarted; hardware random synchronization still requires testing after updating the DLL.


## Belt Knight HUD

Telemetry 0.5.2 adds native MOVE and VIBE cells (HUD V3), independent gold-tinted level bars and OFFLINE/IDLE/SYNC state. A dedicated HUD settings checkbox controls both cells. They remain visible when Pulse/Opossum A/B filters are off, allowing a Belt Knight-only HUD. Values are display-only requested indices, not movement acknowledgements. The existing size, opacity and anchor controls apply to all visible cells. HUD preferences do not authorize, stop or alter any hardware output. Old HUD V2 games retain their four-cell protocol and show an update hint for this feature. Twelve targeted HUD/settings/backend cases passed, QML previews rendered in both languages, and the game DLL compiled without deployment. No entity-device test or production package was run for this change.


Release validation for v1.2.0: 360 source cases, 76 frozen BLE/FN010-RX/HUD cases and 11 frozen V4 loopback scenarios passed. A maintainer reported FN010-RX basic connection and sync working; this does not constitute verification of every hardware variant, random-speed behavior or native HUD output.

# Manaka × DG-LAB Control Center — English Quick Start

This community-made Windows tool connects **Secret Flasher Manaka** to **DG-LAB Pulse and/or Opossum** devices via V3/V4. It can synchronize in-game heart rate, actions, and Climax events to channels A/B. The public build does **not** include the game.

## 1. Before you start

- Windows 10 or 11, 64-bit
- A legally obtained copy of Secret Flasher Manaka v1.1.1, v1.1.2, or v1.1.3
- A supported DG-LAB device and matching mobile app; Opossum requires the DG-LAB 4 App
- The PC and phone connected to the same local network

Electrical stimulation can cause pain, skin irritation, involuntary muscle contraction, or other injury. Start at low strength, keep the physical controller within reach, and stop immediately if you feel unwell. Read the in-app agreement before use.

## 2. Download and launch

1. Download the latest portable Windows archive from the [project website](https://manaka-dglab.web.app/?lang=en) or [GitHub Releases](https://github.com/1zhiguo/manaka-dglab-control-center/releases/latest).
2. Extract the entire ZIP file to a normal writable folder. Do not run the EXE from inside the ZIP.
3. Launch `ManakaQmlControlCenter.exe`.
4. Choose **English** in **Settings**, or in the first-run agreement window.
5. Read and accept the user agreement. No game listener or DG-LAB Socket service starts before acceptance.

The app is unsigned, so Windows SmartScreen may show an “Unknown publisher” warning. Verify that the file came from an official project download and compare the published SHA-256 before choosing **More info → Run anyway**.

## 3. Select the game folder

Open **Device & Game** and select the folder that directly contains:

```text
SecretFlasherManaka.exe
SecretFlasherManaka_Data/
```

Do not select `BepInEx`, `plugins`, or `SecretFlasherManaka_Data` itself.

For a clean game copy, choose **Install and Launch Game**. The control center supports v1.1.1, v1.1.2, and v1.1.3; it installs or repairs BepInEx 6 IL2CPP, prepares Interop for the selected game build, deploys the standalone Manaka telemetry plugin, and then starts the game.

## 4. Connect DG-LAB using V3 or V4

1. In **Setup**, select V3 or V4 above the QR code. Keep the PC and phone on the same LAN.
2. For **V3**, connect Coyote in the DG-LAB 3 App, open **SOCKET Control**, initialize it and scan the QR code under **Connect server**. The default port is TCP `9999`.
3. For **V4**, connect supported Coyote Pulse (COYOTE_030) and/or Opossum (OVC_1) hardware and accessories in the DG-LAB 4 App, then scan once. Both devices share the V4 QR code on TCP `9998`.
4. V4 discovers and selects supported devices automatically, but output requires separate manual enabling. A device added in the phone app is not necessarily connected over Bluetooth. Click an unavailable enable button to see its reason.
5. Devices may be enabled before starting the game; they wait at zero output until fresh game data arrives. A brief telemetry/producer interruption zeros output and waits for newly received valid data. Bluetooth disconnects and output errors require manual re-enabling.

Use **Can't connect?** to change the QR code's LAN address or diagnose private-network firewall access. After upgrading, close the game, use **Install / Repair Runtime**, and restart it to load the new telemetry/HUD plugin.

## 5. Safe first test

1. Start with the **Low · 5–30** preset.
2. Keep the safety hard cap at 30 for the first test.
3. Enter a playable scene and confirm that live heart rate is updating.
4. By default A follows heart rate and B follows actions. In **Waveforms**, either channel can use either source; both may share one source. Save changes and manually re-enable Pulse.
5. Use the V3 pause/resume control or V4 device enable controls for individual devices. **Stop All** stops both devices and requires manual re-enabling.

Pausing the game with Esc should also place output in safety idle. If the telemetry stream is interrupted, the control center automatically returns output to zero.

## 6. Waveforms

- Pulse A/B sources are independent. Channels using the same source share its waveform assignments. Heart-rate settings show actual low/mid/high BPM boundaries at 30% and 70% of the configured trigger-to-full interval.
- The **Opossum** workbench requires V4. Choose direct game-vibrator sync or independent A/B action, random, fixed and off policies. Game Random follows the game's actual selected level.
- Use built-in vibration envelopes or your own curves. Previews never send output. Saving Opossum settings stops that device until manually re-enabled.
- The HUD group in the top bar controls visibility and opens content, size, opacity and position settings. **Settings** also contains language and day/night preferences. Hiding the HUD does not stop devices.

- Built-in DG-LAB waveforms are read-only previews.
- The smart strategy maps different heart-rate and action zones to different waveforms.
- Custom waveforms use a simple 16-point envelope and are saved under `%APPDATA%\ManakaDGLab\waveforms`.
- Climax uses a synchronized double-hit waveform on channels A/B and remains limited by the configured hard cap and rolling peak limiter.

## 7. Mod Manager

Release archives do not redistribute third-party Mods. They include only the verified BepInEx runtime and this project's DG-LAB telemetry plugin. The manager handles three local content types: BepInEx plugins, CustomMission 1 JSON missions, and CustomMission 2 packages.

**Local Mods** always scans the selected game folder. Open **Workshop** for original F95Zone source links, use the Drop-in inbox for individual files, or open route 2 and run the dedicated user9527 importer. The Mod Manager no longer switches between separate repositories.

### Import the user9527 Chinese pack

1. Select the game root under **Device & Game** and install the BepInEx runtime first.
2. Fully close the game, open **Mod Manager**, and choose **Import 9527 Pack**.
3. Select the extracted folder that directly contains `BepInEx`, `CustomMissions`,
   `CustomMissions2`, and the required readme files.
4. Review the detected plugin and mission counts, read the author's instructions, and confirm the plan.
5. The wizard backs up every file it will replace, imports configuration and supporting assets,
   then enables only `SFM_custom_mission.dll` and `SFM_custom_mission_v2.dll`. Other third-party
   DLLs and all V1/V2 content start in `ManakaModManager/disabled`.
6. Enable only the missions you want under **Local Mods**. The DG-LAB telemetry plugin remains enabled.

Backups are stored under `ManakaModManager/backups/9527-timestamp` in the game folder. The wizard
does not execute or upload EXE, BAT, or script files from the downloaded pack.

To import external content, place a plugin DLL, V1 JSON file, V2 folder, or supported ZIP in:

```text
dropin_mods/incoming
```

Then choose **Import & Scan**. Imported content is stored in `dropin_mods/repository`; it is copied into the game only after you enable it. Fully exit the game before enabling, disabling, replacing, or deleting Mods.

V1 missions require **CustomMission 1**. V2 packages such as Moaning2 or Aftermath & StageLock require **CustomMission 2**.

## 8. EXP / RP editor

1. Load the target manual save.
2. Move the character outdoors.
3. Press Esc to pause the game.
4. Open **Save Tools**, refresh the current values, and create a backup.
5. Enter the new RP and EXP values, then choose **Back Up, Edit & Save**.

After changing EXP, complete any mission and return home to trigger settlement before the displayed level updates. Backups are stored under `%APPDATA%\ManakaDGLab\save_backups`.

## Support

- Website: https://manaka-dglab.web.app/?lang=en
- X: https://x.com/1zhiguo
- GitHub issues: https://github.com/1zhiguo/manaka-dglab-control-center/issues
- QQ technical group: `1129729751`


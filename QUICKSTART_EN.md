# Manaka × DG-LAB Control Center — English Quick Start

This community-made Windows tool connects **Secret Flasher Manaka** to a **DG-LAB 3.0** device. It can synchronize in-game heart rate, actions, and Climax events to channels A/B. The public build does **not** include the game.

## 1. Before you start

- Windows 10 or 11, 64-bit
- A legally obtained copy of Secret Flasher Manaka v1.1.3
- A DG-LAB 3.0 device and the current DG-LAB mobile app
- The PC and phone connected to the same local network

Electrical stimulation can cause pain, skin irritation, involuntary muscle contraction, or other injury. Start at low strength, keep the physical controller within reach, and stop immediately if you feel unwell. Read the in-app agreement before use.

## 2. Download and launch

1. Download the latest portable Windows archive from the [project website](https://manaka-dglab.web.app/?lang=en) or [GitHub Releases](https://github.com/1zhiguo/manaka-dglab-control-center/releases/latest).
2. Extract the entire ZIP file to a normal writable folder. Do not run the EXE from inside the ZIP.
3. Launch `ManakaQmlControlCenter.exe`.
4. Choose **English** in the top bar or in the first-run agreement window.
5. Read and accept the user agreement. No game listener or DG-LAB Socket service starts before acceptance.

The app is unsigned, so Windows SmartScreen may show an “Unknown publisher” warning. Verify that the file came from an official project download and compare the published SHA-256 before choosing **More info → Run anyway**.

## 3. Select the game folder

Open **Device & Game** and select the folder that directly contains:

```text
SecretFlasherManaka.exe
SecretFlasherManaka_Data/
```

Do not select `BepInEx`, `plugins`, or `SecretFlasherManaka_Data` itself.

For a clean game copy, choose **Install and Launch Game**. The control center installs or repairs the verified BepInEx 6 IL2CPP runtime and the standalone Manaka telemetry plugin, then starts the game.

## 4. Connect DG-LAB 3.0

1. Keep the control center running.
2. Connect the DG-LAB device in the mobile app.
3. Open **SOCKET Control** in the DG-LAB app.
4. Initialize Socket control if the app asks you to do so.
5. Choose **Connect server**, then scan the QR code shown in the control center with the camera option.
6. Wait until the desktop app shows **DG-LAB connected**.

If the QR code does not connect, confirm that the phone and PC are on the same LAN and that Windows Firewall allows the control center on private networks.

## 5. Safe first test

1. Start with the **Low · 5–30** preset.
2. Keep the safety hard cap at 30 for the first test.
3. Enter a playable scene and confirm that live heart rate is updating.
4. Confirm that channel A follows heart rate and channel B reacts to supported actions.
5. Use the large **Pause output** button at any time. It sets A/B output to zero while keeping the device connection alive; press again to resume.

Pausing the game with Esc should also place output in safety idle. If the telemetry stream is interrupted, the control center automatically returns output to zero.

## 6. Waveforms

- Built-in DG-LAB waveforms are read-only previews.
- The smart strategy maps different heart-rate and action zones to different waveforms.
- Custom waveforms use a simple 16-point envelope and are saved under `%APPDATA%\ManakaDGLab\waveforms`.
- Climax uses a synchronized double-hit waveform on channels A/B and remains limited by the configured hard cap and rolling peak limiter.

## 7. Mod Manager

The bundled public repository does not include the game. Release archives may include a separate third-party Mod repository.

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


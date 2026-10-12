# Manaka × DG-LAB Control Center — English Quick Start

This community-made Windows tool connects **Secret Flasher Manaka** to a **DG-LAB 3.0** device. It synchronizes in-game heart rate, actions, and Climax events to channels A/B. The public build does **not** include the game.

## 1. Before you start

- Windows 10 or 11, 64-bit
- A legally obtained copy of Secret Flasher Manaka v1.1.3
- A DG-LAB 3.0 device and the current DG-LAB mobile app
- The PC and phone connected to the same local network

Electrical stimulation can cause pain, skin irritation, involuntary muscle contraction, or other injury. Start at low strength, keep the physical controller within reach, and stop immediately if you feel unwell. Read the in-app agreement before use.

## 2. Download and launch

1. Download the portable Windows archive from the [project website](https://manaka-dglab.web.app/?lang=en) or [GitHub Releases](https://github.com/1zhiguo/manaka-dglab-control-center/releases/latest).
2. Extract the entire ZIP to a normal writable folder. Do not run the EXE from inside the ZIP.
3. Launch `ManakaQmlControlCenter.exe`.
4. Choose **English** in the top bar or first-run agreement window.
5. Read and accept the agreement. Network and device services do not start before acceptance.

The app is unsigned, so Windows SmartScreen may show an “Unknown publisher” warning. Verify the official source and published SHA-256 before choosing **More info → Run anyway**.

## 3. Select the game folder

Open **Device & Game** and select the folder that directly contains:

```text
SecretFlasherManaka.exe
SecretFlasherManaka_Data/
```

Do not select `BepInEx`, `plugins`, or `SecretFlasherManaka_Data` itself. For a clean copy, choose **Install and Launch Game**. The control center installs or repairs the verified BepInEx 6 IL2CPP runtime and telemetry plugin, then starts the game.

## 4. Connect DG-LAB 3.0

1. Keep the control center running.
2. Connect the DG-LAB device in the mobile app.
3. Open **SOCKET Control** and initialize it if requested.
4. Choose **Connect server**, then scan the desktop QR code with the camera option.
5. Wait for **DG-LAB connected**.

If it fails, confirm that the phone and PC are on the same LAN and Windows Firewall allows the control center on private networks.

## 5. Safe first test

1. Start with **Low · 5–30**.
2. Keep the safety hard cap at 30 for the first test.
3. Enter a playable scene and confirm live heart rate updates.
4. Confirm channel A follows heart rate and channel B responds to supported actions.
5. Use **Pause output** at any time. It sets A/B to zero while keeping the connection alive; press again to resume.

Pausing the game with Esc should also place output in safety idle. Interrupted telemetry automatically returns output to zero.

## 6. Waveforms

- Built-in DG-LAB waveforms are read-only previews.
- Smart strategy maps heart-rate and action zones to different waveforms.
- Custom 16-point envelopes are saved in `%APPDATA%\ManakaDGLab\waveforms`.
- Climax uses a synchronized double-hit waveform on A/B and remains limited by the hard cap and rolling peak limiter.

## 7. Mod Manager

Put plugin DLLs, V1 JSON files, V2 folders, or supported ZIP archives in:

```text
dropin_mods/incoming
```

Choose **Import & Scan**. Content is stored in `dropin_mods/repository` and copied into the game only after it is enabled. Fully exit the game before enabling, disabling, replacing, or deleting Mods.

V1 missions require **CustomMission 1**. V2 packages such as Moaning2 or Aftermath & StageLock require **CustomMission 2**.

## 8. EXP / RP editor

1. Load the target manual save and move the character outdoors.
2. Press Esc to pause the game.
3. Open **Save Tools**, refresh values, and create a backup.
4. Enter the new values and choose **Back Up, Edit & Save**.

After changing EXP, complete any mission and return home to trigger settlement before the level updates. Backups are stored in `%APPDATA%\ManakaDGLab\save_backups`.

## Support

- Website: https://manaka-dglab.web.app/?lang=en
- X: https://x.com/1zhiguo
- GitHub issues: https://github.com/1zhiguo/manaka-dglab-control-center/issues
- QQ technical group: `1129729751`


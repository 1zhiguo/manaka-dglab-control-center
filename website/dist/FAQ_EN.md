# Manaka × DG-LAB — Frequently Asked Questions

## Does the download include the game?

No. Select your own legally obtained Secret Flasher Manaka v1.1.3 folder.

## Do I need Python, Node.js, or BepInEx?

The portable build does not require Python or Node.js. A clean game does not need BepInEx preinstalled; **Install and Launch Game** deploys the verified runtime and telemetry plugin.

## Why does Windows show “Unknown publisher”?

The executable is not code-signed. Download only from the official website or GitHub Release and compare the published SHA-256 before using **More info → Run anyway**.

## Why does the QR code not connect?

- Put the phone and PC on the same local network.
- Allow the control center through Windows Firewall on private networks.
- Connect the physical device before opening SOCKET Control.
- Use the camera option inside **Connect server**.
- Avoid guest Wi-Fi or client-isolated networks.

## Why is no waveform sent?

Confirm that game telemetry is live, DG-LAB is connected, output is not paused, and the game is not in safety idle. Enter a playable scene and wait for valid heart-rate or action data.

## What does Pause output do?

It sets both software channels to zero and clears queued output while keeping the Socket connection alive. Press it again to resume after valid game data returns.

## Where are waveforms and backups stored?

```text
%APPDATA%\ManakaDGLab\waveforms
%APPDATA%\ManakaDGLab\save_backups
```

These are per-Windows-user folders, so the full path differs between computers.

## Why did EXP not update the level?

Edit while outdoors and paused. Then complete any mission and return home to trigger settlement.

## How does the Mod Manager toggle Mods?

Enabling copies managed files from the repository into the proper game folder. Disabling moves managed game files into `ManakaModManager/disabled`. Fully exit the game first.

## Can I replace an imported Mod with a newer file of the same name?

Yes. Put the newer item in `dropin_mods/incoming` and choose **Import & Scan**. Enabled game files are refreshed while the game is closed.

## Where can I report a problem?

Use [GitHub Issues](https://github.com/1zhiguo/manaka-dglab-control-center/issues), contact [@1zhiguo on X](https://x.com/1zhiguo), or join QQ group `1129729751`.


# Manaka × DG-LAB — Frequently Asked Questions

## Does the download include the game?

No. The public project and release files do not include the game. Select your own legally obtained Secret Flasher Manaka v1.1.3 folder.

## Do I need to install Python, Node.js, or BepInEx?

The portable Windows build does not require Python or Node.js. A clean game copy does not need BepInEx preinstalled; **Install and Launch Game** deploys the verified runtime and telemetry plugin.

## Why does Windows show “Unknown publisher”?

The executable is not code-signed. Download only from the official website or GitHub Release, compare the SHA-256 checksum, and use **More info → Run anyway** only after verifying the source.

## Why does the QR code not connect?

- Put the phone and PC on the same local network.
- Allow the control center through Windows Firewall on private networks.
- In the DG-LAB app, connect the physical device before opening SOCKET Control.
- Use the camera option inside **Connect server** to scan the desktop QR code.
- Avoid guest Wi-Fi or client-isolated networks.

## Why is no waveform sent to the app?

Confirm that the game telemetry status is live, the DG-LAB device is connected, output is not paused, and the game is not in a safety-idle state. Enter a playable scene and wait for valid heart-rate or action data.

## What does Pause output do?

It immediately sets both software output channels to zero and clears queued output while keeping the Socket connection alive. Press the button again to resume after valid game data returns.

## Where are custom waveforms and save backups stored?

```text
%APPDATA%\ManakaDGLab\waveforms
%APPDATA%\ManakaDGLab\save_backups
```

These are per-Windows-user folders, so the exact absolute path differs between computers.

## Why did changing EXP not update the level?

Edit the save while the character is outdoors and the game is paused. After writing EXP, complete any mission and return home to trigger settlement. The level refreshes during that settlement flow.

## How does the Mod Manager enable and disable Mods?

The repository keeps a managed source copy. Enabling synchronizes the selected files into the appropriate game folder. Disabling moves managed game files into `ManakaModManager/disabled`. Always fully exit the game before changing Mod state.

## Can I replace an imported Mod with a newer file of the same name?

Yes. Put the newer item in `dropin_mods/incoming` and choose **Import & Scan**. The Drop-in copy replaces the repository version; enabled game files are refreshed while the game is closed.

## Where can I report a problem?

Use [GitHub Issues](https://github.com/1zhiguo/manaka-dglab-control-center/issues), contact [@1zhiguo on X](https://x.com/1zhiguo), or join QQ group `1129729751`.


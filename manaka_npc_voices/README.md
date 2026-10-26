# Manaka NPC Voices

Current plugin version: 0.6.1. The 0.6.1 manual package clarifies the core
installation path and prevents the optional CM2 phone bridge from being
mistaken for the main plugin.

Native BepInEx/IL2CPP NPC voice plugin for Secret Flasher Manaka. Version 1.1.3
is verified; other game revisions are allowed for experimental compatibility
testing and are not blocked by the control center.

- Reads phone actions, watching, suspicion-value jumps/thresholds, exact
  player-found events, and the game-over event.
- Zero-suspicion NPCs may mutter after remaining nearby and visible for a
  randomized delay. Phone users keep their own separate chatter pool; neither
  mode is an immediate proximity greeting.
- Ordinary muttering requires a visible NPC within 10 metres. Phone chatter
  keeps its stricter 7-metre range.
- Watching requires at least 10 suspicion and an 8-metre range. Alert and found
  reactions use 12-metre and 16-metre ranges. Eligibility is checked once when
  queued and again before playback, so stale distant reactions are discarded.
- Attaches a 3D Unity `AudioSource` to the speaking NPC.
- Keeps failure audio on a persistent 2D source so it survives the failure scene change.
- Detects NPCBehaviorModifier without a hard dependency. When its caught-NPC
  interaction starts, a separate editable Aftermath dialogue pool speaks during
  the scene and stops when that interaction finishes.
- Gives phone, alert, and found reactions separate per-NPC cooldowns. Failure clears
  queued reactions, stops ordinary speech, and cannot be overwritten afterward.
- Lets watching reactions follow phone chatter after a short 2.5-second pause.
  Alert/found escalation interrupts lower-priority chatter and takes its playback
  slot, so an ambient cooldown cannot swallow an important reaction.
- Every loaded NPC may speak over time. Only simultaneous playback is capped
  (1-4 voices, default 4); the plugin never chooses a permanent four-NPC subset.
- Uses replaceable local Japanese short-reaction WAVs for every subtitle language.
- Selects editable subtitles independently from audio. Users can change one-line
  subtitle candidates in the control center without regenerating any voice file.
- Detects young/older and female/male NPC avatar types. Each of the four profiles
  has an independent subtitle pool; older voices also receive subtle local pitch
  shaping until dedicated age-specific recordings are installed.
  Interaction (`aftermath`) text supports multi-line paragraphs separated by a
  blank line, and displays one complete paragraph per trigger.
- Falls back to built-in subtitles when a matching WAV is not installed.
- Labels subtitles with the NPC's screen direction (left/right/front/behind) and distance.
- Selects the bundled female/male voice using the NPC's real gender metadata. Custom
  packs can override a state with folders such as `young_female` or `older_male`.
- Writes a local NPC metadata snapshot to
  `BepInEx/config/ManakaNpcVoices.npc_profiles.csv`, including age/gender class,
  inferred role, avatar/fixed type, hair/body/face indices, and hair material name.
- Logs each queued and played trigger to `BepInEx/LogOutput.log` while
  `DiagnosticLogging = true`.
- When Custom Missions 2 is installed, the optional
  `ManakaNpcVoices.CustomMissions2.dll` bridge adds an `NPC VOICE` app to its
  in-game phone. The page controls the master switch, subtitle language, local audio,
  subtitles, volume, simultaneous voices, per-state cooldowns, and preview.
- The CM2 bridge is a separate DLL: removing it only removes the phone page and
  does not disable the core NPC voice plugin.

Build and deploy to a local test copy:

```powershell
.\build_plugin.ps1 -GameDir "C:\path\to\SecretFlasherManaka v1.1.3" -Deploy
```

The core plugin requires only BepInEx 6 IL2CPP. NPCBehaviorModifier is detected
at runtime and is optional; it only adds dialogue during its post-failure
interaction. Custom Missions 2 is also optional and is used only by the separate
phone-settings bridge DLL.

## One-click user installation

The packaged Manaka × DG-LAB Control Center includes this first-party
plugin, Japanese reaction audio, and Chinese, Japanese, and English subtitle text. Select the
game root, fully exit the game, open **NPC Voices**, then choose **Install NPC
Voices**. The installer copies the core DLL, the Japanese runtime WAV files,
editable subtitle defaults,
and the optional Custom Missions 2 phone bridge when CM2 is present.

For manual testing/distribution, build a standalone ZIP with:

```powershell
.\package_manual_release.ps1 -GameDir "C:\path\to\SecretFlasherManaka v1.1.3"
```

The ZIP places the core under `BepInEx/` and keeps the CM2 bridge under a clearly
labelled optional folder. It does not include or depend on NPCBehaviorModifier.

Users never need a Fish Audio API key. Subtitle language, local audio, and subtitles can
be selected in the control center; the same settings remain available from the
Custom Missions 2 phone page while the game is running.

## Fish Audio batch generation (development only)

Voice generation is a maintainer-only workflow. The optional saved API key is
protected by Windows DPAPI for the current Windows account and stored outside the
repository under `%LOCALAPPDATA%\ManakaDGLab`. It is never written to
`config.json`, logs, the game, or a release archive.

The same workflow is available as a CLI. Literal command-line keys are
intentionally unsupported because they may leak through process listings:

```powershell
.\devtools\save_fish_api_key.ps1
.\devtools\generate_fish_voice_pack.ps1 -State alert -DryRun
.\devtools\generate_fish_voice_pack.ps1 -Force
```

The first command prompts securely once. Later generation runs load that
credential automatically. Pass `-ResetApiKey` to the generator to replace an
expired key. The four selected Japanese reference IDs live in
`devtools/profile_interjection_lines.json`.

Generated files use the runtime layout
`VoicePacks/ja/<state>/<profile>/voice_a_01.wav`, where profile is one of
`young_female`, `young_male`, `older_female`, or `older_male`. The emotion and pacing prompt
stays in `devtools/profile_interjection_lines.json`; bracketed Fish directives are never
shown as subtitles. Editable default text lives in `SubtitleLines/`, while local
user overrides live under `BepInEx/config/ManakaNpcVoices/lines`. Official voice
reference IDs are pinned in the manifest so generation does not depend on changing
search results.

## Offline-only runtime rule

The deployed BepInEx plugin must never open a network connection or call a TTS/API
service. It only reads local PCM WAV and subtitle files. TTS generation belongs in
`devtools/`, runs only during development, and is never copied into the game.

Run `devtools/verify_offline.ps1` after every runtime change.

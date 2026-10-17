# Runtime network policy

`ManakaNpcVoices.dll` is an offline-only game plugin.

Runtime code must not:

- use HTTP, WebSocket, UDP, TCP, DNS, browser automation, or cloud SDKs;
- contain or read API keys, access tokens, or cloud credentials;
- send gameplay, player, NPC, file, machine, or usage data anywhere;
- download voices, models, updates, manifests, or configuration;
- execute the developer TTS generator.

Runtime code may only read local configuration, local subtitle text, and local
16-bit PCM WAV files from its own BepInEx plugin directory.

TTS services are permitted only in the separate developer generation workflow,
including the control center's explicit Voice Studio page. That page writes local
assets and is never invoked by the game plugin.
Generated files must be reviewed before bundling, and their provider/model terms
must allow the intended distribution.

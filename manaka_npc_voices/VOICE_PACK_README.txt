Manaka NPC Voices - voice pack layout

Put the active uncompressed 16-bit PCM WAV files in:

  VoicePacks/ja/ambient
  VoicePacks/ja/phone
  VoicePacks/ja/watching
  VoicePacks/ja/alert
  VoicePacks/ja/found
  VoicePacks/ja/failure
  VoicePacks/ja/aftermath

Dedicated actor folders may be placed below each state:

  VoicePacks/ja/alert/young_female
  VoicePacks/ja/alert/young_male
  VoicePacks/ja/alert/older_female
  VoicePacks/ja/alert/older_male

Young NPCs randomly mix their matching root voice_a/voice_b clips with the
matching profile folder. Older NPCs use their dedicated profile folder and only
fall back to the root actor when that folder is unavailable.

Audio always comes from the Japanese folders above. The zh, ja, and en
folders select subtitle text only.

Profile-aware subtitle defaults are stored in each language's profiles.txt.
The supported keys are young_female, young_male, older_female, and older_male.
User edits are saved as state.profile.txt under the config override folder.

Each state folder also contains a UTF-8 lines.txt. Every non-empty line is an
editable subtitle candidate. Short reaction audio is selected independently,
so changing dialogue never requires regenerating speech. Ambient currently
reuses phone reactions; Aftermath reuses failure reactions.

The aftermath state uses paragraphs instead: consecutive lines belong to one
paragraph, and a blank line separates selectable paragraphs. One complete
paragraph remains visible during each interaction trigger.

  ja/alert/voice_a_01.wav
  zh/alert/lines.txt

The active voice pack uses Japanese short reaction clips for every subtitle
language. User subtitle overrides are stored under
BepInEx/config/ManakaNpcVoices/lines and are not replaced by repair installs.
If a state folder has no WAV file, the plugin still shows a local subtitle.
Settings are created in BepInEx/config/local.manaka.npcvoices.cfg after first run.

Do not put API keys in this directory or distribute them with the plugin.

AI audio disclosure
-------------------
The bundled Japanese reaction clips were generated during development with
the Fish Audio API. The runtime is fully offline and does not ship or request
an API key. Selected public reference model IDs:

  young_female  0089dce5fefb4c6ba9b9f2f0debe1ddc
  young_male    8f99ad75c8184f1db0c21d3a906445a4
  older_female  0429f2b252464b88b2ab2128f084290c
  older_male    a365c3050dd04026a81291145e017d6f

Model pages use https://fish.audio/app/m/<model-id>. These are AI-generated
reactions, not performances recorded for this project by human voice actors.

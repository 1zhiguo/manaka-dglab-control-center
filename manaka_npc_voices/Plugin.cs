using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using ExposureUnnoticed2.Object3D.NPC.Script;
using ExposureUnnoticed2.Object3D.Player.Scripts;
using ExposureUnnoticed2.Scripts.InGame;
using UnityEngine;
using UnityEngine.UI;

namespace ManakaNpcVoices
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    public sealed class Plugin : BasePlugin
    {
        public const string PluginGuid = "local.manaka.npcvoices";
        public const string PluginName = "Manaka NPC Voices";
        public const string PluginVersion = "0.6.0";

        private Harmony _harmony;
        internal static ManualLogSource PluginLog;
        internal static PluginSettings Settings;
        internal static ConfigFile PluginConfig;
        internal static Harmony HarmonyInstance;

        public override void Load()
        {
            PluginLog = Log;
            PluginConfig = Config;
            Settings = new PluginSettings(Config);
            NpcVoiceRuntime.Start();
            _harmony = new Harmony(PluginGuid);
            HarmonyInstance = _harmony;
            _harmony.PatchAll();
            OptionalNpcBehaviorBridge.EnsurePatched(_harmony);
            Log.LogInfo("NPC voice prototype enabled. Language=" + Settings.Language.Value);
            Log.LogInfo("Voice packs: " + NpcVoiceRuntime.VoicePackRoot);
        }

        public override bool Unload()
        {
            if (_harmony != null)
            {
                _harmony.UnpatchSelf();
            }
            HarmonyInstance = null;

            NpcVoiceRuntime.Stop();
            return true;
        }
    }

    /// <summary>
    /// Stable, deliberately small surface used by optional UI integrations.
    /// Keeping this API in the core plugin lets the Custom Missions 2 bridge be
    /// removed without affecting NPC voices when CM2 is not installed.
    /// </summary>
    public static class NpcVoiceSettingsApi
    {
        public static bool IsReady { get { return Plugin.Settings != null; } }

        public static bool Enabled
        {
            get { return IsReady && Plugin.Settings.Enabled.Value; }
            set { if (IsReady) Plugin.Settings.Enabled.Value = value; }
        }

        public static bool VoiceEnabled
        {
            get { return IsReady && Plugin.Settings.VoiceEnabled.Value; }
            set { if (IsReady) Plugin.Settings.VoiceEnabled.Value = value; }
        }

        public static bool SubtitlesEnabled
        {
            get { return IsReady && Plugin.Settings.SubtitlesEnabled.Value; }
            set { if (IsReady) Plugin.Settings.SubtitlesEnabled.Value = value; }
        }

        public static string Language
        {
            get { return !IsReady ? "zh" : NormalizeLanguage(Plugin.Settings.Language.Value); }
            set { if (IsReady) Plugin.Settings.Language.Value = NormalizeLanguage(value); }
        }

        public static float Volume
        {
            get { return !IsReady ? 0.85f : Plugin.Settings.Volume.Value; }
            set { if (IsReady) Plugin.Settings.Volume.Value = Mathf.Clamp01(value); }
        }

        public static int MaxConcurrentVoices
        {
            get { return !IsReady ? 4 : Plugin.Settings.MaxConcurrentVoices.Value; }
            set { if (IsReady) Plugin.Settings.MaxConcurrentVoices.Value = Math.Max(1, Math.Min(4, value)); }
        }

        public static float PhoneCooldown
        {
            get { return !IsReady ? 90f : Plugin.Settings.PhoneCooldown.Value; }
            set { if (IsReady) Plugin.Settings.PhoneCooldown.Value = Mathf.Clamp(value, 15f, 300f); }
        }

        public static float AmbientCooldown
        {
            get { return !IsReady ? 75f : Plugin.Settings.AmbientCooldown.Value; }
            set { if (IsReady) Plugin.Settings.AmbientCooldown.Value = Mathf.Clamp(value, 20f, 300f); }
        }

        public static float AlertCooldown
        {
            get { return !IsReady ? 16f : Plugin.Settings.AlertCooldown.Value; }
            set { if (IsReady) Plugin.Settings.AlertCooldown.Value = Mathf.Clamp(value, 3f, 120f); }
        }

        public static float FoundCooldown
        {
            get { return !IsReady ? 45f : Plugin.Settings.FoundCooldown.Value; }
            set { if (IsReady) Plugin.Settings.FoundCooldown.Value = Mathf.Clamp(value, 5f, 180f); }
        }

        public static void Save()
        {
            if (Plugin.PluginConfig != null) Plugin.PluginConfig.Save();
        }

        public static void Preview()
        {
            if (IsReady) NpcVoiceRuntime.Preview();
        }

        private static string NormalizeLanguage(string language)
        {
            string value = (language ?? "zh").Trim().ToLowerInvariant();
            if (value.StartsWith("ja")) return "ja";
            if (value.StartsWith("en")) return "en";
            return "zh";
        }
    }

    internal sealed class PluginSettings
    {
        internal readonly ConfigEntry<bool> Enabled;
        internal readonly ConfigEntry<string> Language;
        internal readonly ConfigEntry<bool> VoiceEnabled;
        internal readonly ConfigEntry<bool> SubtitlesEnabled;
        internal readonly ConfigEntry<float> PerNpcCooldown;
        internal readonly ConfigEntry<float> GlobalCooldown;
        internal readonly ConfigEntry<float> AmbientCooldown;
        internal readonly ConfigEntry<float> PhoneCooldown;
        internal readonly ConfigEntry<float> AlertCooldown;
        internal readonly ConfigEntry<float> FoundCooldown;
        internal readonly ConfigEntry<float> AlertJumpThreshold;
        internal readonly ConfigEntry<float> WatchingMinimumStrangeness;
        internal readonly ConfigEntry<float> AmbientTriggerDistance;
        internal readonly ConfigEntry<float> PhoneTriggerDistance;
        internal readonly ConfigEntry<float> WatchingTriggerDistance;
        internal readonly ConfigEntry<float> AlertTriggerDistance;
        internal readonly ConfigEntry<float> FoundTriggerDistance;
        internal readonly ConfigEntry<bool> RequireVisibleForAmbient;
        internal readonly ConfigEntry<bool> DiagnosticLogging;
        internal readonly ConfigEntry<int> MaxConcurrentVoices;
        internal readonly ConfigEntry<float> Volume;
        internal readonly ConfigEntry<float> MinDistance;
        internal readonly ConfigEntry<float> MaxDistance;

        internal PluginSettings(ConfigFile config)
        {
            Enabled = config.Bind("General", "Enabled", true, "Enable NPC voices and subtitles.");
            Language = config.Bind("General", "Language", "zh", "Subtitle text language: zh, ja, or en. Audio always uses the Japanese reaction pack.");
            VoiceEnabled = config.Bind("General", "VoiceEnabled", true, "Play local WAV files when available.");
            SubtitlesEnabled = config.Bind("General", "SubtitlesEnabled", true, "Show compact bottom-center subtitles.");
            PerNpcCooldown = config.Bind("Triggers", "PerNpcCooldownSeconds", 18f, "Minimum seconds between lines from the same NPC.");
            GlobalCooldown = config.Bind("Triggers", "GlobalCooldownSeconds", 2.5f, "Minimum seconds between any two NPC lines.");
            AmbientCooldown = config.Bind("Triggers", "AmbientCooldownSeconds", 75f, "Minimum seconds between ordinary muttering lines from the same NPC.");
            PhoneCooldown = config.Bind("Triggers", "PhoneCooldownSeconds", 90f, "Minimum seconds between phone chatter from the same NPC.");
            AlertCooldown = config.Bind("Triggers", "AlertCooldownSeconds", 16f, "Minimum seconds between alert lines from the same NPC.");
            FoundCooldown = config.Bind("Triggers", "FoundCooldownSeconds", 45f, "Minimum seconds between found lines from the same NPC.");
            AlertJumpThreshold = config.Bind("Triggers", "AlertJumpThreshold", 0.08f, "A sudden normalized suspicion increase at or above this value triggers an alert line (0.08 = 8%).");
            WatchingMinimumStrangeness = config.Bind("Triggers", "WatchingMinimumStrangeness", 0.10f, "Minimum normalized suspicion required before a watching reaction can speak (0.10 = 10%).");
            AmbientTriggerDistance = config.Bind("Triggers", "AmbientTriggerDistance", 10f, "Maximum player distance for ordinary ambient muttering.");
            PhoneTriggerDistance = config.Bind("Triggers", "PhoneTriggerDistance", 7f, "Maximum player distance for phone chatter.");
            WatchingTriggerDistance = config.Bind("Triggers", "WatchingTriggerDistance", 8f, "Maximum player distance for a watching reaction.");
            AlertTriggerDistance = config.Bind("Triggers", "AlertTriggerDistance", 12f, "Maximum player distance for an alert reaction.");
            FoundTriggerDistance = config.Bind("Triggers", "FoundTriggerDistance", 16f, "Maximum player distance for a confirmed-found reaction.");
            RequireVisibleForAmbient = config.Bind("Triggers", "RequireVisibleForAmbient", true, "Only allow nearby/watching chatter from an NPC visible in the camera area.");
            DiagnosticLogging = config.Bind("Debug", "DiagnosticLogging", true, "Write trigger decisions to BepInEx/LogOutput.log.");
            MaxConcurrentVoices = config.Bind("Audio", "MaxConcurrentVoices", 4, "Maximum simultaneous NPC voices (1-4). This never limits how many NPCs are allowed to speak over time.");
            Volume = config.Bind("Audio", "Volume", 0.85f, "Voice volume from 0 to 1.");
            MinDistance = config.Bind("Audio", "MinDistance", 1.5f, "Distance where a 3D voice begins to fade.");
            MaxDistance = config.Bind("Audio", "MaxDistance", 18f, "Distance where a 3D voice becomes inaudible.");

            // Versions through 0.3.2 treated the game's normalized 0-1
            // suspicion value as if it were 0-100. Repair those persisted
            // defaults automatically so existing users are not left with
            // triggers that can never fire.
            if (AlertJumpThreshold.Value > 1f) AlertJumpThreshold.Value = 0.08f;
            if (WatchingMinimumStrangeness.Value > 1f) WatchingMinimumStrangeness.Value = 0.10f;
        }
    }

    internal enum VoiceState
    {
        None = 0,
        Ambient = 1,
        Phone = 2,
        Watching = 3,
        Alert = 4,
        Found = 5,
        Failure = 6,
        Aftermath = 7
    }

    internal sealed class NpcRuntime
    {
        internal VoiceState State;
        internal VoiceState PendingState;
        internal float PendingExpiresAt;
        internal float LastSpokenAt = -999f;
        internal VoiceState LastSpokenState;
        internal readonly Dictionary<VoiceState, float> LastSpokenByState = new Dictionary<VoiceState, float>();
        internal float LastSeenAt;
        internal float LastStrangeness;
        internal bool HasSample;
        internal VoiceState LastQueuedState;
        internal float LastQueuedAt = -999f;
        internal float AmbientObservedSince = -1f;
        internal float NextAmbientSpeechAt = -1f;
        internal float PhoneObservedSince = -1f;
        internal float NextPhoneSpeechAt = -1f;
        internal AudioSource Source;
        internal VoiceState PlayingState;
        internal float AudioStopAt = -1f;
        internal NpcController Npc;
        internal NpcProfile Profile;
    }

    internal sealed class NpcProfile
    {
        internal string Gender;
        internal string Age;
        internal string Role;
        internal string VoiceKey;
        internal string AvatarType;
        internal string FixedType;
        internal int HairIndex = -1;
        internal int BodyIndex = -1;
        internal int FaceIndex = -1;
        internal string HairMaterial;
    }

    [HarmonyPatch(typeof(PlayerController), nameof(PlayerController.OnFoundStrangerEvent))]
    internal static class PlayerFoundPatch
    {
        [HarmonyPrefix]
        private static void Prefix(NpcController __0)
        {
            NpcVoiceRuntime.NotifyFound(__0, "PlayerController.OnFoundStrangerEvent");
        }
    }

    [HarmonyPatch(typeof(NpcStrangenessManager), nameof(NpcStrangenessManager.OnStagger))]
    internal static class NpcStaggerPatch
    {
        [HarmonyPostfix]
        private static void Postfix(NpcStrangenessManager __instance)
        {
            if (__instance != null && __instance.nca != null)
            {
                NpcVoiceRuntime.NotifyAlert(__instance.nca.NpcController, "NpcStrangenessManager.OnStagger", 0f, 0f);
            }
        }
    }

    [HarmonyPatch(typeof(NpcStrangenessManager), nameof(NpcStrangenessManager.ForceSetStrangeness))]
    internal static class NpcForceStrangenessPatch
    {
        [HarmonyPrefix]
        private static void Prefix(NpcStrangenessManager __instance, ref float __state)
        {
            __state = __instance != null && __instance.Strangeness != null
                ? __instance.Strangeness.Value
                : 0f;
        }

        [HarmonyPostfix]
        private static void Postfix(NpcStrangenessManager __instance, float __state)
        {
            if (__instance == null || __instance.nca == null || __instance.Strangeness == null)
            {
                return;
            }
            float current = __instance.Strangeness.Value;
            if (current - __state >= Math.Max(0.001f, Plugin.Settings.AlertJumpThreshold.Value))
            {
                NpcVoiceRuntime.NotifyAlert(__instance.nca.NpcController,
                    "NpcStrangenessManager.ForceSetStrangeness", __state, current);
            }
        }
    }

    [HarmonyPatch(typeof(GameOverController), nameof(GameOverController.OnGameOverEvent))]
    internal static class GameOverPatch
    {
        [HarmonyPrefix]
        private static void Prefix()
        {
            NpcVoiceRuntime.NotifyGameOver("GameOverController.OnGameOverEvent");
        }
    }

    internal sealed class VoiceLine
    {
        internal string Subtitle;
        internal string WavPath;
    }

    [HarmonyPatch(typeof(PlayerController), nameof(PlayerController.OnUpdate))]
    internal static class PlayerUpdatePatch
    {
        [HarmonyPostfix]
        private static void Postfix()
        {
            NpcVoiceRuntime.Tick();
        }
    }

    /// <summary>
    /// NPCBehaviorModifier is optional and is not referenced at build time.  When
    /// it is present, patch its scene lifecycle by name so the core voice plugin
    /// remains loadable for users who do not install that mod.
    /// </summary>
    internal static class OptionalNpcBehaviorBridge
    {
        private static bool _patched;
        private static float _nextAttemptAt;

        internal static void EnsurePatched(Harmony harmony)
        {
            if (_patched || harmony == null || Time.unscaledTime < _nextAttemptAt)
            {
                return;
            }
            _nextAttemptAt = Time.unscaledTime + 5f;

            try
            {
                // AccessTools.TypeByName enumerates every loaded Unity interop
                // assembly.  Several of those assemblies intentionally contain
                // types that cannot be resolved without optional game modules,
                // so polling it produced a large TypeLoadException storm.  The
                // optional mod owns the interaction classes; ask only its own
                // assembly for exact types and remain silent when it is absent.
                Assembly behaviorAssembly = null;
                foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    string assemblyName = assembly.GetName().Name ?? string.Empty;
                    if (!string.Equals(assemblyName, "NPCBehaviorModifier", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }
                    behaviorAssembly = assembly;
                    break;
                }
                if (behaviorAssembly == null)
                {
                    return;
                }

                // Current 1.1.4 builds enter the post-capture scene through
                // CoroutineHelper.StartSexDelayRoutine(NpcController).
                Type coroutineType = behaviorAssembly.GetType("CoroutineHelper", false);
                MethodInfo coroutineStart = coroutineType == null
                    ? null
                    : AccessTools.Method(coroutineType, "StartSexDelayRoutine", new Type[] { typeof(NpcController) });
                if (coroutineStart != null)
                {
                    harmony.Patch(coroutineStart,
                        postfix: new HarmonyMethod(typeof(OptionalNpcBehaviorBridge), nameof(InteractionStartedCoroutinePostfix)));
                    Type[] nestedTypes = coroutineType.GetNestedTypes(BindingFlags.Public | BindingFlags.NonPublic);
                    for (int index = 0; index < nestedTypes.Length; index++)
                    {
                        if (nestedTypes[index].Name.IndexOf("<SexFlowCoroutine>", StringComparison.Ordinal) < 0)
                        {
                            continue;
                        }
                        MethodInfo moveNext = AccessTools.Method(nestedTypes[index], "MoveNext", Type.EmptyTypes);
                        if (moveNext != null)
                        {
                            harmony.Patch(moveNext,
                                postfix: new HarmonyMethod(typeof(OptionalNpcBehaviorBridge), nameof(InteractionCoroutineMoveNextPostfix)));
                        }
                    }
                    _patched = true;
                    Plugin.PluginLog.LogInfo("NPCBehaviorModifier 1.1.4 interaction bridge enabled.");
                    return;
                }

                // Keep compatibility with the later queue-based variant.
                Type queueType = behaviorAssembly.GetType("SexQueue", false);
                MethodInfo queueStart = queueType == null
                    ? null
                    : AccessTools.Method(queueType, "StartNpcScene", new Type[] { typeof(NpcController) });
                if (queueStart != null)
                {
                    harmony.Patch(queueStart,
                        postfix: new HarmonyMethod(typeof(OptionalNpcBehaviorBridge), nameof(InteractionStartedQueuePostfix)));
                    PatchEndMethod(harmony, queueType, "ReturnToBusiness", new Type[] { typeof(NpcController) }, nameof(InteractionEndedWithNpcPostfix));
                    PatchEndMethod(harmony, queueType, "FinishQueue", Type.EmptyTypes, nameof(InteractionEndedPostfix));
                    PatchEndMethod(harmony, queueType, "ForceFinishScene", new Type[] { typeof(string) }, nameof(InteractionEndedPostfix));

                    _patched = true;
                    Plugin.PluginLog.LogInfo("NPCBehaviorModifier queue interaction bridge enabled.");
                    return;
                }

                Plugin.PluginLog.LogWarning("NPCBehaviorModifier detected, but no supported interaction entry point was found.");
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("Could not enable NPCBehaviorModifier interaction bridge: " + error.Message);
            }
        }

        private static void PatchEndMethod(Harmony harmony, Type type, string name, Type[] parameters, string postfixName)
        {
            MethodInfo method = AccessTools.Method(type, name, parameters);
            if (method != null)
            {
                harmony.Patch(method, postfix: new HarmonyMethod(typeof(OptionalNpcBehaviorBridge), postfixName));
            }
        }

        private static void InteractionStartedCoroutinePostfix(NpcController __0)
        {
            NpcVoiceRuntime.NotifyInteractionStarted(__0, "NPCBehaviorModifier.StartSexDelayRoutine");
        }

        private static void InteractionStartedQueuePostfix(NpcController __0)
        {
            NpcVoiceRuntime.NotifyInteractionStarted(__0, "NPCBehaviorModifier.StartNpcScene");
        }

        private static void InteractionCoroutineMoveNextPostfix(bool __result)
        {
            if (!__result)
            {
                NpcVoiceRuntime.NotifyInteractionEnded(null, "NPCBehaviorModifier.SexFlowCoroutine finished");
            }
        }

        private static void InteractionEndedWithNpcPostfix(NpcController __0)
        {
            NpcVoiceRuntime.NotifyInteractionEnded(__0, "NPCBehaviorModifier.ReturnToBusiness");
        }

        private static void InteractionEndedPostfix()
        {
            NpcVoiceRuntime.NotifyInteractionEnded(null, "NPCBehaviorModifier scene finished");
        }
    }

    internal static class NpcVoiceRuntime
    {
        private const float PollInterval = 0.20f;
        private const float MaxAudioClipSeconds = 8f;
        private static readonly Dictionary<int, NpcRuntime> Npcs = new Dictionary<int, NpcRuntime>();
        private static readonly Dictionary<string, AudioClip> ClipCache = new Dictionary<string, AudioClip>(StringComparer.OrdinalIgnoreCase);
        private static readonly System.Random Random = new System.Random();
        private static float _nextPollAt;
        private static float _lastGlobalSpeechAt = -999f;
        private static float _lastFailureAt = -999f;
        private static bool _wasGlobalFound;
        private static bool _wasGameOver;
        private static NpcController _interactionNpc;
        private static float _nextInteractionSpeechAt = -1f;
        private static float _interactionEndsAt = -1f;
        private static GameObject _globalAudioRoot;
        private static AudioSource _globalSource;
        private static float _globalAudioStopAt = -1f;
        private static readonly HashSet<string> WrittenProfiles = new HashSet<string>(StringComparer.Ordinal);
        private static bool _started;

        internal static string VoicePackRoot
        {
            get { return Path.Combine(Paths.PluginPath, "ManakaNpcVoices", "VoicePacks"); }
        }

        internal static string ProfileSnapshotPath
        {
            get { return Path.Combine(Paths.ConfigPath, "ManakaNpcVoices.npc_profiles.csv"); }
        }

        internal static string SubtitleOverrideRoot
        {
            get { return Path.Combine(Paths.ConfigPath, "ManakaNpcVoices", "lines"); }
        }

        internal static void Start()
        {
            Directory.CreateDirectory(VoicePackRoot);
            WrittenProfiles.Clear();
            try
            {
                File.WriteAllText(ProfileSnapshotPath,
                    "npc_id,voice_key,gender,age,role,avatar_type,fixed_type,hair_index,body_index,face_index,hair_material\r\n");
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("Could not initialize NPC profile snapshot: " + error.Message);
            }
            _started = true;
        }

        internal static void Stop()
        {
            _started = false;
            foreach (NpcRuntime runtime in Npcs.Values)
            {
                if (runtime.Source != null)
                {
                    UnityEngine.Object.Destroy(runtime.Source);
                }
            }
            Npcs.Clear();
            _interactionNpc = null;
            _nextInteractionSpeechAt = -1f;
            _interactionEndsAt = -1f;

            foreach (AudioClip clip in ClipCache.Values)
            {
                if (clip != null)
                {
                    UnityEngine.Object.Destroy(clip);
                }
            }
            ClipCache.Clear();
            if (_globalAudioRoot != null)
            {
                UnityEngine.Object.Destroy(_globalAudioRoot);
                _globalAudioRoot = null;
                _globalSource = null;
            }
            SubtitleOverlay.Destroy();
        }

        internal static void NotifyFound(NpcController npc, string reason)
        {
            if (!IsEnabled() || IsGameOverNow() || npc == null || !npc.IsAlive)
            {
                return;
            }

            float now = Time.unscaledTime;
            NpcRuntime runtime = GetRuntime(npc, now);
            if (!IsWithinTriggerDistance(npc, VoiceState.Found))
            {
                LogTrigger("SKIP_DISTANCE", npc, VoiceState.Found, reason, runtime.LastStrangeness, npc.StrangenessValue);
                return;
            }
            Queue(runtime, VoiceState.Found, now, 8f, reason);
            TrySpeakQueued(now);
        }

        internal static void NotifyAlert(NpcController npc, string reason, float previousStrangeness, float currentStrangeness)
        {
            if (!IsEnabled() || IsGameOverNow() || npc == null || !npc.IsAlive)
            {
                return;
            }

            float now = Time.unscaledTime;
            NpcRuntime runtime = GetRuntime(npc, now);
            if (!IsWithinTriggerDistance(npc, VoiceState.Alert))
            {
                LogTrigger("SKIP_DISTANCE", npc, VoiceState.Alert, reason, previousStrangeness, currentStrangeness);
                return;
            }
            Queue(runtime, VoiceState.Alert, now, 8f, reason, previousStrangeness, currentStrangeness);
            TrySpeakQueued(now);
        }

        internal static void NotifyGameOver(string reason)
        {
            if (!IsEnabled())
            {
                return;
            }

            float now = Time.unscaledTime;
            if (now - _lastFailureAt < 3f)
            {
                return;
            }
            _lastFailureAt = now;
            _wasGameOver = true;
            _interactionNpc = null;
            _nextInteractionSpeechAt = -1f;
            _interactionEndsAt = -1f;

            foreach (NpcRuntime runtime in Npcs.Values)
            {
                runtime.PendingState = VoiceState.None;
                if (runtime.Source != null && runtime.Source.isPlaying)
                {
                    runtime.Source.Stop();
                }
                runtime.PlayingState = VoiceState.None;
            }
            _lastGlobalSpeechAt = now;

            NpcController culprit = FindCulprit(NpcManager.Instance);
            int voiceId = culprit != null ? culprit.id : 0;
            NpcProfile profile = culprit != null ? GetRuntime(culprit, now).Profile : null;
            VoiceLine line = SelectLine(VoiceState.Failure, voiceId, profile);
            string speaker = culprit != null ? BuildSpeakerLabel(culprit, profile) : LocalizedNpcLabel("nearby");
            float distance = culprit != null ? culprit.PlayerDistance : -1f;
            LogTrigger("SPEAK", culprit, VoiceState.Failure, reason, 0f, 0f);

            if (Plugin.Settings.SubtitlesEnabled.Value)
            {
                SubtitleOverlay.Show(speaker, line.Subtitle, distance);
            }
            if (Plugin.Settings.VoiceEnabled.Value && !string.IsNullOrEmpty(line.WavPath))
            {
                AudioClip clip = GetClip(line.WavPath);
                if (clip != null)
                {
                    AudioSource source = EnsureGlobalSource();
                    StopSource(source);
                    ConfigureSource(source, false);
                    ApplyVoiceProfile(source, profile);
                    source.clip = clip;
                    source.Play();
                    _globalAudioStopAt = GetAudioStopAt(clip, now, source.pitch);
                    Plugin.PluginLog.LogInfo("NPC voice audio started (failure): " + Path.GetFileName(line.WavPath));
                }
            }
        }

        internal static void NotifyInteractionStarted(NpcController npc, string reason)
        {
            if (!IsEnabled() || npc == null || npc.GameObject == null)
            {
                return;
            }

            float now = Time.unscaledTime;
            NpcRuntime runtime = GetRuntime(npc, now);
            _interactionNpc = npc;
            _nextInteractionSpeechAt = now + 1.5f;
            _interactionEndsAt = now + 180f;
            LogTrigger("INTERACTION_START", npc, VoiceState.Aftermath, reason,
                runtime.LastStrangeness, npc.StrangenessValue);
        }

        internal static void NotifyInteractionEnded(NpcController npc, string reason)
        {
            if (_interactionNpc == null || (npc != null && npc.id != _interactionNpc.id))
            {
                return;
            }
            Plugin.PluginLog.LogInfo("NPC voice interaction ended: " + reason);
            _interactionNpc = null;
            _nextInteractionSpeechAt = -1f;
            _interactionEndsAt = -1f;
        }

        internal static void Preview()
        {
            VoiceLine line = SelectLine(VoiceState.Alert, 0, null);
            if (Plugin.Settings.SubtitlesEnabled.Value)
            {
                SubtitleOverlay.Show(LocalizedNpcLabel("nearby"), line.Subtitle, 0f);
            }
            if (Plugin.Settings.VoiceEnabled.Value && !string.IsNullOrEmpty(line.WavPath))
            {
                AudioClip clip = GetClip(line.WavPath);
                if (clip != null)
                {
                    AudioSource source = EnsureGlobalSource();
                    StopSource(source);
                    ConfigureSource(source, false);
                    source.clip = clip;
                    source.Play();
                    _globalAudioStopAt = GetAudioStopAt(clip, Time.unscaledTime, source.pitch);
                }
            }
        }

        internal static void Tick()
        {
            if (!_started || Plugin.Settings == null)
            {
                return;
            }

            float now = Time.unscaledTime;
            EnforceAudioSafety(now);
            if (!Plugin.Settings.Enabled.Value)
            {
                SubtitleOverlay.Hide();
                return;
            }

            SubtitleOverlay.Tick();
            OptionalNpcBehaviorBridge.EnsurePatched(Plugin.HarmonyInstance);
            if (now < _nextPollAt)
            {
                return;
            }
            _nextPollAt = now + PollInterval;

            try
            {
                TickInteraction(now);
                SampleNpcs();
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("NPC voice sample failed: " + error.Message);
            }
        }

        private static void TickInteraction(float now)
        {
            if (_interactionNpc == null)
            {
                return;
            }
            if (now > _interactionEndsAt || _interactionNpc.GameObject == null)
            {
                NotifyInteractionEnded(null, "interaction timeout or NPC removed");
                return;
            }
            if (now < _nextInteractionSpeechAt)
            {
                return;
            }

            NpcRuntime runtime = GetRuntime(_interactionNpc, now);
            if (CanSpeak(runtime, VoiceState.Aftermath, now))
            {
                LogTrigger("SPEAK", _interactionNpc, VoiceState.Aftermath,
                    "active NPCBehaviorModifier interaction", runtime.LastStrangeness, _interactionNpc.StrangenessValue);
                Speak(_interactionNpc, runtime, VoiceState.Aftermath, now);
                // Interaction text is a complete multi-line paragraph. Leave it
                // on screen long enough to read before choosing another paragraph.
                _nextInteractionSpeechAt = now + 20f + (float)Random.NextDouble() * 8f;
            }
            else
            {
                _nextInteractionSpeechAt = now + 0.75f;
            }
        }

        private static void SampleNpcs()
        {
            NpcManager manager = NpcManager.Instance;
            if (manager == null || manager.ExistNpcList == null)
            {
                return;
            }

            float now = Time.unscaledTime;
            bool globalFound = manager.IsSomeOnePlayerFound;
            if (globalFound && !_wasGlobalFound)
            {
                NpcController culprit = FindCulprit(manager, VoiceState.Found);
                if (culprit != null)
                {
                    NpcRuntime foundRuntime = GetRuntime(culprit, now);
                    Queue(foundRuntime, VoiceState.Found, now, 8f, "NpcManager.IsSomeOnePlayerFound edge");
                }
            }
            _wasGlobalFound = globalFound;

            bool gameOver = InGameManager.Instance != null
                && InGameManager.Instance.TempInGameState != null
                && InGameManager.Instance.TempInGameState.IsGameOver;
            if (gameOver && !_wasGameOver)
            {
                NotifyGameOver("TemporaryInGameState.IsGameOver edge");
            }
            _wasGameOver = gameOver;
            if (gameOver)
            {
                return;
            }

            for (int index = 0; index < manager.ExistNpcList.Count; index++)
            {
                NpcController npc = manager.ExistNpcList[index];
                if (npc == null || !npc.IsAlive || npc.GameObject == null)
                {
                    continue;
                }

                int id = npc.id;
                NpcRuntime runtime = GetRuntime(npc, now);

                float currentStrangeness = npc.StrangenessValue;
                float previousStrangeness = runtime.HasSample ? runtime.LastStrangeness : currentStrangeness;
                float increase = currentStrangeness - previousStrangeness;
                bool crossedAlertBand = runtime.HasSample && CrossedAlertBand(previousStrangeness, currentStrangeness);
                bool jumped = runtime.HasSample && increase >= Math.Max(0.001f, Plugin.Settings.AlertJumpThreshold.Value);
                bool usingPhone = IsUsingPhone(npc);
                bool quietAndVisible = currentStrangeness <= 0.01f
                    && IsVisibleForAmbient(npc);
                bool phoneIdle = quietAndVisible
                    && IsWithinTriggerDistance(npc, VoiceState.Phone)
                    && usingPhone;
                if (phoneIdle)
                {
                    if (runtime.PhoneObservedSince < 0f)
                    {
                        runtime.PhoneObservedSince = now;
                        runtime.NextPhoneSpeechAt = now + 6f + (float)Random.NextDouble() * 10f;
                    }
                    if (now >= runtime.NextPhoneSpeechAt)
                    {
                        Queue(runtime, VoiceState.Phone, now, 8f, "stable phone action", currentStrangeness, currentStrangeness);
                        runtime.NextPhoneSpeechAt = now + Mathf.Max(15f, Plugin.Settings.PhoneCooldown.Value)
                            + (float)Random.NextDouble() * 20f;
                    }
                }
                else
                {
                    runtime.PhoneObservedSince = -1f;
                    runtime.NextPhoneSpeechAt = -1f;
                }

                bool ambientIdle = quietAndVisible
                    && _interactionNpc == null
                    && !usingPhone
                    && IsWithinTriggerDistance(npc, VoiceState.Ambient)
                    && IsAmbientEligible(npc);
                if (ambientIdle)
                {
                    if (runtime.AmbientObservedSince < 0f)
                    {
                        runtime.AmbientObservedSince = now;
                        runtime.NextAmbientSpeechAt = now + 8f + (float)Random.NextDouble() * 10f;
                    }
                    if (now >= runtime.NextAmbientSpeechAt)
                    {
                        Queue(runtime, VoiceState.Ambient, now, 10f, "stable ambient activity",
                            currentStrangeness, currentStrangeness);
                        runtime.NextAmbientSpeechAt = now + Mathf.Max(20f, Plugin.Settings.AmbientCooldown.Value)
                            + (float)Random.NextDouble() * 30f;
                    }
                }
                else
                {
                    runtime.AmbientObservedSince = -1f;
                    runtime.NextAmbientSpeechAt = -1f;
                }

                VoiceState next = DetermineState(npc, jumped || crossedAlertBand, currentStrangeness);
                VoiceState previous = runtime.State;
                runtime.State = next;
                runtime.LastStrangeness = currentStrangeness;
                runtime.HasSample = true;
                bool escalated = next > previous;
                if (escalated && next >= VoiceState.Watching)
                {
                    string reason = jumped
                        ? "suspicion jump"
                        : crossedAlertBand ? "suspicion threshold" : "state edge";
                    Queue(runtime, next, now, next >= VoiceState.Alert ? 8f : 5f, reason, previousStrangeness, currentStrangeness);
                }
            }

            TrySpeakQueued(now);

            List<int> staleIds = new List<int>();
            foreach (KeyValuePair<int, NpcRuntime> pair in Npcs)
            {
                if (now - pair.Value.LastSeenAt > 8f)
                {
                    if (pair.Value.Source != null)
                    {
                        UnityEngine.Object.Destroy(pair.Value.Source);
                    }
                    staleIds.Add(pair.Key);
                }
            }
            for (int index = 0; index < staleIds.Count; index++)
            {
                Npcs.Remove(staleIds[index]);
            }
        }

        private static VoiceState DetermineState(NpcController npc, bool alertEdge, float strangeness)
        {
            float watchingThreshold = Mathf.Max(0f, Plugin.Settings.WatchingMinimumStrangeness.Value);
            bool sampledFound = npc.IsPlayerFound
                || (npc.stateModel != null && npc.stateModel.CurrentState == NpcStateModel.State.FoundStranger);
            // IsPlayerFound is not a reliable per-NPC culprit flag in this game:
            // ordinary passers-by can inherit it with zero suspicion. Exact
            // PlayerController events are handled by NotifyFound; this sampled
            // fallback therefore also requires evidence that this NPC observed
            // the player.
            if (sampledFound
                && IsWithinTriggerDistance(npc, VoiceState.Found)
                && IsVisibleForAmbient(npc)
                && (npc.IsWatchingStranger || strangeness >= watchingThreshold))
            {
                return VoiceState.Found;
            }
            if (IsWithinTriggerDistance(npc, VoiceState.Alert)
                && (alertEdge || (strangeness >= watchingThreshold && npc.IsRiseStrangeness)))
            {
                return VoiceState.Alert;
            }
            if (strangeness >= watchingThreshold
                && IsWithinTriggerDistance(npc, VoiceState.Watching)
                && IsVisibleForAmbient(npc)
                && npc.IsWatchingStranger)
            {
                return VoiceState.Watching;
            }
            return VoiceState.None;
        }

        private static bool CanSpeak(NpcRuntime runtime, VoiceState state, float now)
        {
            RefreshPlayingState(runtime);
            bool urgent = state >= VoiceState.Alert;
            bool priorityUpgrade = state > runtime.LastSpokenState;
            float perNpcCooldown;
            if (urgent && priorityUpgrade)
            {
                // A confirmed escalation must not be swallowed by an earlier
                // ambient line. The short global guard below still prevents two
                // hooks for the same event from producing an audible double hit.
                perNpcCooldown = 0f;
            }
            else if (state == VoiceState.Watching
                && (runtime.LastSpokenState == VoiceState.Phone || runtime.LastSpokenState == VoiceState.Ambient))
            {
                // Let the reaction follow phone chatter after a short natural
                // pause instead of waiting for the full ambient cooldown.
                perNpcCooldown = 2.5f;
            }
            else
            {
                perNpcCooldown = urgent ? 1.25f : Mathf.Max(0f, Plugin.Settings.PerNpcCooldown.Value);
            }
            float globalCooldown = urgent ? 0.65f : Mathf.Max(0f, Plugin.Settings.GlobalCooldown.Value);
            if (now - runtime.LastSpokenAt < perNpcCooldown)
            {
                return false;
            }
            float lastForState;
            if (runtime.LastSpokenByState.TryGetValue(state, out lastForState)
                && now - lastForState < CooldownFor(state))
            {
                return false;
            }
            if (now - _lastGlobalSpeechAt < globalCooldown)
            {
                return false;
            }

            int playing = CountPlayingVoices();
            if (playing < Math.Max(1, Plugin.Settings.MaxConcurrentVoices.Value))
            {
                return true;
            }

            // An urgent line may take a slot from lower-priority ambient speech.
            // The actual stop happens immediately before playback.
            if (urgent)
            {
                foreach (NpcRuntime item in Npcs.Values)
                {
                    RefreshPlayingState(item);
                    if (item.Source != null && item.Source.isPlaying && item.PlayingState < state)
                    {
                        return true;
                    }
                }
            }
            return false;
        }

        private static void Speak(NpcController npc, NpcRuntime runtime, VoiceState state, float now)
        {
            if (state >= VoiceState.Alert)
            {
                PreemptLowerPriorityVoices(state, runtime);
            }
            VoiceLine line = SelectLine(state, npc.id, runtime.Profile);
            runtime.LastSpokenAt = now;
            runtime.LastSpokenState = state;
            runtime.LastSpokenByState[state] = now;
            _lastGlobalSpeechAt = now;

            if (Plugin.Settings.SubtitlesEnabled.Value)
            {
                bool paragraph = state == VoiceState.Aftermath;
                float duration = paragraph
                    ? Mathf.Clamp(8f + line.Subtitle.Length * 0.10f, 11f, 18f)
                    : 4.5f;
                SubtitleOverlay.Show(BuildSpeakerLabel(npc, runtime.Profile), line.Subtitle,
                    npc.PlayerDistance, duration, paragraph);
            }

            if (Plugin.Settings.VoiceEnabled.Value && !string.IsNullOrEmpty(line.WavPath))
            {
                AudioClip clip = GetClip(line.WavPath);
                if (clip != null)
                {
                    if (runtime.Source == null)
                    {
                        // Never reuse the game's own NPC AudioSource: replacing its clip
                        // can silence footsteps or built-in reactions.
                        runtime.Source = npc.GameObject.AddComponent<AudioSource>();
                    }
                    StopSource(runtime.Source);
                    ConfigureSource(runtime.Source, true);
                    ApplyVoiceProfile(runtime.Source, runtime.Profile);
                    runtime.Source.clip = clip;
                    runtime.Source.Play();
                    runtime.PlayingState = state;
                    runtime.AudioStopAt = GetAudioStopAt(clip, now, runtime.Source.pitch);
                    Plugin.PluginLog.LogInfo("NPC voice audio started: npc=" + npc.id.ToString(CultureInfo.InvariantCulture)
                        + " state=" + state + " file=" + Path.GetFileName(line.WavPath));
                }
            }
        }

        private static void RefreshPlayingState(NpcRuntime runtime)
        {
            if (runtime != null && (runtime.Source == null || !runtime.Source.isPlaying))
            {
                runtime.PlayingState = VoiceState.None;
                runtime.AudioStopAt = -1f;
            }
        }

        private static void EnforceAudioSafety(float now)
        {
            bool audioAllowed = Plugin.Settings.Enabled.Value && Plugin.Settings.VoiceEnabled.Value;
            foreach (NpcRuntime runtime in Npcs.Values)
            {
                if (runtime.Source == null || !runtime.Source.isPlaying)
                {
                    RefreshPlayingState(runtime);
                    continue;
                }
                if (!audioAllowed || (runtime.AudioStopAt > 0f && now >= runtime.AudioStopAt))
                {
                    if (runtime.AudioStopAt > 0f && now >= runtime.AudioStopAt)
                    {
                        Plugin.PluginLog.LogWarning("NPC voice watchdog stopped an overlong sound.");
                    }
                    StopSource(runtime.Source);
                    runtime.PlayingState = VoiceState.None;
                    runtime.AudioStopAt = -1f;
                }
            }

            if (_globalSource != null && _globalSource.isPlaying
                && (!audioAllowed || (_globalAudioStopAt > 0f && now >= _globalAudioStopAt)))
            {
                if (_globalAudioStopAt > 0f && now >= _globalAudioStopAt)
                {
                    Plugin.PluginLog.LogWarning("NPC voice watchdog stopped an overlong global sound.");
                }
                StopSource(_globalSource);
                _globalAudioStopAt = -1f;
            }
        }

        private static float GetAudioStopAt(AudioClip clip, float now, float pitch = 1f)
        {
            float safePitch = Mathf.Max(0.1f, Mathf.Abs(pitch));
            float duration = clip != null ? clip.length / safePitch : 0f;
            return now + Mathf.Clamp(duration + 0.25f, 0.5f, MaxAudioClipSeconds);
        }

        private static void StopSource(AudioSource source)
        {
            if (source == null)
            {
                return;
            }
            source.loop = false;
            if (source.isPlaying)
            {
                source.Stop();
            }
            source.clip = null;
        }

        private static int CountPlayingVoices()
        {
            int playing = 0;
            foreach (NpcRuntime item in Npcs.Values)
            {
                RefreshPlayingState(item);
                if (item.Source != null && item.Source.isPlaying)
                {
                    playing++;
                }
            }
            return playing;
        }

        private static void PreemptLowerPriorityVoices(VoiceState state, NpcRuntime speaker)
        {
            // First interrupt this NPC's own lower-priority chatter. This makes a
            // phone/observing line yield as soon as the same NPC becomes alert.
            if (speaker != null)
            {
                RefreshPlayingState(speaker);
                if (speaker.Source != null && speaker.Source.isPlaying && speaker.PlayingState < state)
                {
                    speaker.Source.Stop();
                    speaker.PlayingState = VoiceState.None;
                    speaker.AudioStopAt = -1f;
                }
            }

            int limit = Math.Max(1, Plugin.Settings.MaxConcurrentVoices.Value);
            while (CountPlayingVoices() >= limit)
            {
                NpcRuntime candidate = null;
                foreach (NpcRuntime item in Npcs.Values)
                {
                    if (item == speaker || item.Source == null || !item.Source.isPlaying || item.PlayingState >= state)
                    {
                        continue;
                    }
                    if (candidate == null || item.PlayingState < candidate.PlayingState)
                    {
                        candidate = item;
                    }
                }
                if (candidate == null)
                {
                    break;
                }
                candidate.Source.Stop();
                candidate.PlayingState = VoiceState.None;
                candidate.AudioStopAt = -1f;
            }
        }

        private static void ConfigureSource(AudioSource source, bool spatial)
        {
            source.playOnAwake = false;
            source.loop = false;
            source.spatialBlend = spatial ? 1f : 0f;
            source.dopplerLevel = 0f;
            source.rolloffMode = AudioRolloffMode.Logarithmic;
            source.minDistance = Mathf.Max(0.1f, Plugin.Settings.MinDistance.Value);
            source.maxDistance = Mathf.Max(source.minDistance + 0.1f, Plugin.Settings.MaxDistance.Value);
            source.volume = Mathf.Clamp01(Plugin.Settings.Volume.Value);
            source.pitch = 1f;
        }

        private static void ApplyVoiceProfile(AudioSource source, NpcProfile profile)
        {
            if (source == null || profile == null)
            {
                return;
            }
            // Every age/gender profile now has a dedicated performance. Preserve
            // the actor's natural delivery instead of synthesizing age by pitch.
            source.pitch = 1f;
        }

        private static List<string> FindVoiceFiles(string directory, string prefix)
        {
            List<string> all = new List<string>();
            if (string.IsNullOrEmpty(directory) || !Directory.Exists(directory))
            {
                return all;
            }
            string[] files = Directory.GetFiles(directory, "*.wav", SearchOption.TopDirectoryOnly);
            List<string> matching = new List<string>();
            for (int index = 0; index < files.Length; index++)
            {
                all.Add(files[index]);
                if (Path.GetFileName(files[index]).StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    matching.Add(files[index]);
                }
            }
            return matching.Count > 0 ? matching : all;
        }

        private static string ChoosePlayableVoice(List<string> candidates)
        {
            // Load candidates in random order so a malformed or overlong WAV can
            // never turn a valid trigger into silence. GetClip caches both valid
            // and rejected files, so subsequent selections stay inexpensive.
            while (candidates.Count > 0)
            {
                int index = Random.Next(candidates.Count);
                string path = candidates[index];
                candidates.RemoveAt(index);
                if (GetClip(path) != null)
                {
                    return path;
                }
            }
            return null;
        }

        private static VoiceLine SelectLine(VoiceState state, int npcId, NpcProfile profile)
        {
            string textLanguage = NormalizeLanguage(Plugin.Settings.Language.Value);
            string stateName = state.ToString().ToLowerInvariant();
            string subtitleDirectory = Path.Combine(VoicePackRoot, textLanguage, stateName);
            string subtitle = SelectSubtitle(textLanguage, stateName, subtitleDirectory, state, profile);

            // Spoken reactions intentionally stay Japanese. The language option
            // controls subtitle text only, so changing it never changes the voice.
            string audioDirectory = Path.Combine(VoicePackRoot, "ja", stateName);
            if (!Directory.Exists(audioDirectory) || Directory.GetFiles(audioDirectory, "*.wav", SearchOption.AllDirectories).Length == 0)
            {
                string fallbackState = state == VoiceState.Ambient
                    ? "phone"
                    : state == VoiceState.Aftermath ? "failure" : stateName;
                audioDirectory = Path.Combine(VoicePackRoot, "ja", fallbackState);
            }
            if (Directory.Exists(audioDirectory))
            {
                string prefix = profile != null
                    ? (profile.Gender == "female" ? "voice_a_" : "voice_b_")
                    : ((npcId & 1) == 0 ? "voice_a_" : "voice_b_");
                List<string> legacyFiles = FindVoiceFiles(audioDirectory, prefix);
                List<string> candidates = new List<string>();
                string profileDirectory = profile != null
                    ? Path.Combine(audioDirectory, profile.VoiceKey)
                    : null;
                List<string> profileFiles = FindVoiceFiles(profileDirectory, prefix);

                if (profile != null && profile.Age == "older" && profileFiles.Count > 0)
                {
                    // Dedicated older voices fully replace the old pitch-shifted
                    // young actors. The legacy pool remains an emergency fallback.
                    candidates.AddRange(profileFiles);
                }
                else
                {
                    // Young NPCs retain the original actor and mix in the newly
                    // selected actor, giving each trigger a varied performance.
                    candidates.AddRange(legacyFiles);
                    candidates.AddRange(profileFiles);
                }
                if (candidates.Count == 0)
                {
                    candidates.AddRange(legacyFiles);
                }
                string path = ChoosePlayableVoice(candidates);
                if (string.IsNullOrEmpty(path) && profile != null && profile.Age == "older")
                {
                    path = ChoosePlayableVoice(legacyFiles);
                }
                if (!string.IsNullOrEmpty(path))
                {
                    return new VoiceLine { Subtitle = subtitle, WavPath = path };
                }
            }
            return new VoiceLine { Subtitle = subtitle, WavPath = null };
        }

        private static string SelectSubtitle(string language, string stateName, string bundledDirectory,
            VoiceState state, NpcProfile profile)
        {
            bool paragraphs = state == VoiceState.Aftermath;
            string profileKey = profile != null ? profile.VoiceKey : string.Empty;
            List<string> lines = new List<string>();
            if (!string.IsNullOrEmpty(profileKey))
            {
                string profileOverride = Path.Combine(SubtitleOverrideRoot, language,
                    stateName + "." + profileKey + ".txt");
                lines = paragraphs ? ReadSubtitleParagraphs(profileOverride) : ReadSubtitleLines(profileOverride);
                if (lines.Count == 0)
                {
                    string profileSource = Path.Combine(Path.GetDirectoryName(bundledDirectory), "profiles.txt");
                    lines = ReadProfileSubtitleSection(profileSource, profileKey + "." + stateName, paragraphs);
                }
            }
            // Old unprofiled overrides remain a compatible fallback.
            if (lines.Count == 0)
            {
                string genericOverride = Path.Combine(SubtitleOverrideRoot, language, stateName + ".txt");
                lines = paragraphs ? ReadSubtitleParagraphs(genericOverride) : ReadSubtitleLines(genericOverride);
            }
            if (lines.Count == 0)
            {
                lines = paragraphs
                    ? ReadSubtitleParagraphs(Path.Combine(bundledDirectory, "lines.txt"))
                    : ReadSubtitleLines(Path.Combine(bundledDirectory, "lines.txt"));
            }
            if (lines.Count == 0 && Directory.Exists(bundledDirectory))
            {
                string[] legacyFiles = Directory.GetFiles(bundledDirectory, "*.txt", SearchOption.TopDirectoryOnly);
                for (int index = 0; index < legacyFiles.Length; index++)
                {
                    if (string.Equals(Path.GetFileName(legacyFiles[index]), "lines.txt", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }
                    List<string> legacyLines = ReadSubtitleLines(legacyFiles[index]);
                    if (legacyLines.Count > 0)
                    {
                        lines.Add(legacyLines[0]);
                    }
                }
            }
            return lines.Count > 0 ? lines[Random.Next(lines.Count)] : BuiltInSubtitle(language, state);
        }

        private static List<string> ReadProfileSubtitleSection(string path, string section, bool paragraphs)
        {
            List<string> sectionLines = new List<string>();
            try
            {
                if (!File.Exists(path)) return sectionLines;
                string expected = "[" + section + "]";
                bool collecting = false;
                string[] source = File.ReadAllLines(path);
                for (int index = 0; index < source.Length; index++)
                {
                    string trimmed = source[index].Trim();
                    if (trimmed.StartsWith("[") && trimmed.EndsWith("]"))
                    {
                        if (collecting) break;
                        collecting = string.Equals(trimmed, expected, StringComparison.OrdinalIgnoreCase);
                        continue;
                    }
                    if (collecting) sectionLines.Add(source[index]);
                }
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("Could not read NPC profile subtitles '" + path + "': " + error.Message);
                return new List<string>();
            }

            if (!paragraphs)
            {
                List<string> result = new List<string>();
                for (int index = 0; index < sectionLines.Count; index++)
                {
                    string line = sectionLines[index].Trim();
                    if (!string.IsNullOrEmpty(line) && !line.StartsWith("#")) result.Add(line);
                }
                return result;
            }

            List<string> paragraphsResult = new List<string>();
            List<string> paragraph = new List<string>();
            for (int index = 0; index <= sectionLines.Count; index++)
            {
                string line = index < sectionLines.Count ? sectionLines[index].Trim() : string.Empty;
                if (string.IsNullOrEmpty(line))
                {
                    if (paragraph.Count > 0)
                    {
                        paragraphsResult.Add(string.Join("\n", paragraph.ToArray()));
                        paragraph.Clear();
                    }
                }
                else if (!line.StartsWith("#"))
                {
                    paragraph.Add(line);
                }
            }
            return paragraphsResult;
        }

        private static List<string> ReadSubtitleLines(string path)
        {
            List<string> result = new List<string>();
            try
            {
                if (!File.Exists(path))
                {
                    return result;
                }
                string[] rawLines = File.ReadAllLines(path);
                for (int index = 0; index < rawLines.Length; index++)
                {
                    string value = rawLines[index].Trim();
                    if (!string.IsNullOrEmpty(value) && !value.StartsWith("#", StringComparison.Ordinal))
                    {
                        result.Add(value);
                    }
                }
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("Could not read NPC subtitle lines '" + path + "': " + error.Message);
            }
            return result;
        }

        private static List<string> ReadSubtitleParagraphs(string path)
        {
            List<string> result = new List<string>();
            try
            {
                if (!File.Exists(path))
                {
                    return result;
                }

                List<string> paragraph = new List<string>();
                string[] rawLines = File.ReadAllLines(path);
                for (int index = 0; index < rawLines.Length; index++)
                {
                    string value = rawLines[index].Trim();
                    if (value.StartsWith("#", StringComparison.Ordinal))
                    {
                        continue;
                    }
                    if (string.IsNullOrEmpty(value))
                    {
                        AddParagraph(result, paragraph);
                        continue;
                    }
                    paragraph.Add(value);
                }
                AddParagraph(result, paragraph);
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("Could not read NPC subtitle paragraphs '" + path + "': " + error.Message);
            }
            return result;
        }

        private static void AddParagraph(List<string> result, List<string> paragraph)
        {
            if (paragraph.Count == 0)
            {
                return;
            }
            result.Add(string.Join("\n", paragraph.ToArray()));
            paragraph.Clear();
        }

        private static string NormalizeLanguage(string language)
        {
            string value = (language ?? "zh").Trim().ToLowerInvariant();
            if (value.StartsWith("ja")) return "ja";
            if (value.StartsWith("en")) return "en";
            return "zh";
        }

        private static string BuiltInSubtitle(string language, VoiceState state)
        {
            if (language == "ja")
            {
                if (state == VoiceState.Ambient) return "今日は妙に忙しいな……";
                if (state == VoiceState.Phone) return "また残業か……もう勘弁してよ。";
                if (state == VoiceState.Aftermath) return "まだ終わってないよ。";
                if (state == VoiceState.Failure) return "見つけた！もう逃げられないよ。";
                if (state == VoiceState.Found) return "見つけた！";
                if (state == VoiceState.Alert) return "今、何か見えたような…";
                if (state == VoiceState.Watching) return "あの人、何をしているんだろう？";
                return "こんにちは。";
            }
            if (language == "en")
            {
                if (state == VoiceState.Ambient) return "Why is it so busy today...?";
                if (state == VoiceState.Phone) return "More overtime again? Give me a break.";
                if (state == VoiceState.Aftermath) return "We are not finished yet.";
                if (state == VoiceState.Failure) return "Got you! You are not getting away this time.";
                if (state == VoiceState.Found) return "Hey! I saw that!";
                if (state == VoiceState.Alert) return "Wait... did I just see something?";
                if (state == VoiceState.Watching) return "What is she doing over there?";
                return "Oh, hello.";
            }
            if (state == VoiceState.Ambient) return "今天怎么这么忙……";
            if (state == VoiceState.Phone) return "又要加班，真是受够了。";
            if (state == VoiceState.Aftermath) return "事情还没结束呢。";
            if (state == VoiceState.Failure) return "抓到你了！这下你跑不掉了。";
            if (state == VoiceState.Found) return "喂！我看见了！";
            if (state == VoiceState.Alert) return "等等……刚才是不是有什么？";
            if (state == VoiceState.Watching) return "她在那里做什么呢？";
            return "啊，你好。";
        }

        private static AudioClip GetClip(string path)
        {
            AudioClip cached;
            if (ClipCache.TryGetValue(path, out cached))
            {
                return cached;
            }
            try
            {
                AudioClip clip = WavLoader.Load(path);
                if (clip != null && clip.length > MaxAudioClipSeconds)
                {
                    float duration = clip.length;
                    UnityEngine.Object.Destroy(clip);
                    throw new InvalidDataException("Audio duration "
                        + duration.ToString("0.00", CultureInfo.InvariantCulture)
                        + "s exceeds the " + MaxAudioClipSeconds.ToString("0", CultureInfo.InvariantCulture)
                        + "s safety limit.");
                }
                ClipCache[path] = clip;
                return clip;
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("Could not load WAV '" + path + "': " + error.Message);
                ClipCache[path] = null;
                return null;
            }
        }

        private static bool IsEnabled()
        {
            return _started && Plugin.Settings != null && Plugin.Settings.Enabled.Value;
        }

        private static bool IsGameOverNow()
        {
            return _wasGameOver
                || (InGameManager.Instance != null
                    && InGameManager.Instance.TempInGameState != null
                    && InGameManager.Instance.TempInGameState.IsGameOver);
        }

        private static NpcRuntime GetRuntime(NpcController npc, float now)
        {
            NpcRuntime runtime;
            if (!Npcs.TryGetValue(npc.id, out runtime))
            {
                runtime = new NpcRuntime();
                runtime.Profile = BuildProfile(npc);
                Npcs[npc.id] = runtime;
                WriteProfileSnapshot(npc, runtime.Profile);
            }
            runtime.LastSeenAt = now;
            runtime.Npc = npc;
            return runtime;
        }

        private static float CooldownFor(VoiceState state)
        {
            if (state == VoiceState.Ambient) return Mathf.Max(20f, Plugin.Settings.AmbientCooldown.Value);
            if (state == VoiceState.Phone) return Mathf.Max(15f, Plugin.Settings.PhoneCooldown.Value);
            if (state == VoiceState.Alert) return Mathf.Max(3f, Plugin.Settings.AlertCooldown.Value);
            if (state == VoiceState.Found) return Mathf.Max(5f, Plugin.Settings.FoundCooldown.Value);
            if (state == VoiceState.Watching) return Mathf.Max(8f, Plugin.Settings.PerNpcCooldown.Value);
            if (state == VoiceState.Aftermath) return 18f;
            return 0f;
        }

        private static bool IsVisibleForAmbient(NpcController npc)
        {
            return !Plugin.Settings.RequireVisibleForAmbient.Value
                || (npc.IsVisible && npc.IsInCameraArea);
        }

        private static float TriggerDistanceFor(VoiceState state)
        {
            if (state == VoiceState.Ambient) return Mathf.Max(0.5f, Plugin.Settings.AmbientTriggerDistance.Value);
            if (state == VoiceState.Phone) return Mathf.Max(0.5f, Plugin.Settings.PhoneTriggerDistance.Value);
            if (state == VoiceState.Watching) return Mathf.Max(0.5f, Plugin.Settings.WatchingTriggerDistance.Value);
            if (state == VoiceState.Alert) return Mathf.Max(0.5f, Plugin.Settings.AlertTriggerDistance.Value);
            if (state == VoiceState.Found) return Mathf.Max(0.5f, Plugin.Settings.FoundTriggerDistance.Value);
            if (state == VoiceState.Aftermath) return Mathf.Max(0.5f, Plugin.Settings.MaxDistance.Value);
            return float.MaxValue;
        }

        private static bool IsWithinTriggerDistance(NpcController npc, VoiceState state)
        {
            if (state == VoiceState.Failure)
            {
                return true;
            }
            if (npc == null)
            {
                return false;
            }
            float distance = npc.PlayerDistance;
            return !float.IsNaN(distance)
                && !float.IsInfinity(distance)
                && distance >= 0f
                && distance <= TriggerDistanceFor(state);
        }

        private static bool IsUsingPhone(NpcController npc)
        {
            if (npc == null || npc.stateModel == null)
            {
                return false;
            }
            NpcStateModel model = npc.stateModel;
            return model.isSumahoWalk
                || model.CurrentFixedType == NpcStateModel.FixedType.SitSumaho
                || model.CurrentFixedType == NpcStateModel.FixedType.StandSumaho;
        }

        private static bool IsAmbientEligible(NpcController npc)
        {
            if (npc == null || npc.stateModel == null || npc.IsWatchingStranger || npc.IsPlayerFound)
            {
                return false;
            }
            if (npc.stateModel.CurrentState == NpcStateModel.State.FoundStranger)
            {
                return false;
            }
            // Car NPCs pass through the camera too quickly and their voice would
            // appear to come from an implausible position.  Other walking,
            // standing and workplace actions may use ambient muttering.
            return !string.Equals(npc.stateModel.CurrentFixedType.ToString(), "Car", StringComparison.OrdinalIgnoreCase);
        }

        private static NpcProfile BuildProfile(NpcController npc)
        {
            NpcProfile profile = new NpcProfile
            {
                Gender = "unknown",
                Age = "adult",
                Role = "civilian",
                VoiceKey = "adult_unknown",
                AvatarType = "Unknown",
                FixedType = "None",
                HairMaterial = string.Empty
            };
            if (npc == null || npc.stateModel == null)
            {
                return profile;
            }

            NpcStateModel model = npc.stateModel;
            profile.AvatarType = model.AvatarType.ToString();
            profile.FixedType = model.CurrentFixedType.ToString();
            profile.Gender = model.isFemale ? "female" : "male";
            if (model.AvatarType == NpcAvatarComponent.AvatarType.NewOba
                || model.AvatarType == NpcAvatarComponent.AvatarType.NewOji)
            {
                profile.Age = "older";
            }
            else if (model.AvatarType == NpcAvatarComponent.AvatarType.NewFemale
                || model.AvatarType == NpcAvatarComponent.AvatarType.NewMale)
            {
                profile.Age = "young";
            }

            if (model.IsPolice)
            {
                profile.Role = "police";
            }
            else if (model.CurrentFixedType == NpcStateModel.FixedType.Conbini)
            {
                profile.Role = "convenience_clerk";
            }
            else if (model.CurrentFixedType == NpcStateModel.FixedType.SitWork)
            {
                profile.Role = "office_worker";
            }
            profile.VoiceKey = profile.Age + "_" + profile.Gender;

            try
            {
                NpcAvatarComponent avatar = npc.Nca != null ? npc.Nca.AvatarComponent : null;
                if (avatar != null)
                {
                    profile.HairIndex = avatar.hairIndex;
                    profile.BodyIndex = avatar.bodyIndex;
                    profile.FaceIndex = avatar.faceIndex;
                    if (avatar.HairRenderer != null && avatar.HairRenderer.sharedMaterial != null)
                    {
                        profile.HairMaterial = avatar.HairRenderer.sharedMaterial.name;
                    }
                }
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogDebug("Could not inspect NPC appearance metadata: " + error.Message);
            }
            return profile;
        }

        private static void WriteProfileSnapshot(NpcController npc, NpcProfile profile)
        {
            if (npc == null || profile == null)
            {
                return;
            }
            string key = npc.id.ToString(CultureInfo.InvariantCulture) + ":" + profile.VoiceKey + ":"
                + profile.Role + ":" + profile.HairIndex.ToString(CultureInfo.InvariantCulture);
            if (!WrittenProfiles.Add(key))
            {
                return;
            }
            try
            {
                string row = string.Join(",", new[]
                {
                    npc.id.ToString(CultureInfo.InvariantCulture),
                    Csv(profile.VoiceKey), Csv(profile.Gender), Csv(profile.Age), Csv(profile.Role),
                    Csv(profile.AvatarType), Csv(profile.FixedType),
                    profile.HairIndex.ToString(CultureInfo.InvariantCulture),
                    profile.BodyIndex.ToString(CultureInfo.InvariantCulture),
                    profile.FaceIndex.ToString(CultureInfo.InvariantCulture), Csv(profile.HairMaterial)
                });
                File.AppendAllText(ProfileSnapshotPath, row + "\r\n");
                Plugin.PluginLog.LogInfo("NPC profile: npc=" + npc.id.ToString(CultureInfo.InvariantCulture)
                    + " voice_key=" + profile.VoiceKey + " role=" + profile.Role
                    + " avatar=" + profile.AvatarType + " fixed=" + profile.FixedType
                    + " hair=" + profile.HairIndex.ToString(CultureInfo.InvariantCulture)
                    + " body=" + profile.BodyIndex.ToString(CultureInfo.InvariantCulture)
                    + " face=" + profile.FaceIndex.ToString(CultureInfo.InvariantCulture)
                    + " material=" + profile.HairMaterial);
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("Could not write NPC profile snapshot: " + error.Message);
            }
        }

        private static string Csv(string value)
        {
            return "\"" + (value ?? string.Empty).Replace("\"", "\"\"") + "\"";
        }

        private static void Queue(NpcRuntime runtime, VoiceState state, float now, float lifetime, string reason,
            float previousStrangeness = 0f, float currentStrangeness = 0f)
        {
            if (runtime == null || runtime.Npc == null || state == VoiceState.None)
            {
                return;
            }
            if (!IsWithinTriggerDistance(runtime.Npc, state))
            {
                LogTrigger("SKIP_DISTANCE", runtime.Npc, state, reason, previousStrangeness, currentStrangeness);
                return;
            }
            if (runtime.LastQueuedState == state && now - runtime.LastQueuedAt < 1.5f)
            {
                return;
            }
            if (runtime.PendingState != VoiceState.None && now > runtime.PendingExpiresAt)
            {
                runtime.PendingState = VoiceState.None;
                runtime.PendingExpiresAt = 0f;
            }
            runtime.LastQueuedState = state;
            runtime.LastQueuedAt = now;
            if (state < runtime.PendingState)
            {
                // Keep the higher-priority reaction already waiting. Ambient
                // chatter is intentionally disposable when the scene escalates.
                return;
            }
            if (state > runtime.PendingState)
            {
                runtime.PendingState = state;
            }
            runtime.PendingExpiresAt = Math.Max(runtime.PendingExpiresAt, now + lifetime);

            if (state >= VoiceState.Alert)
            {
                // Stop lower-priority speech now; playback begins as soon as the
                // short global duplicate guard allows it.
                RefreshPlayingState(runtime);
                if (runtime.Source != null && runtime.Source.isPlaying && runtime.PlayingState < state)
                {
                    runtime.Source.Stop();
                    runtime.PlayingState = VoiceState.None;
                }
            }
            LogTrigger("QUEUE", runtime.Npc, state, reason, previousStrangeness, currentStrangeness);
        }

        private static void TrySpeakQueued(float now)
        {
            NpcRuntime selected = null;
            VoiceState selectedState = VoiceState.None;
            foreach (NpcRuntime runtime in Npcs.Values)
            {
                if (runtime.PendingState == VoiceState.None)
                {
                    continue;
                }
                if (now > runtime.PendingExpiresAt || runtime.Npc == null || !runtime.Npc.IsAlive)
                {
                    runtime.PendingState = VoiceState.None;
                    continue;
                }
                if (!IsWithinTriggerDistance(runtime.Npc, runtime.PendingState))
                {
                    LogTrigger("DROP_DISTANCE", runtime.Npc, runtime.PendingState, "left trigger range before playback",
                        runtime.LastStrangeness, runtime.Npc.StrangenessValue);
                    runtime.PendingState = VoiceState.None;
                    continue;
                }
                if (runtime.PendingState > selectedState && CanSpeak(runtime, runtime.PendingState, now))
                {
                    selected = runtime;
                    selectedState = runtime.PendingState;
                }
            }
            if (selected != null)
            {
                selected.PendingState = VoiceState.None;
                LogTrigger("SPEAK", selected.Npc, selectedState, "queued trigger", selected.LastStrangeness, selected.Npc.StrangenessValue);
                Speak(selected.Npc, selected, selectedState, now);
            }
        }

        private static bool CrossedAlertBand(float previous, float current)
        {
            if (current <= previous)
            {
                return false;
            }
            return (previous < 0.25f && current >= 0.25f)
                || (previous < 0.50f && current >= 0.50f)
                || (previous < 0.75f && current >= 0.75f);
        }

        private static NpcController FindCulprit(NpcManager manager, VoiceState requiredState = VoiceState.None)
        {
            if (manager == null || manager.ExistNpcList == null)
            {
                return null;
            }
            NpcController best = null;
            float bestScore = float.MinValue;
            for (int index = 0; index < manager.ExistNpcList.Count; index++)
            {
                NpcController npc = manager.ExistNpcList[index];
                if (npc == null || !npc.IsAlive)
                {
                    continue;
                }
                if (requiredState != VoiceState.None && !IsWithinTriggerDistance(npc, requiredState))
                {
                    continue;
                }
                if (requiredState == VoiceState.Found
                    && (!IsVisibleForAmbient(npc)
                        || (!npc.IsWatchingStranger
                            && npc.StrangenessValue < Mathf.Max(0f, Plugin.Settings.WatchingMinimumStrangeness.Value))))
                {
                    continue;
                }
                float score = npc.StrangenessValue;
                if (npc.IsPlayerFound) score += 10000f;
                if (npc.stateModel != null && npc.stateModel.CurrentState == NpcStateModel.State.FoundStranger) score += 5000f;
                if (npc.IsVisible && npc.IsInCameraArea) score += 500f;
                score -= Mathf.Max(0f, npc.PlayerDistance);
                if (score > bestScore)
                {
                    bestScore = score;
                    best = npc;
                }
            }
            return best;
        }

        private static AudioSource EnsureGlobalSource()
        {
            if (_globalSource != null)
            {
                return _globalSource;
            }
            _globalAudioRoot = new GameObject("ManakaNpcVoiceGlobalAudio");
            UnityEngine.Object.DontDestroyOnLoad(_globalAudioRoot);
            _globalSource = _globalAudioRoot.AddComponent<AudioSource>();
            return _globalSource;
        }

        private static string BuildSpeakerLabel(NpcController npc, NpcProfile profile)
        {
            if (npc == null)
            {
                return LocalizedNpcLabel("nearby");
            }
            string direction = "nearby";
            Camera camera = Camera.main;
            if (camera != null && npc.Transform != null)
            {
                Vector3 screen = camera.WorldToViewportPoint(npc.Transform.position + Vector3.up * 1.4f);
                if (screen.z <= 0f) direction = "behind";
                else if (screen.x < 0.4f) direction = "left";
                else if (screen.x > 0.6f) direction = "right";
                else direction = "front";
            }
            string label = LocalizedNpcLabel(direction);
            string description = LocalizedProfile(profile);
            return string.IsNullOrEmpty(description) ? label : description + " · " + label;
        }

        private static string LocalizedProfile(NpcProfile profile)
        {
            if (profile == null) return string.Empty;
            string language = NormalizeLanguage(Plugin.Settings.Language.Value);
            if (language == "ja")
            {
                string person = profile.Age == "older"
                    ? (profile.Gender == "female" ? "年配の女性" : "年配の男性")
                    : (profile.Gender == "female" ? "若い女性" : "若い男性");
                if (profile.Role == "police") return person + "・警察官";
                if (profile.Role == "convenience_clerk") return person + "・コンビニ店員";
                if (profile.Role == "office_worker") return person + "・会社員";
                return person;
            }
            if (language == "en")
            {
                string person = (profile.Age == "older" ? "Older " : "Young ")
                    + (profile.Gender == "female" ? "woman" : "man");
                if (profile.Role == "police") return person + " · police officer";
                if (profile.Role == "convenience_clerk") return person + " · store clerk";
                if (profile.Role == "office_worker") return person + " · office worker";
                return person;
            }
            string chinese = profile.Age == "older"
                ? (profile.Gender == "female" ? "年长女性" : "年长男性")
                : (profile.Gender == "female" ? "年轻女性" : "年轻男性");
            if (profile.Role == "police") return chinese + "·警察";
            if (profile.Role == "convenience_clerk") return chinese + "·便利店店员";
            if (profile.Role == "office_worker") return chinese + "·上班族";
            return chinese;
        }

        private static string LocalizedNpcLabel(string direction)
        {
            string language = NormalizeLanguage(Plugin.Settings.Language.Value);
            if (language == "ja")
            {
                if (direction == "left") return "左側のNPC";
                if (direction == "right") return "右側のNPC";
                if (direction == "front") return "正面のNPC";
                if (direction == "behind") return "後ろのNPC";
                return "近くのNPC";
            }
            if (language == "en")
            {
                if (direction == "left") return "NPC on the left";
                if (direction == "right") return "NPC on the right";
                if (direction == "front") return "NPC ahead";
                if (direction == "behind") return "NPC behind you";
                return "Nearby NPC";
            }
            if (direction == "left") return "左侧 NPC";
            if (direction == "right") return "右侧 NPC";
            if (direction == "front") return "前方 NPC";
            if (direction == "behind") return "身后 NPC";
            return "附近 NPC";
        }

        private static void LogTrigger(string action, NpcController npc, VoiceState state, string reason,
            float previousStrangeness, float currentStrangeness)
        {
            if (Plugin.Settings == null || !Plugin.Settings.DiagnosticLogging.Value)
            {
                return;
            }
            string npcInfo = npc == null
                ? "npc=none"
                : "npc=" + npc.id.ToString(CultureInfo.InvariantCulture)
                    + " dist=" + npc.PlayerDistance.ToString("0.0", CultureInfo.InvariantCulture)
                    + " visible=" + npc.IsVisible
                    + " camera=" + npc.IsInCameraArea
                    + " watching=" + npc.IsWatchingStranger
                    + " found=" + npc.IsPlayerFound
                    + (Npcs.ContainsKey(npc.id) && Npcs[npc.id].Profile != null
                        ? " profile=" + Npcs[npc.id].Profile.VoiceKey + "/" + Npcs[npc.id].Profile.Role
                        : string.Empty);
            Plugin.PluginLog.LogInfo("NPC voice " + action + ": " + npcInfo
                + " state=" + state
                + " suspicion=" + previousStrangeness.ToString("0.0", CultureInfo.InvariantCulture)
                + "->" + currentStrangeness.ToString("0.0", CultureInfo.InvariantCulture)
                + " reason=" + reason);
        }
    }

    internal static class WavLoader
    {
        internal static AudioClip Load(string path)
        {
            byte[] data = File.ReadAllBytes(path);
            if (data.Length < 44 || ReadAscii(data, 0, 4) != "RIFF" || ReadAscii(data, 8, 4) != "WAVE")
            {
                throw new InvalidDataException("Only RIFF/WAVE files are supported.");
            }

            int position = 12;
            short format = 0;
            short channels = 0;
            int sampleRate = 0;
            short bitsPerSample = 0;
            int pcmOffset = -1;
            int pcmLength = 0;
            while (position + 8 <= data.Length)
            {
                string chunk = ReadAscii(data, position, 4);
                int length = BitConverter.ToInt32(data, position + 4);
                int start = position + 8;
                if (length < 0 || start + length > data.Length)
                {
                    break;
                }
                if (chunk == "fmt " && length >= 16)
                {
                    format = BitConverter.ToInt16(data, start);
                    channels = BitConverter.ToInt16(data, start + 2);
                    sampleRate = BitConverter.ToInt32(data, start + 4);
                    bitsPerSample = BitConverter.ToInt16(data, start + 14);
                }
                else if (chunk == "data")
                {
                    pcmOffset = start;
                    pcmLength = length;
                }
                position = start + length + (length & 1);
            }

            if (format != 1 || channels < 1 || channels > 2 || bitsPerSample != 16 || sampleRate <= 0 || pcmOffset < 0)
            {
                throw new InvalidDataException("Use uncompressed 16-bit PCM WAV (mono or stereo).");
            }

            int sampleCount = pcmLength / 2;
            float[] samples = new float[sampleCount];
            for (int index = 0; index < sampleCount; index++)
            {
                samples[index] = BitConverter.ToInt16(data, pcmOffset + index * 2) / 32768f;
            }
            int frameCount = sampleCount / channels;
            AudioClip clip = AudioClip.Create(Path.GetFileNameWithoutExtension(path), frameCount, channels, sampleRate, false);
            if (!clip.SetData(samples, 0))
            {
                UnityEngine.Object.Destroy(clip);
                throw new InvalidDataException("Unity rejected the PCM sample data.");
            }
            return clip;
        }

        private static string ReadAscii(byte[] data, int start, int length)
        {
            char[] value = new char[length];
            for (int index = 0; index < length; index++)
            {
                value[index] = (char)data[start + index];
            }
            return new string(value);
        }
    }

    internal static class SubtitleOverlay
    {
        private static GameObject _root;
        private static GameObject _panel;
        private static RectTransform _panelRect;
        private static Text _speaker;
        private static Text _line;
        private static float _hideAt;

        internal static void Show(string speaker, string line, float distance,
            float duration = 4.5f, bool paragraph = false)
        {
            EnsureCreated();
            if (_panel == null) return;
            if (_panelRect != null)
            {
                _panelRect.anchoredPosition = new Vector2(0f, paragraph ? 70f : 92f);
                _panelRect.sizeDelta = new Vector2(0f, paragraph ? 168f : 78f);
            }
            _line.fontSize = paragraph ? 20 : 23;
            SetRect(_speaker.rectTransform,
                paragraph ? new Vector2(0.035f, 0.80f) : new Vector2(0.035f, 0.58f),
                new Vector2(0.965f, 0.95f));
            SetRect(_line.rectTransform,
                new Vector2(0.035f, 0.08f),
                paragraph ? new Vector2(0.965f, 0.82f) : new Vector2(0.965f, 0.66f));
            _speaker.text = speaker + "  ·  " + Mathf.Max(0f, distance).ToString("0", CultureInfo.InvariantCulture) + " m";
            _line.text = line;
            _hideAt = Time.unscaledTime + Mathf.Max(1f, duration);
            _panel.SetActive(true);
        }

        internal static void Tick()
        {
            if (_panel != null && _panel.activeSelf && Time.unscaledTime >= _hideAt)
            {
                _panel.SetActive(false);
            }
        }

        internal static void Hide()
        {
            if (_panel != null) _panel.SetActive(false);
        }

        internal static void Destroy()
        {
            if (_root != null)
            {
                UnityEngine.Object.Destroy(_root);
                _root = null;
                _panel = null;
                _panelRect = null;
            }
        }

        private static void EnsureCreated()
        {
            if (_root != null) return;
            _root = new GameObject("ManakaNpcVoiceCanvas");
            UnityEngine.Object.DontDestroyOnLoad(_root);
            Canvas canvas = _root.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 31990;
            CanvasScaler scaler = _root.AddComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = 0.5f;

            Image panel = CreateImage("Panel", _root.transform, new Color(0.02f, 0.025f, 0.04f, 0.72f));
            _panel = panel.gameObject;
            RectTransform rect = panel.rectTransform;
            _panelRect = rect;
            rect.anchorMin = new Vector2(0.25f, 0f);
            rect.anchorMax = new Vector2(0.75f, 0f);
            rect.pivot = new Vector2(0.5f, 0f);
            rect.anchoredPosition = new Vector2(0f, 92f);
            rect.sizeDelta = new Vector2(0f, 78f);

            Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            _speaker = CreateText("Speaker", _panel.transform, font, 15, new Color(0.42f, 0.85f, 0.94f, 1f));
            SetRect(_speaker.rectTransform, new Vector2(0.035f, 0.58f), new Vector2(0.965f, 0.95f));
            _line = CreateText("Line", _panel.transform, font, 23, Color.white);
            SetRect(_line.rectTransform, new Vector2(0.035f, 0.08f), new Vector2(0.965f, 0.66f));
            _panel.SetActive(false);
        }

        private static Image CreateImage(string name, Transform parent, Color color)
        {
            GameObject child = new GameObject(name);
            child.transform.SetParent(parent, false);
            Image image = child.AddComponent<Image>();
            image.color = color;
            image.raycastTarget = false;
            return image;
        }

        private static Text CreateText(string name, Transform parent, Font font, int size, Color color)
        {
            GameObject child = new GameObject(name);
            child.transform.SetParent(parent, false);
            Text text = child.AddComponent<Text>();
            text.font = font;
            text.fontSize = size;
            text.fontStyle = FontStyle.Bold;
            text.alignment = TextAnchor.MiddleLeft;
            text.color = color;
            text.raycastTarget = false;
            return text;
        }

        private static void SetRect(RectTransform rect, Vector2 min, Vector2 max)
        {
            rect.anchorMin = min;
            rect.anchorMax = max;
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;
        }
    }
}

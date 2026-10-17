using System;
using BepInEx;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime;
using ManakaNpcVoices;
using SFM_custom_mission_v2.UI;
using TMPro;
using UnityEngine;
using UnityEngine.Events;

namespace ManakaNpcVoices.CustomMissions2
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    [BepInDependency(ManakaNpcVoices.Plugin.PluginGuid, BepInDependency.DependencyFlags.HardDependency)]
    [BepInDependency("SFM_custom_mission_v2", BepInDependency.DependencyFlags.HardDependency)]
    public sealed class PhoneBridgePlugin : BasePlugin
    {
        public const string PluginGuid = "local.manaka.npcvoices.cm2phone";
        public const string PluginName = "Manaka NPC Voices - CM2 Phone";
        public const string PluginVersion = "0.1.2";

        private Harmony _harmony;
        internal static NpcVoiceApp RegisteredApp;

        public override void Load()
        {
            _harmony = new Harmony(PluginGuid);
            _harmony.PatchAll();
            TryRegister();
            Log.LogInfo("Custom Missions 2 phone bridge loaded.");
        }

        public override bool Unload()
        {
            if (PluginGUI.instance != null && RegisteredApp != null)
            {
                PluginGUI.UnregisterApp(RegisteredApp);
            }
            RegisteredApp = null;
            if (_harmony != null) _harmony.UnpatchSelf();
            return true;
        }

        internal static void TryRegister()
        {
            if (RegisteredApp != null || PluginGUI.instance == null || !NpcVoiceSettingsApi.IsReady) return;
            RegisteredApp = new NpcVoiceApp();
            PluginGUI.RegisterApp(RegisteredApp);
        }
    }

    [HarmonyPatch(typeof(PluginGUI), "Start")]
    internal static class PluginGuiStartPatch
    {
        [HarmonyPostfix]
        private static void Postfix()
        {
            PhoneBridgePlugin.TryRegister();
        }
    }

    public sealed class NpcVoiceApp : App
    {
        private static readonly Color Accent = new Color(0.98f, 0.36f, 0.67f, 1f);
        private static readonly Color Button = new Color(0.10f, 0.15f, 0.25f, 1f);
        private static readonly Color Foreground = new Color(0.96f, 0.97f, 1f, 1f);

        public override GameObject CreateButton(GameObject parent, float size)
        {
            return PluginGUI.CreateButton(
                parent,
                "NpcVoiceApp",
                size,
                0.18f,
                Button,
                Foreground,
                "NPC",
                DelegateSupport.ConvertDelegate<UnityAction>(new Action(Open)),
                0.72f);
        }

        public override Window InitializeWindow()
        {
            return new NpcVoiceSettingsWindow();
        }
    }

    public sealed class NpcVoiceSettingsWindow : Window
    {
        private static readonly Color Background = new Color(0.035f, 0.055f, 0.10f, 1f);
        private static readonly Color Panel = new Color(0.075f, 0.105f, 0.17f, 0.96f);
        private static readonly Color Button = new Color(0.11f, 0.16f, 0.25f, 1f);
        private static readonly Color Accent = new Color(0.98f, 0.36f, 0.67f, 1f);
        private static readonly Color Cyan = new Color(0.34f, 0.85f, 0.91f, 1f);
        private static readonly Color Foreground = new Color(0.96f, 0.97f, 1f, 1f);
        private static readonly Color Muted = new Color(0.64f, 0.69f, 0.78f, 1f);

        private TMP_Text _languageZh;
        private TMP_Text _languageJa;
        private TMP_Text _languageEn;
        private TMP_Text _volumeValue;
        private TMP_Text _voiceCountValue;
        private TMP_Text _ambientCooldownValue;
        private TMP_Text _phoneCooldownValue;
        private TMP_Text _alertCooldownValue;
        private TMP_Text _foundCooldownValue;
        private TMP_Text _status;
        private GameObject _mainPage;
        private GameObject _cooldownPage;

        public NpcVoiceSettingsWindow() : base("NPC Voices", Background)
        {
            Build();
        }

        public override void OnShow()
        {
            base.OnShow();
            Refresh();
        }

        private void Build()
        {
            GameObject content = PluginGUI.CreateRect("NpcVoiceSettings", gameObject, new Vector2(84f, 146f), Panel, null);
            Place(content, 0f, -7f);

            _mainPage = PluginGUI.CreateRect("MainPage", content, Vector2.zero, Color.clear, null);
            Stretch(_mainPage);
            AddText(_mainPage, "OFFLINE VOICE SETTINGS", 0f, 63f, 76f, 7f, 4.2f, Foreground, TextAlignmentOptions.MidlineLeft);
            AddText(_mainPage, "Saved instantly · No online API", 0f, 56f, 76f, 5f, 2.5f, Muted, TextAlignmentOptions.MidlineLeft);

            AddText(_mainPage, "GENERAL", 0f, 47f, 76f, 5f, 2.8f, Cyan, TextAlignmentOptions.MidlineLeft);
            AddToggle(_mainPage, "Enabled", 36f, NpcVoiceSettingsApi.Enabled, value => SetAndSave(() => NpcVoiceSettingsApi.Enabled = value));
            AddToggle(_mainPage, "Local Audio", 26f, NpcVoiceSettingsApi.VoiceEnabled, value => SetAndSave(() => NpcVoiceSettingsApi.VoiceEnabled = value));
            AddToggle(_mainPage, "Subtitles", 16f, NpcVoiceSettingsApi.SubtitlesEnabled, value => SetAndSave(() => NpcVoiceSettingsApi.SubtitlesEnabled = value));

            AddText(_mainPage, "TEXT LANGUAGE", 0f, 6f, 76f, 5f, 2.8f, Cyan, TextAlignmentOptions.MidlineLeft);
            _languageZh = ButtonText(AddButton(_mainPage, "Chinese", -27f, -3f, 22f, 8f, () => SetLanguage("zh")));
            _languageJa = ButtonText(AddButton(_mainPage, "Japanese", 0f, -3f, 22f, 8f, () => SetLanguage("ja")));
            _languageEn = ButtonText(AddButton(_mainPage, "English", 27f, -3f, 22f, 8f, () => SetLanguage("en")));

            AddValueRow(_mainPage, "Volume", -17f, ref _volumeValue, "85%", () => ChangeVolume(-0.1f), () => ChangeVolume(0.1f));
            AddValueRow(_mainPage, "Voice Limit", -30f, ref _voiceCountValue, "4", () => ChangeVoiceCount(-1), () => ChangeVoiceCount(1));
            AddButton(_mainPage, "Preview", -20f, -47f, 34f, 9f, Preview);
            AddButton(_mainPage, "Cooldowns", 20f, -47f, 34f, 9f, () => ShowCooldownPage(true));
            _status = AddText(_mainPage, "", 0f, -59f, 76f, 5f, 2.3f, Muted, TextAlignmentOptions.Midline);

            _cooldownPage = PluginGUI.CreateRect("CooldownPage", content, Vector2.zero, Color.clear, null);
            Stretch(_cooldownPage);
            AddText(_cooldownPage, "NPC COOLDOWNS", 0f, 63f, 76f, 7f, 4f, Foreground, TextAlignmentOptions.MidlineLeft);
            AddText(_cooldownPage, "Prevents repeated lines from the same NPC", 0f, 56f, 76f, 5f, 2.5f, Muted, TextAlignmentOptions.MidlineLeft);
            AddCooldownRow(_cooldownPage, "Ambient", 40f, ref _ambientCooldownValue, () => NpcVoiceSettingsApi.AmbientCooldown, value => NpcVoiceSettingsApi.AmbientCooldown = value, 20f);
            AddCooldownRow(_cooldownPage, "Phone", 25f, ref _phoneCooldownValue, () => NpcVoiceSettingsApi.PhoneCooldown, value => NpcVoiceSettingsApi.PhoneCooldown = value, 15f);
            AddCooldownRow(_cooldownPage, "Alert", 10f, ref _alertCooldownValue, () => NpcVoiceSettingsApi.AlertCooldown, value => NpcVoiceSettingsApi.AlertCooldown = value, 3f);
            AddCooldownRow(_cooldownPage, "Found", -5f, ref _foundCooldownValue, () => NpcVoiceSettingsApi.FoundCooldown, value => NpcVoiceSettingsApi.FoundCooldown = value, 5f);
            AddText(_cooldownPage, "Recommended: 75 / 90 / 16 / 45 sec", 0f, -21f, 76f, 6f, 2.5f, Muted, TextAlignmentOptions.Midline);
            AddButton(_cooldownPage, "Reset", -20f, -39f, 34f, 9f, RestoreCooldownDefaults);
            AddButton(_cooldownPage, "Back", 20f, -39f, 34f, 9f, () => ShowCooldownPage(false));
            _cooldownPage.SetActive(false);
            Refresh();
        }

        private void AddToggle(GameObject parent, string caption, float y, bool value, Action<bool> changed)
        {
            AddText(parent, caption, -8f, y, 56f, 7f, 3.3f, Foreground, TextAlignmentOptions.MidlineLeft);
            GameObject checkbox = PluginGUI.CreateCheckbox(parent, 6.5f, value, true,
                DelegateSupport.ConvertDelegate<UnityAction<bool>>(new Action<bool>(checkedValue => changed(checkedValue))),
                Muted, Button, Accent);
            Place(checkbox, 31f, y);
        }

        private void AddValueRow(GameObject parent, string caption, float y, ref TMP_Text valueLabel,
            string initialValue, Action decrease, Action increase)
        {
            AddText(parent, caption, -25f, y, 24f, 7f, 3.2f, Foreground, TextAlignmentOptions.MidlineLeft);
            AddButton(parent, "−", -7f, y, 9f, 8f, decrease);
            valueLabel = AddText(parent, initialValue, 9f, y, 18f, 7f, 3.2f, Foreground, TextAlignmentOptions.Midline);
            AddButton(parent, "+", 25f, y, 9f, 8f, increase);
        }

        private void AddCooldownRow(GameObject parent, string caption, float y, ref TMP_Text valueLabel,
            Func<float> getter, Action<float> setter, float minimum)
        {
            AddText(parent, caption, -25f, y, 25f, 7f, 3.2f, Foreground, TextAlignmentOptions.MidlineLeft);
            AddButton(parent, "−", -7f, y, 9f, 8f, () => ChangeCooldown(getter, setter, -5f, minimum));
            valueLabel = AddText(parent, "0 sec", 9f, y, 18f, 7f, 3.1f, Foreground, TextAlignmentOptions.Midline);
            AddButton(parent, "+", 25f, y, 9f, 8f, () => ChangeCooldown(getter, setter, 5f, minimum));
        }

        private GameObject AddButton(GameObject parent, string caption, float x, float y, float width, float height, Action action)
        {
            GameObject button = PluginGUI.CreateButton(parent, "NpcVoice_" + caption,
                new Vector2(width, height), 0.2f, Button, Foreground, caption,
                DelegateSupport.ConvertDelegate<UnityAction>(new Action(() => action())), 0.68f);
            Place(button, x, y);
            return button;
        }

        private TMP_Text AddText(GameObject parent, string caption, float x, float y, float width, float height,
            float fontSize, Color color, TextAlignmentOptions alignment)
        {
            GameObject text = PluginGUI.CreateText(caption, parent, new Vector2(width, height), color, fontSize, alignment);
            Place(text, x, y);
            return text.GetComponent<TMP_Text>();
        }

        private static TMP_Text ButtonText(GameObject button)
        {
            return button == null ? null : button.GetComponentInChildren<TMP_Text>();
        }

        private static void Place(GameObject target, float x, float y)
        {
            PluginGUI.SetPosition(target, new Vector2(x, y), new Vector2(0.5f, 0.5f),
                new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f));
        }

        private static void Stretch(GameObject target)
        {
            PluginGUI.SetPosition(target, Vector2.zero, new Vector2(0.5f, 0.5f),
                Vector2.zero, Vector2.one);
        }

        private void ShowCooldownPage(bool show)
        {
            if (_mainPage != null) _mainPage.SetActive(!show);
            if (_cooldownPage != null) _cooldownPage.SetActive(show);
            Refresh();
        }

        private void SetLanguage(string language)
        {
            NpcVoiceSettingsApi.Language = language;
            Save("Text language changed");
        }

        private void ChangeVolume(float delta)
        {
            NpcVoiceSettingsApi.Volume = NpcVoiceSettingsApi.Volume + delta;
            Save("Volume saved");
        }

        private void ChangeVoiceCount(int delta)
        {
            NpcVoiceSettingsApi.MaxConcurrentVoices = NpcVoiceSettingsApi.MaxConcurrentVoices + delta;
            Save("Voice limit saved");
        }

        private void ChangeCooldown(Func<float> getter, Action<float> setter, float delta, float minimum)
        {
            setter(Mathf.Max(minimum, getter() + delta));
            Save("Cooldown saved");
        }

        private void Preview()
        {
            NpcVoiceSettingsApi.Preview();
            SetStatus("Japanese reaction · selected subtitle language");
        }

        private void RestoreCooldownDefaults()
        {
            NpcVoiceSettingsApi.AmbientCooldown = 75f;
            NpcVoiceSettingsApi.PhoneCooldown = 90f;
            NpcVoiceSettingsApi.AlertCooldown = 16f;
            NpcVoiceSettingsApi.FoundCooldown = 45f;
            Save("Recommended cooldowns restored");
        }

        private void SetAndSave(Action action)
        {
            action();
            Save("Settings saved");
        }

        private void Save(string message)
        {
            NpcVoiceSettingsApi.Save();
            Refresh();
            SetStatus(message);
        }

        private void SetStatus(string message)
        {
            if (_status != null) _status.text = message;
        }

        private void Refresh()
        {
            string language = NpcVoiceSettingsApi.Language;
            if (_languageZh != null) _languageZh.text = language == "zh" ? "✓ Chinese" : "Chinese";
            if (_languageJa != null) _languageJa.text = language == "ja" ? "✓ Japanese" : "Japanese";
            if (_languageEn != null) _languageEn.text = language == "en" ? "✓ English" : "English";
            if (_volumeValue != null) _volumeValue.text = Mathf.RoundToInt(NpcVoiceSettingsApi.Volume * 100f) + "%";
            if (_voiceCountValue != null) _voiceCountValue.text = NpcVoiceSettingsApi.MaxConcurrentVoices.ToString();
            if (_ambientCooldownValue != null) _ambientCooldownValue.text = Mathf.RoundToInt(NpcVoiceSettingsApi.AmbientCooldown) + " sec";
            if (_phoneCooldownValue != null) _phoneCooldownValue.text = Mathf.RoundToInt(NpcVoiceSettingsApi.PhoneCooldown) + " sec";
            if (_alertCooldownValue != null) _alertCooldownValue.text = Mathf.RoundToInt(NpcVoiceSettingsApi.AlertCooldown) + " sec";
            if (_foundCooldownValue != null) _foundCooldownValue.text = Mathf.RoundToInt(NpcVoiceSettingsApi.FoundCooldown) + " sec";
        }
    }
}

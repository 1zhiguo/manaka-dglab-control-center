using System;
using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using ExposureUnnoticed2.Object3D.NPC.Script;
using ExposureUnnoticed2.Object3D.Player.Scripts;
using ExposureUnnoticed2.Object3D.AdultGoods;
using ExposureUnnoticed2.ObjectUI.SystemMenu;
using ExposureUnnoticed2.Scripts.Base;
using ExposureUnnoticed2.Scripts.InGame;
using UnityEngine;
using UnityEngine.UI;

namespace ManakaDGLab.Telemetry
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    public sealed class Plugin : BasePlugin
    {
        public const string PluginGuid = "local.manaka.dglab.telemetry";
        public const string PluginName = "Manaka DG-LAB Telemetry";
        public const string PluginVersion = "0.5.1-channel-hud-v2";

        private Harmony _harmony;
        internal static ManualLogSource PluginLog;

        public override void Load()
        {
            PluginLog = Log;
            TelemetryPublisher.Start();
            ProgressCommandServer.Start();
            HudStatusReceiver.Start();

            _harmony = new Harmony(PluginGuid);
            _harmony.PatchAll(typeof(PlayerUpdatePatch));

            Log.LogInfo("Pilot telemetry enabled: UDP 127.0.0.1:45678");
            Log.LogInfo("Progress editor enabled: local-only UDP 127.0.0.1:45679");
            Log.LogInfo("In-game A/B HUD listener enabled: local-only UDP 127.0.0.1:45680");
            Log.LogInfo("This plugin does not send any DG-LAB commands.");
        }

        public override bool Unload()
        {
            if (_harmony != null)
            {
                _harmony.UnpatchSelf();
            }

            TelemetryPublisher.Stop();
            ProgressCommandServer.Stop();
            HudStatusReceiver.Stop();
            CustomHudCanvas.Destroy();
            return true;
        }
    }

    internal sealed class HudStatus
    {
        internal bool Visible;
        internal bool Connected;
        internal bool Active;
        internal float StrengthA;
        internal float StrengthB;
        internal float PulseA;
        internal float PulseB;
        internal int Flags = 125; // Pulse, A/B, numbers, status, waveforms.
        internal float Scale = 100;
        internal float Opacity = 35;
        internal int Anchor;
        internal float X = 30;
        internal float Y = 96;
        internal int Connections;
        internal int Activities;
        internal float[] Strengths = new float[4];
        internal float[] Caps = new float[] { 30, 30, 30, 30 };
        internal float[] Pulses = new float[4];
        internal long ReceivedAt;

        internal HudStatus Copy()
        {
            return (HudStatus)MemberwiseClone();
        }
    }

    internal static class HudStatusReceiver
    {
        private const int Port = 45680;
        private static readonly object Gate = new object();
        private static UdpClient _listener;
        private static Thread _thread;
        private static bool _running;
        private static bool _loggedFirstPacket;
        private static HudStatus _status = new HudStatus();

        internal static void Start()
        {
            try
            {
                _listener = new UdpClient(new IPEndPoint(IPAddress.Loopback, Port));
                _listener.Client.ReceiveTimeout = 500;
                _running = true;
                _thread = new Thread(ListenLoop)
                {
                    IsBackground = true,
                    Name = "ManakaHudStatus"
                };
                _thread.Start();
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("HUD status listener unavailable: " + error.Message);
            }
        }

        internal static void Stop()
        {
            _running = false;
            if (_listener != null)
            {
                try { _listener.Close(); } catch { }
                _listener = null;
            }
            lock (Gate)
            {
                _status = new HudStatus();
            }
        }

        internal static HudStatus Snapshot()
        {
            lock (Gate)
            {
                return _status.Copy();
            }
        }

        private static void ListenLoop()
        {
            IPEndPoint sender = new IPEndPoint(IPAddress.Loopback, 0);
            while (_running && _listener != null)
            {
                try
                {
                    byte[] payload = _listener.Receive(ref sender);
                    if (!IPAddress.IsLoopback(sender.Address) || payload.Length > 512)
                    {
                        continue;
                    }

                    HudStatus parsed;
                    if (TryParse(Encoding.ASCII.GetString(payload), out parsed))
                    {
                        lock (Gate)
                        {
                            _status = parsed;
                        }
                        if (!_loggedFirstPacket)
                        {
                            _loggedFirstPacket = true;
                            Plugin.PluginLog.LogInfo("First HUD status received from the control center.");
                        }
                    }
                }
                catch (SocketException)
                {
                    // Receive timeout keeps shutdown responsive.
                }
                catch (ObjectDisposedException)
                {
                    return;
                }
                catch (Exception error)
                {
                    Plugin.PluginLog.LogWarning("HUD status receive failed: " + error.Message);
                }
            }
        }

        private static bool TryParse(string value, out HudStatus status)
        {
            status = null;
            string[] parts = (value ?? string.Empty).Split('|');
            if (parts.Length == 24 && parts[0] == "MANAKA_HUD_V2" && parts[23] == "END")
            {
                return TryParseV2(parts, out status);
            }
            if (parts.Length != 10 || parts[0] != "MANAKA_HUD_V1" || parts[9] != "END")
            {
                return false;
            }

            long sequence;
            float strengthA;
            float strengthB;
            float pulseA;
            float pulseB;
            if (!long.TryParse(parts[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out sequence)
                || !float.TryParse(parts[5], NumberStyles.Float, CultureInfo.InvariantCulture, out strengthA)
                || !float.TryParse(parts[6], NumberStyles.Float, CultureInfo.InvariantCulture, out strengthB)
                || !float.TryParse(parts[7], NumberStyles.Float, CultureInfo.InvariantCulture, out pulseA)
                || !float.TryParse(parts[8], NumberStyles.Float, CultureInfo.InvariantCulture, out pulseB))
            {
                return false;
            }

            status = new HudStatus
            {
                Visible = parts[2] == "1",
                Connected = parts[3] == "1",
                Active = parts[4] == "1",
                // This parser runs on the UDP receiver thread. Calling Unity APIs from
                // that thread can crash IL2CPP, so keep clamping entirely in managed code.
                StrengthA = Clamp(strengthA, 0f, 200f),
                StrengthB = Clamp(strengthB, 0f, 200f),
                PulseA = Clamp(pulseA, 0f, 1f),
                PulseB = Clamp(pulseB, 0f, 1f),
                Connections = parts[3] == "1" ? 1 : 0,
                Activities = parts[4] == "1" ? 1 : 0,
                Strengths = new float[] { Clamp(strengthA, 0, 100), Clamp(strengthB, 0, 100), 0, 0 },
                Pulses = new float[] { Clamp(pulseA, 0, 1), Clamp(pulseB, 0, 1), 0, 0 },
                ReceivedAt = Environment.TickCount64
            };
            return true;
        }

        private static bool TryParseV2(string[] parts, out HudStatus status)
        {
            status = null;
            float[] values = new float[22];
            for (int i = 1; i <= 22; i++)
            {
                if (!float.TryParse(parts[i], NumberStyles.Float, CultureInfo.InvariantCulture, out values[i - 1])
                    || float.IsNaN(values[i - 1]) || float.IsInfinity(values[i - 1])) return false;
            }
            status = new HudStatus {
                Visible = parts[2] == "1", Flags = (int)Clamp(values[2], 0, 127),
                Scale = Clamp(values[3], 60, 180), Opacity = Clamp(values[4], 0, 100),
                Anchor = (int)Clamp(values[5], 0, 7), X = Clamp(values[6], 0, 100), Y = Clamp(values[7], 0, 100),
                Connections = (int)Clamp(values[8], 0, 3), Activities = (int)Clamp(values[9], 0, 3),
                ReceivedAt = Environment.TickCount64
            };
            for (int i = 0; i < 4; i++) {
                status.Strengths[i] = Clamp(values[10 + i], 0, 200);
                status.Caps[i] = Clamp(values[14 + i], 0, 200);
                status.Pulses[i] = Clamp(values[18 + i], 0, 1);
            }
            return true;
        }

        private static float Clamp(float value, float minimum, float maximum)
        {
            if (float.IsNaN(value) || float.IsInfinity(value)) return minimum;
            if (value < minimum) return minimum;
            if (value > maximum) return maximum;
            return value;
        }
    }

    internal static class HudCanvas
    {
        private const int HistoryLength = 32;
        private static readonly float[] HistoryA = new float[HistoryLength];
        private static readonly float[] HistoryB = new float[HistoryLength];
        private static readonly Image[] LinesA = new Image[HistoryLength - 1];
        private static readonly Image[] LinesB = new Image[HistoryLength - 1];
        private static GameObject _root;
        private static GameObject _panel;
        private static Text _strengthA;
        private static Text _strengthB;
        private static RectTransform _graphA;
        private static RectTransform _graphB;
        private static float _nextSampleAt;
        private static bool _loggedVisible;

        internal static void Tick()
        {
            EnsureCreated();
            if (_panel == null)
            {
                return;
            }

            HudStatus status = HudStatusReceiver.Snapshot();
            bool fresh = Environment.TickCount64 - status.ReceivedAt <= 1000;
            bool visible = fresh && status.Visible;
            if (_panel.activeSelf != visible)
            {
                _panel.SetActive(visible);
            }
            if (!visible)
            {
                return;
            }

            if (!_loggedVisible)
            {
                _loggedVisible = true;
                Plugin.PluginLog.LogInfo("In-game A/B HUD canvas is visible at " + Screen.width + "x" + Screen.height + ".");
            }

            if (Time.unscaledTime >= _nextSampleAt)
            {
                _nextSampleAt = Time.unscaledTime + 0.1f;
                Push(HistoryA, status.PulseA);
                Push(HistoryB, status.PulseB);
            }

            _strengthA.text = Mathf.RoundToInt(status.StrengthA).ToString(CultureInfo.InvariantCulture);
            _strengthB.text = Mathf.RoundToInt(status.StrengthB).ToString(CultureInfo.InvariantCulture);
            Color inactive = new Color(0.48f, 0.53f, 0.62f, 0.82f);
            UpdateWaveform(_graphA, LinesA, HistoryA, status.Active ? new Color(1f, 0.38f, 0.69f, 0.98f) : inactive);
            UpdateWaveform(_graphB, LinesB, HistoryB, status.Active ? new Color(0.33f, 0.84f, 0.91f, 0.98f) : inactive);
        }

        internal static void Destroy()
        {
            if (_root != null)
            {
                UnityEngine.Object.Destroy(_root);
                _root = null;
                _panel = null;
            }
        }

        private static void EnsureCreated()
        {
            if (_root != null)
            {
                return;
            }

            try
            {
                _root = new GameObject("ManakaDGLabHudCanvas");
                UnityEngine.Object.DontDestroyOnLoad(_root);
                Canvas canvas = _root.AddComponent<Canvas>();
                canvas.renderMode = RenderMode.ScreenSpaceOverlay;
                canvas.sortingOrder = 32000;
                CanvasScaler scaler = _root.AddComponent<CanvasScaler>();
                scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
                scaler.referenceResolution = new Vector2(1920f, 1080f);
                scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
                scaler.matchWidthOrHeight = 0.5f;

                Image panelImage = CreateImage("Panel", _root.transform, new Color(0.025f, 0.035f, 0.055f, 0.36f));
                _panel = panelImage.gameObject;
                RectTransform panelRect = panelImage.rectTransform;
                panelRect.anchorMin = new Vector2(0.21f, 0f);
                panelRect.anchorMax = new Vector2(0.59f, 0f);
                panelRect.pivot = new Vector2(0.5f, 0f);
                panelRect.anchoredPosition = new Vector2(0f, 24f);
                panelRect.sizeDelta = new Vector2(0f, 68f);

                Image topLine = CreateImage("TopLine", _panel.transform, new Color(0.5f, 0.65f, 0.9f, 0.20f));
                SetRect(topLine.rectTransform, new Vector2(0f, 1f), new Vector2(1f, 1f), new Vector2(0.5f, 1f), Vector2.zero, new Vector2(0f, 1f));

                Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
                CreateChannel(_panel.transform, "A", 0.012f, 0.492f, new Color(1f, 0.38f, 0.69f, 0.98f), font, out _strengthA, out _graphA, LinesA);
                CreateChannel(_panel.transform, "B", 0.508f, 0.988f, new Color(0.33f, 0.84f, 0.91f, 0.98f), font, out _strengthB, out _graphB, LinesB);
                _panel.SetActive(false);
                Plugin.PluginLog.LogInfo("In-game A/B HUD canvas created.");
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogError("HUD canvas creation failed: " + error);
                Destroy();
            }
        }

        private static void CreateChannel(
            Transform parent,
            string label,
            float left,
            float right,
            Color color,
            Font font,
            out Text strength,
            out RectTransform graph,
            Image[] lines)
        {
            Image holder = CreateImage("Channel" + label, parent, new Color(0.05f, 0.075f, 0.12f, 0.48f));
            SetRect(holder.rectTransform, new Vector2(left, 0f), new Vector2(right, 1f), new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);

            Image accent = CreateImage("Accent", holder.transform, color);
            SetRect(accent.rectTransform, new Vector2(0f, 0f), new Vector2(0f, 1f), new Vector2(0f, 0.5f), Vector2.zero, new Vector2(2f, 0f));

            Text channel = CreateText("Label", holder.transform, label, font, 15, color);
            SetRect(channel.rectTransform, new Vector2(0.025f, 0.68f), new Vector2(0.10f, 1f), new Vector2(0f, 0.5f), new Vector2(4f, 0f), Vector2.zero);
            strength = CreateText("Strength", holder.transform, "0", font, 13, Color.white);
            strength.alignment = TextAnchor.MiddleRight;
            SetRect(strength.rectTransform, new Vector2(0.82f, 0.68f), new Vector2(0.965f, 1f), new Vector2(1f, 0.5f), Vector2.zero, Vector2.zero);

            Image graphImage = CreateImage("Waveform", holder.transform, Color.clear);
            graph = graphImage.rectTransform;
            SetRect(graph, new Vector2(0.035f, 0.10f), new Vector2(0.965f, 0.70f), new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);

            for (int gridIndex = 0; gridIndex < 3; gridIndex++)
            {
                float y = (gridIndex + 1f) / 4f;
                Image grid = CreateImage("Grid" + gridIndex.ToString(CultureInfo.InvariantCulture), graph, new Color(color.r, color.g, color.b, 0.10f));
                SetRect(grid.rectTransform, new Vector2(0f, y), new Vector2(1f, y), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(0f, 1f));
            }

            Image playhead = CreateImage("Playhead", graph, new Color(color.r, color.g, color.b, 0.28f));
            SetRect(playhead.rectTransform, new Vector2(0.72f, 0f), new Vector2(0.72f, 1f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(1f, 0f));

            for (int index = 0; index < lines.Length; index++)
            {
                Image line = CreateImage("Line" + index.ToString(CultureInfo.InvariantCulture), graph, color);
                line.rectTransform.anchorMin = new Vector2(0.5f, 0.5f);
                line.rectTransform.anchorMax = new Vector2(0.5f, 0.5f);
                line.rectTransform.pivot = new Vector2(0f, 0.5f);
                lines[index] = line;
            }
        }

        private static Image CreateImage(string name, Transform parent, Color color)
        {
            GameObject value = new GameObject(name);
            value.transform.SetParent(parent, false);
            Image image = value.AddComponent<Image>();
            image.color = color;
            image.raycastTarget = false;
            return image;
        }

        private static Text CreateText(string name, Transform parent, string value, Font font, int size, Color color)
        {
            GameObject child = new GameObject(name);
            child.transform.SetParent(parent, false);
            Text text = child.AddComponent<Text>();
            text.text = value;
            text.font = font;
            text.fontSize = size;
            text.fontStyle = FontStyle.Bold;
            text.alignment = TextAnchor.MiddleLeft;
            text.color = color;
            text.raycastTarget = false;
            return text;
        }

        private static void SetRect(RectTransform rect, Vector2 min, Vector2 max, Vector2 pivot, Vector2 position, Vector2 size)
        {
            rect.anchorMin = min;
            rect.anchorMax = max;
            rect.pivot = pivot;
            rect.anchoredPosition = position;
            rect.sizeDelta = size;
        }

        private static void UpdateWaveform(RectTransform graph, Image[] lines, float[] values, Color color)
        {
            if (graph == null)
            {
                return;
            }

            float width = Mathf.Max(10f, graph.rect.width);
            float height = Mathf.Max(10f, graph.rect.height);
            float left = -width * 0.5f;
            float bottom = -height * 0.5f;
            for (int index = 0; index < lines.Length; index++)
            {
                Image line = lines[index];
                if (line == null)
                {
                    continue;
                }

                float x1 = left + width * index / (HistoryLength - 1f);
                float x2 = left + width * (index + 1f) / (HistoryLength - 1f);
                float y1 = bottom + height * (0.08f + 0.84f * values[index]);
                float y2 = bottom + height * (0.08f + 0.84f * values[index + 1]);
                float dx = x2 - x1;
                float dy = y2 - y1;

                line.color = color;
                line.rectTransform.anchoredPosition = new Vector2(x1, y1);
                line.rectTransform.sizeDelta = new Vector2(Mathf.Sqrt(dx * dx + dy * dy), 2.6f);
                line.rectTransform.localEulerAngles = new Vector3(0f, 0f, Mathf.Atan2(dy, dx) * Mathf.Rad2Deg);
            }
        }

        private static void Push(float[] values, float value)
        {
            for (int index = 1; index < values.Length; index++)
            {
                values[index - 1] = values[index];
            }
            values[values.Length - 1] = Mathf.Clamp01(value);
        }
    }

    [HarmonyPatch(typeof(PlayerController), nameof(PlayerController.OnUpdate))]
    internal static class PlayerUpdatePatch
    {
        [HarmonyPostfix]
        private static void Postfix(PlayerController __instance)
        {
            if (__instance == null || __instance.Pca == null || __instance.Pca.PlayerHeartBeat == null)
            {
                return;
            }

            TelemetryPublisher.Sample(__instance.Pca.PlayerHeartBeat);
            CustomHudCanvas.Tick();
        }
    }

    internal static class TelemetryPublisher
    {
        private const int Port = 45678;
        private const long SendIntervalMilliseconds = 100;

        private static UdpClient _udp;
        private static IPEndPoint _target;
        private static long _lastSendAt;
        private static long _sequence;
        private static long _lastErrorAt;
        private static string _sessionId;

        internal static void Start()
        {
            _target = new IPEndPoint(IPAddress.Loopback, Port);
            _udp = new UdpClient();
            _lastSendAt = 0;
            _sequence = 0;
            _sessionId = Guid.NewGuid().ToString("N");
        }

        internal static void Stop()
        {
            if (_udp != null)
            {
                _udp.Dispose();
                _udp = null;
            }
        }

        internal static void Sample(PlayerHeartBeat heartBeat)
        {
            long now = Environment.TickCount64;
            if (_udp == null || now - _lastSendAt < SendIntervalMilliseconds)
            {
                return;
            }

            _lastSendAt = now;

            try
            {
                ProgressCommandServer.ApplyPending();
                float heartRate = heartBeat.HeartRate;
                float timeScale = Time.timeScale;
                float managedTimeScale = GetManagedTimeScale(timeScale);
                bool systemMenuOpen = IsSystemMenuOpen();
                bool paused = timeScale <= 0.001f || managedTimeScale <= 0.001f || systemMenuOpen;
                PlayerStateModel state = heartBeat.playerStateModel;

                bool moving = state != null && state.MoveV.sqrMagnitude > 0f;
                bool dashing = state != null && state.IsDash;
                bool crouching = state != null && state.IsCrouch;
                bool sitting = state != null && state.IsSit;
                bool playingAction = state != null && state.IsPlayingAction;
                string action = state != null && state.CurrentAction != null
                    ? state.CurrentAction.type.ToString()
                    : "None";

                GameStateData gameState = GameState.GameStateData;
                float ecstasy = gameState != null ? gameState.PlayerEcstasy : 0f;
                bool orgasm = state != null && state.IsEcstasyMotion;
                bool showingOff = state != null && state.IsLookedFlashing;
                string vibration = VibratorStateReader.Read(gameState);
                int piston = gameState != null ? gameState.PistonMachineModeType : 0;
                double currentRp = gameState != null ? gameState.CurrentRp : 0d;
                int exposeExp = gameState != null ? gameState.ExposeExp : 0;
                int currentSaveSlot = SaveManager.CurrentSaveSlot;

                InGameManager inGameManager = InGameManager.Instance;
                bool gameOver = inGameManager != null
                    && inGameManager.TempInGameState != null
                    && inGameManager.TempInGameState.IsGameOver;
                int foundNpcId = -1;

                bool watched = state != null
                    && (state.IsLookedHip || state.IsLookedUpper || state.IsLookedFlashing);
                bool detectionRising = false;
                bool found = false;
                float detection = state != null ? state.BaseBareyasusa : 0f;
                float maxNpcAlert = 0f;
                float nearestNpcDistance = -1f;
                int npcCount = 0;
                int watchingNpcCount = 0;
                int risingNpcCount = 0;
                NpcManager npcManager = NpcManager.Instance;
                if (npcManager != null)
                {
                    detectionRising = npcManager.IsRiseStrange;
                    found = npcManager.IsSomeOnePlayerFound;

                    if (npcManager.ExistNpcList != null)
                    {
                        for (int index = 0; index < npcManager.ExistNpcList.Count; index++)
                        {
                            NpcController npc = npcManager.ExistNpcList[index];
                            if (npc == null || !npc.IsAlive)
                            {
                                continue;
                            }

                            npcCount++;
                            if (npc.StrangenessValue > maxNpcAlert)
                            {
                                maxNpcAlert = npc.StrangenessValue;
                            }

                            if (nearestNpcDistance < 0f || npc.PlayerDistance < nearestNpcDistance)
                            {
                                nearestNpcDistance = npc.PlayerDistance;
                            }

                            if (npc.IsWatchingStranger)
                            {
                                watchingNpcCount++;
                            }

                            if (npc.IsRiseStrangeness)
                            {
                                risingNpcCount++;
                            }

                            if (npc.IsPlayerFound)
                            {
                                found = true;
                            }
                        }
                    }
                }

                string stage = inGameManager != null && inGameManager.CurrentStageController != null
                    ? inGameManager.CurrentStageController.StageType.ToString()
                    : "None";

                string json = BuildJson(
                    ++_sequence,
                    now,
                    timeScale,
                    managedTimeScale,
                    systemMenuOpen,
                    paused,
                    heartRate,
                    stage,
                    action,
                    moving,
                    dashing,
                    crouching,
                    sitting,
                    playingAction,
                    watched,
                    showingOff,
                    detectionRising,
                    found,
                    foundNpcId,
                    detection,
                    ecstasy,
                    orgasm,
                    vibration,
                    piston,
                    currentRp,
                    exposeExp,
                    currentSaveSlot,
                    gameOver,
                    maxNpcAlert,
                    nearestNpcDistance,
                    npcCount,
                    watchingNpcCount,
                    risingNpcCount);

                byte[] payload = Encoding.UTF8.GetBytes(json);
                _udp.Send(payload, payload.Length, _target);

                if (_sequence == 1)
                {
                    Plugin.PluginLog.LogInfo(
                        "First telemetry sample sent: BPM="
                        + heartRate.ToString("0.00", CultureInfo.InvariantCulture));
                }
            }
            catch (Exception error)
            {
                if (now - _lastErrorAt > 5000)
                {
                    _lastErrorAt = now;
                    Plugin.PluginLog.LogWarning("Telemetry sample failed: " + error.Message);
                }
            }
        }

        private static string BuildJson(
            long sequence,
            long monotonicMilliseconds,
            float timeScale,
            float managedTimeScale,
            bool systemMenuOpen,
            bool paused,
            float heartRate,
            string stage,
            string action,
            bool moving,
            bool dashing,
            bool crouching,
            bool sitting,
            bool playingAction,
            bool watched,
            bool showingOff,
            bool detectionRising,
            bool found,
            int foundNpcId,
            float detection,
            float ecstasy,
            bool orgasm,
            string vibration,
            int piston,
            double currentRp,
            int exposeExp,
            int currentSaveSlot,
            bool gameOver,
            float maxNpcAlert,
            float nearestNpcDistance,
            int npcCount,
            int watchingNpcCount,
            int risingNpcCount)
        {
            return "{"
                + "\"version\":2,"
                + "\"sessionId\":\"" + _sessionId + "\","
                + ReadDeviceModesJson()
                + "\"sequence\":" + sequence.ToString(CultureInfo.InvariantCulture) + ","
                + "\"monotonicMs\":" + monotonicMilliseconds.ToString(CultureInfo.InvariantCulture) + ","
                + "\"hudProtocol\":2,"
                + "\"timeScale\":" + timeScale.ToString("0.000", CultureInfo.InvariantCulture) + ","
                + "\"managedTimeScale\":" + managedTimeScale.ToString("0.000", CultureInfo.InvariantCulture) + ","
                + "\"systemMenuOpen\":" + JsonBool(systemMenuOpen) + ","
                + "\"paused\":" + JsonBool(paused) + ","
                + "\"heartRate\":" + heartRate.ToString("0.00", CultureInfo.InvariantCulture) + ","
                + "\"stage\":\"" + Escape(stage) + "\","
                + "\"action\":\"" + Escape(action) + "\","
                + "\"moving\":" + JsonBool(moving) + ","
                + "\"dashing\":" + JsonBool(dashing) + ","
                + "\"crouching\":" + JsonBool(crouching) + ","
                + "\"sitting\":" + JsonBool(sitting) + ","
                + "\"playingAction\":" + JsonBool(playingAction) + ","
                + "\"watched\":" + JsonBool(watched) + ","
                + "\"showingOff\":" + JsonBool(showingOff) + ","
                + "\"detectionRising\":" + JsonBool(detectionRising) + ","
                + "\"found\":" + JsonBool(found) + ","
                + "\"foundNpcId\":" + foundNpcId.ToString(CultureInfo.InvariantCulture) + ","
                + "\"detection\":" + detection.ToString("0.000", CultureInfo.InvariantCulture) + ","
                + "\"ecstasy\":" + ecstasy.ToString("0.000", CultureInfo.InvariantCulture) + ","
                + "\"orgasm\":" + JsonBool(orgasm) + ","
                + "\"vibration\":\"" + Escape(vibration) + "\","
                + "\"piston\":" + piston.ToString(CultureInfo.InvariantCulture) + ","
                + "\"currentRp\":" + currentRp.ToString("0.##", CultureInfo.InvariantCulture) + ","
                + "\"exposeExp\":" + exposeExp.ToString(CultureInfo.InvariantCulture) + ","
                + "\"currentSaveSlot\":" + currentSaveSlot.ToString(CultureInfo.InvariantCulture) + ","
                + "\"gameOver\":" + JsonBool(gameOver) + ","
                + "\"maxNpcAlert\":" + maxNpcAlert.ToString("0.000", CultureInfo.InvariantCulture) + ","
                + "\"nearestNpcDistance\":" + nearestNpcDistance.ToString("0.000", CultureInfo.InvariantCulture) + ","
                + "\"npcCount\":" + npcCount.ToString(CultureInfo.InvariantCulture) + ","
                + "\"watchingNpcCount\":" + watchingNpcCount.ToString(CultureInfo.InvariantCulture) + ","
                + "\"risingNpcCount\":" + risingNpcCount.ToString(CultureInfo.InvariantCulture)
                + "}";
        }

        // Actual-mode sampling adapted from kusadact/SecretFlasherManaka2_X_DGLAB
        // (MIT, Copyright (c) 2026 kusadact). See THIRD_PARTY_NOTICES.md.
        // Missing/changed optional APIs affect only the corresponding source.
        private static string ReadDeviceModesJson()
        {
            bool hasVibrator = false;
            string configured = "Unknown";
            string effective = "Unknown";
            bool hasPiston = false;
            int pistonEffective = 0;
            bool pistonRandom = false;
            try
            {
                hasVibrator = ReadActualVibrator(out configured, out effective);
            }
            catch { }
            try
            {
                hasPiston = ReadActualPiston(out pistonEffective, out pistonRandom);
            }
            catch { }
            return "\"hasVibratorData\":" + JsonBool(hasVibrator) + ","
                + "\"vibratorConfiguredMode\":\"" + Escape(configured) + "\","
                + "\"vibratorEffectiveMode\":\"" + Escape(effective) + "\","
                + "\"hasPistonData\":" + JsonBool(hasPiston) + ","
                + "\"pistonEffectiveMode\":" + pistonEffective.ToString(CultureInfo.InvariantCulture) + ","
                + "\"pistonRandom\":" + JsonBool(pistonRandom) + ",";
        }

        // Isolate optional member references in separately JIT-compiled methods.
        // A missing member in an older game is caught by the caller above,
        // without preventing the remaining telemetry packet from being sent.
        [MethodImpl(MethodImplOptions.NoInlining)]
        private static bool ReadActualVibrator(out string configured, out string effective)
        {
            configured = "Unknown";
            effective = "Unknown";
            CommonVibratorController source = CommonVibratorController.Leader;
            if (source == null) return false;
            configured = CommonVibratorController.VibrationStrength.ToString();
            effective = source.currentMode.ToString();
            return true;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static bool ReadActualPiston(out int effective, out bool random)
        {
            effective = 0;
            random = false;
            PlayerController player = PlayerController.Instance;
            var piston = player == null || player.Pca == null ? null : player.Pca.PistonMachineController;
            if (piston == null) return false;
            effective = piston.CurrentSpeedType;
            random = piston.isRandomMode;
            return true;
        }

        private static float GetManagedTimeScale(float fallback)
        {
            try
            {
                TimeScaleManager manager = TimeScaleManager.Instance;
                return manager != null ? manager.GetCurrentScale : fallback;
            }
            catch
            {
                return fallback;
            }
        }

        private static bool IsSystemMenuOpen()
        {
            try
            {
                SystemMenuView view = SystemMenuView.Instance;
                return view != null && view.gameObject != null && view.gameObject.activeInHierarchy;
            }
            catch
            {
                return false;
            }
        }

        private static string JsonBool(bool value)
        {
            return value ? "true" : "false";
        }

        private static string Escape(string value)
        {
            return (value ?? string.Empty)
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"");
        }

        internal static void SendLocalJson(string json)
        {
            try
            {
                if (_udp == null || _target == null)
                {
                    return;
                }

                byte[] payload = Encoding.UTF8.GetBytes(json);
                _udp.Send(payload, payload.Length, _target);
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("Local response failed: " + error.Message);
            }
        }
    }

    internal sealed class ProgressCommand
    {
        internal string Id;
        internal double Rp;
        internal int Exp;
        internal bool Save;
    }

    internal static class ProgressCommandServer
    {
        private const int CommandPort = 45679;
        private const double MaxRp = 999999999d;
        private const int MaxExp = 999999999;
        private static readonly object Gate = new object();
        private static UdpClient _listener;
        private static Thread _thread;
        private static bool _running;
        private static ProgressCommand _pending;
        private static string _lastAppliedId = string.Empty;

        internal static void Start()
        {
            try
            {
                _listener = new UdpClient(new IPEndPoint(IPAddress.Loopback, CommandPort));
                _listener.Client.ReceiveTimeout = 500;
                _running = true;
                _thread = new Thread(ListenLoop);
                _thread.IsBackground = true;
                _thread.Name = "ManakaProgressCommand";
                _thread.Start();
            }
            catch (Exception error)
            {
                Plugin.PluginLog.LogWarning("Progress command listener unavailable: " + error.Message);
            }
        }

        internal static void Stop()
        {
            _running = false;
            if (_listener != null)
            {
                try { _listener.Close(); } catch { }
                _listener = null;
            }
        }

        private static void ListenLoop()
        {
            IPEndPoint sender = new IPEndPoint(IPAddress.Loopback, 0);
            while (_running && _listener != null)
            {
                try
                {
                    byte[] payload = _listener.Receive(ref sender);
                    if (!IPAddress.IsLoopback(sender.Address))
                    {
                        continue;
                    }

                    string error;
                    ProgressCommand command;
                    if (!TryParse(Encoding.UTF8.GetString(payload), out command, out error))
                    {
                        SendResult("invalid", false, error, 0d, 0, -1);
                        continue;
                    }
                    lock (Gate)
                    {
                        if (command.Id != _lastAppliedId)
                        {
                            _pending = command;
                        }
                    }
                }
                catch (SocketException)
                {
                    // Receive timeout keeps shutdown responsive.
                }
                catch (ObjectDisposedException)
                {
                    return;
                }
                catch (Exception error)
                {
                    Plugin.PluginLog.LogWarning("Progress command receive failed: " + error.Message);
                }
            }
        }

        internal static void ApplyPending()
        {
            ProgressCommand command = null;
            lock (Gate)
            {
                if (_pending != null)
                {
                    command = _pending;
                    _pending = null;
                }
            }

            if (command != null && command.Id != _lastAppliedId)
            {
                ApplyProgress(command);
            }

        }

        private static void ApplyProgress(ProgressCommand command)
        {
            try
            {
                GameStateData state = GameState.GameStateData;
                if (state == null)
                {
                    SendResult(command.Id, false, "尚未载入可编辑存档", 0d, 0, -1);
                    return;
                }

                state.CurrentRp = command.Rp;
                state.ExposeExp = command.Exp;
                int slot = SaveManager.CurrentSaveSlot;
                if (command.Save)
                {
                    if (slot < 0)
                    {
                        throw new InvalidOperationException("当前没有有效的手动存档槽位");
                    }

                    SaveManager.Save(SaveRapper.SaveDataType.ManualSlot, slot, false);
                }

                _lastAppliedId = command.Id;
                SendResult(command.Id, true, command.Save ? "数值已写入并保存" : "数值已应用到当前游戏", state.CurrentRp, state.ExposeExp, slot);
                Plugin.PluginLog.LogInfo("Progress updated: RP=" + state.CurrentRp.ToString("0.##", CultureInfo.InvariantCulture)
                    + ", EXP=" + state.ExposeExp.ToString(CultureInfo.InvariantCulture)
                    + ", slot=" + slot.ToString(CultureInfo.InvariantCulture));
            }
            catch (Exception error)
            {
                SendResult(command.Id, false, error.Message, 0d, 0, SaveManager.CurrentSaveSlot);
                Plugin.PluginLog.LogWarning("Progress update failed: " + error);
            }
        }

        private static bool TryParse(string value, out ProgressCommand command, out string error)
        {
            command = null;
            error = string.Empty;
            string[] parts = (value ?? string.Empty).Split('|');
            if (parts.Length != 6 || parts[0] != "MANAKA_PROGRESS_V1")
            {
                error = "无法识别的本地修改命令";
                return false;
            }

            double rp;
            int exp;
            int saveFlag;
            if (string.IsNullOrWhiteSpace(parts[1])
                || !double.TryParse(parts[2], NumberStyles.Float, CultureInfo.InvariantCulture, out rp)
                || !int.TryParse(parts[3], NumberStyles.Integer, CultureInfo.InvariantCulture, out exp)
                || !int.TryParse(parts[4], NumberStyles.Integer, CultureInfo.InvariantCulture, out saveFlag)
                || parts[5] != "END")
            {
                error = "修改参数格式不正确";
                return false;
            }

            if (double.IsNaN(rp) || double.IsInfinity(rp) || rp < 0d || rp > MaxRp || exp < 0 || exp > MaxExp)
            {
                error = "数值必须在 0–999999999 之间";
                return false;
            }

            command = new ProgressCommand { Id = parts[1], Rp = rp, Exp = exp, Save = saveFlag == 1 };
            return true;
        }

        private static void SendResult(string id, bool ok, string message, double rp, int exp, int slot)
        {
            string json = "{"
                + "\"type\":\"progressResult\","
                + "\"id\":\"" + Escape(id) + "\","
                + "\"ok\":" + (ok ? "true" : "false") + ","
                + "\"message\":\"" + Escape(message) + "\","
                + "\"currentRp\":" + rp.ToString("0.##", CultureInfo.InvariantCulture) + ","
                + "\"exposeExp\":" + exp.ToString(CultureInfo.InvariantCulture) + ","
                + "\"currentSaveSlot\":" + slot.ToString(CultureInfo.InvariantCulture)
                + "}";
            TelemetryPublisher.SendLocalJson(json);
        }

        private static string Escape(string value)
        {
            return (value ?? string.Empty).Replace("\\", "\\\\").Replace("\"", "\\\"");
        }
    }
}

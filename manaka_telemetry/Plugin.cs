using System;
using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using ExposureUnnoticed2.Object3D.NPC.Script;
using ExposureUnnoticed2.Object3D.Player.Scripts;
using ExposureUnnoticed2.ObjectUI.SystemMenu;
using ExposureUnnoticed2.Scripts.Base;
using ExposureUnnoticed2.Scripts.InGame;
using UnityEngine;

namespace ManakaDGLab.Telemetry
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    public sealed class Plugin : BasePlugin
    {
        public const string PluginGuid = "local.manaka.dglab.telemetry";
        public const string PluginName = "Manaka DG-LAB Telemetry";
        public const string PluginVersion = "0.3.1-standalone";

        private Harmony _harmony;
        internal static ManualLogSource PluginLog;

        public override void Load()
        {
            PluginLog = Log;
            TelemetryPublisher.Start();
            ProgressCommandServer.Start();

            _harmony = new Harmony(PluginGuid);
            _harmony.PatchAll(typeof(PlayerUpdatePatch));

            Log.LogInfo("Pilot telemetry enabled: UDP 127.0.0.1:45678");
            Log.LogInfo("Progress editor enabled: local-only UDP 127.0.0.1:45679");
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
            return true;
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

        internal static void Start()
        {
            _target = new IPEndPoint(IPAddress.Loopback, Port);
            _udp = new UdpClient();
            _lastSendAt = 0;
            _sequence = 0;
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
                string vibration = gameState != null
                    ? gameState.PlayerVibrationModeType.ToString()
                    : "None";
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
                + "\"version\":1,"
                + "\"sequence\":" + sequence.ToString(CultureInfo.InvariantCulture) + ","
                + "\"monotonicMs\":" + monotonicMilliseconds.ToString(CultureInfo.InvariantCulture) + ","
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

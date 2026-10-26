using ExposureUnnoticed2.Object3D.AdultGoods;
using ExposureUnnoticed2.Scripts.InGame;

namespace ManakaDGLab.Telemetry
{
    internal static class VibratorStateReader
    {
        // Read-only, called from the player's main-thread telemetry update.
        internal static string Read(GameStateData state)
        {
            string selected = state == null ? "Off" : state.PlayerVibrationModeType.ToString();
            if (selected != "Random") return selected;
            try {
                CommonVibratorController current = CommonVibratorController.Leader;
                if (current == null) return "Unknown";
                ExposureUnnoticed2.Master.AdultGoods.VibrationModeType effective = current.currentMode;
                return effective.ToString() == "Random" ? "Unknown" : effective.ToString();
            } catch { return "Unknown"; }
        }
    }
}

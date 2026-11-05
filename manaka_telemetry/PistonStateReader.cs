using ExposureUnnoticed2.Object3D.Player.Scripts;
using ExposureUnnoticed2.Scripts.InGame;

namespace ManakaDGLab.Telemetry
{
    internal static class PistonStateReader
    {
        // Read only from the player's main-thread update. Never invent a random speed.
        internal static int ReadEffective(int selected, PlayerClassAccessor player, out bool random)
        {
            random = selected == 4;
            if (selected == 0) return 0;
            if (selected < 1 || selected > 4) return -1;
            try
            {
                var current = player == null ? null : player.PistonMachineController;
                if (current != null) random = random || current.isRandomMode;
                if (!random) return selected;
                if (current == null) return -1;
                int effective = current.CurrentSpeedType;
                return effective >= 0 && effective <= 3 ? effective : -1;
            }
            catch { return random ? -1 : selected; }
        }
    }
}

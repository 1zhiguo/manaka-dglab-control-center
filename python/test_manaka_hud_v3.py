"""HUD display data only: no radio, no game connection."""
import unittest
from manaka_devices.hud_settings import DEFAULTS,build_packet,sanitize_settings
from test_manaka_ovc import Harness

class HudV3Tests(unittest.TestCase):
    def packet(self,boo=None,settings=None):
        return build_packet(1,settings or DEFAULTS,visible=True,connected=(True,False),active=(True,False),
                            strengths=(10,20,0,0),caps=(30,30,200,200),pulses=(.2,.5,0,0),booboop=boo).decode().split("|")
    def test_six_display_cells_have_independent_role_and_bounds(self):
        p=self.packet({"connected":True,"active":True,"stretch":99,"vibration":2,"cap":4})
        self.assertEqual((p[0],len(p),p[-1]),("MANAKA_HUD_V3",30,"END"))
        self.assertEqual(p[23:29],["4.00","2.00","4.00","4.00","0.000","0.000"])
        self.assertEqual((int(p[9]),int(p[10])),(5,5))
        self.assertTrue(int(p[3])&128)
        self.assertLess(len("|".join(p)),512)
    def test_offline_and_idle_never_display_nonzero_levels(self):
        for connected,active in ((False,True),(True,False)):
            p=self.packet({"connected":connected,"active":active,"stretch":9,"vibration":9,"cap":4})
            self.assertEqual(p[23:25],["0.00","0.00"])
            self.assertFalse(int(p[10])&4)
        p=self.packet({"connected":True,"active":True,"stretch":3,"vibration":2,"cap":float("nan")})
        self.assertEqual(p[23:27],["0.00"]*4)
    def test_hiding_belt_changes_display_mask_only(self):
        boo={"connected":True,"active":True,"stretch":3,"vibration":1,"cap":4}
        shown=self.packet(boo)
        hidden=self.packet(boo,{**DEFAULTS,"show_booboop":False})
        self.assertFalse(int(hidden[3])&128)
        self.assertEqual(shown[9:],hidden[9:])
    def test_belt_only_is_valid_without_ab_channels(self):
        settings={**DEFAULTS,"show_pulse":False,"show_ovc":False,"show_a":False,"show_b":False}
        self.assertEqual(sanitize_settings(settings),settings)
        b=Harness()
        self.assertTrue(b.saveHudSettings(settings))
        b.bridge.emergency_stop.assert_not_called()
        self.assertTrue(b.auto_output_enabled)
        self.assertFalse(b.saveHudSettings({**settings,"show_booboop":False}))
    def test_v2_fallback_does_not_leak_belt_flags(self):
        p=self.packet()
        self.assertEqual((p[0],len(p)),("MANAKA_HUD_V2",24))
        self.assertFalse(int(p[3])&128)
        self.assertLessEqual(int(p[9]),3)
        only={**DEFAULTS,"show_pulse":False,"show_ovc":False}
        self.assertEqual(self.packet(settings=only)[2],"0")

if __name__=="__main__":unittest.main()

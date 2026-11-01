import unittest
from manaka_waveforms import WaveformPreset
from manaka_wave_mix import mix_waveforms
from manaka_dglab_bridge import pulse_message


class WaveMixTests(unittest.TestCase):
    def setUp(self):
        self.first = WaveformPreset("first","first","","","#000000",(100,0),(10,))
        self.second = WaveformPreset("second","second","","","#000000",(0,100),(20,))

    def test_weighted_amplitudes_are_not_multiplied_twice(self):
        wave = mix_waveforms(((self.first,7,0),(self.second,3,0)))
        self.assertEqual(wave.v3_frames()[0], "0A0A0A0A46464646")
        self.assertEqual(wave.v3_frames()[1], "141414141E1E1E1E")
        pulse_message("A",wave.v3_frames())

    def test_phase_shifts_sampling_and_results_are_cached(self):
        layers = ((self.first,1,100),)
        shifted = mix_waveforms(layers)
        self.assertEqual(shifted.amplitudes,(0,100))
        self.assertIs(mix_waveforms(layers),shifted)

    def test_large_weights_remain_valid_and_empty_layers_are_silent(self):
        wave = mix_waveforms(((self.first,1000,0),(self.second,1000,100)))
        self.assertLessEqual(max(wave.amplitudes),100)
        self.assertIsNone(mix_waveforms(()))

    def test_streaming_windows_follow_absolute_phase_without_shortening_period(self):
        long = WaveformPreset("long","long","","","#000000",tuple(range(100)),(10,))
        layers = ((long,1,0),)
        early = mix_waveforms(layers,0,8)
        later = mix_waveforms(layers,88,8)
        self.assertEqual(early.amplitudes,tuple(range(8)))
        self.assertEqual(later.amplitudes,tuple(range(88,96)))

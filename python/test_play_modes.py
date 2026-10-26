"""Gameplay contracts: migration, independent caps, roles, legacy and reference assets."""
import json
from dataclasses import replace, asdict
from pathlib import Path
import unittest

from manaka_channel_engine import MappingSettings, ChannelSettings, Binding, ChannelEngine, migrate_settings
from manaka_runtime import RuntimeConfig, RealtimeProcessor, DisplayMailbox
from manaka_trigger_engine import ManakaTriggerEngine
from manaka_waveforms import PRESETS, GAME_ACTION_TYPES, action_label
from manaka_wave_library import parse_import
from manaka_wave_rules import WavePolicy, ChannelRules, WaveRule, migrate_policy, WaveRouter
from test_realtime_runtime import FakeBridge, packet


class PlayModeTests(unittest.TestCase):
    def test_schema_two_migration_preserves_effective_limits_then_removes_shared_cap(self):
        raw=MappingSettings(A=ChannelSettings(hard_cap=10),B=ChannelSettings(hard_cap=60)).to_dict()
        raw.update(schema=2,global_cap=30)
        migrated=MappingSettings.parse(raw)
        self.assertEqual((migrated.A.hard_cap,migrated.B.hard_cap),(10,30))
        raw=migrated.to_dict(); raw['B']['hard_cap']=60
        restored=MappingSettings.parse(raw)
        self.assertEqual((restored.A.hard_cap,restored.B.hard_cap,restored.global_cap),(10,60,200))

    def run_processor(self, mapping, *, policy=None, caps=None, **changes):
        bridge=FakeBridge()
        if caps: bridge.channel_limit=lambda key:caps[key]
        now=[10.]
        runtime=RealtimeProcessor(RuntimeConfig(mapping=mapping,wave_policy=policy or WavePolicy()),bridge,DisplayMailbox(),clock=lambda:now[0])
        for i in range(1,31):
            now[0]+=.1
            snap=runtime.process(packet(i,**changes))
        self.assertIsNotNone(snap)
        return snap, runtime

    def test_caps_and_device_feedback_do_not_cross_channels(self):
        a=ChannelSettings(maximum=80,hard_cap=10,attack=100)
        b=replace(a,hard_cap=60)
        snap,_=self.run_processor(MappingSettings(A=a,B=b))
        self.assertEqual((snap.output_a,snap.output_b),(10,60))
        snap,_=self.run_processor(MappingSettings(A=a,B=b),caps=dict(A=3,B=70))
        self.assertEqual((snap.output_a,snap.output_b),(3,60))

    def test_200_range_is_not_truncated_in_mapping_limiter_or_hud(self):
        a=ChannelSettings(maximum=200,hard_cap=200,attack=100)
        b=replace(a,hard_cap=180)
        mapping=MappingSettings.parse(MappingSettings(A=a,B=b).to_dict())
        snap,_=self.run_processor(mapping,caps=dict(A=200,B=180))
        self.assertEqual((snap.output_a,snap.output_b),(200,180))
        from manaka_channel_engine import ChannelPeakLimiter
        self.assertEqual(ChannelPeakLimiter().apply('A',200,peak=False,now=1,cap=200),200)
        raw=mapping.to_dict(); raw['A']['hard_cap']=201
        with self.assertRaises(ValueError): MappingSettings.parse(raw)
        raw=mapping.to_dict();raw['A']['bindings'][0]['strong']=101
        with self.assertRaises(ValueError): MappingSettings.parse(raw)

    def test_schema_three_keeps_calibrated_caps_when_range_increases(self):
        raw=MappingSettings().to_dict();raw.update(schema=3,global_cap=100)
        raw['A']['hard_cap']=65;raw['B']['hard_cap']=80
        settings=MappingSettings.parse(raw)
        self.assertEqual((settings.A.hard_cap,settings.B.hard_cap),(65,80))
        self.assertEqual(settings.global_cap,200)

    def test_sync_directions_keep_caps_off_wave_and_disabled_channels(self):
        a=ChannelSettings(maximum=40,hard_cap=30,attack=100)
        b=replace(a,maximum=5,hard_cap=20)
        for sync,expected in [('off',(30,5)),('A_to_B',(30,20)),('B_to_A',(5,5))]:
            snap,_=self.run_processor(MappingSettings(A=a,B=b,intensity_sync=sync))
            self.assertEqual((snap.output_a,snap.output_b),expected)
        snap,_=self.run_processor(MappingSettings(A=replace(a,enabled=False),B=b,intensity_sync='A_to_B'))
        self.assertEqual((snap.output_a,snap.output_b),(0,0))
        snap,_=self.run_processor(MappingSettings(A=a,B=b,intensity_sync='A_to_B'),policy=WavePolicy(B=ChannelRules('off')))
        self.assertEqual(snap.output_b,0)

    def test_swapping_roles_changes_level_source_without_rewriting_wave_conditions(self):
        a=ChannelSettings(device='piston',maximum=40,hard_cap=60,attack=100,bindings=(Binding(source='device'),))
        b=replace(a,device='vibrator')
        snap,_=self.run_processor(MappingSettings(A=a,B=b),hasPistonData=True,pistonEffectiveMode=2,hasVibratorData=True,vibratorEffectiveMode='high')
        self.assertEqual((snap.output_a,snap.output_b),(20,28))
        self.assertEqual((snap.wave_a.key,snap.wave_b.key),('official_breath','official_tide'))

    def test_telemetry_intensity_is_gated_by_bound_device_even_when_sync_enabled(self):
        a=ChannelSettings(maximum=40,hard_cap=60,attack=100)
        b=replace(a,device='piston',bindings=(Binding(source='action_active'),))
        for sync in ('off','A_to_B'):
            snap,_=self.run_processor(MappingSettings(A=a,B=b,intensity_sync=sync),hasPistonData=True,pistonEffectiveMode=0)
            self.assertEqual(snap.output_b,0)
            snap,_=self.run_processor(MappingSettings(A=a,B=b,intensity_sync=sync),hasPistonData=True,pistonEffectiveMode=1,ecstasy=None)
            self.assertEqual(snap.output_b,40)

    def test_action_wave_condition_does_not_need_ecstasy(self):
        router=WaveRouter(WavePolicy(A=ChannelRules(rules=(WaveRule('walk','action','donor_piston',value='Walking',stable_ms=0),))))
        result=router.evaluate(packet(action='Walking',ecstasy=None,playingAction=True),10,lambda *args:1)
        self.assertEqual(result['A'].wave,'donor_piston')

    def test_exact_user_selected_reference_names_and_all_subframes(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/donor_selected_waves.json').read_text(encoding='utf-8'))
        expected=parse_import(json.dumps(fixture))
        for key,row in zip(('donor_vibrator','donor_piston','donor_climax'),expected):
            self.assertEqual(PRESETS[key].name,row['name'])
            self.assertEqual(PRESETS[key].v3_frames(),tuple(row['frames']))
        policy=migrate_policy({},migrate_settings({}))
        self.assertEqual(policy.A.default_wave,'donor_vibrator')
        self.assertEqual(policy.B.default_wave,'donor_piston')
        self.assertEqual(next(x.wave for x in policy.A.rules if x.source=='climax'),'donor_climax')

    def test_legacy_curves_events_timing_and_cooldown_match_original_replay(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/legacy_original_replay.json').read_text())
        engine=ManakaTriggerEngine(max_strength=30,min_strength=5,output_max=24)
        engine.channel_caps=(30,30)
        for row in fixture['records']:
            expected=dict(row['frame']);expected['events']=tuple(expected['events'])
            self.assertEqual(asdict(engine.evaluate(row['packet'],row['dt'])),expected)

    def test_new_rules_do_not_control_legacy_events_or_action_wave(self):
        mapping=MappingSettings(mode='legacy_v1')
        snap,runtime=self.run_processor(mapping,policy=WavePolicy(A=ChannelRules('off'),B=ChannelRules('off')),action='Dogeza')
        self.assertEqual(snap.wave_b.key,'official_breath')
        runtime.clock=lambda:13.1
        snap=runtime.process(packet(31,orgasm=True))
        self.assertEqual(snap.frame.pattern_a,'peak')
        self.assertTrue(snap.reason_a.startswith('legacy:'))

    def test_all_known_actions_have_chinese_labels(self):
        for key in GAME_ACTION_TYPES:
            self.assertTrue(any('\u4e00'<=c<='\u9fff' for c in action_label(key,'zh')),key)


if __name__=='__main__': unittest.main()

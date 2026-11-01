"""Normalized V3 sampling and weighted overlay, independent of device intensity.

The layer/phase approach follows SecretFlasherManaka2_X_DGLAB (MIT, kusadact).
See THIRD_PARTY_NOTICES.md. Both intensity and encoded amplitudes stay bounded.
"""
from functools import lru_cache
from math import lcm

from manaka_waveforms import WaveformPreset


@lru_cache(maxsize=64)
def mix_waveforms(layers, start_frame=None, frame_count=None):
    """Layers are (preset, absolute contribution, phase_ms) tuples.

    Amplitudes are a weighted average because absolute contributions have
    already been summed into the independent channel strength. This avoids
    applying the same intensity mapping a second time inside the waveform.
    """
    layers = tuple((wave, max(0., float(weight)), int(phase)) for wave, weight, phase in layers if wave and weight > 0)
    if not layers:
        return None
    periods = [len(wave.v3_frames()) for wave, _, _ in layers]
    period = min(80, lcm(*periods)) if frame_count is None else frame_count
    origin = 0 if start_frame is None else start_frame
    total = sum(weight for _, weight, _ in layers)
    frames, preview, frequencies = [], [], []
    for frame_index in range(origin,origin+period):
        frequency_bytes, amplitude_bytes = [], []
        for slot in range(4):
            combined, maximum, selected_frequency = 0., -1., 10
            for wave, weight, phase in layers:
                sample = frame_index*4+slot-phase//25
                encoded = wave.v3_frames()[(sample//4) % len(wave.v3_frames())]
                offset = sample % 4
                frequency = int(encoded[offset*2:offset*2+2],16)
                amplitude = int(encoded[8+offset*2:10+offset*2],16)
                contribution = weight * amplitude
                combined += contribution
                if contribution > maximum:
                    maximum, selected_frequency = contribution, frequency
            frequency_bytes.append(f"{selected_frequency:02X}")
            amplitude_bytes.append(f"{max(0,min(100,round(combined/total))):02X}")
        frames.append("".join(frequency_bytes+amplitude_bytes))
        preview.append(max(int(value,16) for value in amplitude_bytes))
        frequencies.append(int(frequency_bytes[0],16))
    return WaveformPreset("mixed:"+":".join(wave.key for wave,_,_ in layers), "混合波形", "按来源权重合成", "多来源联动",
        "#59DCE7",tuple(preview),tuple(frequencies),raw_frames=tuple(frames))

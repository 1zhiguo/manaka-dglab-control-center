"""Curated DG-LAB Coyote V3 waveform frames.

The frame data is derived from dungeonlab-open/dglab-kit's official waveform
catalog.  Keeping it in a separate module makes provenance explicit and lets
the main application use the original V3 data without approximating it.

Source: https://github.com/dungeonlab-open/dglab-kit/blob/main/src/waveform/coyote.ts
License: GNU General Public License v3.0
"""

from __future__ import annotations


def _frame(frequency: int, amplitude: int) -> str:
    """Build one official-style V3 frame from four equal 25 ms groups."""
    return (f"{frequency:02X}" * 4) + (f"{amplitude:02X}" * 4)


OFFICIAL_WAVEFORMS: dict[str, tuple[str, ...]] = {
    "official_breath": tuple(
        _frame(10, amplitude)
        for amplitude in (0, 20, 40, 60, 80, 100, 100, 100, 0, 0, 0, 0)
    ),
    "official_tide": tuple(
        _frame(frequency, amplitude)
        for frequency, amplitude in (
            (10, 0),
            (11, 16),
            (13, 33),
            (14, 50),
            (16, 66),
            (18, 83),
            (19, 100),
            (21, 92),
            (22, 84),
            (24, 76),
            (26, 68),
            (26, 0),
            (27, 16),
            (29, 33),
            (30, 50),
            (32, 66),
            (34, 83),
            (35, 100),
            (37, 92),
            (38, 84),
            (40, 76),
            (42, 68),
            (10, 0),
        )
    ),
    "official_pulsating": tuple(
        _frame(10, amplitude)
        for amplitude in (100, 0, 100, 66, 33, 0, 0, 0) * 3
    ),
    "official_gradual": tuple(
        _frame(10, amplitude)
        for amplitude in (
            0,
            28,
            0,
            52,
            0,
            73,
            0,
            87,
            0,
            100,
            0,
            0,
            28,
            0,
            52,
            0,
            73,
            0,
            87,
            0,
            100,
            0,
            0,
        )
    ),
    "official_heartbeat": tuple(
        _frame(frequency, amplitude)
        for frequency, amplitude in (
            (112, 100),
            (112, 100),
            (112, 100),
            (112, 100),
            (112, 100),
            (112, 100),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 75),
            (10, 83),
            (10, 91),
            (10, 100),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 75),
            (10, 83),
            (10, 91),
            (10, 100),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
            (10, 0),
        )
    ),
    "official_bouncy": tuple(
        _frame(frequency, amplitude)
        for frequency, amplitude in (
            (10, 0), (10, 33), (11, 66), (12, 100),
            (12, 0), (13, 33), (14, 66), (15, 100),
            (15, 0), (15, 33), (16, 66), (17, 100),
            (17, 0), (18, 33), (19, 66), (20, 100),
            (20, 0), (20, 33), (21, 66), (22, 100),
            (22, 0), (23, 33), (24, 66), (25, 100),
            (25, 0), (25, 33), (26, 66), (27, 100),
            (27, 0), (28, 33), (29, 66), (30, 100),
            (30, 0), (30, 33), (31, 66), (32, 100),
            (32, 0), (33, 33), (34, 66), (35, 100),
            (35, 0), (35, 33), (36, 66), (37, 100),
            (37, 0), (38, 33), (39, 66), (40, 100),
            (10, 0), (10, 0),
        )
    ),
    "official_ripple": tuple(
        _frame(frequency, amplitude)
        for frequency in (10, 17, 25, 33, 40, 48, 56, 63, 71, 79, 86, 94, 100, 102)
        for amplitude in (0, 50, 100, 73)
    )
    + (_frame(10, 0),),
    "official_tease2": tuple(
        _frame(frequency, amplitude)
        for _ in range(4)
        for frequency, amplitude in zip(
            (37, 34, 32, 30, 28, 25, 23, 21, 19, 17),
            (0, 11, 22, 33, 44, 55, 66, 77, 88, 100),
        )
    )
    + (_frame(10, 0),)
    + tuple(
        _frame(frequency, amplitude)
        for frequency in range(11, 30)
        for amplitude in (100, 0)
    )
    + (_frame(30, 100), _frame(10, 0), _frame(10, 0)),
}


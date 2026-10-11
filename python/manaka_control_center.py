"""Manaka × DG-LAB beginner-friendly Windows control center."""

from __future__ import annotations

import json
import math
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import qrcode
from PIL import Image, ImageTk

from manaka_dglab_bridge import DEFAULT_PORT, DGLabBridge
from manaka_trigger_engine import ManakaTriggerEngine, TriggerFrame, clamp
from manaka_waveforms import (
    DEFAULT_WAVE_MAP,
    LEGACY_DEFAULT_WAVE_MAP,
    PRESETS,
    WAVE_ZONES,
    ZONE_LABELS,
    ZONE_REASONS,
    WaveformPreset,
    WaveformSelector,
    sanitize_wave_map,
)


APP_NAME = "Manaka Control Center"
APP_VERSION = "0.10.0-theme-smooth"
UDP_HOST = "127.0.0.1"
UDP_PORT = 45678
STALE_SECONDS = 0.75

THEMES = {
    "dark": {
        "BG": "#070A11",
        "PANEL": "#111724",
        "PANEL_2": "#192235",
        "GLASS_BORDER": "#2C3A52",
        "GLASS_HIGHLIGHT": "#52617A",
        "SHADOW": "#02040A",
        "TEXT": "#F7F9FD",
        "MUTED": "#929DB0",
        "ACCENT": "#FF6FAE",
        "VIOLET": "#A78BFA",
        "CYAN": "#59DCE7",
        "GREEN": "#4ADDA5",
        "AMBER": "#F7C55B",
        "RED": "#FF5D7A",
        "TRACK": "#293449",
        "INPUT_BG": "#0B111C",
        "PREVIEW_BG": "#0B1220",
        "GRID": "#27354C",
        "ALERT_PANEL": "#281923",
        "BUTTON_TEXT": "#10131A",
        "LOG_BG": "#070B12",
        "LOG_TEXT": "#C9D3E3",
    },
    "light": {
        "BG": "#EEF2F8",
        "PANEL": "#F8FAFD",
        "PANEL_2": "#E8EEF7",
        "GLASS_BORDER": "#C8D2E2",
        "GLASS_HIGHLIGHT": "#FFFFFF",
        "SHADOW": "#CCD5E2",
        "TEXT": "#182033",
        "MUTED": "#657188",
        "ACCENT": "#E6508A",
        "VIOLET": "#7659D9",
        "CYAN": "#178F9C",
        "GREEN": "#16986D",
        "AMBER": "#C98112",
        "RED": "#D94362",
        "TRACK": "#CCD6E5",
        "INPUT_BG": "#FFFFFF",
        "PREVIEW_BG": "#F1F5FA",
        "GRID": "#D5DEEA",
        "ALERT_PANEL": "#FCEAF0",
        "BUTTON_TEXT": "#111827",
        "LOG_BG": "#F7F9FC",
        "LOG_TEXT": "#334155",
    },
}


def apply_theme_palette(name: str) -> str:
    """Expose the selected immutable palette through the legacy color globals."""
    selected = name if name in THEMES else "dark"
    globals().update(THEMES[selected])
    return selected


apply_theme_palette("dark")


def rounded_rectangle(canvas, x1, y1, x2, y2, radius, **kwargs):
    radius = max(2, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    points = (
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    )
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def blend(color_a: str, color_b: str, ratio: float) -> str:
    ratio = clamp(ratio, 0.0, 1.0)
    a = tuple(int(color_a[i : i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(color_b[i : i + 2], 16) for i in (1, 3, 5))
    mixed = tuple(round(left + (right - left) * ratio) for left, right in zip(a, b))
    return "#" + "".join(f"{channel:02X}" for channel in mixed)


class GlassSurface(tk.Canvas):
    """Rounded glass-like container with a soft shadow and inset highlight."""

    def __init__(self, parent, *, padding=18, fill=None, radius=22, height=None, **kwargs) -> None:
        fill = PANEL if fill is None else fill
        super().__init__(
            parent,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            height=height or 1,
            **kwargs,
        )
        self.padding = padding
        self.fill = fill
        self.radius = radius
        self.content = tk.Frame(self, bg=fill, bd=0, highlightthickness=0)
        self.content_window = self.create_window(
            padding,
            padding,
            anchor="nw",
            window=self.content,
            tags=("glass-content",),
        )
        self.bind("<Configure>", self._redraw)

    def _redraw(self, _event=None) -> None:
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 4 or height <= 4:
            return
        self.delete("glass-shape")
        rounded_rectangle(
            self,
            5,
            7,
            width - 2,
            height - 2,
            self.radius,
            fill=SHADOW,
            outline="",
            tags=("glass-shape",),
        )
        rounded_rectangle(
            self,
            1,
            1,
            width - 5,
            height - 6,
            self.radius,
            fill=self.fill,
            outline=GLASS_BORDER,
            width=1,
            tags=("glass-shape",),
        )
        self.create_line(
            self.radius,
            2,
            width - self.radius - 5,
            2,
            fill=GLASS_HIGHLIGHT,
            width=1,
            tags=("glass-shape",),
        )
        self.tag_lower("glass-shape")
        inset = self.padding
        self.coords(self.content_window, inset, inset)
        self.itemconfigure(
            self.content_window,
            width=max(1, width - inset * 2 - 4),
            height=max(1, height - inset * 2 - 6),
        )


class GlassButton(tk.Canvas):
    """Keyboard-accessible rounded button drawn on a transparent-looking canvas."""

    def __init__(self, parent, text, command, color=None, fg=None, padx=16, pady=9, **kwargs) -> None:
        color = ACCENT if color is None else color
        fg = BUTTON_TEXT if fg is None else fg
        font_size = kwargs.pop("font_size", 10)
        width = kwargs.pop("width", max(88, len(text) * 17 + padx * 2))
        height = kwargs.pop("height", max(38, 19 + pady * 2))
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=1,
            **kwargs,
        )
        self.text = text
        self.command = command
        self.color = color
        self.fg = fg
        self.font = ("Microsoft YaHei UI", font_size, "bold")
        self.hovered = False
        self.pressed = False
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", lambda _event: self.command())
        self.bind("<space>", lambda _event: self.command())

    def _enter(self, _event) -> None:
        self.hovered = True
        self._draw()

    def _leave(self, _event) -> None:
        self.hovered = False
        self.pressed = False
        self._draw()

    def _press(self, _event) -> None:
        self.pressed = True
        self.focus_set()
        self._draw()

    def _release(self, event) -> None:
        should_invoke = self.pressed and 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self.pressed = False
        self._draw()
        if should_invoke:
            self.command()

    def _draw(self, _event=None) -> None:
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 2 or height <= 2:
            return
        self.delete("all")
        tone = self.color
        if self.pressed:
            tone = blend(self.color, BG, 0.16)
        elif self.hovered:
            tone = blend(self.color, "#FFFFFF", 0.10)
        rounded_rectangle(self, 3, 5, width - 2, height - 1, 13, fill=SHADOW, outline="")
        rounded_rectangle(self, 1, 1, width - 4, height - 5, 13, fill=tone, outline=blend(tone, "#FFFFFF", 0.22), width=1)
        self.create_line(14, 2, max(15, width - 17), 2, fill=blend(tone, "#FFFFFF", 0.32), width=1)
        self.create_text(width / 2 - 1, (height - 4) / 2, text=self.text, fill=self.fg, font=self.font)

    def set_text(self, text: str) -> None:
        self.text = text
        self._draw()


class PillBadge(tk.Canvas):
    def __init__(self, parent, text, color=None, **kwargs) -> None:
        color = GREEN if color is None else color
        width = kwargs.pop("width", max(118, len(text) * 15 + 30))
        super().__init__(parent, width=width, height=34, bg=parent.cget("bg"), highlightthickness=0, bd=0, **kwargs)
        self.text = text
        self.color = color
        self.bind("<Configure>", self._draw)

    def _draw(self, _event=None) -> None:
        self.delete("all")
        width = self.winfo_width()
        rounded_rectangle(self, 1, 2, width - 2, 31, 14, fill=blend(self.color, BG, 0.76), outline=blend(self.color, BG, 0.34), width=1)
        self.create_oval(13, 14, 19, 20, fill=self.color, outline="")
        self.create_text(width / 2 + 6, 17, text=self.text, fill=self.color, font=("Microsoft YaHei UI", 9, "bold"))

    def set(self, text: str, color: str | None = None) -> None:
        self.text = text
        if color is not None:
            self.color = color
        self._draw()


class ModernProgress(tk.Canvas):
    """A time-based progress bar whose UI animation is independent of telemetry FPS."""

    def __init__(self, parent, maximum=100, color=None, **kwargs) -> None:
        super().__init__(parent, height=18, bg=parent.cget("bg"), highlightthickness=0, **kwargs)
        self.maximum = max(1.0, float(maximum))
        self.value = 0.0
        self.target_value = 0.0
        self.color = ACCENT if color is None else color
        self._animation_job = None
        self._last_tick = time.perf_counter()
        self._track_item = None
        self._glow_item = None
        self._fill_item = None
        self._knob_item = None
        self.bind("<Configure>", lambda _event: self.redraw())

    def set(self, value: float, *, immediate: bool = False) -> None:
        self.target_value = clamp(float(value), 0.0, self.maximum)
        if immediate:
            self.value = self.target_value
            if self._animation_job is not None:
                self.after_cancel(self._animation_job)
                self._animation_job = None
            self.redraw()
            return
        if self._animation_job is None:
            self._last_tick = time.perf_counter()
            self._animation_job = self.after(16, self._animate)

    def _animate(self) -> None:
        self._animation_job = None
        if not self.winfo_exists():
            return
        now = time.perf_counter()
        elapsed = min(0.08, max(0.001, now - self._last_tick))
        self._last_tick = now
        difference = self.target_value - self.value
        # A frame-rate-independent 120 ms ease: smooth at 60 Hz and stable if a frame is late.
        self.value += difference * (1.0 - math.exp(-elapsed / 0.12))
        if abs(self.target_value - self.value) < 0.025:
            self.value = self.target_value
        self.redraw()
        if self.value != self.target_value:
            self._animation_job = self.after(16, self._animate)

    def destroy(self) -> None:
        if self._animation_job is not None:
            try:
                self.after_cancel(self._animation_job)
            except tk.TclError:
                pass
            self._animation_job = None
        super().destroy()

    def _ensure_items(self) -> None:
        if self._track_item is not None:
            return
        self._track_item = self.create_line(7, 9, 8, 9, width=8, capstyle="round")
        self._glow_item = self.create_line(7, 9, 8, 9, width=14, capstyle="round")
        self._fill_item = self.create_line(7, 9, 8, 9, width=7, capstyle="round")
        self._knob_item = self.create_oval(4, 6, 10, 12, outline="")

    def redraw(self) -> None:
        width = self.winfo_width()
        if width <= 2:
            return
        self._ensure_items()
        y = 9
        self.coords(self._track_item, 7, y, width - 7, y)
        self.itemconfigure(self._track_item, fill=TRACK)
        fill_width = 7 + (width - 14) * (self.value / self.maximum)
        if fill_width > 9:
            self.coords(self._glow_item, 7, y, fill_width, y)
            self.coords(self._fill_item, 7, y, fill_width, y)
            self.coords(self._knob_item, fill_width - 3, y - 3, fill_width + 3, y + 3)
            self.itemconfigure(self._glow_item, fill=blend(self.color, BG, 0.68), state="normal")
            self.itemconfigure(self._fill_item, fill=self.color, state="normal")
            self.itemconfigure(self._knob_item, fill=TEXT, state="normal")
        else:
            self.itemconfigure(self._glow_item, state="hidden")
            self.itemconfigure(self._fill_item, state="hidden")
            self.itemconfigure(self._knob_item, state="hidden")


class ValueSlider(tk.Canvas):
    def __init__(self, parent, variable, minimum, maximum, command=None, color=None, **kwargs) -> None:
        super().__init__(parent, height=48, bg=kwargs.pop("bg", PANEL_2), highlightthickness=0, cursor="hand2", **kwargs)
        self.variable = variable
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.command = command
        self.color = color
        self.margin = 17
        self.bind("<Configure>", lambda _event: self.redraw())
        self.bind("<Button-1>", self._set)
        self.bind("<B1-Motion>", self._set)
        self.variable.trace_add("write", lambda *_args: self.redraw())

    def _x(self, value: float) -> float:
        ratio = (value - self.minimum) / (self.maximum - self.minimum)
        return self.margin + clamp(ratio, 0.0, 1.0) * max(1, self.winfo_width() - self.margin * 2)

    def _set(self, event) -> None:
        ratio = clamp((event.x - self.margin) / max(1, self.winfo_width() - self.margin * 2), 0.0, 1.0)
        value = int(round(self.minimum + ratio * (self.maximum - self.minimum)))
        self.variable.set(value)
        if self.command:
            self.command(value)

    def redraw(self) -> None:
        width = self.winfo_width()
        if width <= 2:
            return
        self.delete("all")
        value = float(self.variable.get())
        x = self._x(value)
        y = 24
        active = self.color or (GREEN if value <= 30 else AMBER if value <= 60 else RED)
        self.create_line(self.margin, y, width - self.margin, y, fill=TRACK, width=8, capstyle="round")
        self.create_line(self.margin, y, x, y, fill=blend(active, BG, 0.70), width=15, capstyle="round")
        self.create_line(self.margin, y, x, y, fill=active, width=8, capstyle="round")
        self.create_oval(x - 14, y - 14, x + 14, y + 14, fill=blend(active, BG, 0.72), outline="")
        self.create_oval(x - 10, y - 10, x + 10, y + 10, fill=TEXT, outline=active, width=3)


class RangeSlider(tk.Canvas):
    """Simple two-thumb slider built only with Tkinter Canvas."""

    def __init__(
        self,
        parent,
        low_variable,
        high_variable,
        minimum,
        maximum,
        step=1,
        min_gap=0,
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            height=48,
            bg=kwargs.pop("bg", PANEL_2),
            highlightthickness=0,
            cursor="hand2",
            **kwargs,
        )
        self.low_variable = low_variable
        self.high_variable = high_variable
        self.minimum = float(minimum)
        self.maximum = float(maximum)
        self.step = float(step)
        self.min_gap = float(min_gap)
        self.active_thumb = None
        self.margin = 17
        self.bind("<Configure>", lambda _event: self.redraw())
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self.low_variable.trace_add("write", lambda *_args: self.redraw())
        self.high_variable.trace_add("write", lambda *_args: self.redraw())

    def _track_width(self) -> float:
        return max(1.0, self.winfo_width() - self.margin * 2)

    def _value_to_x(self, value: float) -> float:
        ratio = (value - self.minimum) / (self.maximum - self.minimum)
        return self.margin + clamp(ratio, 0.0, 1.0) * self._track_width()

    def _x_to_value(self, x: float) -> float:
        ratio = clamp((x - self.margin) / self._track_width(), 0.0, 1.0)
        raw = self.minimum + ratio * (self.maximum - self.minimum)
        return round(raw / self.step) * self.step

    def redraw(self) -> None:
        if self.winfo_width() <= 1:
            return
        self.delete("all")
        low = float(self.low_variable.get())
        high = float(self.high_variable.get())
        low_x = self._value_to_x(low)
        high_x = self._value_to_x(high)
        y = 24
        self.create_line(self.margin, y, self.winfo_width() - self.margin, y, fill=TRACK, width=8, capstyle="round")
        self.create_line(low_x, y, high_x, y, fill=blend(ACCENT, BG, 0.72), width=15, capstyle="round")
        self.create_line(low_x, y, high_x, y, fill=ACCENT, width=8, capstyle="round")
        for x, selected in ((low_x, self.active_thumb == "low"), (high_x, self.active_thumb == "high")):
            radius = 10 if selected else 9
            self.create_oval(x - radius - 4, y - radius - 4, x + radius + 4, y + radius + 4, fill=blend(ACCENT, BG, 0.72), outline="")
            self.create_oval(x - radius, y - radius, x + radius, y + radius, fill=TEXT, outline=ACCENT, width=3)

    def _press(self, event) -> None:
        low_x = self._value_to_x(float(self.low_variable.get()))
        high_x = self._value_to_x(float(self.high_variable.get()))
        self.active_thumb = "low" if abs(event.x - low_x) <= abs(event.x - high_x) else "high"
        self._set_from_x(event.x)

    def _drag(self, event) -> None:
        self._set_from_x(event.x)

    def _release(self, _event) -> None:
        self.active_thumb = None
        self.redraw()

    def _set_from_x(self, x: float) -> None:
        value = self._x_to_value(x)
        low = float(self.low_variable.get())
        high = float(self.high_variable.get())
        if self.active_thumb == "low":
            value = clamp(value, self.minimum, high - self.min_gap)
            self.low_variable.set(int(value) if self.step >= 1 else value)
        elif self.active_thumb == "high":
            value = clamp(value, low + self.min_gap, self.maximum)
            self.high_variable.set(int(value) if self.step >= 1 else value)


class PersonalizationDialog(tk.Toplevel):
    def __init__(self, owner) -> None:
        super().__init__(owner)
        self.owner = owner
        self.title("个性化 Pulse 设置")
        self.geometry("720x670")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.transient(owner)
        self.grab_set()

        self.trigger_bpm = tk.IntVar(value=owner.trigger_bpm.get())
        self.full_bpm = tk.IntVar(value=owner.full_bpm.get())
        self.min_strength = tk.IntVar(value=owner.min_strength.get())
        self.output_max = tk.IntVar(value=owner.output_max.get())
        self.hard_cap = tk.IntVar(value=owner.hard_cap.get())
        self.heart_summary = tk.StringVar()
        self.strength_summary = tk.StringVar()
        self.cap_summary = tk.StringVar()

        for variable in (
            self.trigger_bpm,
            self.full_bpm,
            self.min_strength,
            self.output_max,
            self.hard_cap,
        ):
            variable.trace_add("write", lambda *_args: self._refresh())

        self._build()
        self._refresh()
        self.after(50, self._redraw_sliders)

    def _label(self, parent, text=None, variable=None, size=10, color=None, bold=False, **kwargs):
        color = TEXT if color is None else color
        return tk.Label(
            parent,
            text=text,
            textvariable=variable,
            bg=parent.cget("bg"),
            fg=color,
            font=("Microsoft YaHei UI", size, "bold" if bold else "normal"),
            **kwargs,
        )

    def _section(self, parent, title, description, summary_variable):
        glass = GlassSurface(parent, padding=15, fill=PANEL_2, radius=18, height=150)
        glass.pack(fill="x", pady=7)
        frame = glass.content
        top = tk.Frame(frame, bg=PANEL_2)
        top.pack(fill="x")
        self._label(top, title, size=11, bold=True).pack(side="left")
        self._label(top, variable=summary_variable, size=12, color=ACCENT, bold=True).pack(side="right")
        self._label(frame, description, size=9, color=MUTED, justify="left").pack(anchor="w", pady=(3, 2))
        return frame

    def _build(self) -> None:
        header = tk.Frame(self, bg=BG, padx=24, pady=18)
        header.pack(fill="x")
        self._label(header, "个性化 Pulse 设置", size=17, bold=True).pack(anchor="w")
        self._label(header, "拖动左右把手选择范围，不需要逐个输入数字。", color=MUTED).pack(anchor="w", pady=(3, 0))

        content = tk.Frame(self, bg=BG, padx=24)
        content.pack(fill="both", expand=True)
        heart = self._section(
            content,
            "① 心率触发范围",
            "左端：开始输出 Pulse　　右端：达到目标最高强度",
            self.heart_summary,
        )
        self.heart_slider = RangeSlider(
            heart,
            self.trigger_bpm,
            self.full_bpm,
            minimum=60,
            maximum=220,
            min_gap=5,
        )
        self.heart_slider.pack(fill="x")
        ends = tk.Frame(heart, bg=PANEL_2)
        ends.pack(fill="x")
        self._label(ends, "60 BPM", size=8, color=MUTED).pack(side="left")
        self._label(ends, "220 BPM", size=8, color=MUTED).pack(side="right")

        strength = self._section(
            content,
            "② 输出强度范围",
            "心率从左端升到右端时，输出在此范围内平滑变化",
            self.strength_summary,
        )
        self.strength_slider = RangeSlider(
            strength,
            self.min_strength,
            self.output_max,
            minimum=0,
            maximum=100,
            min_gap=0,
        )
        self.strength_slider.pack(fill="x")
        ends = tk.Frame(strength, bg=PANEL_2)
        ends.pack(fill="x")
        self._label(ends, "0", size=8, color=MUTED).pack(side="left")
        self._label(ends, "100", size=8, color=MUTED).pack(side="right")

        cap = self._section(
            content,
            "③ 安全硬上限",
            "任何规则和设备命令都不能超过此值；设备协议上限为 100",
            self.cap_summary,
        )
        self.cap_slider = ValueSlider(
            cap,
            self.hard_cap,
            minimum=1,
            maximum=100,
            command=self._cap_changed,
        )
        self.cap_slider.pack(fill="x", pady=(5, 0))

        buttons = tk.Frame(content, bg=BG)
        buttons.pack(fill="x", pady=(12, 0))
        GlassButton(buttons, "取消", self.destroy, color=PANEL_2, fg=TEXT, padx=24).pack(side="right")
        GlassButton(buttons, "应用并保存", self._apply, color=GREEN, padx=24).pack(side="right", padx=(0, 10))

    def _cap_changed(self, value) -> None:
        cap = int(float(value))
        if self.output_max.get() > cap:
            self.output_max.set(cap)
        if self.min_strength.get() > self.output_max.get():
            self.min_strength.set(self.output_max.get())

    def _refresh(self) -> None:
        self.heart_summary.set(f"{self.trigger_bpm.get()} – {self.full_bpm.get()} BPM")
        self.strength_summary.set(f"{self.min_strength.get()} – {self.output_max.get()}")
        self.cap_summary.set(f"{self.hard_cap.get()} / 100")

    def _redraw_sliders(self) -> None:
        self.heart_slider.redraw()
        self.strength_slider.redraw()
        self.cap_slider.redraw()

    def _apply(self) -> None:
        if self.owner.apply_personal_settings(
            trigger_bpm=self.trigger_bpm.get(),
            full_bpm=self.full_bpm.get(),
            min_strength=self.min_strength.get(),
            output_max=self.output_max.get(),
            hard_cap=self.hard_cap.get(),
        ):
            self.destroy()


class ConnectionGuideDialog(tk.Toplevel):
    """Four-step visual walkthrough for the DG-LAB 3.0 mobile app."""

    STEPS = (
        (
            "step1_socket.png",
            "先连接 3.0 主机，再进入 SOCKET 控制",
            "打开 DG-LAB App 后，先点“开始使用”完成蓝牙连接。主机连接成功后返回首页，再点右下角“SOCKET 控制”。",
        ),
        (
            "step2_initialize.png",
            "等待设备数据初始化",
            "进入时会短暂显示“正在初始化数据中”。如果长时间没有完成，请返回首页，先通过“开始使用”连接 DG-LAB 3.0 主机。",
        ),
        (
            "step3_connect_server.png",
            "点击“连接服务器”",
            "进入 SOCKET 控制页并看到 A/B 通道后，点击页面中间的“连接服务器”。此时插件里的二维码窗口应保持打开。",
        ),
        (
            "step4_camera_scan.png",
            "选择摄像头扫描插件二维码",
            "弹窗里选择右侧的摄像头图标，把手机摄像头对准本插件显示的二维码。不要选左侧相册，除非你已经保存了二维码图片。",
        ),
    )

    def __init__(self, owner) -> None:
        super().__init__(owner)
        self.owner = owner
        self.title("DG-LAB 3.0 连接图解")
        self.geometry("900x760")
        self.minsize(820, 700)
        self.configure(bg=BG)
        self.transient(owner)
        self.index = 0
        self.photo = None
        self.step_counter = tk.StringVar()
        self.step_title = tk.StringVar()
        self.step_detail = tk.StringVar()
        self._build()
        self._show_step()

    def _label(self, parent, text=None, variable=None, size=10, color=None, bold=False, **kwargs):
        color = TEXT if color is None else color
        return tk.Label(
            parent,
            text=text,
            textvariable=variable,
            bg=parent.cget("bg"),
            fg=color,
            font=("Microsoft YaHei UI", size, "bold" if bold else "normal"),
            **kwargs,
        )

    def _build(self) -> None:
        header = tk.Frame(self, bg=BG, padx=26, pady=18)
        header.pack(fill="x")
        self._label(header, "DG-LAB 3.0 手机 App 操作指引", size=17, bold=True).pack(side="left")
        self._label(header, variable=self.step_counter, color=ACCENT, size=11, bold=True).pack(side="right", pady=(5, 0))

        body = tk.Frame(self, bg=BG, padx=26)
        body.pack(fill="both", expand=True)
        image_glass = GlassSurface(body, padding=12, fill=PANEL, radius=22)
        image_glass.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=(0, 22))
        self.image_label = tk.Label(image_glass.content, bg=PREVIEW_BG)
        self.image_label.pack(fill="both", expand=True)

        info_glass = GlassSurface(body, padding=22, fill=PANEL_2, radius=22, width=410)
        info_glass.pack(side="right", fill="y", padx=(10, 0), pady=(0, 22))
        info = info_glass.content
        self._label(info, "连接步骤", color=MUTED, size=9, bold=True).pack(anchor="w")
        self._label(info, variable=self.step_title, size=15, bold=True, wraplength=340, justify="left").pack(
            anchor="w", pady=(10, 12)
        )
        self._label(info, variable=self.step_detail, size=10, color=MUTED, wraplength=340, justify="left").pack(
            anchor="w"
        )

        notice = tk.Frame(info, bg=ALERT_PANEL, padx=14, pady=12)
        notice.pack(fill="x", pady=(28, 0))
        self._label(notice, "安全提醒", color=AMBER, size=10, bold=True).pack(anchor="w")
        self._label(
            notice,
            "扫码即表示启用本次游戏连接。连接成功后会自动回到主界面，输出仍受个性化范围和安全硬上限保护。",
            color=TEXT,
            size=9,
            wraplength=310,
            justify="left",
        ).pack(anchor="w", pady=(5, 0))

        nav = tk.Frame(info, bg=PANEL_2)
        nav.pack(side="bottom", fill="x")
        self.prev_button = GlassButton(nav, "上一步", self._previous, color=PANEL, fg=TEXT, padx=16)
        self.prev_button.pack(side="left")
        self.next_button = GlassButton(nav, "下一步", self._next, color=GREEN, padx=20)
        self.next_button.pack(side="right")

    def _show_step(self) -> None:
        filename, title, detail = self.STEPS[self.index]
        path = bundled_guide_dir() / filename
        try:
            image = Image.open(path).convert("RGB")
            image.thumbnail((330, 640), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(image)
            self.image_label.configure(image=self.photo, text="")
        except OSError:
            self.image_label.configure(image="", text=f"缺少指引图片\n{path}", fg=RED, font=("Microsoft YaHei UI", 10))
        self.step_counter.set(f"{self.index + 1} / {len(self.STEPS)}")
        self.step_title.set(title)
        self.step_detail.set(detail)
        self.prev_button.set_text("关闭" if self.index == 0 else "上一步")
        self.next_button.set_text("返回扫码" if self.index == len(self.STEPS) - 1 else "下一步")

    def _previous(self) -> None:
        if self.index == 0:
            self.destroy()
            return
        self.index -= 1
        self._show_step()

    def _next(self) -> None:
        if self.index == len(self.STEPS) - 1:
            self.destroy()
            return
        self.index += 1
        self._show_step()


class DeviceConnectionDialog(tk.Toplevel):
    """One-step QR binding that returns to the main screen when connected."""

    def __init__(self, owner) -> None:
        super().__init__(owner)
        self.owner = owner
        self.title("连接 DG-LAB 设备")
        self.geometry("700x650")
        self.minsize(620, 540)
        self.resizable(True, True)
        self.configure(bg=BG)
        self.transient(owner)
        self.qr_photo = None
        self.last_qr_url = ""
        self.status = tk.StringVar(value="正在启动本机 Socket 服务…")
        self.detail = tk.StringVar(value="手机和电脑需要连接同一个局域网。")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._build()
        self.after(100, self._refresh)

    def _label(self, parent, text=None, variable=None, size=10, color=None, bold=False, **kwargs):
        color = TEXT if color is None else color
        return tk.Label(
            parent,
            text=text,
            textvariable=variable,
            bg=parent.cget("bg"),
            fg=color,
            font=("Microsoft YaHei UI", size, "bold" if bold else "normal"),
            **kwargs,
        )

    def _build(self) -> None:
        header = tk.Frame(self, bg=BG, padx=26, pady=12)
        header.pack(fill="x")
        title = tk.Frame(header, bg=BG)
        title.pack(fill="x")
        self._label(title, "连接 DG-LAB", size=18, bold=True).pack(side="left")
        GlassButton(title, "查看 DG-LAB 3.0 图解", self._open_guide, color=PANEL_2, fg=TEXT, padx=15, pady=6).pack(
            side="right"
        )
        self._label(
            header,
            "用 DG-LAB App 扫码；连接成功后会自动启用 A 通道并返回主界面。",
            color=MUTED,
        ).pack(anchor="w", pady=(4, 0))

        # Keep emergency/close actions outside the scrolling area so they are
        # always reachable on high-DPI and smaller displays.
        footer = tk.Frame(self, bg=BG)
        footer.pack(side="bottom", fill="x", padx=26, pady=(8, 14))
        GlassButton(footer, "暂停 / 继续输出", self.owner.toggle_output_pause, color=AMBER, padx=22).pack(
            side="left", fill="x", expand=True
        )
        GlassButton(footer, "关闭", self._close, color=PANEL_2, fg=TEXT, padx=22).pack(side="right", padx=(10, 0))

        viewport = tk.Frame(self, bg=BG)
        viewport.pack(fill="both", expand=True)
        self.scroll_canvas = tk.Canvas(viewport, bg=BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=self.scroll_canvas.yview)
        scrollbar.pack(side="right", fill="y", padx=(0, 8))
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)
        body = tk.Frame(self.scroll_canvas, bg=BG, padx=26, pady=8)
        self.scroll_window = self.scroll_canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", self._update_scroll_region)
        self.scroll_canvas.bind("<Configure>", self._resize_scroll_body)
        self.bind("<MouseWheel>", self._on_mousewheel)

        connect_glass = GlassSurface(body, padding=16, fill=PANEL, radius=22, height=340)
        connect_glass.pack(fill="x")
        connect = connect_glass.content
        top = tk.Frame(connect, bg=PANEL)
        top.pack(fill="x")
        self._label(top, "① 用 DG-LAB App 扫码", size=12, bold=True).pack(side="left")
        self._label(top, variable=self.status, color=GREEN, size=9, bold=True).pack(side="right")
        self.qr_label = tk.Label(connect, bg="#FFFFFF", width=260, height=260)
        self.qr_label.pack(pady=(12, 8))
        self._label(connect, variable=self.detail, color=MUTED, size=9, wraplength=620, justify="center").pack()

    def _update_scroll_region(self, _event=None) -> None:
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def _resize_scroll_body(self, event) -> None:
        self.scroll_canvas.itemconfigure(self.scroll_window, width=max(1, event.width))

    def _on_mousewheel(self, event) -> None:
        if event.delta:
            self.scroll_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _refresh(self) -> None:
        if not self.winfo_exists():
            return
        snapshot = self.owner.bridge.snapshot()
        if snapshot.qr_url and snapshot.qr_url != self.last_qr_url:
            qr = qrcode.QRCode(version=None, box_size=4, border=2)
            qr.add_data(snapshot.qr_url)
            qr.make(fit=True)
            image = qr.make_image(fill_color="#111522", back_color="#FFFFFF").convert("RGB")
            self.qr_photo = ImageTk.PhotoImage(image)
            self.qr_label.configure(image=self.qr_photo, width=image.width, height=image.height)
            self.last_qr_url = snapshot.qr_url
        if self.owner.device_connected:
            self.status.set("● 已连接")
            self.detail.set(f"设备绑定成功 · {snapshot.lan_ip}:{snapshot.port}")
        elif snapshot.server_ready and snapshot.qr_url:
            self.status.set("等待扫码")
            self.detail.set(f"同一局域网内，用 DG-LAB App 扫描二维码 · {snapshot.lan_ip}:{snapshot.port}")
        else:
            self.status.set("正在准备…")
        self.after(300, self._refresh)

    def _open_guide(self) -> None:
        ConnectionGuideDialog(self)

    def _close(self) -> None:
        self.owner.connection_dialog = None
        self.destroy()


class WaveformPreview(tk.Canvas):
    """Animated waveform preview; custom mode also supports click-and-drag drawing."""

    def __init__(self, parent, points, color=None, editable=False, command=None, **kwargs) -> None:
        super().__init__(parent, bg=PREVIEW_BG, highlightthickness=0, bd=0, cursor="crosshair" if editable else "arrow", **kwargs)
        self.points = list(points)
        self.color = ACCENT if color is None else color
        self.editable = editable
        self.command = command
        self.phase = 0.0
        self._last_animation = time.perf_counter()
        self.bind("<Configure>", lambda _event: self.redraw())
        self.bind("<Button-1>", self._paint)
        self.bind("<B1-Motion>", self._paint)
        self._animation_job = self.after(33, self._animate)

    def set_wave(self, points, color, editable=False) -> None:
        self.points = list(points)
        self.color = color
        self.editable = editable
        self.configure(cursor="crosshair" if editable else "arrow")
        self.phase = 0.0
        self._last_animation = time.perf_counter()
        self.redraw()

    def _animate(self) -> None:
        if not self.winfo_exists():
            return
        if not self.editable and self.points:
            now = time.perf_counter()
            elapsed = min(0.1, max(0.0, now - self._last_animation))
            self._last_animation = now
            self.phase = (self.phase + elapsed * 12.5) % max(1, len(self.points) * 4)
            self.redraw()
        self._animation_job = self.after(33, self._animate)

    def destroy(self) -> None:
        if getattr(self, "_animation_job", None) is not None:
            try:
                self.after_cancel(self._animation_job)
            except tk.TclError:
                pass
            self._animation_job = None
        super().destroy()

    def _coords(self):
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        left, right, top, bottom = 20, width - 20, 18, height - 22
        count = max(2, len(self.points))
        coords = []
        for index, value in enumerate(self.points):
            x = left + (right - left) * index / (count - 1)
            y = bottom - (bottom - top) * clamp(float(value) / 100.0, 0.0, 1.0)
            coords.extend((x, y))
        return coords, (left, right, top, bottom)

    def redraw(self) -> None:
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 10 or height <= 10 or len(self.points) < 2:
            return
        for fraction in (0.25, 0.5, 0.75):
            y = 18 + (height - 40) * fraction
            self.create_line(18, y, width - 18, y, fill=GRID, dash=(3, 6))
        coords, (left, right, _top, bottom) = self._coords()
        polygon = [left, bottom, *coords, right, bottom]
        self.create_polygon(polygon, fill=blend(self.color, BG, 0.78), outline="")
        self.create_line(*coords, fill=blend(self.color, BG, 0.58), width=11, smooth=True, splinesteps=20)
        self.create_line(*coords, fill=self.color, width=3, smooth=True, splinesteps=20)
        if self.editable:
            for index in range(0, len(coords), 2):
                x, y = coords[index], coords[index + 1]
                self.create_oval(x - 4, y - 4, x + 4, y + 4, fill=TEXT, outline=self.color, width=2)
        else:
            play_x = left + (right - left) * self.phase / max(1, len(self.points) * 4 - 1)
            self.create_line(play_x, 13, play_x, bottom + 5, fill=blend(self.color, TEXT, 0.25), width=2)
            self.create_oval(play_x - 4, 10, play_x + 4, 18, fill=TEXT, outline=self.color, width=2)

    def _paint(self, event) -> None:
        if not self.editable or not self.points:
            return
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        left, right, top, bottom = 20, width - 20, 18, height - 22
        ratio_x = clamp((event.x - left) / max(1, right - left), 0.0, 1.0)
        index = int(round(ratio_x * (len(self.points) - 1)))
        value = int(round(clamp((bottom - event.y) / max(1, bottom - top), 0.0, 1.0) * 100))
        self.points[index] = value
        if self.command:
            self.command(list(self.points))
        self.redraw()


class WaveformStudio(tk.Toplevel):
    def __init__(self, owner) -> None:
        super().__init__(owner)
        self.owner = owner
        self.title("Manaka 波形工作台")
        self.geometry("1060x840")
        self.minsize(980, 760)
        self.configure(bg=BG)
        self.transient(owner)
        self.grab_set()

        self.mode = tk.StringVar(value=owner.wave_mode.get())
        self.fixed_preset = owner.fixed_wave.get()
        self.wave_map = dict(owner.wave_map)
        self.custom_points = list(owner.custom_wave_points)
        self.custom_frequency = tk.IntVar(value=owner.custom_wave_frequency.get())
        self.selected_key = (
            self.fixed_preset
            if self.fixed_preset in PRESETS or self.fixed_preset == "custom"
            else "official_heartbeat"
        )
        self.preset_buttons = []
        self.mapping_buttons = {}
        self._build()
        self._select_preset(self.selected_key)

    def _label(self, parent, text=None, variable=None, size=10, color=None, bold=False, **kwargs):
        color = TEXT if color is None else color
        return tk.Label(
            parent,
            text=text,
            textvariable=variable,
            bg=parent.cget("bg"),
            fg=color,
            font=("Microsoft YaHei UI", size, "bold" if bold else "normal"),
            **kwargs,
        )

    def _button(self, parent, text, command, color=None, fg=None, **kwargs):
        color = PANEL_2 if color is None else color
        fg = TEXT if fg is None else fg
        return GlassButton(parent, text, command, color=color, fg=fg, **kwargs)

    def _custom_preset(self) -> WaveformPreset:
        return WaveformPreset(
            "custom",
            "我的波形",
            "在预览图上拖动绘制 16 个波形节点",
            "保存后可分配给任意心率区间或固定模式",
            CYAN,
            tuple(int(clamp(value, 0, 100)) for value in self.custom_points),
            (int(clamp(self.custom_frequency.get(), 10, 240)),),
            source="我的波形",
        )

    def _preset(self, key: str) -> WaveformPreset:
        return self._custom_preset() if key == "custom" else PRESETS[key]

    def _build(self) -> None:
        header = tk.Frame(self, bg=BG, padx=28, pady=20)
        header.pack(fill="x")
        title = tk.Frame(header, bg=BG)
        title.pack(side="left")
        self._label(title, "波形工作台", size=19, bold=True).pack(anchor="w")
        self._label(title, "官方波形会做保守体感归一，且始终受强度范围与安全硬上限约束。", color=MUTED, size=9).pack(anchor="w", pady=(3, 0))
        self._button(header, "保存配置", self._apply, color=GREEN, fg=BUTTON_TEXT, padx=22).pack(side="right")
        self._button(header, "取消", self.destroy, padx=18).pack(side="right", padx=(0, 10))

        body = tk.Frame(self, bg=BG, padx=28, pady=0)
        body.pack(fill="both", expand=True, pady=(0, 24))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=7)
        body.grid_rowconfigure(0, weight=1)

        left_glass = GlassSurface(body, padding=18, fill=PANEL, radius=22)
        left_glass.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_glass = GlassSurface(body, padding=18, fill=PANEL, radius=22)
        right_glass.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        left = left_glass.content
        right = right_glass.content

        self._label(left, "切换方式", size=12, bold=True).pack(anchor="w")
        mode_row = tk.Frame(left, bg=PANEL)
        mode_row.pack(fill="x", pady=(10, 18))
        self.smart_button = self._button(mode_row, "智能切换", lambda: self._set_mode("smart"), padx=12)
        self.smart_button.pack(side="left", fill="x", expand=True)
        self.fixed_button = self._button(mode_row, "固定预设", lambda: self._set_mode("fixed"), padx=12)
        self.fixed_button.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self._label(left, "预设波形", size=12, bold=True).pack(anchor="w", pady=(0, 6))
        preset_view = tk.Frame(left, bg=PANEL)
        preset_view.pack(fill="both", expand=True)
        self.preset_canvas = tk.Canvas(preset_view, bg=PANEL, highlightthickness=0, bd=0)
        preset_scrollbar = ttk.Scrollbar(preset_view, orient="vertical", command=self.preset_canvas.yview)
        preset_scrollbar.pack(side="right", fill="y")
        self.preset_canvas.pack(side="left", fill="both", expand=True)
        self.preset_canvas.configure(yscrollcommand=preset_scrollbar.set)
        self.preset_list = tk.Frame(self.preset_canvas, bg=PANEL)
        self.preset_window = self.preset_canvas.create_window((0, 0), window=self.preset_list, anchor="nw")
        self.preset_list.bind(
            "<Configure>", lambda _event: self.preset_canvas.configure(scrollregion=self.preset_canvas.bbox("all"))
        )
        self.preset_canvas.bind(
            "<Configure>", lambda event: self.preset_canvas.itemconfigure(self.preset_window, width=max(1, event.width))
        )
        self.bind("<MouseWheel>", self._scroll_presets)
        self._rebuild_preset_buttons()

        preview_top = tk.Frame(right, bg=PANEL)
        preview_top.pack(fill="x")
        self.preview_name = tk.StringVar()
        self.preview_tag = tk.StringVar()
        self._label(preview_top, variable=self.preview_name, size=15, bold=True).pack(side="left")
        self._label(preview_top, variable=self.preview_tag, size=9, color=CYAN, bold=True).pack(side="right", pady=(5, 0))
        self.preview = WaveformPreview(right, PRESETS["official_heartbeat"].amplitudes, height=170)
        self.preview.pack(fill="x", pady=(12, 10))
        self.preview_description = tk.StringVar()
        self.preview_best_for = tk.StringVar()
        self._label(right, variable=self.preview_description, color=TEXT, size=10).pack(anchor="w")
        self._label(right, variable=self.preview_best_for, color=MUTED, size=9, wraplength=620, justify="left").pack(anchor="w", pady=(3, 12))

        self.custom_controls = tk.Frame(right, bg=PANEL)
        self._label(self.custom_controls, "频率代码（10–240）", color=MUTED, size=9).pack(anchor="w")
        self.frequency_value = tk.StringVar()
        frequency_header = tk.Frame(self.custom_controls, bg=PANEL)
        frequency_header.pack(fill="x")
        self._label(frequency_header, "拖动画布节点改变包络；频率先保持保守范围，实际联机时再标定。", color=MUTED, size=8).pack(side="left")
        self._label(frequency_header, variable=self.frequency_value, color=CYAN, bold=True).pack(side="right")
        self.frequency_slider = ValueSlider(
            self.custom_controls,
            self.custom_frequency,
            minimum=10,
            maximum=240,
            command=lambda _value: self._refresh_custom(),
            color=CYAN,
            bg=PANEL,
        )
        self.frequency_slider.pack(fill="x")

        rule_header = tk.Frame(right, bg=PANEL)
        rule_header.pack(fill="x", pady=(6, 3))
        self._label(rule_header, "智能切换规则", size=12, bold=True).pack(side="left")
        self._label(rule_header, "点击右侧预设名即可轮换", size=8, color=MUTED).pack(side="right", pady=(4, 0))
        self.rules_frame = tk.Frame(right, bg=PANEL)
        self.rules_frame.pack(fill="both", expand=True)
        self._build_rule_rows()
        self._refresh_mode_buttons()

    def _rebuild_preset_buttons(self) -> None:
        for child in self.preset_list.winfo_children():
            child.destroy()
        keys = list(PRESETS) + ["custom"]
        for key in keys:
            preset = self._preset(key)
            selected = key == self.selected_key
            button = self._button(
                self.preset_list,
                f"{preset.name}   ·   {preset.description}",
                lambda selected_key=key: self._select_preset(selected_key),
                color=blend(preset.color, BG, 0.55) if selected else PANEL_2,
                fg=TEXT,
                padx=12,
                pady=6,
                font_size=9,
            )
            button.pack(fill="x", pady=3)

    def _scroll_presets(self, event) -> None:
        if event.delta:
            self.preset_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _build_rule_rows(self) -> None:
        for child in self.rules_frame.winfo_children():
            child.destroy()
        self.mapping_buttons.clear()
        for zone in WAVE_ZONES:
            row = tk.Frame(self.rules_frame, bg=PANEL)
            row.pack(fill="x", pady=3)
            labels = tk.Frame(row, bg=PANEL)
            labels.pack(side="left", fill="x", expand=True)
            self._label(labels, ZONE_LABELS[zone], size=9, bold=True).pack(anchor="w")
            self._label(labels, ZONE_REASONS[zone], size=8, color=MUTED).pack(anchor="w")
            preset = self._preset(self.wave_map[zone])
            button = self._button(
                row,
                preset.name,
                lambda selected_zone=zone: self._cycle_mapping(selected_zone),
                color=blend(preset.color, BG, 0.58),
                fg=TEXT,
                padx=12,
                pady=4,
                width=116,
                font_size=9,
            )
            button.pack(side="right", padx=(10, 0))
            self.mapping_buttons[zone] = button

    def _set_mode(self, mode: str) -> None:
        self.mode.set(mode)
        self._refresh_mode_buttons()

    def _refresh_mode_buttons(self) -> None:
        for button, active in (
            (self.smart_button, self.mode.get() == "smart"),
            (self.fixed_button, self.mode.get() == "fixed"),
        ):
            button.color = blend(ACCENT, BG, 0.35) if active else PANEL_2
            button._draw()

    def _select_preset(self, key: str) -> None:
        self.selected_key = key
        self.fixed_preset = key
        preset = self._preset(key)
        self.preview_name.set(preset.name)
        self.preview_tag.set(
            "可编辑" if key == "custom" else f"{preset.source} · 体感 {round(preset.feel_scale * 100)}%"
        )
        self.preview_description.set(preset.description)
        self.preview_best_for.set(f"适合：{preset.best_for}　·　{preset.caution}")
        self.preview.set_wave(preset.amplitudes, preset.color, editable=key == "custom")
        self.preview.command = self._custom_changed if key == "custom" else None
        if key == "custom":
            self.custom_controls.pack(fill="x", before=self.rules_frame, pady=(0, 8))
            self._refresh_custom()
        else:
            self.custom_controls.pack_forget()
        self._rebuild_preset_buttons()

    def _custom_changed(self, points) -> None:
        self.custom_points = [int(value) for value in points]

    def _refresh_custom(self) -> None:
        self.frequency_value.set(str(self.custom_frequency.get()))
        if self.selected_key == "custom":
            self.preview.color = CYAN
            self.preview.redraw()

    def _cycle_mapping(self, zone: str) -> None:
        keys = list(PRESETS) + ["custom"]
        current = self.wave_map.get(zone, DEFAULT_WAVE_MAP[zone])
        self.wave_map[zone] = keys[(keys.index(current) + 1) % len(keys)] if current in keys else keys[0]
        self._build_rule_rows()

    def _apply(self) -> None:
        self.owner.apply_wave_settings(
            mode=self.mode.get(),
            fixed_preset=self.fixed_preset,
            wave_map=self.wave_map,
            custom_points=self.custom_points,
            custom_frequency=self.custom_frequency.get(),
        )
        self.destroy()


class WaveformMonitor(tk.Toplevel):
    """Live, read-only view of the currently selected A/B waveforms."""

    def __init__(self, owner) -> None:
        super().__init__(owner)
        self.owner = owner
        self.title("A/B 实时波形")
        self.geometry("980x600")
        self.minsize(780, 500)
        self.configure(bg=BG)
        self.transient(owner)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.status_text = tk.StringVar(value="正在读取…")
        self.channel_name: dict[str, tk.StringVar] = {}
        self.channel_detail: dict[str, tk.StringVar] = {}
        self.channel_source: dict[str, tk.StringVar] = {}
        self.previews: dict[str, WaveformPreview] = {}
        self.last_signature: dict[str, tuple] = {"A": (), "B": ()}
        self._build()
        self.after(80, self._refresh)

    def _label(self, parent, text=None, variable=None, size=10, color=None, bold=False, **kwargs):
        color = TEXT if color is None else color
        return tk.Label(
            parent,
            text=text,
            textvariable=variable,
            bg=parent.cget("bg"),
            fg=color,
            font=("Microsoft YaHei UI", size, "bold" if bold else "normal"),
            **kwargs,
        )

    def _build(self) -> None:
        header = tk.Frame(self, bg=BG, padx=26, pady=20)
        header.pack(fill="x")
        title = tk.Frame(header, bg=BG)
        title.pack(side="left")
        self._label(title, "A/B 实时波形", size=19, bold=True).pack(anchor="w")
        self._label(title, variable=self.status_text, color=AMBER, size=9).pack(anchor="w", pady=(3, 0))
        GlassButton(header, "关闭", self._close, color=PANEL_2, fg=TEXT, padx=18, pady=7).pack(side="right")

        body = tk.Frame(self, bg=BG, padx=26, pady=0)
        body.pack(fill="both", expand=True, pady=(0, 18))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self._build_channel(body, "A", 0, AMBER, "实际下发 · 由游戏心率驱动")
        self._build_channel(body, "B", 1, VIOLET, "当前仅预览 · 尚未向设备下发")

        note = tk.Frame(self, bg=BG, padx=26, pady=0)
        note.pack(fill="x", pady=(0, 18))
        self._label(
            note,
            "波形图显示发送包络；强度数值已包含该预设的体感系数，并继续受安全硬上限约束。",
            color=MUTED,
            size=9,
        ).pack(anchor="w")

    def _build_channel(self, parent, channel: str, column: int, color: str, note: str) -> None:
        glass = GlassSurface(parent, padding=20, fill=PANEL, radius=24)
        glass.grid(row=0, column=column, sticky="nsew", padx=(0, 10) if column == 0 else (10, 0))
        panel = glass.content
        top = tk.Frame(panel, bg=PANEL)
        top.pack(fill="x")
        self._label(top, f"{channel} 通道", size=13, color=color, bold=True).pack(side="left")
        self.channel_source[channel] = tk.StringVar(value="待机")
        self._label(top, variable=self.channel_source[channel], size=8, color=MUTED).pack(side="right", pady=(4, 0))
        self.channel_name[channel] = tk.StringVar(value="待机")
        self._label(panel, variable=self.channel_name[channel], size=17, bold=True).pack(anchor="w", pady=(14, 0))
        self.channel_detail[channel] = tk.StringVar(value="强度 0.0")
        self._label(panel, variable=self.channel_detail[channel], color=MUTED, size=9).pack(anchor="w", pady=(3, 10))
        preview = WaveformPreview(panel, (0, 0, 0, 0), color=color, height=250)
        preview.pack(fill="both", expand=True, pady=(0, 12))
        self.previews[channel] = preview
        self._label(panel, note, color=MUTED, size=9).pack(anchor="w")

    def _refresh(self) -> None:
        if not self.winfo_exists():
            return
        if not self.owner.device_connected:
            self.status_text.set("设备未连接 · 当前显示游戏侧选择结果")
        elif not self.owner.auto_output_enabled:
            self.status_text.set("输出已暂停 · A/B 实际强度均为 0")
        elif self.owner.safety_wait_reason:
            self.status_text.set(f"安全待机 · {self.owner.safety_wait_reason} · 输出为 0")
        else:
            self.status_text.set("● 实时输出中")

        channels = (
            ("A", self.owner.current_wave_a, self.owner.current_output_a),
            ("B", self.owner.current_wave_b, self.owner.current_output_b),
        )
        for channel, wave, strength in channels:
            if wave is None:
                name = "待机 / 无波形"
                source = "队列已清空"
                points = (0, 0, 0, 0)
                color = AMBER if channel == "A" else VIOLET
                signature = ("idle",)
            else:
                name = wave.name
                source = f"{wave.source} · 体感 {round(wave.feel_scale * 100)}%"
                points = wave.amplitudes
                color = wave.color
                signature = (wave.key, points, color)
            actual_strength = strength if self.owner.auto_output_enabled and not self.owner.safety_wait_reason else 0.0
            self.channel_name[channel].set(name)
            self.channel_source[channel].set(source)
            self.channel_detail[channel].set(
                f"当前强度 {actual_strength:.1f} / 安全硬上限 {self.owner.hard_cap.get()}"
            )
            if signature != self.last_signature[channel]:
                self.previews[channel].set_wave(points, color)
                self.last_signature[channel] = signature
        self.after(100, self._refresh)

    def _close(self) -> None:
        self.owner.wave_monitor_window = None
        self.destroy()


def app_data_dir() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    return base / "ManakaDGLab"


def config_path() -> Path:
    return app_data_dir() / "config.json"


def bundled_plugin_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "assets" / "ManakaDGLabTelemetry.dll"
    return Path(__file__).resolve().parents[1] / "manaka_telemetry" / "bin" / "ManakaDGLabTelemetry.dll"


def bundled_guide_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "assets" / "dglab_guide"
    return Path(__file__).resolve().parent / "assets" / "dglab_guide"


def validate_game_folder(folder: Path) -> tuple[bool, str]:
    if not (folder / "SecretFlasherManaka.exe").is_file():
        return False, (
            "选错目录：这里没有 SecretFlasherManaka.exe。请选择能直接看到该 EXE 的文件夹，"
            "不要选择 BepInEx、plugins 或 SecretFlasherManaka_Data。"
        )
    if not (folder / "BepInEx" / "core" / "BepInEx.Core.dll").is_file():
        return False, "没有检测到 BepInEx 6"
    dependency = folder / "BepInEx" / "plugins" / "SFM_custom_mission_v2.dll"
    if not dependency.is_file():
        return False, "缺少 SFM_custom_mission_v2.dll"
    return True, "游戏与依赖检查通过"


def default_game_folder() -> str:
    saved = load_config().get("game_folder", "")
    if saved and Path(saved).is_dir():
        return saved
    return ""


def load_config() -> dict:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(values: dict) -> None:
    target = config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")


def update_config(values: dict) -> None:
    current = load_config()
    current.update(values)
    save_config(current)


class TelemetryWorker(threading.Thread):
    def __init__(self, messages: queue.Queue) -> None:
        super().__init__(name="manaka-telemetry", daemon=True)
        self.messages = messages
        self.stop_event = threading.Event()
        self.receiver: socket.socket | None = None

    def run(self) -> None:
        try:
            self.receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.receiver.bind((UDP_HOST, UDP_PORT))
            self.receiver.settimeout(0.2)
            self.messages.put(("listener", "ready"))
            while not self.stop_event.is_set():
                try:
                    payload, _ = self.receiver.recvfrom(65535)
                except socket.timeout:
                    continue
                packet = json.loads(payload.decode("utf-8"))
                self.messages.put(("telemetry", packet))
        except Exception as error:
            self.messages.put(("listener", f"error:{error}"))
        finally:
            if self.receiver is not None:
                self.receiver.close()

    def stop(self) -> None:
        self.stop_event.set()
        if self.receiver is not None:
            try:
                self.receiver.close()
            except OSError:
                pass


class ControlCenter(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        saved = load_config()
        self.theme_mode = apply_theme_palette(str(saved.get("theme", "dark")))
        self.title(f"{APP_NAME}  {APP_VERSION}")
        self.geometry("1080x820")
        self.minsize(980, 740)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.close_app)

        self.messages: queue.Queue = queue.Queue()
        self.worker: TelemetryWorker | None = None
        self.engine = ManakaTriggerEngine(
            max_strength=float(saved.get("hard_cap", 30)),
            min_strength=float(saved.get("min_strength", 3)),
            output_max=float(saved.get("output_max", 30)),
            trigger_bpm=float(saved.get("trigger_bpm", 100)),
            full_bpm=float(saved.get("full_bpm", 150)),
        )
        self.last_packet: dict = {}
        self.last_receive = 0.0
        self.last_game_ms: int | None = None
        self.stale_reported = False
        self.last_action = "None"
        self.log_lines: list[str] = []
        self.log_window = None
        self.log_text = None
        self.wave_monitor_window = None
        self.connection_dialog = None
        self.device_connected = False
        self.auto_output_enabled = False
        self.safety_wait_reason = ""
        self.current_frame = self.engine.force_safe_cut("startup")
        self.current_wave_a: WaveformPreset | None = None
        self.current_wave_b: WaveformPreset | None = None
        self.current_output_a = 0.0
        self.current_output_b = 0.0
        self.bridge = DGLabBridge(self.messages, port=int(saved.get("socket_port", DEFAULT_PORT)))

        self.game_folder = tk.StringVar(value=default_game_folder())
        self.telemetry_status = tk.StringVar(value="正在准备监听…")
        self.game_status = tk.StringVar(value="尚未检查")
        self.device_status = tk.StringVar(value="等待设备扫码 · 输出未启用")
        self.stage_text = tk.StringVar(value="—")
        self.action_text = tk.StringVar(value="None")
        self.bpm_text = tk.StringVar(value="— BPM")
        self.alert_text = tk.StringVar(value="0%")
        self.ecstasy_text = tk.StringVar(value="0%")
        self.channel_a_text = tk.StringVar(value="0.0 · idle")
        self.channel_b_text = tk.StringVar(value="0.0 · idle")
        self.trigger_bpm = tk.IntVar(value=int(self.engine.trigger_bpm))
        self.full_bpm = tk.IntVar(value=int(self.engine.full_bpm))
        self.min_strength = tk.IntVar(value=int(self.engine.min_strength))
        self.output_max = tk.IntVar(value=int(self.engine.output_max))
        self.hard_cap = tk.IntVar(value=int(self.engine.hard_cap))
        self.wave_mode = tk.StringVar(value="fixed" if saved.get("wave_mode") == "fixed" else "smart")
        fixed_wave = str(saved.get("fixed_wave", "official_heartbeat"))
        self.fixed_wave = tk.StringVar(
            value=fixed_wave if fixed_wave in PRESETS or fixed_wave == "custom" else "official_heartbeat"
        )
        saved_wave_map = saved.get("wave_map", DEFAULT_WAVE_MAP)
        if saved_wave_map == LEGACY_DEFAULT_WAVE_MAP:
            saved_wave_map = DEFAULT_WAVE_MAP
        self.wave_map = sanitize_wave_map(saved_wave_map)
        self.wave_selector = WaveformSelector(hold_seconds=0.8)
        saved_points = saved.get("custom_wave_points")
        if not isinstance(saved_points, list) or len(saved_points) != 16:
            saved_points = [0, 18, 48, 82, 100, 58, 20, 0, 0, 25, 68, 45, 15, 0, 0, 0]
        self.custom_wave_points = [int(clamp(float(value), 0, 100)) for value in saved_points]
        self.custom_wave_frequency = tk.IntVar(value=int(clamp(float(saved.get("custom_wave_frequency", 92)), 10, 240)))
        self.heart_range_summary = tk.StringVar()
        self.strength_range_summary = tk.StringVar()
        self.hard_cap_summary = tk.StringVar()
        self.wave_policy_summary = tk.StringVar()
        self._refresh_settings_summary()

        self._configure_style()
        self._build_ui()
        self.after(100, self._poll_messages)
        self.after(250, self._check_stale)
        self.after(200, self.start_listener)
        self.after(220, self.start_socket_bridge)
        self.after(350, self.check_installation)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor=TRACK, background=ACCENT, borderwidth=0)
        style.configure("A.Horizontal.TProgressbar", troughcolor=TRACK, background=AMBER)
        style.configure("B.Horizontal.TProgressbar", troughcolor=TRACK, background=ACCENT)

    def _label(self, parent, text=None, variable=None, size=10, color=None, bold=False, **kwargs):
        color = TEXT if color is None else color
        font = ("Microsoft YaHei UI", size, "bold" if bold else "normal")
        return tk.Label(parent, text=text, textvariable=variable, bg=parent.cget("bg"), fg=color, font=font, **kwargs)

    def _button(self, parent, text, command, color=None, fg=None, **kwargs):
        color = ACCENT if color is None else color
        fg = BUTTON_TEXT if fg is None else fg
        padx = kwargs.pop("padx", 16)
        pady = kwargs.pop("pady", 9)
        return GlassButton(parent, text, command, color=color, fg=fg, padx=padx, pady=pady, **kwargs)

    def _panel(self, parent, **kwargs):
        padding = kwargs.pop("padding", 20)
        return GlassSurface(parent, padding=padding, fill=PANEL, radius=24, **kwargs)

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=BG, padx=28, pady=18)
        header.pack(fill="x")
        self._label(header, "MANAKA / DG-LAB", size=20, bold=True).pack(side="left")
        theme_text = "☀  日间" if self.theme_mode == "dark" else "☾  夜间"
        self.theme_button = self._button(
            header,
            theme_text,
            self.toggle_theme,
            color=PANEL_2,
            fg=TEXT,
            width=98,
            padx=10,
            pady=6,
        )
        self.theme_button.pack(side="left", padx=(14, 0), pady=(1, 0))
        self.device_badge = PillBadge(header, "等待设备连接", AMBER, width=156)
        self.device_badge.pack(side="right")
        self._button(header, "事件日志", self.show_log_window, color=PANEL_2, fg=TEXT, padx=12, pady=6).pack(
            side="right", padx=(0, 10)
        )
        self._button(header, "A/B 波形", self.open_waveform_monitor, color=PANEL_2, fg=CYAN, padx=12, pady=6).pack(
            side="right", padx=(0, 10)
        )
        self._button(header, "波形工作台", self.open_waveform_studio, color=PANEL_2, fg=TEXT, padx=12, pady=6).pack(
            side="right", padx=(0, 10)
        )
        self._button(header, "连接设备", self.open_device_connection, color=GREEN, padx=12, pady=6).pack(
            side="right", padx=(0, 10)
        )

        body = tk.Frame(self, bg=BG, padx=28)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=6)
        body.grid_rowconfigure(0, weight=1)

        left_glass = self._panel(body, padding=22)
        left_glass.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right_glass = self._panel(body, padding=22)
        right_glass.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        left = left_glass.content
        right = right_glass.content

        self._build_setup_panel(left)
        self._build_live_panel(right)

    def toggle_theme(self) -> None:
        """Switch palette without restarting listeners, Socket state, or the game session."""
        self.theme_mode = apply_theme_palette("light" if self.theme_mode == "dark" else "dark")
        update_config({"theme": self.theme_mode})

        # Rebuilding only the visual tree avoids stale hard-coded Tk colors while all
        # controller state, workers, device connection and StringVars stay alive.
        for child in list(self.winfo_children()):
            child.destroy()
        self.log_window = None
        self.log_text = None
        self.wave_monitor_window = None
        self.connection_dialog = None
        self.configure(bg=BG)
        self._configure_style()
        self._build_ui()
        self._restore_live_visuals()
        self._log(f"界面已切换为{'日间' if self.theme_mode == 'light' else '夜间'}模式")

    def _restore_live_visuals(self) -> None:
        packet = self.last_packet
        bpm = float(packet.get("heartRate", 0) or 0)
        alert = max(0.0, min(1.0, float(packet.get("maxNpcAlert", 0) or 0)))
        ecstasy = max(0.0, min(1.0, float(packet.get("ecstasy", 0) or 0)))
        self.bpm_bar.set(min(180, bpm), immediate=True)
        self.alert_bar.set(alert * 100, immediate=True)
        self.ecstasy_bar.set(ecstasy * 100, immediate=True)
        self.a_bar.set(self.current_output_a, immediate=True)
        self.b_bar.set(self.current_output_b, immediate=True)
        if self.device_connected and not self.auto_output_enabled:
            self.device_badge.set("输出已暂停", AMBER)
        elif self.device_connected and self.current_frame.safe_cut:
            self.device_badge.set("安全待机", AMBER)
        elif self.device_connected:
            self.device_badge.set("A 通道输出中", RED)
        elif "断开" in self.device_status.get() or "异常" in self.device_status.get():
            self.device_badge.set("设备未连接", RED)
        else:
            self.device_badge.set("等待设备连接", AMBER)
        self._refresh_pause_button()

    def _build_setup_panel(self, parent) -> None:
        self._label(parent, "快速开始", size=15, bold=True).pack(anchor="w")
        self._label(parent, "首次使用只需选择游戏目录，然后点一个按钮。", color=MUTED, wraplength=350, justify="left").pack(anchor="w", pady=(4, 18))

        for number, title, detail in (
            ("1", "安装/检查插件", "自动复制遥测 DLL，不修改游戏资源。"),
            ("2", "启动游戏", "进入可操作场景后会自动出现数据。"),
            ("3", "连接设备", "扫码成功后自动启用 A 通道并返回主界面。"),
        ):
            row = tk.Frame(parent, bg=PANEL)
            row.pack(fill="x", pady=6)
            tk.Label(row, text=number, width=3, height=1, bg=PANEL_2, fg=ACCENT, font=("Microsoft YaHei UI", 11, "bold")).pack(side="left", padx=(0, 10))
            text = tk.Frame(row, bg=PANEL)
            text.pack(side="left", fill="x", expand=True)
            self._label(text, title, bold=True).pack(anchor="w")
            self._label(text, detail, color=MUTED, size=9, wraplength=310, justify="left").pack(anchor="w")

        path_title = tk.Frame(parent, bg=PANEL)
        path_title.pack(fill="x", pady=(18, 4))
        self._label(path_title, "游戏根目录", color=TEXT, size=10, bold=True).pack(side="left")
        self._button(
            path_title,
            "目录怎么选？",
            self.show_game_folder_help,
            color=PANEL_2,
            fg=ACCENT,
            padx=10,
            pady=4,
            font_size=9,
        ).pack(side="right")
        self._label(
            parent,
            "选择能直接看到 SecretFlasherManaka.exe 的文件夹\n不要选 BepInEx、plugins 或 SecretFlasherManaka_Data",
            color=MUTED,
            size=9,
            wraplength=360,
            justify="left",
        ).pack(anchor="w", pady=(0, 7))
        path_row = tk.Frame(parent, bg=PANEL)
        path_row.pack(fill="x")
        entry = tk.Entry(
            path_row,
            textvariable=self.game_folder,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Microsoft YaHei UI", 9),
        )
        entry.pack(side="left", fill="x", expand=True, ipady=8)
        self._button(path_row, "浏览", self.browse_game, color=PANEL_2, fg=TEXT, padx=10).pack(side="left", padx=(8, 0))

        self._label(parent, variable=self.game_status, color=AMBER, size=9, wraplength=350, justify="left").pack(anchor="w", pady=(8, 14))
        self._button(parent, "安装/更新插件并启动游戏", self.install_and_launch).pack(fill="x")
        self._button(parent, "仅检查安装", self.check_installation, color=PANEL_2, fg=TEXT).pack(fill="x", pady=(8, 0))

        safety_glass = GlassSurface(parent, padding=15, fill=ALERT_PANEL, radius=18, height=162)
        safety_glass.pack(fill="x", pady=(20, 0))
        safety = safety_glass.content
        self._label(safety, "输出控制", size=11, bold=True).pack(anchor="w")
        self._label(safety, variable=self.device_status, color=GREEN, size=9).pack(anchor="w", pady=(3, 8))
        self.pause_button = self._button(
            safety,
            "暂停输出",
            self.toggle_output_pause,
            color=AMBER,
            font_size=16,
            height=62,
            pady=15,
        )
        self.pause_button.pack(fill="x")
        self._refresh_pause_button()

    def _metric(self, parent, title, variable, maximum, style="TProgressbar"):
        top = tk.Frame(parent, bg=PANEL)
        top.pack(fill="x", pady=(10, 4))
        self._label(top, title, color=MUTED, size=9).pack(side="left")
        self._label(top, variable=variable, bold=True).pack(side="right")
        color = ACCENT
        if style == "A.Horizontal.TProgressbar":
            color = AMBER
        elif style == "B.Horizontal.TProgressbar":
            color = VIOLET
        bar = ModernProgress(parent, maximum=maximum, color=color)
        bar.pack(fill="x")
        return bar

    def _build_live_panel(self, parent) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x")
        self._label(row, "实时状态", size=15, bold=True).pack(side="left")
        self._label(row, variable=self.telemetry_status, color=AMBER, size=9).pack(side="right")

        info_glass = GlassSurface(parent, padding=15, fill=PANEL_2, radius=18, height=92)
        info_glass.pack(fill="x", pady=(16, 8))
        info = info_glass.content
        a = tk.Frame(info, bg=PANEL_2)
        a.pack(side="left", fill="x", expand=True)
        self._label(a, "场景", color=MUTED, size=8).pack(anchor="w")
        self._label(a, variable=self.stage_text, size=12, bold=True).pack(anchor="w")
        b = tk.Frame(info, bg=PANEL_2)
        b.pack(side="left", fill="x", expand=True)
        self._label(b, "动作", color=MUTED, size=8).pack(anchor="w")
        self._label(b, variable=self.action_text, size=12, bold=True).pack(anchor="w")

        self.bpm_bar = self._metric(parent, "游戏心率", self.bpm_text, 180)
        self.alert_bar = self._metric(parent, "NPC 警觉度", self.alert_text, 100, "A.Horizontal.TProgressbar")
        self.ecstasy_bar = self._metric(parent, "兴奋度", self.ecstasy_text, 100, "B.Horizontal.TProgressbar")

        self._label(parent, "输出预览", size=12, bold=True).pack(anchor="w", pady=(22, 2))
        self._label(parent, "实机仅输出 A 通道心率；NPC 警觉度不参与输出。", color=MUTED, size=9).pack(anchor="w")
        self.a_bar = self._metric(parent, "A · 心跳 Pulse", self.channel_a_text, 100, "A.Horizontal.TProgressbar")
        self.b_bar = self._metric(parent, "B · 动作进程", self.channel_b_text, 100, "B.Horizontal.TProgressbar")

        settings_glass = GlassSurface(parent, padding=15, fill=PANEL_2, radius=18, height=154)
        settings_glass.pack(fill="x", pady=(16, 0))
        settings = settings_glass.content
        title = tk.Frame(settings, bg=PANEL_2)
        title.pack(fill="x")
        self._label(title, "个性化 Pulse", size=10, bold=True).pack(side="left")
        self._button(title, "调整范围", self.open_personalization, color=GREEN, padx=12, pady=5).pack(side="right")
        summaries = tk.Frame(settings, bg=PANEL_2)
        summaries.pack(fill="x", pady=(8, 0))
        for label, variable, color in (
            ("心率范围", self.heart_range_summary, ACCENT),
            ("强度范围", self.strength_range_summary, ACCENT),
            ("安全硬上限", self.hard_cap_summary, AMBER),
        ):
            cell = tk.Frame(summaries, bg=PANEL_2)
            cell.pack(side="left", fill="x", expand=True)
            self._label(cell, label, color=MUTED, size=8).pack(anchor="w")
            self._label(cell, variable=variable, color=color, size=10, bold=True).pack(anchor="w", pady=(2, 0))
        wave_row = tk.Frame(settings, bg=PANEL_2)
        wave_row.pack(fill="x", pady=(8, 0))
        self._label(wave_row, "波形策略", color=MUTED, size=8).pack(side="left")
        self._label(wave_row, variable=self.wave_policy_summary, color=CYAN, size=9, bold=True).pack(side="right")

    def browse_game(self) -> None:
        chosen = filedialog.askdirectory(title="选择能看到 SecretFlasherManaka.exe 的游戏根目录")
        if chosen:
            self.game_folder.set(chosen)
            update_config({"game_folder": chosen})
            self.check_installation()

    def show_game_folder_help(self) -> None:
        current = Path(self.game_folder.get().strip())
        current_note = ""
        if (current / "SecretFlasherManaka.exe").is_file():
            current_note = f"\n\n✓ 当前填写的目录正确：\n{current}"
        elif str(current):
            current_note = f"\n\n✗ 当前填写的目录里没有找到游戏 EXE：\n{current}"
        messagebox.showinfo(
            "游戏目录怎么选",
            "请选择游戏的最外层文件夹。打开它后，应当能直接看到：\n\n"
            "  SecretFlasherManaka.exe\n"
            "  BepInEx 文件夹\n"
            "  SecretFlasherManaka_Data 文件夹\n\n"
            "正确示例：\n"
            "  D:\\Games\\SecretFlasherManaka v1.1.3\n\n"
            "不要选择：\n"
            "  ...\\BepInEx\n"
            "  ...\\BepInEx\\plugins\n"
            "  ...\\SecretFlasherManaka_Data"
            f"{current_note}",
        )

    def check_installation(self) -> bool:
        folder = Path(self.game_folder.get().strip())
        valid, detail = validate_game_folder(folder)
        if not valid:
            self.game_status.set(detail)
            return False
        target = folder / "BepInEx" / "plugins" / "ManakaDGLabTelemetry" / "ManakaDGLabTelemetry.dll"
        if target.is_file():
            self.game_status.set("✓ 游戏、依赖和遥测插件均已就绪")
        else:
            self.game_status.set("游戏检查通过；遥测插件尚未安装")
        return True

    def install_plugin(self) -> bool:
        folder = Path(self.game_folder.get().strip())
        valid, detail = validate_game_folder(folder)
        if not valid:
            messagebox.showerror("无法安装", detail)
            return False
        source = bundled_plugin_path()
        if not source.is_file():
            messagebox.showerror("缺少文件", f"找不到遥测插件：\n{source}")
            return False
        target_dir = folder / "BepInEx" / "plugins" / "ManakaDGLabTelemetry"
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, target_dir / source.name)
        except PermissionError:
            messagebox.showerror("文件正在使用", "请完全退出游戏后再更新插件。")
            return False
        update_config({"game_folder": str(folder)})
        self._log("插件安装/更新完成")
        self.check_installation()
        return True

    def install_and_launch(self) -> None:
        if not self.install_plugin():
            return
        executable = Path(self.game_folder.get().strip()) / "SecretFlasherManaka.exe"
        try:
            subprocess.Popen([str(executable)], cwd=str(executable.parent))
            self._log("游戏已启动，等待进入可操作场景")
        except OSError as error:
            messagebox.showerror("启动失败", str(error))

    def start_listener(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        self.worker = TelemetryWorker(self.messages)
        self.worker.start()

    def start_socket_bridge(self) -> None:
        self.bridge.start()

    def open_device_connection(self) -> None:
        if self.connection_dialog is not None and self.connection_dialog.winfo_exists():
            self.connection_dialog.lift()
            return
        self.connection_dialog = DeviceConnectionDialog(self)

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "listener":
                    if payload == "ready":
                        self.telemetry_status.set("等待游戏数据")
                        self._log("遥测监听已启动；设备输出保持锁定")
                    else:
                        self.telemetry_status.set("监听端口被占用")
                        self._log(str(payload))
                elif kind == "telemetry":
                    self._on_telemetry(payload)
                elif kind == "dglab":
                    self._handle_dglab_event(payload)
        except queue.Empty:
            pass
        self.after(50, self._poll_messages)

    def _handle_dglab_event(self, payload: dict) -> None:
        event = str(payload.get("event", ""))
        if event == "ready":
            self.device_status.set("Socket 已就绪 · 等待手机扫码")
            self.device_badge.set("等待设备连接", AMBER)
            self._log(f"DG-LAB Socket 已就绪：{payload.get('lan_ip')}:{payload.get('port')}")
        elif event == "connected":
            self.device_connected = True
            self.auto_output_enabled = True
            self.safety_wait_reason = self.current_frame.reason if self.current_frame.safe_cut else ""
            self.bridge.set_auto_enabled(True)
            if self.current_frame.safe_cut:
                self.device_status.set("设备已连接 · 安全待机，等待游戏场景")
                self.device_badge.set("安全待机", AMBER)
            else:
                self.device_status.set("设备已连接 · A 通道心率输出已启用")
                self.device_badge.set("A 通道已启用", RED)
            self._refresh_pause_button()
            self._log("DG-LAB 手机端绑定成功；已自动启用 A 通道心率输出")
            self._show_frame(self.current_frame)
            dialog = self.connection_dialog
            if dialog is not None and dialog.winfo_exists():
                dialog.status.set("● 连接成功，正在返回…")
                dialog.after(500, dialog._close)
        elif event == "disconnected":
            self.device_connected = False
            self.auto_output_enabled = False
            self.safety_wait_reason = ""
            self.device_status.set("设备已断开 · 输出已归零")
            self.device_badge.set("设备已断开", RED)
            self._refresh_pause_button()
            self._log("DG-LAB 连接断开；自动输出已关闭")
        elif event == "feedback":
            message = str(payload.get("message", ""))
            if message.startswith("strength-"):
                self._log(f"设备强度反馈：{message}")
        elif event == "error":
            detail = str(payload.get("detail", "未知错误"))
            self.device_status.set("Socket 连接不可用")
            self.device_badge.set("连接服务异常", RED)
            self._log(detail)

    def _on_telemetry(self, packet: dict) -> None:
        now = time.monotonic()
        game_ms = int(packet.get("monotonicMs", 0) or 0)
        dt = 0.1 if self.last_game_ms is None else max(0.0, min(0.5, (game_ms - self.last_game_ms) / 1000.0))
        self.last_game_ms = game_ms
        self.last_receive = now
        self.last_packet = packet
        self.stale_reported = False
        frame = self.engine.evaluate(packet, dt)
        self.telemetry_status.set("Ⅱ 游戏已暂停" if frame.reason == "game-paused" else "● 实时连接")
        bpm = float(packet.get("heartRate", 0) or 0)
        alert = max(0.0, min(1.0, float(packet.get("maxNpcAlert", 0) or 0)))
        ecstasy = max(0.0, min(1.0, float(packet.get("ecstasy", 0) or 0)))
        action = str(packet.get("action", "None") or "None")

        self.stage_text.set(str(packet.get("stage", "None")))
        self.action_text.set(action)
        self.bpm_text.set(f"{bpm:.1f} BPM")
        self.alert_text.set(f"{alert * 100:.0f}%")
        self.ecstasy_text.set(f"{ecstasy * 100:.0f}%")
        self.bpm_bar.set(min(180, bpm))
        self.alert_bar.set(alert * 100)
        self.ecstasy_bar.set(ecstasy * 100)
        if frame.safe_cut:
            self._enter_safety_idle(frame.reason)
        else:
            self._leave_safety_idle()
        self._show_frame(frame)

        if action != self.last_action:
            self._log(f"动作：{self.last_action} → {action}")
            self.last_action = action
        for event in frame.events:
            self._log(f"事件：{event}")

    def _show_frame(self, frame: TriggerFrame) -> None:
        self.current_frame = frame
        custom = self._custom_waveform()
        wave_a = self.wave_selector.select(
            "A", frame.pattern_a, self.wave_mode.get(), self.fixed_wave.get(), self.wave_map, custom
        )
        wave_b = self.wave_selector.select(
            "B", frame.pattern_b, self.wave_mode.get(), self.fixed_wave.get(), self.wave_map, custom
        )
        strength_a = frame.strength_a * wave_a.feel_scale if wave_a else 0.0
        strength_b = frame.strength_b * wave_b.feel_scale if wave_b else 0.0
        self.a_bar.set(strength_a)
        self.b_bar.set(strength_b)
        self.channel_a_text.set(f"{strength_a:.1f} · {wave_a.name if wave_a else '待机'}")
        self.channel_b_text.set(f"{strength_b:.1f} · {wave_b.name if wave_b else '待机'}")
        self.current_wave_a = wave_a
        self.current_wave_b = wave_b
        self.current_output_a = strength_a
        self.current_output_b = strength_b
        if self.auto_output_enabled:
            if wave_a is None or strength_a <= 0:
                self.bridge.update_auto_output(0, (), wave_key="idle", hard_cap=self.hard_cap.get())
            else:
                self.bridge.update_auto_output(
                    strength_a,
                    wave_a.v3_frames(),
                    wave_key=wave_a.key,
                    hard_cap=self.hard_cap.get(),
                )

    def _check_stale(self) -> None:
        if self.last_receive and time.monotonic() - self.last_receive >= STALE_SECONDS and not self.stale_reported:
            self.stale_reported = True
            self.telemetry_status.set("等待游戏数据")
            self._enter_safety_idle("telemetry-stale")
            self._show_frame(self.engine.force_safe_cut("telemetry-stale"))
            self._log("安全归零：遥测中断")
        self.after(250, self._check_stale)

    def _enter_safety_idle(self, reason: str) -> None:
        if not self.auto_output_enabled:
            return
        if self.safety_wait_reason != reason:
            self._log(f"安全待机并归零：{reason}；游戏数据恢复后自动继续")
        self.safety_wait_reason = reason
        self.device_status.set("安全待机 · 输出归零，等待有效游戏数据")
        if self.device_connected:
            self.device_badge.set("安全待机", AMBER)

    def _leave_safety_idle(self) -> None:
        if not self.auto_output_enabled or not self.device_connected:
            return
        if self.safety_wait_reason:
            self._log("有效游戏数据已恢复；自动继续 A 通道心率输出")
        self.safety_wait_reason = ""
        self.device_status.set("设备已连接 · A 通道心率输出中")
        self.device_badge.set("A 通道输出中", RED)

    def _refresh_settings_summary(self) -> None:
        self.heart_range_summary.set(f"{self.trigger_bpm.get()}–{self.full_bpm.get()} BPM")
        self.strength_range_summary.set(f"{self.min_strength.get()}–{self.output_max.get()}")
        self.hard_cap_summary.set(f"{self.hard_cap.get()} / 100")
        if self.wave_mode.get() == "fixed":
            preset = self._waveform_by_key(self.fixed_wave.get())
            self.wave_policy_summary.set(f"固定 · {preset.name}")
        else:
            low = self._waveform_by_key(self.wave_map["low"]).name
            mid = self._waveform_by_key(self.wave_map["mid"]).name
            high = self._waveform_by_key(self.wave_map["high"]).name
            self.wave_policy_summary.set(f"智能 · {low} → {mid} → {high}")

    def open_personalization(self) -> None:
        PersonalizationDialog(self)

    def open_waveform_studio(self) -> None:
        WaveformStudio(self)

    def open_waveform_monitor(self) -> None:
        if self.wave_monitor_window is not None and self.wave_monitor_window.winfo_exists():
            self.wave_monitor_window.lift()
            self.wave_monitor_window.focus_force()
            return
        self.wave_monitor_window = WaveformMonitor(self)

    def _custom_waveform(self) -> WaveformPreset:
        return WaveformPreset(
            "custom",
            "我的波形",
            "用户绘制的自定义包络",
            "由用户分配的心率区间",
            CYAN,
            tuple(self.custom_wave_points),
            (self.custom_wave_frequency.get(),),
            source="我的波形",
        )

    def _waveform_by_key(self, key: str) -> WaveformPreset:
        return self._custom_waveform() if key == "custom" else PRESETS.get(key, PRESETS["official_heartbeat"])

    def apply_wave_settings(
        self,
        *,
        mode: str,
        fixed_preset: str,
        wave_map: dict[str, str],
        custom_points: list[int],
        custom_frequency: int,
    ) -> None:
        allowed = set(PRESETS) | {"custom"}
        mode = "fixed" if mode == "fixed" else "smart"
        fixed_preset = fixed_preset if fixed_preset in allowed else "official_heartbeat"
        clean_map = sanitize_wave_map(wave_map)
        if len(custom_points) != 16:
            raise ValueError("custom waveform must contain 16 points")
        clean_points = [int(clamp(float(value), 0, 100)) for value in custom_points]
        clean_frequency = int(clamp(float(custom_frequency), 10, 240))
        self.wave_mode.set(mode)
        self.fixed_wave.set(fixed_preset)
        self.wave_map = clean_map
        self.custom_wave_points = clean_points
        self.custom_wave_frequency.set(clean_frequency)
        self.wave_selector.reset()
        update_config(
            {
                "wave_mode": mode,
                "fixed_wave": fixed_preset,
                "wave_map": clean_map,
                "custom_wave_points": clean_points,
                "custom_wave_frequency": clean_frequency,
            }
        )
        self._refresh_settings_summary()
        self._log(f"波形配置已保存：{self.wave_policy_summary.get()}")

    def apply_personal_settings(
        self,
        *,
        trigger_bpm: int,
        full_bpm: int,
        min_strength: int,
        output_max: int,
        hard_cap: int,
    ) -> bool:
        if not 60 <= trigger_bpm < full_bpm <= 220:
            messagebox.showerror("心率范围无效", "开始 BPM 必须低于满幅 BPM，范围为 60–220。")
            return False
        if not 0 <= min_strength <= output_max <= hard_cap <= 100:
            messagebox.showerror(
                "强度范围无效",
                "必须满足：0 ≤ 最低强度 ≤ 日常最高 ≤ 安全硬上限 ≤ 100。",
            )
            return False

        previous_cap = self.engine.hard_cap
        if hard_cap > 30 and previous_cap <= 30:
            accepted = messagebox.askyesno(
                "提高安全硬上限",
                "你正在把安全硬上限提高到 30 以上。\n\n"
                "请先在 DG-LAB App 中确认个人可承受范围，并从低强度逐步测试。"
                "是否继续？",
                icon="warning",
            )
            if not accepted:
                return False

        self.engine.configure(
            min_strength=min_strength,
            output_max=output_max,
            hard_cap=hard_cap,
            trigger_bpm=trigger_bpm,
            full_bpm=full_bpm,
        )
        self.trigger_bpm.set(trigger_bpm)
        self.full_bpm.set(full_bpm)
        self.min_strength.set(min_strength)
        self.output_max.set(output_max)
        self.hard_cap.set(hard_cap)
        self._refresh_settings_summary()
        update_config(
            {
                "trigger_bpm": trigger_bpm,
                "full_bpm": full_bpm,
                "min_strength": min_strength,
                "output_max": output_max,
                "hard_cap": hard_cap,
            }
        )
        self._log(
            f"已保存个性化范围：BPM {trigger_bpm}–{full_bpm}，"
            f"强度 {min_strength}–{output_max}，硬上限 {hard_cap}"
        )
        return True

    def _refresh_pause_button(self) -> None:
        button = getattr(self, "pause_button", None)
        if button is None:
            return
        if self.device_connected and self.auto_output_enabled:
            button.set_text("Ⅱ  暂停输出")
            button.color = AMBER
            button.fg = BUTTON_TEXT
        elif self.device_connected:
            button.set_text("▶  继续输出")
            button.color = GREEN
            button.fg = BUTTON_TEXT
        else:
            button.set_text("尚未连接设备")
            button.color = PANEL_2
            button.fg = MUTED
        button._draw()

    def toggle_output_pause(self) -> None:
        if not self.device_connected:
            messagebox.showinfo("尚未连接", "请先用 DG-LAB App 扫描二维码连接设备。")
            return
        if self.auto_output_enabled:
            self.auto_output_enabled = False
            self.safety_wait_reason = ""
            self.bridge.emergency_stop()
            self.device_status.set("输出已暂停 · A/B 已归零 · 设备保持连接")
            self.device_badge.set("输出已暂停", AMBER)
            self._log("手动暂停输出：A/B 已归零并清空队列，Socket 保持连接")
        else:
            self.auto_output_enabled = True
            self.bridge.set_auto_enabled(True)
            if self.current_frame.safe_cut:
                self.safety_wait_reason = self.current_frame.reason
                self.device_status.set("已继续 · 安全待机，等待有效游戏数据")
                self.device_badge.set("安全待机", AMBER)
            else:
                self.safety_wait_reason = ""
                self.device_status.set("设备已连接 · A 通道心率输出已恢复")
                self.device_badge.set("A 通道已启用", RED)
            self._show_frame(self.current_frame)
            self._log("继续输出：已恢复 A 通道心率驱动")
        self._refresh_pause_button()

    def _log(self, text: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        line = f"{stamp}  {text}"
        self.log_lines.append(line)
        self.log_lines = self.log_lines[-300:]
        if self.log_text is not None and self.log_text.winfo_exists():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

    def show_log_window(self) -> None:
        if self.log_window is not None and self.log_window.winfo_exists():
            self.log_window.lift()
            return
        self.log_window = tk.Toplevel(self)
        self.log_window.title("Manaka 事件日志")
        self.log_window.geometry("760x420")
        self.log_window.configure(bg=BG)
        header = tk.Frame(self.log_window, bg=BG, padx=18, pady=14)
        header.pack(fill="x")
        self._label(header, "事件日志", size=15, bold=True).pack(side="left")
        self._button(header, "清空", self.clear_log, color=PANEL_2, fg=MUTED, padx=12, pady=5).pack(side="right")
        self.log_text = tk.Text(
            self.log_window,
            bg=LOG_BG,
            fg=LOG_TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Cascadia Mono", 10),
            padx=14,
            pady=12,
            state="normal",
        )
        self.log_text.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        if self.log_lines:
            self.log_text.insert("end", "\n".join(self.log_lines) + "\n")
            self.log_text.see("end")
        self.log_text.configure(state="disabled")

        def closed() -> None:
            if self.log_window is not None:
                self.log_window.destroy()
            self.log_window = None
            self.log_text = None

        self.log_window.protocol("WM_DELETE_WINDOW", closed)

    def clear_log(self) -> None:
        self.log_lines.clear()
        if self.log_text is not None and self.log_text.winfo_exists():
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")

    def close_app(self) -> None:
        if self.worker is not None:
            self.worker.stop()
        self.auto_output_enabled = False
        self.bridge.stop()
        self.destroy()


def main() -> None:
    ControlCenter().mainloop()


if __name__ == "__main__":
    main()

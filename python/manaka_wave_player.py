"""Bounded per-channel V3 queue planner, using monotonic playback time."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PlaybackPlan:
    clear: bool = False
    frames: tuple[str, ...] = ()
    finished: bool = False


class ChannelPlayer:
    def __init__(self, lookahead=.3, settle=.15):
        self.lookahead = lookahead
        self.settle = settle
        self.reset()

    def reset(self):
        self.identity = None
        self.cursor = 0
        self.queued_until = 0.
        self.ready_at = 0.
        self.active = False

    def plan(self, now, token, frames, loop=True, enabled=True, transition="immediate"):
        identity = (token, frames, loop)
        if not enabled or not frames:
            clear = self.active
            self.active = False
            # A completed one-shot remains completed until its rule re-enters.
            if loop:
                self.identity = None
            return PlaybackPlan(clear=clear)
        if self.identity != identity:
            if transition == "cycle" and self.identity and self.active:
                old_token, old_frames, old_loop = self.identity
                # Finish the cycle actually queued to the device, including its
                # 150 ms clear gap. Router timestamps alone cannot know this.
                if self.cursor % len(old_frames) or now < self.queued_until:
                    remaining = max(0., self.queued_until-now)
                    if now < self.ready_at or remaining > .1 or not self.cursor % len(old_frames):
                        return PlaybackPlan()
                    count = min(len(old_frames)-self.cursor%len(old_frames),
                        max(1, math.floor((self.lookahead-remaining+1e-9)/.1)))
                    chunk = tuple(old_frames[(self.cursor+i)%len(old_frames)] for i in range(count))
                    self.cursor += count
                    self.queued_until = max(now,self.queued_until)+count*.1
                    return PlaybackPlan(frames=chunk)
            self.identity = identity
            self.cursor = 0
            self.queued_until = now
            self.ready_at = now+self.settle
            self.active = True
            return PlaybackPlan(clear=True)
        if not self.active:
            self.active = True
            self.queued_until = now
            self.ready_at = now+self.settle
            return PlaybackPlan(clear=True)
        if now < self.ready_at:
            return PlaybackPlan()
        if not loop and self.cursor >= len(frames):
            return PlaybackPlan(finished=now >= self.queued_until)
        remaining = max(0., self.queued_until-now)
        if remaining > .1:
            return PlaybackPlan()
        count = max(1, math.floor((self.lookahead-remaining+1e-9)/.1))
        if not loop:
            count = min(count, len(frames)-self.cursor)
        chunk = tuple(frames[(self.cursor+i) % len(frames)] for i in range(count))
        self.cursor += count
        self.queued_until = max(now, self.queued_until)+.1*count
        return PlaybackPlan(frames=chunk)

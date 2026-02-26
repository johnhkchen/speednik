"""speednik/agents/scripted.py — ScriptedAgent: frame-indexed timeline playback.

Takes a list of (start_frame, end_frame, action) tuples and returns the action
for the active time window. Tracks its own frame counter.
"""

from __future__ import annotations

import numpy as np

from speednik.agents.actions import ACTION_NOOP


class ScriptedAgent:
    """Agent that plays back a scripted timeline of actions."""

    def __init__(self, timeline: list[tuple[int, int, int]]) -> None:
        self.timeline = timeline
        self._frame: int = 0

    def act(self, obs: np.ndarray) -> int:
        frame = self._frame
        self._frame += 1
        for start, end, action in self.timeline:
            if start <= frame < end:
                return action
        return ACTION_NOOP

    def reset(self) -> None:
        self._frame = 0

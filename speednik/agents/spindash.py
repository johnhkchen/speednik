"""speednik/agents/spindash.py — SpindashAgent: charge/release/run/re-dash cycle.

State machine that charges a spindash, releases it, runs right, and re-dashes
when speed drops below a threshold. Equivalent to the harness spindash_right()
strategy but using observation-based interface.
"""

from __future__ import annotations

import numpy as np

from speednik.agents.actions import ACTION_DOWN, ACTION_DOWN_JUMP, ACTION_RIGHT

# Phase constants
CROUCH = 0
CHARGE = 1
RELEASE = 2
RUN = 3


class SpindashAgent:
    """Agent that spindashes through obstacles."""

    def __init__(
        self, charge_frames: int = 3, redash_speed: float = 0.125
    ) -> None:
        self.charge_frames = charge_frames
        self.redash_speed = redash_speed  # normalized ground_speed threshold
        self._phase: int = CROUCH
        self._counter: int = 0

    def act(self, obs: np.ndarray) -> int:
        if self._phase == CROUCH:
            self._phase = CHARGE
            self._counter = 0
            return ACTION_DOWN

        if self._phase == CHARGE:
            self._counter += 1
            if self._counter >= self.charge_frames:
                self._phase = RELEASE
            return ACTION_DOWN_JUMP

        if self._phase == RELEASE:
            self._phase = RUN
            return ACTION_RIGHT

        # RUN phase
        on_ground = obs[4] > 0.5
        ground_speed = abs(obs[5])
        is_rolling = obs[6] > 0.5

        if on_ground and ground_speed < self.redash_speed and not is_rolling:
            self._phase = CROUCH
            return ACTION_DOWN

        return ACTION_RIGHT

    def reset(self) -> None:
        self._phase = CROUCH
        self._counter = 0

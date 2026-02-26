"""speednik/agents/jump_runner.py — JumpRunnerAgent: run right, jump on landing.

Runs right and jumps on the first frame and after every landing. Equivalent to
the harness hold_right_jump() strategy but using observation-based interface.
When raycasts become available (T-010-16/17), can be extended to jump at obstacles.
"""

from __future__ import annotations

import numpy as np

from speednik.agents.actions import ACTION_RIGHT, ACTION_RIGHT_JUMP


class JumpRunnerAgent:
    """Agent that runs right and jumps on landing."""

    def __init__(self) -> None:
        self._was_airborne: bool = False
        self._first_call: bool = True

    def act(self, obs: np.ndarray) -> int:
        on_ground = obs[4] > 0.5

        # Jump on very first frame if grounded
        if self._first_call:
            self._first_call = False
            if on_ground:
                self._was_airborne = False
                return ACTION_RIGHT_JUMP

        # Detect landing: was airborne last frame, now on ground
        just_landed = self._was_airborne and on_ground
        self._was_airborne = not on_ground

        if just_landed:
            return ACTION_RIGHT_JUMP

        return ACTION_RIGHT

    def reset(self) -> None:
        self._was_airborne = False
        self._first_call = True

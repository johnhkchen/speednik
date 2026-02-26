"""speednik/agents/hold_right.py — HoldRightAgent: always returns ACTION_RIGHT.

The simplest possible agent and the baseline for every scenario.
"""

from __future__ import annotations

import numpy as np

from speednik.agents.actions import ACTION_RIGHT


class HoldRightAgent:
    """Agent that holds right every frame."""

    def act(self, obs: np.ndarray) -> int:
        return ACTION_RIGHT

    def reset(self) -> None:
        pass

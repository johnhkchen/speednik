"""speednik/agents/idle.py — IdleAgent: always returns ACTION_NOOP.

For ground adhesion tests and as a null baseline.
"""

from __future__ import annotations

import numpy as np

from speednik.agents.actions import ACTION_NOOP


class IdleAgent:
    """Agent that does nothing every frame."""

    def act(self, obs: np.ndarray) -> int:
        return ACTION_NOOP

    def reset(self) -> None:
        pass

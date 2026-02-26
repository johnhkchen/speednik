"""speednik/agents/base.py — Agent protocol (Layer 3).

All agents — programmed, RL, or replay — conform to this interface.
Uses Protocol (not ABC) for duck typing with static type checking.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Agent(Protocol):
    """Anything that maps observations to actions."""

    def act(self, obs: np.ndarray) -> int:
        """Given an observation vector, return a discrete action index."""
        ...

    def reset(self) -> None:
        """Called at episode start. Reset internal state if any."""
        ...

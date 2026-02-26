"""speednik/agents/registry.py — Agent name → class mapping.

Used by scenario YAML resolution to instantiate agents by string name.
"""

from __future__ import annotations

from speednik.agents.hold_right import HoldRightAgent
from speednik.agents.idle import IdleAgent
from speednik.agents.jump_runner import JumpRunnerAgent
from speednik.agents.scripted import ScriptedAgent
from speednik.agents.spindash import SpindashAgent

AGENT_REGISTRY: dict[str, type] = {
    "idle": IdleAgent,
    "hold_right": HoldRightAgent,
    "jump_runner": JumpRunnerAgent,
    "spindash": SpindashAgent,
    "scripted": ScriptedAgent,
}

try:
    from speednik.agents.ppo_agent import PPOAgent

    AGENT_REGISTRY["ppo"] = PPOAgent
except ImportError:
    pass


def resolve_agent(name: str, params: dict | None = None):
    """Look up an agent class by name and instantiate with optional kwargs.

    Args:
        name: Agent name (key in AGENT_REGISTRY).
        params: Optional kwargs passed to the agent constructor.

    Returns:
        An instantiated agent conforming to the Agent protocol.

    Raises:
        KeyError: If name is not in the registry.
    """
    if name not in AGENT_REGISTRY:
        if name == "ppo":
            raise KeyError(
                f"Agent 'ppo' is not available. Install PyTorch to use PPOAgent: "
                f"uv add torch"
            )
        raise KeyError(f"Unknown agent: {name!r}. Available: {sorted(AGENT_REGISTRY)}")
    cls = AGENT_REGISTRY[name]
    return cls(**(params or {}))

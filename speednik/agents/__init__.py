"""speednik/agents — Agent interface, action space, and programmed agents (Layer 3)."""

from speednik.agents.actions import (
    ACTION_DOWN,
    ACTION_DOWN_JUMP,
    ACTION_JUMP,
    ACTION_LEFT,
    ACTION_LEFT_JUMP,
    ACTION_MAP,
    ACTION_NOOP,
    ACTION_RIGHT,
    ACTION_RIGHT_JUMP,
    NUM_ACTIONS,
    action_to_input,
)
from speednik.agents.base import Agent
from speednik.agents.hold_right import HoldRightAgent
from speednik.agents.idle import IdleAgent
from speednik.agents.jump_runner import JumpRunnerAgent
from speednik.agents.registry import AGENT_REGISTRY, resolve_agent
from speednik.agents.scripted import ScriptedAgent
from speednik.agents.spindash import SpindashAgent

__all__ = [
    "Agent",
    "ACTION_NOOP",
    "ACTION_LEFT",
    "ACTION_RIGHT",
    "ACTION_JUMP",
    "ACTION_LEFT_JUMP",
    "ACTION_RIGHT_JUMP",
    "ACTION_DOWN",
    "ACTION_DOWN_JUMP",
    "NUM_ACTIONS",
    "ACTION_MAP",
    "action_to_input",
    "IdleAgent",
    "HoldRightAgent",
    "JumpRunnerAgent",
    "SpindashAgent",
    "ScriptedAgent",
    "AGENT_REGISTRY",
    "resolve_agent",
]

try:
    from speednik.agents.ppo_agent import PPOAgent

    __all__.append("PPOAgent")
except ImportError:
    pass

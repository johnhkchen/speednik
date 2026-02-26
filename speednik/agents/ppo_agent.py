"""speednik/agents/ppo_agent — PPO policy agent (Layer 3).

Wraps a trained CleanRL PPO checkpoint as an Agent. Requires torch.
The network architecture mirrors tools/ppo_speednik.py so that
state_dict checkpoints load correctly.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from speednik.agents.actions import NUM_ACTIONS
from speednik.observation import OBS_DIM


def _layer_init(layer: nn.Linear, std: float = np.sqrt(2), bias_const: float = 0.0) -> nn.Linear:
    """Orthogonal weight init matching CleanRL's ppo.py."""
    nn.init.orthogonal_(layer.weight, std)
    nn.init.constant_(layer.bias, bias_const)
    return layer


class _PPONetwork(nn.Module):
    """Actor-critic MLP matching the Agent class in tools/ppo_speednik.py."""

    def __init__(self, obs_dim: int, num_actions: int) -> None:
        super().__init__()
        self.critic = nn.Sequential(
            _layer_init(nn.Linear(obs_dim, 64)),
            nn.Tanh(),
            _layer_init(nn.Linear(64, 64)),
            nn.Tanh(),
            _layer_init(nn.Linear(64, 1), std=1.0),
        )
        self.actor = nn.Sequential(
            _layer_init(nn.Linear(obs_dim, 64)),
            nn.Tanh(),
            _layer_init(nn.Linear(64, 64)),
            nn.Tanh(),
            _layer_init(nn.Linear(64, num_actions), std=0.01),
        )


class PPOAgent:
    """Wraps a trained CleanRL PPO checkpoint as an Agent.

    Loads a state_dict checkpoint, reconstructs the network architecture,
    and provides deterministic (greedy) action selection for evaluation.
    """

    def __init__(
        self,
        model_path: str,
        device: str = "cpu",
        obs_dim: int = OBS_DIM,
        num_actions: int = NUM_ACTIONS,
    ) -> None:
        self.device = torch.device(device)
        self.model = _PPONetwork(obs_dim, num_actions)
        self.model.load_state_dict(
            torch.load(model_path, map_location=self.device, weights_only=True)
        )
        self.model.to(self.device)
        self.model.eval()

    def act(self, obs: np.ndarray) -> int:
        """Return the greedy action for the given observation."""
        with torch.no_grad():
            obs_tensor = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
            logits = self.model.actor(obs_tensor)
            return logits.argmax(dim=-1).item()

    def reset(self) -> None:
        """No internal state to reset."""

"""speednik/env.py — Gymnasium environment wrapper (Layer 5).

Bridges the headless simulation with RL training. Thin adapter that
delegates to simulation, observation, and action modules.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from speednik.agents.actions import NUM_ACTIONS, action_to_input
from speednik.observation import OBS_DIM, extract_observation
from speednik.simulation import SimState, create_sim, sim_step


class SpeednikEnv(gym.Env):
    """Gymnasium environment for Speednik — a Sonic 2 homage."""

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 60}

    def __init__(
        self,
        stage: str = "hillside",
        render_mode: str | None = None,
        max_steps: int = 3600,
    ) -> None:
        super().__init__()
        self.stage_name = stage
        self.render_mode = render_mode
        self.max_steps = max_steps

        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(OBS_DIM,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(NUM_ACTIONS)

        self.sim: SimState | None = None
        self._step_count = 0
        self._prev_jump_held = False

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict | None = None,
    ) -> tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        self.sim = create_sim(self.stage_name)
        self._step_count = 0
        self._prev_jump_held = False
        return self._get_obs(), self._get_info()

    def step(
        self, action: int
    ) -> tuple[np.ndarray, float, bool, bool, dict]:
        inp = self._action_to_input(action)
        events = sim_step(self.sim, inp)
        self._step_count += 1

        obs = self._get_obs()
        reward = self._compute_reward(events)
        terminated = bool(self.sim.goal_reached or self.sim.player_dead)
        truncated = self._step_count >= self.max_steps
        info = self._get_info()

        return obs, reward, terminated, truncated, info

    def _action_to_input(self, action: int):
        inp, self._prev_jump_held = action_to_input(
            action, self._prev_jump_held
        )
        return inp

    def _get_obs(self) -> np.ndarray:
        return extract_observation(self.sim)

    def _compute_reward(self, events: list) -> float:
        # Placeholder — T-010-07 implements the real reward signal.
        return 0.0

    def _get_info(self) -> dict:
        return {
            "frame": self.sim.frame,
            "x": self.sim.player.physics.x,
            "y": self.sim.player.physics.y,
            "max_x": self.sim.max_x_reached,
            "rings": self.sim.rings_collected,
            "deaths": self.sim.deaths,
            "goal_reached": self.sim.goal_reached,
        }

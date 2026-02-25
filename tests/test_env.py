"""Tests for speednik/env.py — SpeednikEnv Gymnasium environment."""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

from speednik.agents.actions import (
    ACTION_JUMP,
    ACTION_NOOP,
    ACTION_RIGHT,
    ACTION_RIGHT_JUMP,
    NUM_ACTIONS,
)
from speednik.env import SpeednikEnv
from speednik.observation import OBS_DIM
from speednik.player import PlayerState


# ---------------------------------------------------------------------------
# Space definitions
# ---------------------------------------------------------------------------

def test_observation_space_shape():
    env = SpeednikEnv()
    assert env.observation_space.shape == (OBS_DIM,)
    assert env.observation_space.dtype == np.float32


def test_action_space():
    env = SpeednikEnv()
    assert env.action_space.n == NUM_ACTIONS


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

def test_reset_returns_obs_info():
    env = SpeednikEnv()
    result = env.reset()
    assert isinstance(result, tuple)
    assert len(result) == 2
    obs, info = result
    assert isinstance(obs, np.ndarray)
    assert isinstance(info, dict)


def test_reset_obs_shape_dtype():
    env = SpeednikEnv()
    obs, _ = env.reset()
    assert obs.shape == (OBS_DIM,)
    assert obs.dtype == np.float32


def test_reset_initializes_sim():
    env = SpeednikEnv()
    assert env.sim is None
    env.reset()
    assert env.sim is not None


def test_reset_info_keys():
    env = SpeednikEnv()
    _, info = env.reset()
    expected_keys = {"frame", "x", "y", "max_x", "rings", "deaths", "goal_reached"}
    assert set(info.keys()) == expected_keys


def test_reset_with_seed():
    env = SpeednikEnv()
    obs1, _ = env.reset(seed=42)
    obs2, _ = env.reset(seed=42)
    np.testing.assert_array_equal(obs1, obs2)


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------

def test_step_returns_5_tuple():
    env = SpeednikEnv()
    env.reset()
    result = env.step(ACTION_RIGHT)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_step_obs_shape():
    env = SpeednikEnv()
    env.reset()
    obs, _, _, _, _ = env.step(ACTION_RIGHT)
    assert obs.shape == (OBS_DIM,)
    assert obs.dtype == np.float32


def test_step_reward_is_float():
    env = SpeednikEnv()
    env.reset()
    _, reward, _, _, _ = env.step(ACTION_RIGHT)
    assert isinstance(reward, float)


def test_step_terminated_truncated_are_bool():
    env = SpeednikEnv()
    env.reset()
    _, _, terminated, truncated, _ = env.step(ACTION_RIGHT)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)


def test_step_advances_frame():
    env = SpeednikEnv()
    env.reset()
    _, _, _, _, info1 = env.step(ACTION_NOOP)
    _, _, _, _, info2 = env.step(ACTION_NOOP)
    assert info2["frame"] == info1["frame"] + 1


def test_step_hold_right_moves_player():
    env = SpeednikEnv()
    env.reset()
    _, _, _, _, info_start = env.step(ACTION_NOOP)
    start_x = info_start["x"]

    for _ in range(60):
        env.step(ACTION_RIGHT)

    _, _, _, _, info_end = env.step(ACTION_RIGHT)
    assert info_end["x"] > start_x


# ---------------------------------------------------------------------------
# Jump edge detection
# ---------------------------------------------------------------------------

def test_jump_pressed_first_frame_only():
    """Verify jump_pressed is True only on the first frame of a jump action."""
    env = SpeednikEnv()
    env.reset()

    # Frame 1: jump action — _prev_jump_held was False, so jump_pressed should be True
    assert env._prev_jump_held is False
    env.step(ACTION_JUMP)
    assert env._prev_jump_held is True

    # Frame 2: jump held — jump_pressed should be False (edge detection)
    env.step(ACTION_JUMP)
    assert env._prev_jump_held is True

    # Frame 3: release (noop)
    env.step(ACTION_NOOP)
    assert env._prev_jump_held is False

    # Frame 4: jump again — jump_pressed should be True again
    env.step(ACTION_JUMP)
    assert env._prev_jump_held is True


def test_jump_edge_detection_with_directional():
    env = SpeednikEnv()
    env.reset()

    # First frame of right+jump
    env.step(ACTION_RIGHT_JUMP)
    assert env._prev_jump_held is True

    # Held
    env.step(ACTION_RIGHT_JUMP)
    assert env._prev_jump_held is True

    # Release
    env.step(ACTION_RIGHT)
    assert env._prev_jump_held is False


# ---------------------------------------------------------------------------
# Termination: goal reached
# ---------------------------------------------------------------------------

def test_terminated_on_goal_reached():
    env = SpeednikEnv()
    env.reset()

    # Place player very close to goal
    env.sim.goal_x = env.sim.player.physics.x + 1.0
    env.sim.goal_y = env.sim.player.physics.y

    # Step until goal is reached or give up after 60 frames
    terminated = False
    for _ in range(60):
        _, _, terminated, _, info = env.step(ACTION_RIGHT)
        if terminated:
            break

    assert terminated, "Should terminate when goal is reached"
    assert info["goal_reached"] is True


# ---------------------------------------------------------------------------
# Termination: player dead
# ---------------------------------------------------------------------------

def test_terminated_on_player_dead():
    env = SpeednikEnv()
    env.reset()

    # Force player into DEAD state
    env.sim.player.state = PlayerState.DEAD

    _, _, terminated, _, _ = env.step(ACTION_NOOP)
    assert terminated is True


# ---------------------------------------------------------------------------
# Truncation: max_steps
# ---------------------------------------------------------------------------

def test_truncated_on_max_steps():
    env = SpeednikEnv(max_steps=10)
    env.reset()

    truncated = False
    for i in range(10):
        _, _, _, truncated, _ = env.step(ACTION_NOOP)

    assert truncated is True


def test_not_truncated_before_max_steps():
    env = SpeednikEnv(max_steps=10)
    env.reset()

    for _ in range(9):
        _, _, _, truncated, _ = env.step(ACTION_NOOP)

    assert truncated is False


# ---------------------------------------------------------------------------
# Info dict
# ---------------------------------------------------------------------------

def test_info_values_after_steps():
    env = SpeednikEnv()
    env.reset()

    for _ in range(30):
        env.step(ACTION_RIGHT)

    _, _, _, _, info = env.step(ACTION_RIGHT)

    assert isinstance(info["frame"], int)
    assert isinstance(info["x"], float)
    assert isinstance(info["y"], float)
    assert isinstance(info["max_x"], float)
    assert isinstance(info["rings"], int)
    assert isinstance(info["deaths"], int)
    assert isinstance(info["goal_reached"], bool)

    assert info["frame"] == 31
    assert info["max_x"] >= info["x"]


# ---------------------------------------------------------------------------
# Multiple episodes
# ---------------------------------------------------------------------------

def test_multiple_reset_step_cycles():
    env = SpeednikEnv()

    for _ in range(3):
        obs, info = env.reset()
        assert obs.shape == (OBS_DIM,)
        assert info["frame"] == 0

        for _ in range(30):
            obs, reward, terminated, truncated, info = env.step(ACTION_RIGHT)

        assert info["frame"] == 30


def test_reset_clears_state():
    env = SpeednikEnv()
    env.reset()

    # Step many times
    for _ in range(100):
        env.step(ACTION_RIGHT)

    _, info_before = env.reset()
    assert info_before["frame"] == 0
    assert env._step_count == 0
    assert env._prev_jump_held is False


# ---------------------------------------------------------------------------
# Gymnasium env_checker
# ---------------------------------------------------------------------------

def test_gymnasium_env_checker():
    from gymnasium.utils.env_checker import check_env

    env = SpeednikEnv()
    check_env(env.unwrapped)


# ---------------------------------------------------------------------------
# Stage parameter
# ---------------------------------------------------------------------------

def test_stage_parameter():
    for stage in ["hillside", "pipeworks", "skybridge"]:
        env = SpeednikEnv(stage=stage)
        obs, info = env.reset()
        assert obs.shape == (OBS_DIM,)
        # Take a step to make sure it runs
        obs, _, _, _, _ = env.step(ACTION_NOOP)
        assert obs.shape == (OBS_DIM,)


# ---------------------------------------------------------------------------
# Reward placeholder
# ---------------------------------------------------------------------------

def test_reward_is_zero_placeholder():
    env = SpeednikEnv()
    env.reset()
    _, reward, _, _, _ = env.step(ACTION_RIGHT)
    assert reward == 0.0


# ---------------------------------------------------------------------------
# No Pyxel imports
# ---------------------------------------------------------------------------

def test_no_pyxel_import_env():
    import speednik.env as mod

    source = Path(inspect.getfile(mod)).read_text()
    assert "import pyxel" not in source
    assert "from pyxel" not in source

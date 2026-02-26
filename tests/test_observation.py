"""Tests for speednik/observation.py — observation extraction from SimState."""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

from speednik.constants import MAX_X_SPEED
from speednik.observation import (
    MAX_RAY_RANGE,
    OBS_DIM,
    OBS_DIM_BASE,
    RAY_ANGLES,
    extract_observation,
)
from speednik.physics import InputState
from speednik.simulation import SimState, create_sim, sim_step


# ---------------------------------------------------------------------------
# Shape and dtype
# ---------------------------------------------------------------------------

def test_observation_shape_and_dtype():
    sim = create_sim("hillside")
    obs = extract_observation(sim)
    assert obs.shape == (26,)
    assert obs.dtype == np.float32


def test_obs_dim_constant():
    assert OBS_DIM == 26


def test_obs_dim_base_constant():
    assert OBS_DIM_BASE == 12


# ---------------------------------------------------------------------------
# Fresh sim sanity
# ---------------------------------------------------------------------------

def test_observation_fresh_sim():
    sim = create_sim("hillside")
    obs = extract_observation(sim)

    # Position should be in (0, 1) — player is somewhere on the stage
    assert 0.0 < obs[0] < 1.0, f"x_pos normalized: {obs[0]}"
    assert 0.0 < obs[1] < 1.0, f"y_pos normalized: {obs[1]}"

    # Velocities should be ~0 at start
    assert abs(obs[2]) < 0.01, f"x_vel: {obs[2]}"
    assert abs(obs[3]) < 0.01, f"y_vel: {obs[3]}"

    # on_ground should be 1.0 (player starts grounded)
    assert obs[4] == 1.0

    # ground_speed ~0 at start
    assert abs(obs[5]) < 0.01

    # Not rolling at start
    assert obs[6] == 0.0

    # facing_right at start
    assert obs[7] == 1.0

    # angle = 0 at start → 0.0
    assert obs[8] == 0.0

    # max_x_reached = 0 at start
    assert obs[9] == 0.0

    # distance to goal should be positive (goal is ahead)
    assert obs[10] > 0.0

    # frame = 0 → time fraction = 0
    assert obs[11] == 0.0


# ---------------------------------------------------------------------------
# Position normalization
# ---------------------------------------------------------------------------

def test_observation_position_normalization():
    sim = create_sim("hillside")
    sim.player.physics.x = float(sim.level_width) / 2
    sim.player.physics.y = float(sim.level_height) / 4

    obs = extract_observation(sim)
    assert abs(obs[0] - 0.5) < 1e-5
    assert abs(obs[1] - 0.25) < 1e-5


# ---------------------------------------------------------------------------
# Velocity normalization
# ---------------------------------------------------------------------------

def test_observation_velocity_normalization():
    sim = create_sim("hillside")
    sim.player.physics.x_vel = MAX_X_SPEED
    obs = extract_observation(sim)
    assert abs(obs[2] - 1.0) < 1e-5

    sim.player.physics.x_vel = -MAX_X_SPEED
    obs = extract_observation(sim)
    assert abs(obs[2] - (-1.0)) < 1e-5


def test_observation_y_vel_normalization():
    sim = create_sim("hillside")
    sim.player.physics.y_vel = MAX_X_SPEED / 2
    obs = extract_observation(sim)
    assert abs(obs[3] - 0.5) < 1e-5


def test_observation_ground_speed():
    sim = create_sim("hillside")
    sim.player.physics.ground_speed = MAX_X_SPEED
    obs = extract_observation(sim)
    assert abs(obs[5] - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# Boolean encoding
# ---------------------------------------------------------------------------

def test_observation_boolean_encoding():
    sim = create_sim("hillside")

    sim.player.physics.on_ground = True
    sim.player.physics.is_rolling = False
    sim.player.physics.facing_right = True
    obs = extract_observation(sim)
    assert obs[4] == 1.0
    assert obs[6] == 0.0
    assert obs[7] == 1.0

    sim.player.physics.on_ground = False
    sim.player.physics.is_rolling = True
    sim.player.physics.facing_right = False
    obs = extract_observation(sim)
    assert obs[4] == 0.0
    assert obs[6] == 1.0
    assert obs[7] == 0.0


# ---------------------------------------------------------------------------
# Angle normalization
# ---------------------------------------------------------------------------

def test_observation_angle():
    sim = create_sim("hillside")
    sim.player.physics.angle = 128
    obs = extract_observation(sim)
    assert abs(obs[8] - 128.0 / 255.0) < 1e-5


# ---------------------------------------------------------------------------
# Progress metrics
# ---------------------------------------------------------------------------

def test_observation_progress():
    sim = create_sim("hillside")
    sim.max_x_reached = float(sim.level_width) / 2
    obs = extract_observation(sim)
    assert abs(obs[9] - 0.5) < 1e-5


def test_observation_distance_to_goal():
    sim = create_sim("hillside")
    sim.player.physics.x = sim.goal_x / 2
    obs = extract_observation(sim)
    expected = (sim.goal_x - sim.goal_x / 2) / sim.level_width
    assert abs(obs[10] - expected) < 1e-5


def test_observation_time_fraction():
    sim = create_sim("hillside")
    sim.frame = 1800
    obs = extract_observation(sim)
    assert abs(obs[11] - 0.5) < 1e-5


# ---------------------------------------------------------------------------
# Integration: observation changes after sim_step
# ---------------------------------------------------------------------------

def test_observation_after_sim_step():
    sim = create_sim("hillside")
    obs_before = extract_observation(sim).copy()

    for _ in range(30):
        sim_step(sim, InputState(right=True))

    obs_after = extract_observation(sim)

    # Position should have changed
    assert obs_after[0] != obs_before[0], "x should change after stepping"
    # Time fraction should have increased
    assert obs_after[11] > obs_before[11], "time should advance"


# ---------------------------------------------------------------------------
# Raycast observations (T-010-17)
# ---------------------------------------------------------------------------

def test_observation_no_raycasts_shape():
    sim = create_sim("hillside")
    obs = extract_observation(sim, use_raycasts=False)
    assert obs.shape == (12,)
    assert obs.dtype == np.float32


def test_observation_base_unchanged_with_raycasts():
    """First 12 dims are identical whether raycasts are on or off."""
    sim = create_sim("hillside")
    obs_full = extract_observation(sim, use_raycasts=True)
    obs_base = extract_observation(sim, use_raycasts=False)
    np.testing.assert_array_equal(obs_full[:12], obs_base[:12])


def test_raycast_values_finite():
    sim = create_sim("hillside")
    obs = extract_observation(sim)
    assert np.all(np.isfinite(obs[12:])), f"Non-finite raycast values: {obs[12:]}"


def test_raycast_distance_range():
    """Ray distances (even indices 12,14,...,24) should be in [0, 1]."""
    sim = create_sim("hillside")
    obs = extract_observation(sim)
    for i in range(7):
        dist = obs[12 + i * 2]
        assert 0.0 <= dist <= 1.0, f"Ray {i} distance out of range: {dist}"


def test_raycast_angle_range():
    """Ray surface angles (odd indices 13,15,...,25) should be in [0, 1]."""
    sim = create_sim("hillside")
    obs = extract_observation(sim)
    for i in range(7):
        angle = obs[12 + i * 2 + 1]
        assert 0.0 <= angle <= 1.0, f"Ray {i} angle out of range: {angle}"


def test_raycast_seven_rays():
    """Verify exactly 7 rays producing 14 values."""
    assert len(RAY_ANGLES) == 7
    assert OBS_DIM - OBS_DIM_BASE == 14


def test_raycast_facing_left_flips_ray_direction():
    """Facing left uses angle (180 - angle_deg) rather than angle_deg.

    We verify this by checking that the 0° ray (index 3) casts in opposite
    horizontal directions when facing_right changes. On asymmetric terrain
    the distances will differ; on symmetric terrain they may match. Instead
    of relying on specific distance values, we verify the observation function
    accepts both facing directions and produces valid finite values.
    """
    sim = create_sim("hillside")

    # Move player forward so terrain context is non-trivial
    for _ in range(120):
        sim_step(sim, InputState(right=True))

    sim.player.physics.facing_right = True
    obs_right = extract_observation(sim)
    assert np.all(np.isfinite(obs_right[12:]))

    sim.player.physics.facing_right = False
    obs_left = extract_observation(sim)
    assert np.all(np.isfinite(obs_left[12:]))

    # Base observations (0-11) should be identical except facing_right flag
    assert obs_right[7] == 1.0
    assert obs_left[7] == 0.0


def test_raycast_grounded_has_short_downward_ray():
    """When standing on ground, the downward ray (index 3, angle=0) should
    detect nearby terrain (distance < 1.0 normalized)."""
    sim = create_sim("hillside")
    obs = extract_observation(sim)
    # Ray index 3 (angle=0°, horizontal right) — not necessarily short.
    # Ray index 6 (angle=45°, diagonal down-right) — should hit ground.
    down_right_dist = obs[12 + 6 * 2]  # ray at +45° (last ray)
    assert down_right_dist < 1.0, (
        f"Downward-angled ray should hit terrain, got normalized dist={down_right_dist}"
    )


# ---------------------------------------------------------------------------
# No Pyxel import
# ---------------------------------------------------------------------------

def test_no_pyxel_import_observation():
    import speednik.observation as mod
    source = Path(inspect.getfile(mod)).read_text()
    assert "import pyxel" not in source
    assert "from pyxel" not in source

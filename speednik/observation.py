"""speednik/observation.py — Observation extraction from SimState.

Produces a flat numpy vector for agent consumption. Default is a
26-dimensional vector with 7-ray terrain raycasts (T-010-17).
"""

from __future__ import annotations

import numpy as np

from speednik.constants import MAX_X_SPEED
from speednik.simulation import SimState
from speednik.terrain import cast_terrain_ray

OBS_DIM = 26
OBS_DIM_BASE = 12

RAY_ANGLES = [-45, -30, -15, 0, 15, 30, 45]
MAX_RAY_RANGE = 128.0


def extract_observation(
    sim: SimState, *, use_raycasts: bool = True
) -> np.ndarray:
    """Extract an observation vector from the current simulation state.

    Returns a 26-dim vector by default (with terrain raycasts), or a 12-dim
    vector when use_raycasts=False.

    Layout:
        [0]  x position (normalized by level_width)
        [1]  y position (normalized by level_height)
        [2]  x velocity (normalized by MAX_X_SPEED)
        [3]  y velocity (normalized by MAX_X_SPEED)
        [4]  on_ground flag (0.0 or 1.0)
        [5]  ground speed (normalized by MAX_X_SPEED)
        [6]  is_rolling flag (0.0 or 1.0)
        [7]  facing_right flag (0.0 or 1.0)
        [8]  surface angle (normalized by 255.0)
        [9]  max progress (max_x_reached / level_width)
        [10] distance to goal ((goal_x - x) / level_width)
        [11] time fraction (frame / 3600.0)
        [12-25] terrain raycasts (7 rays × 2: distance, surface_angle)
    """
    p = sim.player.physics
    obs_dim = OBS_DIM if use_raycasts else OBS_DIM_BASE
    obs = np.zeros(obs_dim, dtype=np.float32)

    # Player kinematics (6)
    obs[0] = p.x / sim.level_width
    obs[1] = p.y / sim.level_height
    obs[2] = p.x_vel / MAX_X_SPEED
    obs[3] = p.y_vel / MAX_X_SPEED
    obs[4] = float(p.on_ground)
    obs[5] = p.ground_speed / MAX_X_SPEED

    # Player state (3)
    obs[6] = float(p.is_rolling)
    obs[7] = float(p.facing_right)
    obs[8] = p.angle / 255.0

    # Progress (3)
    obs[9] = sim.max_x_reached / sim.level_width
    obs[10] = (sim.goal_x - p.x) / sim.level_width
    obs[11] = float(sim.frame) / 3600.0

    # Terrain raycasts (7 rays × 2 = 14 values)
    if use_raycasts:
        for i, angle_deg in enumerate(RAY_ANGLES):
            effective_angle = angle_deg if p.facing_right else (180 - angle_deg)
            dist, surf_angle = cast_terrain_ray(
                sim.tile_lookup, p.x, p.y - 8, effective_angle, MAX_RAY_RANGE
            )
            obs[12 + i * 2] = dist / MAX_RAY_RANGE
            obs[12 + i * 2 + 1] = surf_angle / 255.0

    return obs

# T-010-17 Research: full-observation-vector

## Objective

Integrate the directional terrain raycast (from T-010-16) into the observation extraction
function to produce a 26-dimensional observation vector. Update the Gymnasium environment
to match.

## Current State

### observation.py

- `OBS_DIM = 12` — hard-coded constant used by both observation and env modules.
- `extract_observation(sim: SimState) -> np.ndarray` — produces a 12-dim float32 vector.
- Layout: kinematics (0-5), player state (6-8), progress (9-11).
- Imports: `numpy`, `MAX_X_SPEED` from constants, `SimState` from simulation.
- No raycast logic present; was deferred to T-010-16/17 per docstring.

### terrain.py — cast_terrain_ray (T-010-16 output)

- `cast_terrain_ray(tile_lookup, origin_x, origin_y, angle_deg, max_range=128.0)` exists at
  lines 705-727.
- Returns `(distance_to_surface: float, surface_angle_byte: int)`.
- Convention: `0°=right, 90°=down`. Negative angles go upward.
- Step-based raycasting: walks 1-pixel increments up to `int(max_range)` steps.
- Helper `_pixel_is_solid(tile_lookup, px, py)` at lines 685-702.
- Returns `(max_range, 0)` when nothing is hit.

### env.py — SpeednikEnv

- Constructor: `__init__(self, stage, render_mode, max_steps)` — no `use_raycasts` param.
- `observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(OBS_DIM,), dtype=np.float32)`.
- `_get_obs()` calls `extract_observation(self.sim)` directly.
- No conditional observation logic.
- Imports `OBS_DIM` from observation module.

### env_registration.py

- Registers three environments: Hillside-v0, Pipeworks-v0, Skybridge-v0.
- All use `SpeednikEnv` with `kwargs={"stage": ..., "max_steps": ...}`.
- No NoRay variants exist.

### SimState

- `tile_lookup: TileLookup` — available on the sim, needed for raycasting.
- `player.physics` — has `x`, `y`, `facing_right`, all needed for ray origin/direction.

### Existing Tests

- `test_observation.py`: 13 tests. Hardcoded expectations for shape=(12,) and OBS_DIM==12.
- `test_env.py`: ~28 tests. Use `OBS_DIM` for shape assertions. `check_env` tests exist.
  `test_observations_finite_during_random_play` checks np.isfinite — will cover raycast NaN too.
- Tests reference `OBS_DIM` from observation module, so changing the constant propagates.

### Constants

- `MAX_X_SPEED = 16.0` — used for velocity normalization.
- No `MAX_RAY_RANGE` constant exists yet. Ticket specifies 128.0.

### Dependencies

- T-010-16 (directional-terrain-raycast) is complete (phase: done). `cast_terrain_ray`
  is implemented and tested.
- `extract_observation` currently does NOT import anything from terrain.py.

### Ticket spec for raycast indices

- Indices 12-25: 7 rays × 2 values each.
- Ray angles: `[-45, -30, -15, 0, 15, 30, 45]` degrees relative to facing direction.
- Ray origin: `(p.x, p.y - 8)` — player center.
- If facing left: `effective_angle = 180 - angle_deg`.
- Distance normalized by `max_ray_range` (128.0).
- Surface angle normalized by 255.0.

### Backward Compatibility

- Ticket requires `use_raycasts=True` (default) producing 26-dim, `use_raycasts=False`
  producing 12-dim.
- `extract_observation` will need a parameter or two functions.
- NoRay registration variants: `speednik/Hillside-NoRay-v0` etc.

### Files to Touch

1. `speednik/observation.py` — add raycast logic, change OBS_DIM, add use_raycasts param.
2. `speednik/env.py` — add use_raycasts constructor param, pass to observation.
3. `speednik/env_registration.py` — add NoRay variants.
4. `tests/test_observation.py` — update for 26-dim, add raycast-specific tests.
5. `tests/test_env.py` — update for 26-dim, add use_raycasts=False tests, check_env.

### Risk Areas

- Observation shape changes break all tests that assert shape==(12,).
- `check_env` is very strict about observation_space matching actual observations.
- NaN/Inf risk: division by zero if `max_ray_range` is 0 or `sim.level_width` is 0.
  Both are positive constants, so safe.
- Raycast in mid-air returns (128.0, 0) → normalized to (1.0, 0.0). Fine.

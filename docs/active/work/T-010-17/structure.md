# T-010-17 Structure: full-observation-vector

## Files Modified

### 1. speednik/observation.py

**Changes:**
- `OBS_DIM`: 12 → 26.
- Add `OBS_DIM_BASE = 12` constant for backward compat.
- Add `RAY_ANGLES`, `MAX_RAY_RANGE` module-level constants.
- Import `cast_terrain_ray` from `speednik.terrain`.
- `extract_observation(sim, use_raycasts=True)` — add parameter.
  - When `use_raycasts=True`: allocate 26-dim array, fill indices 0-11 as before,
    fill indices 12-25 with raycast data.
  - When `use_raycasts=False`: allocate 12-dim array, fill indices 0-11 only.

**Public interface after change:**
```python
OBS_DIM = 26          # Default observation dimension
OBS_DIM_BASE = 12     # Without raycasts
RAY_ANGLES = [-45, -30, -15, 0, 15, 30, 45]
MAX_RAY_RANGE = 128.0

def extract_observation(sim: SimState, *, use_raycasts: bool = True) -> np.ndarray:
```

### 2. speednik/env.py

**Changes:**
- `__init__` adds `use_raycasts: bool = True` parameter.
- Store `self.use_raycasts = use_raycasts`.
- `observation_space` shape uses `OBS_DIM if use_raycasts else OBS_DIM_BASE`.
- `_get_obs()` passes `use_raycasts=self.use_raycasts` to `extract_observation`.
- Import `OBS_DIM_BASE` from observation module.

### 3. speednik/env_registration.py

**Changes:**
- Add three NoRay registrations:
  - `speednik/Hillside-NoRay-v0` → `use_raycasts=False`
  - `speednik/Pipeworks-NoRay-v0` → `use_raycasts=False`
  - `speednik/Skybridge-NoRay-v0` → `use_raycasts=False`
- Existing registrations unchanged (they inherit `use_raycasts=True` default).

### 4. tests/test_observation.py

**Changes:**
- `test_obs_dim_constant` → assert OBS_DIM == 26.
- `test_observation_shape_and_dtype` → assert shape == (26,).
- All index-level tests (0-11) unchanged — values don't shift.
- Add new tests:
  - `test_obs_dim_base_constant` — assert OBS_DIM_BASE == 12.
  - `test_observation_raycast_shape` — extract with raycasts, verify shape (26,).
  - `test_observation_no_raycasts_shape` — extract without raycasts, verify shape (12,).
  - `test_raycast_values_finite` — all indices 12-25 are finite.
  - `test_raycast_distance_range` — indices 12,14,16,18,20,22,24 in [0, 1].
  - `test_raycast_angle_range` — indices 13,15,17,19,21,23,25 in [0, 1].
  - `test_raycast_facing_left_flips` — set facing_right=False, verify ray distances differ.
  - `test_observation_base_unchanged_with_raycasts` — first 12 dims identical whether
    raycasts on or off.

### 5. tests/test_env.py

**Changes:**
- `test_observation_space_shape` — now expects (26,) since OBS_DIM = 26.
- Shape assertions in step/reset tests unchanged (they use OBS_DIM).
- Add new tests:
  - `test_use_raycasts_false` — SpeednikEnv(use_raycasts=False) has (12,) obs space.
  - `test_check_env_no_raycasts` — check_env passes with use_raycasts=False.
  - `test_observations_finite_1000_steps_full` — 1000 steps with 26-dim, no NaN/Inf.
  - `test_noray_registration` — NoRay variants can be created via gym.make.
  - `test_check_env_noray_registered` — check_env on a NoRay variant.

## Files NOT Modified

- `speednik/terrain.py` — cast_terrain_ray already exists, no changes.
- `speednik/simulation.py` — no changes needed.
- `speednik/constants.py` — ray constants are observation-specific, live in observation.py.

## Module Dependency Graph (relevant edges)

```
observation.py ──imports──> terrain.cast_terrain_ray  (NEW)
observation.py ──imports──> simulation.SimState
observation.py ──imports──> constants.MAX_X_SPEED
env.py ──imports──> observation.OBS_DIM, OBS_DIM_BASE, extract_observation
env_registration.py ──imports──> (none — uses string entry_point)
```

## Ordering

1. observation.py first (core logic, constants).
2. env.py second (depends on new constants/function signature).
3. env_registration.py third (depends on env accepting use_raycasts).
4. Tests last (depend on all production code).

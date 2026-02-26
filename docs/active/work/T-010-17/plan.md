# T-010-17 Plan: full-observation-vector

## Step 1: Update observation.py

1. Change `OBS_DIM = 12` to `OBS_DIM = 26`.
2. Add `OBS_DIM_BASE = 12`.
3. Add `RAY_ANGLES = [-45, -30, -15, 0, 15, 30, 45]`.
4. Add `MAX_RAY_RANGE = 128.0`.
5. Add import: `from speednik.terrain import cast_terrain_ray`.
6. Update `extract_observation` signature: add `*, use_raycasts: bool = True`.
7. Inside function:
   - Compute `obs_dim = OBS_DIM if use_raycasts else OBS_DIM_BASE`.
   - Allocate `np.zeros(obs_dim, ...)`.
   - Keep indices 0-11 unchanged.
   - Add raycast block for indices 12-25 when `use_raycasts=True`.
8. Update docstring.

**Verify:** `uv run python -c "from speednik.observation import extract_observation, OBS_DIM; print(OBS_DIM)"` → 26.

## Step 2: Update env.py

1. Add `OBS_DIM_BASE` to imports from observation.
2. Add `use_raycasts: bool = True` to `__init__` parameters.
3. Store `self.use_raycasts = use_raycasts`.
4. Compute obs_dim: `OBS_DIM if use_raycasts else OBS_DIM_BASE`.
5. Use `obs_dim` in `observation_space` shape.
6. Update `_get_obs` to pass `use_raycasts=self.use_raycasts`.

**Verify:** Instantiate env both ways, check observation_space.shape.

## Step 3: Update env_registration.py

1. Add NoRay variants for all three stages.
2. Each passes `use_raycasts=False` in kwargs.

**Verify:** `uv run python -c "import speednik.env_registration; import gymnasium; env = gymnasium.make('speednik/Hillside-NoRay-v0'); print(env.observation_space.shape)"` → (12,).

## Step 4: Update test_observation.py

1. Update `test_obs_dim_constant` to assert 26.
2. Update `test_observation_shape_and_dtype` to assert (26,).
3. Add `test_obs_dim_base_constant`.
4. Add `test_observation_no_raycasts_shape`.
5. Add `test_raycast_values_finite`.
6. Add `test_raycast_distance_range`.
7. Add `test_raycast_angle_range`.
8. Add `test_raycast_facing_left_flips`.
9. Add `test_observation_base_unchanged_with_raycasts`.

## Step 5: Update test_env.py

1. Add `test_use_raycasts_false`.
2. Add `test_check_env_no_raycasts`.
3. Add `test_observations_finite_1000_steps_full` (1000-step random play, 26-dim).
4. Add `test_noray_registration`.
5. Add `test_check_env_noray_registered`.

## Step 6: Run full test suite

`uv run pytest tests/ -x`

All tests must pass. Fix any failures.

## Step 7: Validation checks

1. Verify no NaN/Inf in 1000-step random play (covered by test).
2. Verify check_env passes for both 26-dim and 12-dim (covered by test).
3. Verify no Pyxel imports in modified files.

## Testing Strategy

- **Unit tests (observation.py):** Shape, dtype, value ranges, facing direction flip,
  backward compat with use_raycasts=False.
- **Integration tests (env.py):** check_env, random play finite, NoRay variant, space
  shapes.
- **Regression:** All existing tests pass with new defaults (OBS_DIM=26).

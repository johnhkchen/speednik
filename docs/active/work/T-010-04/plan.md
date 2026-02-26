# T-010-04 Plan: Agent Protocol and Observation Extraction

## Step 1: Add numpy dependency

**Action**: Add `numpy` to `pyproject.toml` dependencies, run `uv sync`.

**Verify**: `uv run python -c "import numpy; print(numpy.__version__)"` succeeds.

## Step 2: Create `speednik/agents/` package with Agent protocol

**Files**: `speednik/agents/__init__.py`, `speednik/agents/base.py`

**Action**:
- Create `base.py` with `@runtime_checkable` `Agent` Protocol (act + reset)
- Create `__init__.py` (initially just re-export Agent)

**Verify**: `uv run python -c "from speednik.agents import Agent; print(Agent)"` works.

## Step 3: Create action constants and `action_to_input`

**File**: `speednik/agents/actions.py`

**Action**:
- Define 8 action constants (ACTION_NOOP through ACTION_DOWN_JUMP)
- Define NUM_ACTIONS = 8
- Define ACTION_MAP dict mapping each action int to an InputState template
- Implement `action_to_input(action, prev_jump_held) -> (InputState, bool)`

**Verify**: Quick import check.

## Step 4: Update `__init__.py` re-exports

**Action**: Add action constants and `action_to_input` to `__init__.py` re-exports.

## Step 5: Create `speednik/observation.py`

**File**: `speednik/observation.py`

**Action**:
- Define `OBS_DIM = 12`
- Implement `extract_observation(sim: SimState) -> np.ndarray`
- Follow the exact layout from the ticket: 6 kinematics + 3 state + 3 progress

**Verify**: Quick import and shape check.

## Step 6: Write `tests/test_agents.py`

**Tests**:
1. `test_agent_protocol_conformance` — minimal class passes isinstance
2. `test_agent_protocol_rejects_incomplete` — missing method fails isinstance
3. `test_action_constants_range` — 8 actions, values 0-7
4. `test_action_map_completeness` — all 8 entries, all InputState
5. `test_action_map_noop` — NOOP has all fields False
6. `test_action_map_directional` — LEFT/RIGHT/DOWN set correct flags
7. `test_action_map_jump_actions` — JUMP/LEFT_JUMP/RIGHT_JUMP/DOWN_JUMP
   have jump_pressed=True and jump_held=True in template
8. `test_action_to_input_noop` — returns all-False, prev=False
9. `test_action_to_input_jump_first_frame` — jump_pressed=True on first frame
10. `test_action_to_input_jump_held_frame` — jump_pressed=False on second frame
11. `test_action_to_input_jump_release` — noop after jump resets prev
12. `test_action_to_input_directional_jump` — LEFT_JUMP combines correctly
13. `test_num_actions_matches_map` — NUM_ACTIONS == len(ACTION_MAP)
14. `test_no_pyxel_import_base` — source check on base.py
15. `test_no_pyxel_import_actions` — source check on actions.py

## Step 7: Write `tests/test_observation.py`

**Tests**:
1. `test_observation_shape_and_dtype` — 12 elements, float32
2. `test_observation_fresh_sim` — reasonable initial values
3. `test_observation_position_normalization` — known position maps correctly
4. `test_observation_velocity_normalization` — x_vel = MAX_X_SPEED -> 1.0
5. `test_observation_y_vel_normalization` — y_vel normalized by MAX_X_SPEED
6. `test_observation_boolean_encoding` — on_ground, is_rolling, facing_right
7. `test_observation_angle` — angle=128 -> ~0.502
8. `test_observation_progress` — max_x_reached mapping
9. `test_observation_distance_to_goal` — (goal_x - x) / level_width
10. `test_observation_time_fraction` — frame=1800 -> 0.5
11. `test_observation_after_sim_step` — obs changes after stepping
12. `test_no_pyxel_import_observation` — source check
13. `test_obs_dim_constant` — OBS_DIM == 12

## Step 8: Run full test suite

**Action**: `uv run pytest tests/ -x`

**Verify**: All tests pass including existing 830+ tests and new tests.

## Commit Strategy

Single commit after all tests pass:
- `speednik/agents/__init__.py` (new)
- `speednik/agents/base.py` (new)
- `speednik/agents/actions.py` (new)
- `speednik/observation.py` (new)
- `tests/test_agents.py` (new)
- `tests/test_observation.py` (new)
- `pyproject.toml` (modified — numpy dep)

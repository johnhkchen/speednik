# T-010-04 Progress: Agent Protocol and Observation Extraction

## Completed Steps

### Step 1: Add numpy dependency
- Added `numpy` to `pyproject.toml` dependencies
- `uv sync` installed numpy 2.4.2
- Verified: `import numpy` works

### Step 2: Create agents package with Agent protocol
- Created `speednik/agents/base.py` with `@runtime_checkable` Agent Protocol
- Protocol has `act(obs: np.ndarray) -> int` and `reset() -> None`

### Step 3: Create action constants and action_to_input
- Created `speednik/agents/actions.py`
- 8 action constants (ACTION_NOOP=0 through ACTION_DOWN_JUMP=7)
- ACTION_MAP maps each to InputState template
- `action_to_input(action, prev_jump_held)` handles jump edge detection

### Step 4: Update __init__.py re-exports
- Created `speednik/agents/__init__.py` re-exporting all public API

### Step 5: Create observation extraction
- Created `speednik/observation.py` with OBS_DIM=12 and extract_observation()
- 12-dim float32 vector: 6 kinematics + 3 state + 3 progress
- All values normalized to roughly [-1, 1]

### Step 6: Write agent tests
- Created `tests/test_agents.py` with 16 tests
- Protocol conformance and rejection
- Action constants, ACTION_MAP completeness and correctness
- action_to_input edge detection across frames
- No-Pyxel-import checks

### Step 7: Write observation tests
- Created `tests/test_observation.py` with 14 tests
- Shape, dtype, fresh sim sanity
- Position, velocity, boolean, angle normalization
- Progress metrics, distance to goal, time fraction
- Integration test with sim_step
- No-Pyxel-import check

### Step 8: Full test suite
- `uv run pytest tests/ -x` → 870 passed, 5 xfailed in 1.88s
- All existing tests still pass (no regressions)
- All 30 new tests pass

## Deviations from Plan

None. Implementation followed the plan exactly.

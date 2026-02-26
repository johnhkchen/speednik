# T-010-04 Review: Agent Protocol and Observation Extraction

## Summary of Changes

### Files Created (4 source + 2 test)

| File | Lines | Purpose |
|------|-------|---------|
| `speednik/agents/__init__.py` | 30 | Package init, re-exports public API |
| `speednik/agents/base.py` | 24 | `Agent` protocol (`@runtime_checkable`) |
| `speednik/agents/actions.py` | 59 | Action constants, ACTION_MAP, action_to_input |
| `speednik/observation.py` | 53 | `extract_observation()` → 12-dim float32 vector |
| `tests/test_agents.py` | 153 | 16 tests for protocol and action space |
| `tests/test_observation.py` | 158 | 14 tests for observation extraction |

### Files Modified (1)

| File | Change |
|------|--------|
| `pyproject.toml` | Added `numpy` to dependencies |

## Acceptance Criteria Evaluation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Agent protocol with `act(obs) → int` and `reset()` | PASS | `speednik/agents/base.py:15-22` |
| `@runtime_checkable` so `isinstance` works | PASS | `test_agent_protocol_conformance` passes |
| 8 discrete actions with ACTION_MAP to InputState | PASS | `test_action_map_completeness`, `test_action_constants_range` |
| `action_to_input` handles jump_pressed edge detection | PASS | `test_action_to_input_jump_first_frame`, `_held_frame`, `_release` |
| `extract_observation` returns 12-dim numpy float32 | PASS | `test_observation_shape_and_dtype` |
| Observation values normalized to ~[-1, 1] | PASS | `test_observation_fresh_sim`, position/velocity/angle tests |
| No Pyxel imports | PASS | `test_no_pyxel_import_base`, `_actions`, `_observation` |
| `uv run pytest tests/ -x` passes | PASS | 870 passed, 5 xfailed in 1.88s |

All 8 acceptance criteria pass.

## Test Coverage

### Agent tests (16 tests)

- Protocol conformance (isinstance pass/fail): 2 tests
- Action constants (range, NUM_ACTIONS): 2 tests
- ACTION_MAP (completeness, NOOP, directional, jump actions): 4 tests
- action_to_input (noop, first jump, held, release, combos, right): 6 tests
- No-Pyxel-import: 2 tests

### Observation tests (14 tests)

- Shape/dtype/OBS_DIM constant: 2 tests
- Fresh sim sanity (all 12 elements): 1 test
- Position normalization: 1 test
- Velocity normalization (x_vel, y_vel, ground_speed): 3 tests
- Boolean encoding: 1 test
- Angle normalization: 1 test
- Progress metrics (max progress, distance, time): 3 tests
- Integration with sim_step: 1 test
- No-Pyxel-import: 1 test

### Coverage Gaps

1. **No negative-position test**: observation doesn't guard against player x < 0.
   Not an issue in practice (collision prevents it), but obs[0] could go negative.
2. **No boundary test for obs[11]**: time fraction exceeds 1.0 after frame 3600.
   This is by design — CleanRL normalizes observations — but it's not explicitly
   tested.
3. **action_to_input with invalid action int**: no test for KeyError on action=99.
   The function will raise KeyError from ACTION_MAP lookup, which is fine behavior
   but undocumented.

## Open Concerns

1. **numpy as a main dependency**: numpy is now a runtime dependency (not dev-only).
   This is correct for the scenario testing path, but it means `uv sync` pulls
   numpy even for users who just want to play the game. Consider moving to an
   optional dependency group (e.g., `[project.optional-dependencies] ml = ["numpy"]`)
   when the dependency set grows (gymnasium, torch, etc.). For now the overhead is
   minimal and the simplicity is worth it.

2. **obs[3] y_vel normalization**: y_vel is divided by MAX_X_SPEED (16.0), but
   y_vel can exceed this during fast falls (gravity accumulates). The observation
   value can go outside [-1, 1]. This matches the spec exactly and is acceptable
   because CleanRL's NormalizeObservation wrapper handles it, but downstream
   consumers should be aware.

3. **obs[11] time constant**: The hardcoded 3600.0 divisor assumes a 60-second
   episode at 60 FPS. Future tickets (env wrapper) may use different max_steps
   values. The extract_observation function doesn't know the episode length. This
   is a known simplification — the ticket explicitly uses 3600.0 and defers
   episode-aware time to the env wrapper.

4. **T-010-02 dependency**: This ticket's code depends only on SimState and
   create_sim (from T-010-01), not on sim_step. However, the integration test
   (`test_observation_after_sim_step`) imports sim_step from T-010-02. Both T-010-01
   and T-010-02 are phase:done, so this is safe.

## Architecture Notes

The module layering is clean:
- `agents/base.py` depends only on numpy (Layer 3 protocol)
- `agents/actions.py` depends only on `physics.InputState` (Layer 1 → Layer 3)
- `observation.py` depends on `simulation.SimState` + `constants` (Layer 2 → bridge)
- No circular dependencies, no upward layer violations

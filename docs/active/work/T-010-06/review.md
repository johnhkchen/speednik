# T-010-06 Review: SpeednikEnv Core

## Summary

Implemented `SpeednikEnv`, the Gymnasium environment wrapper (Layer 5) that bridges
the headless simulation with RL training. The env is a thin adapter delegating to
existing simulation, observation, and action modules.

## Files Created

- **`speednik/env.py`** (83 lines) — `SpeednikEnv(gym.Env)` with `__init__`, `reset`,
  `step`, `_action_to_input`, `_get_obs`, `_compute_reward`, `_get_info`.
- **`tests/test_env.py`** (228 lines) — 26 tests covering all acceptance criteria.
- **`docs/active/work/T-010-06/`** — RDSPI artifacts (research, design, structure, plan,
  progress).

## Files Modified

- **`pyproject.toml`** — Added `gymnasium` to dependencies.
- **`uv.lock`** — Updated with gymnasium 1.2.3 + transitive deps.

## Acceptance Criteria Verification

| Criterion | Status | Test(s) |
|---|---|---|
| Subclasses gym.Env | Pass | test_gymnasium_env_checker |
| __init__ accepts stage, render_mode, max_steps | Pass | test_stage_parameter |
| reset() creates fresh sim, returns (obs, info) | Pass | test_reset_returns_obs_info, test_reset_initializes_sim |
| step() advances sim, returns 5-tuple | Pass | test_step_returns_5_tuple, test_step_advances_frame |
| _action_to_input maps 8 actions | Pass | test_jump_pressed_first_frame_only |
| jump_pressed edge detection | Pass | test_jump_pressed_first_frame_only, test_jump_edge_detection_with_directional |
| terminated on goal/death | Pass | test_terminated_on_goal_reached, test_terminated_on_player_dead |
| truncated on max_steps | Pass | test_truncated_on_max_steps, test_not_truncated_before_max_steps |
| _get_info returns all fields | Pass | test_reset_info_keys, test_info_values_after_steps |
| Multiple reset/step cycles | Pass | test_multiple_reset_step_cycles, test_reset_clears_state |
| No Pyxel imports | Pass | test_no_pyxel_import_env |
| pytest passes | Pass | 930 passed, 5 xfailed, 0 failures |

## Test Coverage

26 tests in `tests/test_env.py`:

- **Spaces (2):** observation_space shape/dtype, action_space.n
- **Reset (5):** return type, obs shape, sim init, info keys, seed determinism
- **Step (6):** return type, obs shape, reward type, bool types, frame advance, movement
- **Jump edge detection (2):** first-frame-only press, directional jump
- **Termination (2):** goal reached, player dead
- **Truncation (2):** at max_steps, before max_steps
- **Info (1):** types and values after steps
- **Multiple episodes (2):** reset/step cycles, state clearing
- **Gymnasium compliance (1):** check_env passes
- **Stages (1):** all three stages work
- **Reward (1):** placeholder returns 0.0
- **No Pyxel (1):** source-level check

## Design Decisions

1. **Delegation over duplication:** `_action_to_input` delegates to the existing
   `action_to_input()` function rather than reimplementing edge detection. Same for
   `_get_obs` → `extract_observation()`. Keeps env.py focused on Gymnasium lifecycle.

2. **Inf observation bounds:** Matches the spec. Velocities can exceed normalized range
   (spring launches). Gymnasium warns but this is standard practice.

3. **Reward placeholder:** Returns 0.0. T-010-07 will implement the real reward signal
   including delta-max-x, speed bonus, goal completion, death penalty, and ring collection.

## Open Concerns

1. **Gymnasium registration** — `gym.register()` calls for Hillside-v0/Pipeworks-v0/
   Skybridge-v0 are not in this ticket. The spec §3.4 defines them. Likely a separate
   ticket or part of the CleanRL entry point (Layer 6).

2. **Reward signal is zero** — Training cannot begin until T-010-07 implements
   `_compute_reward`. This is expected and by design (placeholder).

3. **Rendering not implemented** — `render_mode` is accepted but rendering is not
   implemented. The env is headless-only for now. The env_checker warns about this.

4. **Observation bounds warning** — Gymnasium's `check_env` warns about -inf/inf bounds.
   This is a known tradeoff: tighter bounds would clip spring launches and other transient
   states. The spec explicitly uses inf bounds.

## No Known Bugs or Regressions

Full test suite: 930 passed, 5 xfailed, 0 failures. All pre-existing tests unaffected.

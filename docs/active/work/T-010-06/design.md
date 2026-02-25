# T-010-06 Design: SpeednikEnv Core

## Decision: Direct Delegation to Existing Modules

### Approach A: Inline All Logic (rejected)

Copy observation extraction, action mapping, and reward logic directly into SpeednikEnv
methods. Pro: self-contained. Con: duplicates tested code from `observation.py` and
`actions.py`, violates DRY, divergence risk.

### Approach B: Delegate to Existing Modules (chosen)

SpeednikEnv is a thin adapter that wires together existing building blocks:

- `_get_obs()` calls `extract_observation(self.sim)` from `observation.py`.
- `_action_to_input()` calls `action_to_input(action, self._prev_jump_held)` from
  `agents/actions.py` and stores the returned prev_jump_held.
- `_compute_reward()` returns 0.0 placeholder (T-010-07 scope).

**Rationale:** The observation and action modules are already tested independently.
Delegating keeps SpeednikEnv focused on the Gymnasium contract (space definitions,
reset/step lifecycle, termination logic) rather than reimplementing internals.

### Approach C: Separate Env Shell + Reward Module (rejected)

Split reward into a pluggable strategy object. Premature — ticket says placeholder.
T-010-07 can refactor if needed.

## Jump Edge Detection Strategy

The ticket spec shows `_action_to_input` using `base.jump_pressed` to detect jump intent,
but `action_to_input()` in `actions.py` already handles this correctly using `base.jump_held`.
Both approaches are functionally equivalent for detecting the template's jump intent.

**Decision:** Delegate to `action_to_input(action, self._prev_jump_held)` from actions.py.
This function already implements the edge detection correctly and is tested. The env stores
the returned `prev_jump_held` on `self._prev_jump_held`.

## Observation Space Bounds

The spec uses `Box(low=-np.inf, high=np.inf, shape=(OBS_DIM,), dtype=np.float32)`.
While observations are mostly in [-1, 1] after normalization, velocities can exceed
MAX_X_SPEED (e.g., spring launches), and time fraction grows unbounded. Using inf bounds
is correct and standard for continuous observation spaces.

## Termination vs Truncation

Following Gymnasium v1.0 semantics:

- **terminated** = episode ended due to game state (goal reached OR player dead).
- **truncated** = episode ended due to time limit (step_count >= max_steps).

These are not mutually exclusive in the return, but in practice `terminated` is checked
first in `step()`, so if the player dies on the exact frame of max_steps, both would be
True. This is valid Gymnasium behavior.

## Render Mode

Accept `render_mode` parameter for forward compatibility but do not implement rendering.
This ticket is headless only. Rendering is out of scope.

## Error Handling

- Calling `step()` before `reset()` would access `self.sim = None`. The spec doesn't
  require a guard — this is standard Gymnasium behavior (user error). We won't add a guard
  to keep the code simple.

## Test Strategy

- **Gymnasium compliance:** Use `gymnasium.utils.env_checker.check_env` for API validation.
- **Observation correctness:** Verify shape, dtype, matches `extract_observation` output.
- **Action mapping correctness:** Test jump edge detection through the env interface.
- **Termination conditions:** Test goal_reached, player_dead, and max_steps truncation.
- **Info dict:** Verify all keys present and values sensible.
- **Multiple reset/step cycles:** Ensure state isolation between episodes.
- **No Pyxel imports:** Source-level assertion.

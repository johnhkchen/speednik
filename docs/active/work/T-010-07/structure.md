# T-010-07 Structure: Reward Signal and Observation Space

## Files modified

### `speednik/env.py` (modify)

Changes:
1. **Add imports**: `RingCollectedEvent` from `speednik.simulation`, `MAX_X_SPEED` from
   `speednik.constants`.
2. **Add `_prev_max_x` instance variable**: Initialized to 0.0 in `__init__`, reset to 0.0
   in `reset()`.
3. **Update `step()` method**: Save `sim.max_x_reached` to `_prev_max_x` before calling
   `sim_step`. Pass `_prev_max_x` to `_compute_reward` (or access as `self._prev_max_x`).
4. **Replace `_compute_reward(events)`**: Remove placeholder, implement full reward signal
   with 6 components (progress, speed, goal, death, rings, time).

No new public interface — `_compute_reward` remains a private method with same signature.

### `tests/test_env.py` (modify)

Changes:
1. **Remove `test_reward_is_zero_placeholder`** — no longer valid.
2. **Add new imports**: `ACTION_NOOP`, `ACTION_RIGHT` (already imported), `PlayerState`
   (already imported).
3. **Add reward behavioral tests**:
   - `test_reward_idle_negative_total` — 100 NOOP frames → negative sum
   - `test_reward_hold_right_positive_total` — 100 RIGHT frames → positive sum
   - `test_reward_goal_spike` — place near goal, step → single reward > 10.0
   - `test_reward_death_penalty` — force DEAD state → reward includes -5.0
   - `test_reward_ring_collection` — verify ring bonus in reward

## Files NOT modified

- `speednik/observation.py` — Already complete. OBS_DIM=12, extract_observation works.
- `speednik/simulation.py` — No changes. Event types already exported.
- `speednik/constants.py` — MAX_X_SPEED already exists.
- `tests/test_observation.py` — No changes needed.

## Interface contracts

### `_compute_reward(events: list) -> float`

Input: list of Event objects from sim_step for the current frame.
Internal access: `self.sim` (post-step state), `self._prev_max_x` (pre-step max),
`self._step_count`, `self.max_steps`.
Output: float reward value.

### State flow per step

```
step(action):
    prev_max_x = sim.max_x_reached          # save BEFORE sim_step
    events = sim_step(sim, inp)              # sim_step updates max_x_reached
    _step_count += 1
    obs = _get_obs()
    reward = _compute_reward(events)         # uses self._prev_max_x for delta
    ...
```

## Ordering constraints

1. `_prev_max_x` must be saved before `sim_step` runs (sim_step updates max_x_reached).
2. `_compute_reward` must run after `sim_step` (needs post-step state and events).
3. Observation extraction after sim_step (already correct).

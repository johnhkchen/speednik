# T-010-07 Plan: Reward Signal and Observation Space

## Step 1: Add imports and `_prev_max_x` to env.py

**File**: `speednik/env.py`

- Add `RingCollectedEvent` to the import from `speednik.simulation`.
- Add `from speednik.constants import MAX_X_SPEED`.
- Add `self._prev_max_x = 0.0` in `__init__`.
- Add `self._prev_max_x = 0.0` in `reset()`.

**Verify**: File parses, existing tests still pass (reward placeholder test may need updating
concurrently — defer to Step 3).

## Step 2: Update `step()` to capture pre-step max_x

**File**: `speednik/env.py`

Modify `step()`:
```python
def step(self, action):
    inp = self._action_to_input(action)
    self._prev_max_x = self.sim.max_x_reached   # NEW: save before sim_step
    events = sim_step(self.sim, inp)
    self._step_count += 1
    ...
```

**Verify**: Step still returns correct 5-tuple. No behavior change yet (reward still 0.0).

## Step 3: Implement `_compute_reward`

**File**: `speednik/env.py`

Replace the placeholder with:
```python
def _compute_reward(self, events: list) -> float:
    reward = 0.0
    sim = self.sim
    p = sim.player.physics

    # Primary: delta max(x) — rightward progress into new territory
    progress_delta = (sim.max_x_reached - self._prev_max_x) / sim.level_width
    reward += progress_delta * 10.0

    # Speed bonus: reward maintaining high horizontal speed
    reward += abs(p.x_vel) / MAX_X_SPEED * 0.01

    # Goal completion: large bonus scaled by remaining time
    if sim.goal_reached:
        time_bonus = max(0.0, 1.0 - self._step_count / self.max_steps)
        reward += 10.0 + 5.0 * time_bonus

    # Death penalty
    if sim.player_dead:
        reward -= 5.0

    # Ring collection: small bonus per ring
    for e in events:
        if isinstance(e, RingCollectedEvent):
            reward += 0.1

    # Time penalty: small per-frame cost to discourage stalling
    reward -= 0.001

    return reward
```

Note: `sim.max_x_reached` is already updated by `sim_step`, and `self._prev_max_x` was
saved before `sim_step`. So `sim.max_x_reached - self._prev_max_x` gives the correct
delta for this frame.

**Verify**: `uv run python -c "from speednik.env import SpeednikEnv"` succeeds.

## Step 4: Update tests

**File**: `tests/test_env.py`

1. **Remove** `test_reward_is_zero_placeholder`.
2. **Add** the following tests:

### test_reward_idle_negative_total
- Create env, reset, step 100 frames with ACTION_NOOP.
- Sum all rewards.
- Assert total < 0 (time penalty dominates idle agent).

### test_reward_hold_right_positive_total
- Create env, reset, step 100 frames with ACTION_RIGHT.
- Sum all rewards.
- Assert total > 0 (progress reward dominates).

### test_reward_goal_spike
- Create env, reset, place player near goal (goal_x - 1, goal_y).
- Step with ACTION_RIGHT until goal_reached.
- Assert the goal-frame reward > 10.0.

### test_reward_death_penalty
- Create env, reset, force `sim.player.state = PlayerState.DEAD`.
- Step once.
- Assert reward < -4.0 (death penalty -5.0, time penalty -0.001, small speed bonus).

### test_reward_ring_collection
- Create env, reset, place a ring near the player.
- Step until ring collected (check events via info or reward delta).
- Assert that reward on collection frame is higher than adjacent frames by ~0.1.

**Verify**: `uv run pytest tests/test_env.py -x` all pass.

## Step 5: Run full test suite

- `uv run pytest tests/ -x`
- Verify no regressions in test_simulation, test_observation, test_agents, test_env.

## Step 6: Verify acceptance criteria

Walk through each AC item:
- [ ] _compute_reward implements delta_max(x)
- [ ] Speed bonus
- [ ] Goal completion bonus
- [ ] Death penalty
- [ ] Ring collection bonus
- [ ] Time penalty
- [ ] _get_obs() returns correct shape (already passing)
- [ ] Observation normalized (already passing)
- [ ] Idle agent negative reward test
- [ ] Hold-right agent positive reward test
- [ ] Goal spike > 10.0 test
- [ ] No Pyxel imports
- [ ] Full test suite passes

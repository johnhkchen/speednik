# T-010-07 Progress: Reward Signal and Observation Space

## Completed

### Step 1: Add imports and `_prev_max_x` to env.py
- Added `RingCollectedEvent` import from `speednik.simulation`.
- Added `MAX_X_SPEED` import from `speednik.constants`.
- Added `self._prev_max_x = 0.0` in `__init__`.

### Step 2: Update `step()` to capture pre-step max_x
- Added `self._prev_max_x = self.sim.max_x_reached` before `sim_step()` call.

### Step 3: Implement `_compute_reward`
- Replaced placeholder with full reward signal: progress, speed, goal, death, rings, time.
- All 6 components from the ticket spec implemented verbatim.

### Step 4: Fix `_prev_max_x` initialization bug
**Deviation from plan**: `sim.max_x_reached` defaults to 0.0 in `create_sim`, but the
player starts at x=64 (hillside). On the first frame, `sim_step` updates max_x_reached
from 0→64, producing a spurious progress reward of ~0.13 that made the idle agent test fail.

**Fix**: In `reset()`, set `sim.max_x_reached = player.physics.x` immediately after
`create_sim`, then set `_prev_max_x = sim.max_x_reached`. This ensures the initial
max_x_reached reflects the spawn position, eliminating the first-frame artifact.

### Step 5: Update tests
- Removed `test_reward_is_zero_placeholder`.
- Added 6 new reward tests:
  - `test_reward_idle_negative_total` — 100 NOOP frames → total < 0
  - `test_reward_hold_right_positive_total` — 100 RIGHT frames → total > 0
  - `test_reward_goal_spike` — goal-frame reward > 10.0
  - `test_reward_death_penalty` — death reward < -4.0
  - `test_reward_ring_collection` — ring collected on nearby ring
  - `test_reward_includes_time_penalty` — single NOOP frame < 0

### Step 6: Run full test suite
- `uv run pytest tests/ -x`: 935 passed, 5 xfailed, 3 warnings.
- No regressions.

## Remaining

None — all steps complete.

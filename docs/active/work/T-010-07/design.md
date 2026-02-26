# T-010-07 Design: Reward Signal and Observation Space

## Problem

Implement `_compute_reward(events)` in SpeednikEnv with a reward signal that encourages:
1. Rightward progress into new territory (primary signal)
2. Maintaining horizontal speed
3. Goal completion (large bonus)
4. Ring collection (small bonus)
5. Discouraging stalling and death

## Approach: Track `_prev_max_x` in env

### The delta_max(x) problem

The ticket's reward pseudocode computes `progress_delta = (new_max - old_max) / level_width`.
But `sim.max_x_reached` is updated inside `sim_step` before `_compute_reward` runs.

**Option A: Track `_prev_max_x` on the env.**
Save `sim.max_x_reached` before calling `sim_step`, compare after. Simple, explicit.

**Option B: Move max_x update after reward.**
Would require restructuring `sim_step` or the env's step method. Violates the principle that
sim_step is a self-contained frame advance.

**Option C: Compute delta from player x directly.**
`delta = max(0, p.x - old_max) / level_width`. Equivalent to the ticket formula when
max_x_reached hasn't been updated yet. But requires careful ordering.

**Decision: Option A.** Cleanest — add `_prev_max_x: float` to env, save before step, compute
delta after step. Reset to 0.0 in `reset()`. No changes to simulation.py needed.

### Reward components (from ticket)

All components are directly implementable with available state:

| Component       | Formula                                            | Magnitude |
|-----------------|----------------------------------------------------|-----------|
| Progress        | `(new_max - prev_max) / level_width * 10.0`        | 0–10.0    |
| Speed bonus     | `abs(x_vel) / MAX_X_SPEED * 0.01`                  | 0–0.01    |
| Goal completion | `10.0 + 5.0 * max(0, 1 - step_count/max_steps)`   | 10–15     |
| Death penalty   | `-5.0`                                             | -5.0      |
| Ring collection | `+0.1` per ring                                    | 0.1/ring  |
| Time penalty    | `-0.001`                                           | -0.001    |

### Observation space finalization

**No code changes needed.** Research confirmed:
- `_get_obs()` returns `extract_observation(sim)` which produces a (12,) float32 array.
- `observation_space` is `Box(low=-np.inf, high=np.inf, shape=(12,))`.
- `OBS_DIM = 12` is the single constant to change for T-010-17.
- All observation values are normalized (roughly [-1, 1]).

The observation space is already correctly integrated. Tests in `test_observation.py` and
`test_env.py` confirm shape, dtype, and content.

## Rejected alternatives

**Observation space with bounded Box:** Could set `low=-1, high=1` but some dims (time_fraction,
distance_to_goal) can exceed that range. Infinite bounds with normalized values is the
standard Gymnasium approach and what check_env expects.

**Reward shaping with potential-based functions:** Overkill for this stage. The delta_max(x)
signal is proven for Sonic-style platformers (OpenAI Retro Contest 2018). Keep it simple.

**Separate reward module:** The reward function is 20 lines. Putting it in a separate file
adds indirection for no benefit. Keep it as a method on SpeednikEnv.

## Testing strategy

Replace the placeholder test with behavioral tests:

1. **Idle agent → negative total**: 100 frames of NOOP. Time penalty (-0.001 × 100 = -0.1)
   dominates. Total should be negative.
2. **Hold-right agent → positive total**: 100 frames of ACTION_RIGHT. Progress reward
   dominates time penalty. Total should be positive.
3. **Goal reached → spike > 10.0**: Place player near goal, step until goal_reached.
   Single-frame reward should be > 10.0.
4. **Death → negative spike**: Force PlayerState.DEAD, step once. Reward should be < -5.0
   (includes time penalty).
5. **Ring collection → +0.1**: Check that frames with RingCollectedEvent in events get
   the ring bonus.

## New imports needed in env.py

- `RingCollectedEvent` from `speednik.simulation`
- `MAX_X_SPEED` from `speednik.constants`

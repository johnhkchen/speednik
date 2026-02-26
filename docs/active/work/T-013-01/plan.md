# T-013-01 Plan: World Boundary System

## Step 1: Add PIT_DEATH_MARGIN constant

File: `speednik/constants.py`

Add `PIT_DEATH_MARGIN = 32` after the death-related constants section (~line 110).

Verification: Import check — `from speednik.constants import PIT_DEATH_MARGIN`.

## Step 2: Add kwargs to create_sim_from_lookup

File: `speednik/simulation.py`

Change `create_sim_from_lookup` signature to accept keyword-only `level_width` and
`level_height` with defaults of 99999. Use them in the SimState constructor.

Verification: `uv run pytest tests/test_invariants.py -x` — should fix the TypeError
from make_sim() passing these kwargs.

## Step 3: Add boundary enforcement to sim_step

File: `speednik/simulation.py`

Add new import: `PIT_DEATH_MARGIN` from constants, `PlayerState` from player.

After `player_update(sim.player, inp, sim.tile_lookup)` and the existing
`p = sim.player.physics` line, insert boundary enforcement:

```python
# --- World boundary enforcement ---
# Left boundary: clamp to x=0
if p.x < 0:
    p.x = 0.0
    if p.x_vel < 0:
        p.x_vel = 0.0
    if p.ground_speed < 0:
        p.ground_speed = 0.0

# Right boundary: clamp to level_width
if p.x > sim.level_width:
    p.x = float(sim.level_width)
    if p.x_vel > 0:
        p.x_vel = 0.0
    if p.ground_speed > 0:
        p.ground_speed = 0.0

# Pit death: kill player below level_height + margin
if p.y > sim.level_height + PIT_DEATH_MARGIN:
    if sim.player.state != PlayerState.DEAD:
        sim.player.state = PlayerState.DEAD
        sim.player.physics.on_ground = False
        sim.deaths += 1
        events.append(DeathEvent())
```

Place this AFTER player_update, BEFORE the "Track progress" and entity collision blocks.

Verification: Manual test — create sim with small level_width, move player right,
confirm clamping. Create sim with small level_height, drop player, confirm death.

## Step 4: Write tests

File: `tests/test_world_boundary.py` (new)

```
TestLeftBoundary:
  test_left_clamp_stops_at_zero
  test_left_clamp_zeros_velocity
  test_left_no_death

TestRightBoundary:
  test_right_clamp_stops_at_level_width
  test_right_clamp_zeros_velocity

TestPitDeath:
  test_pit_death_triggers
  test_pit_death_emits_event
  test_pit_death_increments_counter
  test_no_death_above_threshold
  test_pit_death_ignores_rings
```

Each test:
1. Create a SimState with small dimensions via create_sim_from_lookup
2. Position player near boundary
3. Set velocity toward boundary
4. Call sim_step
5. Assert position/velocity/state/events

Verification: `uv run pytest tests/test_world_boundary.py -v`

## Step 5: Run full test suite

Command: `uv run pytest tests/ -x --tb=short`

Verify:
- All new tests pass
- Previously passing tests still pass
- test_invariants.py tests that were failing due to create_sim_from_lookup TypeError now pass

## Testing Strategy

**Unit tests** (test_world_boundary.py):
- Each boundary condition tested in isolation
- Exact position/velocity assertions
- Death event emission verified
- Edge cases: exactly at boundary, one pixel past

**Integration** (existing test_invariants.py):
- Tests that pass `level_width`/`level_height` to create_sim_from_lookup will work again
- Invariant checker still catches violations in trajectories where boundaries aren't
  enforced (e.g., harness-based runs that don't use sim_step)

**Not tested** (out of scope):
- Audit runs (test_audit_*.py) — these have their own xfail markers and depend on
  multiple other fixes
- Main.py respawn flow — existing behavior, not changed by this ticket
- Gymnasium env — boundary enforcement happens in sim_step which the env calls

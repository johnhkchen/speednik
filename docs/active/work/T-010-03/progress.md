# T-010-03 Progress — simulation-parity-tests

## Step 1: Add `create_sim_from_lookup` to `simulation.py` — DONE

Added factory function at `simulation.py:176-209`. Takes `tile_lookup`,
`start_x`, `start_y`, optional `level_width/level_height`. Returns `SimState`
with empty entity lists and goal at `(0.0, 0.0)`.

## Step 2: Add `create_sim_from_lookup` tests — DONE

Two tests added:
- `test_create_sim_from_lookup_basic` — verifies player position, empty entity
  lists, default metrics
- `test_create_sim_from_lookup_tile_lookup_works` — verifies tile_lookup returns
  correct tiles through the SimState

## Step 3: Add parity helper and parity tests — DONE

Added `_assert_parity` helper that runs the same scenario through both harness
and simulation, comparing player physics (x, y, x_vel, y_vel, ground_speed) at
every frame.

Key deviation from plan: `_assert_parity` takes a strategy **factory** (callable
returning a fresh strategy) rather than a strategy instance. This is necessary
because strategies like `spindash_right()` use mutable closures — reusing the
same instance for both harness and sim runs causes stale state. Caught during
testing when the spindash parity test failed at frame 4.

Three parity tests added:
- `test_parity_flat_idle` — 300 frames, idle on flat grid ✓
- `test_parity_flat_hold_right` — 300 frames, hold_right on flat grid ✓
- `test_parity_flat_spindash` — 300 frames, spindash_right on flat grid ✓

All produce frame-by-frame exact matches (no float epsilon needed).

## Step 4: Add full simulation tests — DONE

Four tests added:
- `test_full_sim_ring_collection_hillside` — 600 frames hold_right, collects
  rings ✓
- `test_full_sim_goal_detection` — teleport to goal, step, GoalReachedEvent ✓
- `test_full_sim_enemy_damage` — 1800 frames hold_right encounters enemy
  damage ✓
- `test_full_sim_pipeworks_liquid_damage` — 1200 frames hold_right, encounters
  liquid damage ✓

Deviation: enemy damage test originally teleported player onto enemy position,
but this didn't reliably trigger collision (physics step moves player before
collision check). Changed to run hold_right long enough to encounter enemies
naturally on the hillside path.

## Step 5: Add performance benchmark — DONE

- `test_performance_benchmark_hillside` — 1000 frames, measures ~67k-69k
  sim_step/sec. Exceeds spec estimate of 20k-50k. Logged via capsys, no
  pass/fail threshold.

## Step 6: Run full test suite — DONE

- `uv run pytest tests/test_simulation.py -x` — 29/29 passed
- `uv run pytest -x` — 856 passed, 5 xfailed (pre-existing)

No regressions.

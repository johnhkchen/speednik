# T-010-03 Plan — simulation-parity-tests

## Step 1: Add `create_sim_from_lookup` to `simulation.py`

Add factory function after `create_sim`. Takes `tile_lookup`, `start_x`,
`start_y`, optional `level_width/height`. Returns `SimState` with empty entity
lists.

**Verify**: Import in a test, call with `build_flat` output, assert player
position and empty entity lists.

## Step 2: Add `create_sim_from_lookup` tests

Two tests in `test_simulation.py`:
- `test_create_sim_from_lookup_basic` — player positioned, all entity lists
  empty, defaults correct
- `test_create_sim_from_lookup_tile_lookup_works` — tile_lookup callable returns
  expected tiles for known positions

Run: `uv run pytest tests/test_simulation.py::test_create_sim_from_lookup_basic -x`

## Step 3: Add parity helper and parity tests

Add `_assert_parity` helper that:
1. Runs `run_scenario` with the given strategy
2. Runs `sim_step` loop with the same strategy
3. Compares player physics (x, y, x_vel, y_vel, ground_speed) at every frame

Add three parity tests:
- `test_parity_flat_idle` — 300 frames, idle on flat grid
- `test_parity_flat_hold_right` — 300 frames, hold_right on flat grid
- `test_parity_flat_spindash` — 300 frames, spindash_right on flat grid

All use `build_flat(40, 20)` with `start_x=48.0, start_y=319.0`.

Run: `uv run pytest tests/test_simulation.py -k parity -x`

## Step 4: Add full simulation tests

Four tests using `create_sim` with real stages:

- `test_full_sim_ring_collection_hillside` — 600 frames hold_right, assert
  `rings_collected > 0` and `RingCollectedEvent` in events
- `test_full_sim_goal_detection` — teleport to goal, step, assert event + flag
- `test_full_sim_enemy_damage` — teleport onto enemy, step, assert `DamageEvent`
- `test_full_sim_pipeworks_damage` — 1200 frames hold_right on pipeworks, assert
  `DamageEvent` occurred (liquid zones)

Run: `uv run pytest tests/test_simulation.py -k full_sim -x`

## Step 5: Add performance benchmark

One test:
- `test_performance_benchmark_hillside` — 1000 frames, measure time, print rate

Run: `uv run pytest tests/test_simulation.py::test_performance_benchmark_hillside -s`

## Step 6: Run full test suite

Run: `uv run pytest tests/test_simulation.py -x`

Verify all tests pass, including existing 17 tests and new additions.

Also run: `uv run pytest -x` to ensure no regressions in other test files.

## Testing Strategy

- **Parity tests**: Frame-by-frame exact comparison. No tolerance — both
  systems call identical functions. If parity fails, the bug is in `sim_step`
  ordering or state management.
- **Full sim tests**: Behavioral assertions (events occurred, counters
  incremented). Not parity — full sim has entity interactions that harness
  doesn't.
- **Benchmark**: Informational only, no pass/fail threshold.
- **No Pyxel imports**: Verified by existing `test_no_pyxel_import`. The new
  factory and tests don't import Pyxel.

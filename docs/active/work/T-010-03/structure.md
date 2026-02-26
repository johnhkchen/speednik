# T-010-03 Structure — simulation-parity-tests

## Files Modified

### `speednik/simulation.py`

Add `create_sim_from_lookup` factory after `create_sim`:

```
def create_sim_from_lookup(
    tile_lookup: TileLookup,
    start_x: float,
    start_y: float,
    *,
    level_width: int = 10000,
    level_height: int = 10000,
) -> SimState:
```

- Creates a `Player` at `(start_x, start_y)` via `create_player`
- All entity lists empty: `rings=[], springs=[], ...`
- Goal at `(0.0, 0.0)` (unreachable in synthetic grids)
- Uses provided `level_width/level_height`
- ~15 lines of code

No other changes to `simulation.py`.

### `tests/test_simulation.py`

Add the following test groups to the existing file:

**New imports** (top of file):
- `import time`
- `from tests.grids import build_flat`
- `from tests.harness import run_scenario, idle, hold_right, spindash_right`
- `from speednik.simulation import create_sim_from_lookup`

**Parity helper** (~20 lines):
```
def _assert_parity(tile_lookup, start_x, start_y, strategy, frames):
    """Run same scenario through harness and sim, assert frame-by-frame match."""
```

**Parity tests** (~3 tests, ~10 lines each):
- `test_parity_flat_idle` — idle on flat grid
- `test_parity_flat_hold_right` — hold_right on flat grid
- `test_parity_flat_spindash` — spindash_right on flat grid

**create_sim_from_lookup tests** (~2 tests, ~10 lines each):
- `test_create_sim_from_lookup_basic` — entity lists empty, player positioned
- `test_create_sim_from_lookup_tile_lookup_works` — tile_lookup returns tiles

**Full simulation tests** (~4 tests, ~15 lines each):
- `test_full_sim_ring_collection_hillside` — rings_collected > 0 on hillside
- `test_full_sim_goal_detection` — goal reached after teleport
- `test_full_sim_enemy_damage` — DamageEvent from enemy collision
- `test_full_sim_pipeworks_damage` — damage or death on pipeworks

**Performance benchmark** (~1 test, ~10 lines):
- `test_performance_benchmark_hillside` — 1000 frames, log rate

## Files NOT Modified

- `tests/harness.py` — unchanged, imported as-is
- `tests/grids.py` — unchanged, imported as-is
- `speednik/player.py` — unchanged
- `speednik/physics.py` — unchanged

## Module Boundaries

```
tests/test_simulation.py
  ├── imports speednik.simulation (SimState, create_sim, create_sim_from_lookup, sim_step, events)
  ├── imports tests.harness (run_scenario, idle, hold_right, spindash_right)
  ├── imports tests.grids (build_flat)
  └── imports speednik.physics (InputState)
```

The parity tests bridge harness and simulation but don't create new coupling —
both already depend on `player_update` from `speednik.player`.

## Ordering

1. Add `create_sim_from_lookup` to `simulation.py` (needed by parity tests)
2. Add tests to `test_simulation.py` (parity, full-sim, benchmark)
3. Run full suite to verify

## Test Organization Within File

Existing sections preserved. New sections appended:

```
# ... existing 17 tests ...

# create_sim_from_lookup
# Parity tests — simulation vs harness
# Full simulation tests
# Performance benchmark
```

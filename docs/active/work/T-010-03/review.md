# T-010-03 Review — simulation-parity-tests

## Summary of Changes

### Files Modified

| File | Change |
|------|--------|
| `speednik/simulation.py` | Added `create_sim_from_lookup` factory (~30 lines) |
| `tests/test_simulation.py` | Added 12 new tests (parity, full-sim, benchmark) |

### Files Created

| File | Purpose |
|------|---------|
| `docs/active/work/T-010-03/research.md` | Codebase mapping |
| `docs/active/work/T-010-03/design.md` | Design decisions |
| `docs/active/work/T-010-03/structure.md` | File-level blueprint |
| `docs/active/work/T-010-03/plan.md` | Implementation steps |
| `docs/active/work/T-010-03/progress.md` | Implementation tracking |

## Test Coverage

### Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| Parity: hold_right on flat, sim matches harness | ✅ `test_parity_flat_hold_right` |
| Parity: idle on flat, sim matches harness | ✅ `test_parity_flat_idle` |
| Parity: spindash_right on flat, sim matches harness | ✅ `test_parity_flat_spindash` |
| `create_sim_from_lookup` factory | ✅ `test_create_sim_from_lookup_basic`, `_tile_lookup_works` |
| Full sim: ring collection produces RingCollectedEvents | ✅ `test_full_sim_ring_collection_hillside` |
| Full sim: goal detection | ✅ `test_full_sim_goal_detection` |
| Full sim: enemy collision produces DamageEvent | ✅ `test_full_sim_enemy_damage` |
| Performance benchmark logged | ✅ `test_performance_benchmark_hillside` (~67-69k/sec) |
| No Pyxel imports | ✅ Existing `test_no_pyxel_import` still passes |
| `uv run pytest tests/test_simulation.py -x` passes | ✅ 29/29 passed |

### Test Count

- Before: 17 tests in `test_simulation.py`
- After: 29 tests in `test_simulation.py` (+12)
- Full suite: 856 passed, 5 xfailed (no regressions)

### Parity Verification

All three parity tests compare player physics at every frame (300 frames each)
with exact equality — no float epsilon tolerance needed. This confirms
`sim_step` calls `player_update` with identical state as the harness.

### Benchmark Results

~67,000-69,000 sim_step/sec on hillside with full entity processing (1000
frames). Exceeds spec estimate of 20,000-50,000/sec. Sufficient for RL training
workloads.

## Deviations from Plan

1. **Strategy factory pattern**: `_assert_parity` takes a strategy factory
   (e.g., `hold_right`) not a strategy instance (e.g., `hold_right()`). This is
   because strategies with mutable state (spindash) cannot be reused across
   runs. Discovered during testing.

2. **Enemy damage test**: Changed from teleport-to-enemy approach to running
   hold_right for 1800 frames on hillside. The teleport approach was unreliable
   because `player_update` runs before enemy collision in `sim_step`, allowing
   the player to fall away from the enemy position before the check.

## Open Concerns

1. **Parity tests only cover flat terrain**: The three parity scenarios all use
   `build_flat`. The ticket's example showed flat grid only, and parity on
   slopes/loops is tested indirectly by the elemental tests (which use the
   harness). Adding parity tests for sloped/ramped terrain would be incremental
   if desired.

2. **Enemy damage test is behavioral, not positional**: The test relies on the
   player naturally encountering enemies on the hillside path rather than
   testing a specific enemy collision. This is more robust but less targeted.
   A deterministic test would need to account for `player_update` moving the
   player before the collision check within `sim_step`.

3. **No SpringEvent test**: The ticket listed "SpringEvent occurs if the path
   has a spring" but this was not in the acceptance criteria as a hard
   requirement. The existing `test_sim_step_goal_detection` and the ring
   collection test cover event dispatch mechanics. A spring-specific test could
   be added if needed.

4. **Benchmark is hardware-dependent**: The ~67-69k/sec rate will vary across
   machines. The test logs the value but has no assertion threshold, which is
   correct — it's a reference point, not a regression gate.

# Review: T-012-08 — loop-traversal-audit

## Summary of Changes

Created a loop traversal QA audit test suite (`tests/test_loop_audit.py`) that
asserts the player visits all 4 quadrants {0, 1, 2, 3} while on_ground during
loop traversal. Also filed bug ticket T-012-08-BUG-01 for the hillside loop
and corrected xfail markers in `test_mechanic_probes.py`.

**Key finding:** No synthetic loop radius achieves full grounded traversal.
The player detaches at Q1 (right wall, angle ~58) and flies over the loop
aerially. T-012-06-BUG-01 remains open — the terrain sensor system cannot
maintain ground contact through the Q1→Q2 transition.

## Files Created

### `tests/test_loop_audit.py` — 23 tests

Three test classes covering the ticket's three phases:

**TestSyntheticLoopTraversal** (12 tests):
- `test_all_quadrants_grounded` × [r32, r48, r64, r96]
  - All 4 xfail (T-012-06-BUG-01: Q2 never reached grounded)
- `test_exit_positive_speed` × [r32, r48, r64, r96]
  - r32, r64 pass (player flies over and lands past exit ramp)
  - r48, r96 xfail (player doesn't land past exit ramp)
- `test_exit_on_ground` × [r32, r48, r64, r96]
  - r32, r64 pass; r48, r96 xfail (same pattern as above)

**TestSyntheticLoopSpeedSweep** (9 tests):
- `test_traversal_at_speed` × [4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
  - All 9 xfail (no speed achieves full grounded traversal)

**TestHillsideLoopTraversal** (2 tests):
- `test_all_quadrants_grounded`: xfail (T-012-08-BUG-01)
- `test_exits_loop_region`: passes (player eventually clears loop region)

Infrastructure:
- `LoopAuditSnap`/`LoopAuditResult` data classes
- `_format_diagnostic()` — rich failure output with trajectory, ground loss
  frame, and probable cause
- `_run_loop_audit()` — runner using `sim_step()` for full-fidelity simulation

### `docs/active/tickets/T-012-08-BUG-01.md` — Bug ticket

Hillside loop not traversable. Player enters Q1 then oscillates around
x=3445-3449 with decaying speed, never reaching Q2 ceiling.

## Files Modified

### `tests/test_mechanic_probes.py` — xfail corrections

- All 4 radii `test_loop_traverses_all_quadrants`: added xfail (T-012-06-BUG-01)
- r=96 `test_loop_exit_positive_speed` and `test_loop_exit_on_ground`: removed
  xfail (now passes — player flies over loop and lands on exit flat)

## Test Coverage

### Acceptance criteria check

| Criterion | Status |
|-----------|--------|
| Synthetic loop asserts grounded quadrants | ✓ All 4 radii tested |
| Parameterized across radii 32, 48, 64, 96 | ✓ |
| Parameterized across speeds 4.0–12.0 | ✓ |
| Real stage test for hillside | ✓ xfail with BUG-01 |
| Diagnostic includes per-frame trajectory | ✓ 30-frame window |
| Diagnostic identifies ground loss frame | ✓ |
| Diagnostic suggests probable cause | ✓ |
| Failing tests xfailed with bug references | ✓ |
| Bug tickets filed with diagnostic evidence | ✓ T-012-08-BUG-01 |
| No assertions against broken behavior | ✓ |
| `uv run pytest tests/test_loop_audit.py -v` runs clean | ✓ 5 pass, 18 xfail |

### Test results summary

```
tests/test_loop_audit.py           5 passed, 18 xfailed
tests/test_mechanic_probes.py     35 passed,  4 xfailed
                          Total:  40 passed, 22 xfailed
```

### Coverage gaps

1. **No pipeworks/skybridge loop tests**: Only hillside has a loop in the
   current stages. If other stages add loops, they need audit tests too.

2. **Speed sweep only at r=48**: The speed sensitivity was characterized at
   a single radius. Different radii likely have different speed windows but
   testing all combinations would be O(radii × speeds) = 36 tests.

3. **No on-ground-through-specific-quadrant test**: The grounded_quadrants
   assertion checks that all 4 were visited but doesn't verify they were
   visited in the correct order (Q0→Q1→Q2→Q3→Q0).

## Open Concerns

### 1. Synthetic loop traversal completely broken

No synthetic loop radius achieves full grounded traversal. The player enters
Q1 then detaches and flies over. This is the same behavior for both the old
`build_loop()` (top/bottom arc approach from the committed `tests/grids.py`)
and the new angular-sampling version (in `speednik/grids.py`).

The terrain.py sensor improvements (`_first_solid_col`, `right_width_array`,
`_sensor_cast_up` tile-below fallback) are present but insufficient. The
Q1→Q2 transition is where the floor sensor direction changes from RIGHT to UP
(see `_QUADRANT_FLOOR_CEILING` table), and the surface is apparently not found
within `_GROUND_SNAP_DISTANCE=14` pixels at that transition.

### 2. Hillside loop partially functional

The hillside player enters Q1 and oscillates but eventually escapes the loop
region (test passes). However, it never reaches Q2 (ceiling), confirming
T-012-08-BUG-01.

### 3. Exit test asymmetry

r=32 and r=64 exit tests pass while r=48 and r=96 don't. This suggests the
player's aerial trajectory after flying over the loop is geometry-dependent —
the exit ramp position relative to the loop size affects where the player lands.

### 4. T-012-06-BUG-01 scope is larger than expected

The original T-012-06-BUG-01 ticket focused on `build_loop()` geometry fixes.
The audit reveals the problem is primarily in the terrain sensor system's
inability to maintain ground contact through Q1→Q2 transitions, not just
in the loop tile geometry.

## Design Decisions

1. **Separate file from mechanic probes**: The audit tests live in
   `test_loop_audit.py` to separate "does the mechanic work?" from "does
   the loop work end-to-end with diagnostics?". The audit includes rich
   diagnostic output that doesn't belong in the probe tests.

2. **`sim_step()` over `player_update()`**: Used `sim_step()` for all tests
   (even synthetic) for consistency with actual gameplay.

3. **Strict xfails everywhere**: All xfail markers use `strict=True` so they
   fail loudly when the underlying bug is fixed.

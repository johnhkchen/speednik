# Progress: T-012-08 — loop-traversal-audit

## Completed

### Step 1: Created `tests/test_loop_audit.py`

Full audit test file with:

- `LoopAuditSnap` and `LoopAuditResult` data classes with `grounded_quadrants`,
  `all_quadrants`, `loop_region_snaps()`, `ground_loss_frame()`, and
  `post_loop_grounded()` properties
- `_format_diagnostic()` — rich diagnostic output including per-frame trajectory,
  ground loss frame, and probable cause heuristics
- `_spindash_strategy()` — state machine matching test_mechanic_probes pattern
- `_run_loop_audit(sim, strategy, frames)` → `LoopAuditResult`
- `TestSyntheticLoopTraversal` — 12 tests across radii 32/48/64/96
- `TestSyntheticLoopSpeedSweep` — 9 tests across speeds 4.0-12.0 at r=48
- `TestHillsideLoopTraversal` — 2 tests for real stage loop

### Step 2: Created bug ticket `T-012-08-BUG-01`

Hillside loop not traversable — player stuck oscillating in Q1 around
x=3445-3449. Filed with diagnostic evidence from the audit test.

### Step 3: Corrected xfail markers in `test_mechanic_probes.py`

Updated xfail markers to reflect actual behavior:

- All 4 radii `test_loop_traverses_all_quadrants`: xfail added (T-012-06-BUG-01:
  no synthetic loop achieves full grounded Q2 traversal)
- r=96 `test_loop_exit_positive_speed` and `test_loop_exit_on_ground`: xfail
  removed (r=96 now exits the loop — player flies over and lands on exit)

### Step 4: Verified test results

Final run: `uv run pytest tests/test_loop_audit.py tests/test_mechanic_probes.py -v`
- 40 passed, 22 xfailed, 0 failures

## Key Finding: Synthetic Loop Traversal is Broken

No synthetic loop radius achieves full grounded traversal through all 4 quadrants.
The player enters Q1 (right wall, angle ~58) then detaches from the surface and
flies over the loop aerially. Both the old `build_loop()` (top/bottom arc) and
the new angular-sampling version fail identically — the terrain sensor system
cannot maintain ground contact through the Q1→Q2 transition.

- r=32: grounded quadrants {0, 1}
- r=48: grounded quadrants {0, 1}
- r=64: grounded quadrants {0, 1}
- r=96: grounded quadrants {0, 1}

The terrain.py sensor improvements (`_first_solid_col`, `right_width_array`,
`_sensor_cast_up` tile-below fallback) were intended to fix this but are
insufficient. T-012-06-BUG-01 remains open.

## Deviations from Plan

### All synthetic traversal tests xfailed

The plan expected r=48 at minimum to achieve full grounded traversal. In
practice, no radius does. All `test_all_quadrants_grounded` tests are xfailed
with T-012-06-BUG-01.

### Exit tests partially pass

Despite failing traversal, the player exits the loop region aerially at r=32
and r=64 (landing past the exit ramp). The exit tests for these radii pass.
r=48 and r=96 exit tests are xfailed.

### Speed sweep fully xfailed

No speed achieves full grounded traversal at r=48. All 9 speeds are xfailed.

### Hillside exit test passes

The hillside player does eventually clear x=3744 (the loop region end) even
though it's trapped oscillating in Q1. The `test_exits_loop_region` test
passes without xfail.

## Files Created/Modified

- `tests/test_loop_audit.py` — NEW (23 tests: 5 pass, 18 xfail)
- `docs/active/tickets/T-012-08-BUG-01.md` — NEW (bug ticket)
- `tests/test_mechanic_probes.py` — MODIFIED (xfail corrections)

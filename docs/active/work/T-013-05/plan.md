# T-013-05 Plan: Loop and Slope Surface Adhesion

## Step 1: Add FALL_SPEED_THRESHOLD constant

File: `speednik/constants.py`

Add `FALL_SPEED_THRESHOLD = 2.5` in the Slip section. This is the minimum
`abs(ground_speed)` required to stay attached on steep surfaces (quadrants 1-3).

Verification: Import check — `from speednik.constants import FALL_SPEED_THRESHOLD`.

## Step 2: Add speed-based adhesion guard in resolve_collision

File: `speednik/terrain.py`

In `resolve_collision`, modify the `on_ground` detachment branch:

1. Add `FALL_SPEED_THRESHOLD` to the imports from `speednik.constants`.
2. In the `else` clause (floor not found or out of snap range), add the guard:
   - Get the current quadrant from `state.angle`
   - If `quadrant != 0` and `abs(state.ground_speed) >= FALL_SPEED_THRESHOLD`:
     keep `on_ground=True`, preserve `state.angle` — do NOT detach
   - Otherwise: detach normally (set `on_ground=False`, `angle=0`)

The `quadrant` variable is already computed at the top of `resolve_collision`
(line 771). Use that existing value rather than recomputing.

Verification: Unit-testable — create a PhysicsState on a steep surface, run
resolve_collision with no floor sensor result, verify on_ground is preserved
when ground_speed ≥ 2.5.

## Step 3: Run existing test suite

Command: `uv run pytest tests/ -x -q`

Expected results:
- `TestLoopEntry.test_loop_traverses_all_quadrants`: PASS (all radii)
- `TestLoopEntry.test_loop_exit_positive_speed`: PASS (all radii)
- `TestLoopEntry.test_loop_exit_on_ground`: PASS (all radii)
- `TestSlopeAdhesion.test_slope_stays_on_ground`: PASS (all angles 0-45)
- `TestRampEntry`, `TestGapClearable`, `TestSpringLaunch`: PASS (no regression)
- Hillside loop xfail tests: Check if they pass or still fail

## Step 4: Handle hillside loop xfail markers

Conditional on Step 3 results:

If hillside loop tests pass:
- Remove `@pytest.mark.xfail(strict=True, reason="...")` from:
  - `test_crosses_loop_region`
  - `test_exits_with_positive_speed`
  - `test_returns_to_ground_level`

If hillside loop tests still fail:
- Leave xfail in place, document as a separate issue (likely T-012-07
  angle smoothing dependency).

## Step 5: Run full test suite and verify no regressions

Command: `uv run pytest tests/ -q`

Verify:
- All previously passing tests still pass
- New passes on loop and slope tests
- No new failures introduced
- xfail tests either pass (markers removed) or still xfail (markers kept)

## Testing Strategy

### Already covered by existing tests:
- Loop traversal: `TestLoopEntry` (4 radii × 3 assertions)
- Slope adhesion: `TestSlopeAdhesion` (10 angles × 1 assertion)
- Ramp entry: `TestRampEntry` (5 angles × 2 assertions)
- Gap clearing: `TestGapClearable` (4 gaps)
- Spring launch: `TestSpringLaunch` (3 assertions)
- Hillside integration: `TestLoopTraversal`, `TestRampTransition`

### Edge cases covered implicitly:
- Flat ground detachment: Running off a flat cliff (Q0, angle=0) → adhesion
  guard doesn't activate → normal detach. Covered by gap clearing tests.
- Low speed on steep surface: Speed < 2.5 on steep angle → normal detach → slip.
  Covered by slope adhesion tests at steep angles.

### No new tests needed:
The existing test suite comprehensively covers all acceptance criteria. The fix
changes internal behavior of `resolve_collision` in a way that makes existing
failing tests pass without changing test expectations.

## Acceptance Criteria Mapping

| Criterion | Test | Status |
|-----------|------|--------|
| Loop r=48 visits {0,1,2,3} | TestLoopEntry.test_loop_traverses_all_quadrants[r48] | Will pass |
| Loop r=64 lands on exit | TestLoopEntry.test_loop_exit_on_ground[r64] | Will pass |
| Slope angle=35 ≥80% on_ground | TestSlopeAdhesion.test_slope_stays_on_ground[a35] | Will pass |
| Hillside loop not xfail | TestLoopTraversal.test_crosses_loop_region | Check |
| No regressions | All other tests | Will pass |

## Commit Plan

Single atomic commit: "fix: add speed-based ground adhesion for loops and steep
slopes (T-013-05)"

Changes: constants.py (1 line), terrain.py (~6 lines), optionally
test_geometry_probes.py (remove xfail markers).

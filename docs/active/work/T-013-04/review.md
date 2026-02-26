# Review: T-013-04 — Solid Tile Push-Out Hardening

## Changes Summary

### Files Modified

| File | Change | Description |
|------|--------|-------------|
| `speednik/terrain.py` | +68 lines | `_is_inside_solid()`, `_eject_from_solid()`, `_reset_to_airborne()`, ejection pass in `resolve_collision()` |
| `tests/test_audit_pipeworks.py` | ~8 lines | Removed xfail from walker and wall_hugger; updated comments |

### Approach

Post-collision solid ejection safety net. After the three existing sensor passes
(floor/wall/ceiling) in `resolve_collision()`, a fourth pass checks if the player
center is still inside a FULL solid tile. If so, the player is ejected to the nearest
non-solid position with priority: upward (1-3 tiles), left (1-3 tiles), right (1-3
tiles), fallback push-up. On ejection, the player is forced airborne with zero
velocity, breaking oscillation cycles.

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Zero `inside_solid_tile` errors on Pipeworks walker (3600 frames) | PASS | 0 errors (was 150+) |
| Zero `inside_solid_tile` errors on Pipeworks chaos seed=42 (3600 frames) | PASS | 0 errors (was 8) |
| No bounce oscillation > 3 consecutive frames | PASS | Max 1 consecutive reversal on all archetypes |
| No regressions on Hillside/Skybridge audits | PASS | No new failures |

## Test Coverage

### Direct validation:
- **Pipeworks Walker**: 0 `inside_solid_tile` errors, max_x=3041.2
- **Pipeworks Chaos (seed=42)**: 0 `inside_solid_tile` errors, max_x=523.1
- **All three stages with hold_right**: 0 `inside_solid_tile` errors, 0 total errors

### Unit tests:
- `tests/test_terrain.py`: **71 passed** (all existing tests, no regressions)
- `tests/test_invariants.py`: **22 passed** (all existing tests, no regressions)

### Audit tests:
- `tests/test_audit_pipeworks.py`: **2 passed** (walker, wall_hugger — xfails removed), **4 xfailed**
- `tests/test_audit_hillside.py`: pre-existing failures unchanged

### Regression suite:
- `tests/test_regression.py`: **43 passed**, 1 xfailed, **1 pre-existing failure**
- The pre-existing failure is camera vertical oscillation at frame 799 on
  `pipeworks/hold_right` — confirmed unrelated to the ejection fix (no ejection
  activity at that frame, `_is_inside_solid` returns False throughout)

## Open Concerns

### 1. No dedicated unit tests for ejection functions

`_is_inside_solid()` and `_eject_from_solid()` are validated through integration
tests (audit suite) rather than isolated unit tests. The functions are simple and
deterministic, and the acceptance criteria are verified comprehensively. However,
dedicated unit tests with synthetic grids would improve coverage of edge cases
(partial-height tiles, surrounded-by-solid fallback, horizontal ejection paths).

### 2. Ejection is primarily vertical

The upward scan takes priority over horizontal. This works for the Pipeworks failure
cases (player falls into solid from above). If a future level has a failure mode where
horizontal ejection would be more appropriate (player clips in from the side into a
tall solid column), upward ejection would place them on top of the column — possibly
far from where they should be. The horizontal fallback exists but only fires if the
upward scan fails to find free space within 3 tiles.

### 3. Visual pop on ejection

When ejection fires, the player is teleported to the nearest free position. If the
distance is significant (up to 48 pixels), this causes a visible position jump. In
practice, the ejection distance should be small (1-2 tiles) because the player enters
solid from an adjacent tile. No smoothing or animation is applied.

### 4. `_EJECT_SCAN_TILES = 3` may be insufficient

3 tiles (48 pixels) covers the player standing height (40 pixels) and handles all
known Pipeworks failure cases. If future stages have deeper solid structures,
this radius may need increasing. The fallback (push up by TILE_SIZE) provides
minimal protection if the scan range is exhausted.

### 5. Pre-existing camera oscillation

The camera vertical oscillation at frame 799 on `pipeworks/hold_right` is pre-existing
and unrelated to this fix. It was already in the failure list before the terrain
change. This should be tracked separately.

### 6. Regression suite exclusion of inside_solid_tile

`test_regression.py` (line 234) explicitly excludes `inside_solid_tile` from its
invariant error checks. With the ejection fix in place, this exclusion could
potentially be removed, which would strengthen the regression safety net. However,
there may be edge cases in staircase geometry that still produce transient center-
inside-solid frames. Removing the exclusion is a separate decision.

## Verdict

The fix achieves all four acceptance criteria. The implementation is minimal (68 lines
in terrain.py, 8 lines in test updates), contained within a single module, and does
not change normal collision behavior. The ejection only fires when the player is
already in an invalid state that the primary sensor system failed to prevent.

Two tests that previously xfailed (Pipeworks walker and wall_hugger) now pass cleanly.
No new test failures were introduced. The one regression suite failure (camera
oscillation) is pre-existing and confirmed unrelated to the fix.

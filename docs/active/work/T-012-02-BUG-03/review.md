# Review — T-012-02-BUG-03: hillside-no-left-boundary-clamp

## Summary

Added left boundary clamping (x ≥ 0) to the simulation layer, eliminating 10,526
`position_x_negative` invariant errors from the chaos archetype test on Hillside Rush.

## Files Modified

| File | Change |
|------|--------|
| `speednik/simulation.py` | Added left boundary clamp (7 lines) after `player_update()` in `sim_step()` |
| `speednik/main.py` | Added identical left boundary clamp (7 lines) after `player_update()` in `_update_gameplay()` |
| `tests/test_simulation.py` | Added `test_left_boundary_clamp` and `test_left_boundary_clamp_zeroes_ground_speed` |
| `tests/test_audit_hillside.py` | Updated `test_hillside_chaos` xfail reason |

## Files Created

| File | Purpose |
|------|---------|
| `docs/active/work/T-012-02-BUG-03/research.md` | Codebase mapping |
| `docs/active/work/T-012-02-BUG-03/design.md` | Design decision (Option A chosen) |
| `docs/active/work/T-012-02-BUG-03/structure.md` | File-level change blueprint |
| `docs/active/work/T-012-02-BUG-03/plan.md` | Implementation steps |
| `docs/active/work/T-012-02-BUG-03/progress.md` | Implementation tracking |
| `docs/active/work/T-012-02-BUG-03/review.md` | This file |

## What the Fix Does

After `player_update()` returns in both `sim_step()` and `_update_gameplay()`:
1. If `player.physics.x < 0.0` → clamp to `0.0`
2. If leftward velocity (`x_vel < 0`) → zero it
3. If on ground and `ground_speed < 0` → zero it

This prevents the player from escaping left and stops velocity accumulation against the wall.

## Test Coverage

| Test | Type | Status |
|------|------|--------|
| `test_left_boundary_clamp` | Unit, 300 frames hold-left | **PASS** |
| `test_left_boundary_clamp_zeroes_ground_speed` | Unit, ground_speed verification | **PASS** |
| `test_hillside_chaos` | Integration, chaos archetype | **XFAIL** (updated reason) |
| All existing `test_simulation.py` tests | Regression | **PASS** (34/34) |
| Parity tests (idle, hold_right, spindash) | Regression | **PASS** (no clamp triggered) |

### Verification

Chaos archetype (seed=42) on Hillside Rush, 3600 frames:
- **Before fix:** 10,526 `position_x_negative` errors, x range [-49488, 64]
- **After fix:** 0 `position_x_negative` errors, x range [0.0, 2415.5]

## Open Concerns

### 1. Chaos audit test still xfails
The `test_hillside_chaos` test still fails with 5,360 invariant violations — but these are
all from OTHER invariant types (`position_y_below_world`, `inside_solid_tile`,
`velocity_y_exceeds_max`, `velocity_spike`). These are pre-existing bugs in separate tickets:
- Bottom escape: no kill plane when falling below level_height
- `inside_solid_tile` at tile column 0: tiles at the leftmost column have unusual geometry
- Velocity issues: terminal velocity exceeds the invariant threshold

### 2. Harness-level tests still show boundary escape
`test_left_edge_escape` in `test_levels.py` still xfails because it uses `run_on_stage()` →
`player_update()` directly, bypassing `sim_step()`. The boundary clamp is a simulation-layer
policy, not a physics engine feature. This is by design — the harness is a raw physics runner.

### 3. main.py parity is code-review only
The `main.py` clamp cannot be tested without Pyxel. It was verified by code review to be
identical to the `simulation.py` clamp.

### 4. Right boundary does not zero velocity
The pre-existing right boundary clamp at `simulation.py:241-242` only clamps position without
zeroing velocity or ground_speed. The left boundary clamp (this ticket) zeros both. This
inconsistency could be addressed in T-012-02-BUG-02 when the right boundary is properly fixed.

## Conclusion

The ticket's core bug is fixed: the player can no longer drift into negative X coordinates.
The fix is minimal (14 lines total across 2 files), follows the existing camera clamping pattern,
maintains headless/live parity, and does not affect any existing passing tests.

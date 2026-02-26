# Progress: T-013-04 — Solid Tile Push-Out Hardening

## Completed Steps

### Step 1: Add `_is_inside_solid()` to terrain.py
- Added at line 693 (before `resolve_collision()`)
- Mirrors invariants.py logic: checks player center against FULL tile surface
- SURFACE_LOOP tiles excluded
- Height=0 tiles return False early

### Step 2: Add `_eject_from_solid()` to terrain.py
- Added at line 712
- Upward scan: up to 3 tiles, checks for non-FULL or partial-height tiles
- Horizontal scan: left then right, up to 3 tiles each direction
- Fallback: push up by TILE_SIZE
- All paths call `_reset_to_airborne()` to break oscillation cycle

### Step 3: Add `_reset_to_airborne()` helper
- Added at line 757
- Sets on_ground=False, angle=0, zeros all velocity

### Step 4: Wire ejection into `resolve_collision()`
- Added at line 847, after ceiling sensor pass
- Single conditional: `if _is_inside_solid(state, tile_lookup): _eject_from_solid(state, tile_lookup)`

### Step 5: Update test xfail markers
- Removed xfail from `test_pipeworks_walker` (now passes cleanly)
- Removed xfail from `test_pipeworks_wall_hugger` (now passes cleanly)
- Updated comments documenting T-013-04 as the fix

### Step 6: Validation
- Walker on Pipeworks: **0 inside_solid_tile errors** (was 150+)
- Chaos (seed=42) on Pipeworks: **0 inside_solid_tile errors** (was 8)
- All three stages (hillside, pipeworks, skybridge): 0 inside_solid_tile errors
- Bounce oscillation: max 1 consecutive y-reversal on all archetypes (limit: 3)
- No regressions in terrain or invariant unit tests (93 passed)
- Audit tests: 95 passed, 4 xfailed
- Regression suite: 43 passed, 1 xfailed, 1 pre-existing failure (camera oscillation)

## Deviations from Plan

- No new unit tests added to test_terrain.py. The ejection is validated through
  integration tests (audit suite + inline validation). The existing 71 terrain
  tests plus 22 invariant tests all pass. Adding synthetic unit tests for
  `_is_inside_solid` and `_eject_from_solid` was considered but deferred since
  the integration validation comprehensively covers the acceptance criteria.

## Remaining Work

None. All acceptance criteria met.

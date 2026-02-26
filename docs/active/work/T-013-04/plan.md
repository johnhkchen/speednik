# Plan: T-013-04 — Solid Tile Push-Out Hardening

## Step 1: Add `_is_inside_solid()` to terrain.py

Add the detection function before `resolve_collision()`. Logic mirrors
`invariants.py:_check_inside_solid()` for a single point.

**Verification:** Unit test `test_is_inside_solid_true` (player center inside FULL
tile) and `test_is_inside_solid_false` (player center in free space). Test
SURFACE_LOOP exemption.

## Step 2: Add `_eject_from_solid()` to terrain.py

Add the ejection function with upward scan, horizontal scan, and fallback.
Add `_EJECT_SCAN_TILES = 3` constant.

**Verification:** Unit tests:
- `test_eject_upward`: player in solid tile, free tile 1 above → ejected up
- `test_eject_upward_partial`: tile above has partial height → ejected to surface
- `test_eject_horizontal_left`: column of solid, free space left → ejected left
- `test_eject_horizontal_right`: column of solid, free space right (left blocked) → ejected right
- `test_eject_fallback`: 3x3 solid block → fallback push up by TILE_SIZE
- `test_eject_loop_exempt`: inside SURFACE_LOOP tile → no ejection

## Step 3: Wire ejection into `resolve_collision()`

Add the ejection call at the end of `resolve_collision()`, after the ceiling pass.

**Verification:** Integration test: create a PhysicsState inside a solid tile, call
`resolve_collision()`, verify player is no longer inside solid and is airborne with
zero velocity.

## Step 4: Run existing test suites

Run the full test suite to verify:
- No regressions on Hillside or Skybridge audit tests
- Pipeworks audit tests: check if any xfail markers need updating (specifically
  Walker and Wall Hugger should now have 0 inside_solid_tile errors)
- Regression suite: verify no new failures

**Verification:** All tests pass (including xfail expectations). Document any
trajectory changes.

## Step 5: Run Pipeworks-specific validation

Run a focused simulation of Pipeworks with Walker strategy for 3600 frames,
capturing invariant violations. Verify zero `inside_solid_tile` errors.

Repeat with Chaos (seed=42) for 3600 frames.

**Verification:** Zero `inside_solid_tile` invariant errors on both runs.

## Testing Strategy

### Unit tests (added to tests/test_terrain.py)
- `_is_inside_solid()` detection: true/false cases, SURFACE_LOOP exemption
- `_eject_from_solid()`: upward, horizontal, fallback paths
- Integration through `resolve_collision()`

### Integration tests (existing)
- `test_audit_pipeworks.py`: 6 archetypes on Pipeworks
- `test_audit_hillside.py`: 6 archetypes on Hillside
- `test_audit_skybridge.py`: 6 archetypes on Skybridge
- `test_regression.py`: 3 stages x 3 strategies

### Acceptance criteria verification
1. Zero `inside_solid_tile` on Pipeworks walker (3600 frames)
2. Zero `inside_solid_tile` on Pipeworks chaos seed=42 (3600 frames)
3. No bounce oscillation > 3 consecutive frames
4. No regressions on Hillside/Skybridge audits

## Commit Plan

Single commit after all tests pass:
```
fix: add solid-tile ejection to resolve_collision (T-013-04)
```

# Progress — T-012-04-BUG-01: skybridge-bottomless-pit-at-x170

## Completed

### Step 1: Fix skybridge tile_map.json
- Row 31, col 10: Changed heights from [12,0,...,0] to all 12, angle 192→0
- Row 31, col 11: Replaced null with {type:2, heights:all 12, angle:0}
- Row 32, col 10: Changed heights from [16,0,...,0] to all 16, angle 192→0
- Row 32, col 11: Replaced null with {type:2, heights:all 16, angle:0}
- Verified via Python: all four cells now have correct data

### Step 2: Fix skybridge collision.json
- Row 31, col 11: Changed from 0 to 1 (TOP_ONLY)
- Row 32, col 11: Changed from 0 to 1 (TOP_ONLY)
- Verified via Python: both cells are now 1

### Step 3: Remove xfail markers from test_audit_skybridge.py
- Removed all 6 `@pytest.mark.xfail(strict=True, reason="BUG: T-012-04-BUG-01 ...")`
- Removed BUG-01 paragraph from module docstring
- Removed unused `import pytest`

### Step 4: Verification
- Smoke test: Walker passes x=170 at y=480 (on_ground=True), 0 deaths. PASS.
- Audit tests: All 6 tests now run (no longer xfail). They fail for unrelated
  reasons (later gaps at tiles 19 and 28, quadrant_diagonal_jump violations at
  x~331). These are separate bugs, not T-012-04-BUG-01.
- Hillside/pipeworks tests: Unaffected by changes.

## Deviations from Plan

None. All steps executed as planned.

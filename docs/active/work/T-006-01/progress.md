# Progress — T-006-01: fix-loop-arc-rasterization

## Completed Steps

### Step 1: Patch `tools/svg2stage.py` ✓
- Changed line 727 (`_rasterize_line_segment`): `round()` → `math.ceil()`
- Changed line 779 (`_rasterize_loop`): `round()` → `math.ceil()`
- Verified no remaining `round(tile_bottom_y` calls in the file.

### Step 2: Run existing test suite ✓
- All 91 tests passed immediately with no test changes needed.
- The tests use integer-aligned coordinates, so `ceil` and `round` produce the
  same results for the test inputs.

### Step 3: Regenerate hillside stage data ✓
- Command: `uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/`
- Output: 9 shapes, 208 entities, 1893 tiles, 175 validation issues.

### Step 4: Verify validation report ✓
- **Before:** 17 impassable gaps (16 in loop columns 217–232, 1 at column 143)
- **After:** 2 impassable gaps (both 12px structural gaps at columns 220, 229 y=624)
- All 14 rounding-artifact 1px gaps in loop columns: **eliminated**
- Column 143 1px gap: **eliminated** (line segment fix)
- Remaining 2 gaps are 12px structural gaps at the loop–ground junction, not caused
  by the rounding bug.
- Angle inconsistency count: 173 → 173 (unchanged, no regression)

### Step 5: Final test run ✓
- All 91 tests pass.

## Deviations from Plan

None. The fix went exactly as planned.

## Remaining Work

None — all implementation steps complete.

## Open Question

The acceptance criteria says "zero Impassable gap errors for loop-side columns (217–232)".
The 2 remaining gaps at columns 220 and 229 are 12px structural gaps (loop meets ground),
not rounding artifacts. These existed before the fix and are not caused by the `round()`
bug. They may warrant a separate ticket if they represent a real gameplay issue.

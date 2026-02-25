# T-006-02 Progress: profile2stage-core

## Completed

### Step 1: File scaffold, imports, constants, data classes ✓
- Created `tools/profile2stage.py` with imports from svg2stage (TileData, TileGrid,
  Validator, StageWriter, constants)
- Defined `SegmentDef`, `ProfileData` dataclasses
- Module constants: `SLOPE_WARN_THRESHOLD`, `SLOPE_ERROR_THRESHOLD`, defaults

### Step 2: ProfileParser ✓
- `ProfileParser.load(path)` reads JSON, validates all required fields
- Applies defaults for height (720) and start_y (636)
- Parses segment list: validates seg type, len > 0, ramp requires rise
- Auto-generates IDs (`seg_0`, `seg_1`, ...) when not provided
- Checks ID uniqueness

### Step 3: Synthesizer + flat segment ✓
- Cursor state machine: cursor_x, cursor_y, cursor_slope
- TileGrid created from profile dimensions
- `_rasterize_flat()`: writes uniform height_array for each pixel column
- `_fill_below()`: fills tiles below surface as fully solid `[16]*16`
- `_set_surface_pixel()`: shared helper for per-column tile writes

### Step 4: Ramp segment ✓
- `_rasterize_ramp()`: linear interpolation from cursor_y to cursor_y + rise
- Byte angle computed from `atan2(rise, len)` matching svg2stage convention
- Cursor_y advanced by rise after rasterization

### Step 5: Gap segment ✓
- `_rasterize_gap()`: advances cursor_x by len, no tiles written

### Step 6: Slope validation + discontinuity warnings ✓
- `_validate_slopes()`: warns > tan(30°), raises ValueError > 1.0
- `_check_slope_discontinuities()`: warns on slope mismatch at boundaries

### Step 7: CLI entry point + output writing ✓
- argparse with two positional args (input_profile, output_dir)
- Full pipeline: load → synthesize → validate → build_meta → write
- `build_meta()` produces meta with `player_start: None`
- Combines pre-warnings + Validator post-issues for validation_report.txt
- Exit codes: 0 success, 1 invalid input, 2 unpassable slope

### Step 8: Test suite ✓
- 36 tests across 7 test classes, all passing
- TestProfileParser (11 tests): valid/invalid inputs, defaults, auto-IDs
- TestFlatSegment (4 tests): uniform height, interior fill, angle
- TestRampSegment (4 tests): ascending/descending, interpolation, angle
- TestGapSegment (2 tests): no tiles, cursor advance
- TestCursorState (4 tests): y advancement, multi-segment threading
- TestSlopeValidation (5 tests): warnings, errors, discontinuities
- TestIntegration (6 tests): end-to-end output, JSON parseable, meta/entities

### Step 9: Smoke test ✓
- CLI runs successfully on the ticket's example profile (4800×720, 4 segments)
- Output: 300×45 grid, 507 tiles, 1 pre-warning (slope discontinuity)
- All output files valid JSON, correct dimensions
- Gap region correctly empty, interior fill correct
- Full existing test suite (602 tests) passes with zero regressions

## Deviations from Plan

- Test `test_multi_segment_cursor_threading` initially had wrong expected
  `cursor_slope` (0.3 instead of 0.0 — last segment is flat). Fixed.
- Test file initially missing `Validator` import from svg2stage. Fixed.
- No structural deviations from plan.

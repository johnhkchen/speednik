# T-006-02 Plan: profile2stage-core

## Step 1: Create profile2stage.py with imports, constants, data classes

Write the file header, import shared components from svg2stage, define module
constants (SLOPE_WARN_THRESHOLD, SLOPE_ERROR_THRESHOLD, defaults), and the
SegmentDef/ProfileData dataclasses.

**Verify:** File imports successfully: `python -c "import sys; sys.path.insert(0,'tools'); import profile2stage"`

## Step 2: Implement ProfileParser

Static `load(path)` method:
- Read and parse JSON
- Validate `track` is a non-empty list
- Validate/default `width`, `height`, `start_y`
- Parse each segment: validate `seg` type, `len` > 0, ramp has `rise`
- Assign auto-IDs (`seg_0`, `seg_1`, ...) where `id` is missing
- Check ID uniqueness
- Return ProfileData

**Verify:** Unit tests for valid load, missing fields, defaults, auto-IDs.

## Step 3: Implement Synthesizer scaffold and flat segment

- `__init__`: create TileGrid, initialize cursor (x=0, y=start_y, slope=0)
- `synthesize()`: loop over segments, dispatch by type
- `_rasterize_flat()`: for each pixel column, compute tile coords, set height_array
- `_fill_below()`: fill interior below surface tiles

**Verify:** Flat segment test — height_array values match expected uniform height.

## Step 4: Implement ramp segment

- `_rasterize_ramp()`: linear interpolation from cursor_y to cursor_y + rise
- Compute byte angle from rise/len
- Advance cursor_y by rise after rasterization

**Verify:** Ramp segment test — interpolated heights, cursor_y advancement.

## Step 5: Implement gap segment

- `_rasterize_gap()`: advance cursor_x by len, no tiles written

**Verify:** Gap segment test — no tiles in gap region, cursor advances.

## Step 6: Implement slope validation and discontinuity warnings

- Pre-rasterization: scan segments for slope ratio warnings/errors
- Discontinuity check: compare slope at segment boundaries
- Raise ValueError for unpassable slopes (ratio > 1.0)

**Verify:** Slope warning/error tests pass.

## Step 7: Implement CLI entry point and output writing

- argparse with two positional args
- Wire together: load → synthesize → validate → build meta → write
- Override meta player_start to None
- Combine pre-warnings + Validator issues for validation report
- Print summary to stdout

**Verify:** Integration test — end-to-end profile → output files.

## Step 8: Write complete test suite

Fill out all test classes from structure.md. Ensure:
- `uv run pytest tests/test_profile2stage.py -x` passes
- All acceptance criteria covered

**Verify:** Full test run passes.

## Step 9: Manual smoke test

Run the CLI on a sample profile and verify output is valid JSON that
matches the schema the game engine expects.

---

## Testing Strategy

- **Unit tests**: ProfileParser, each segment type, cursor state, slope validation
- **Integration tests**: full pipeline with temp directories, verify output files
  exist and parse as valid JSON with correct structure
- **Acceptance mapping**:
  - AC "flat segment produces height_array of [16]*16" → TestFlatSegment
  - AC "ramp segment produces linearly interpolated heights" → TestRampSegment
  - AC "gap segment produces no tiles" → TestGapSegment
  - AC "cursor_y correctly advanced" → TestCursorState
  - AC "output files written and parseable JSON" → TestIntegration
  - AC "slope warning at tan(30°)" → TestSlopeValidation
  - AC "error at ratio > 1.0" → TestSlopeValidation

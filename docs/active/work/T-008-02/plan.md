# Plan — T-008-02: synthetic-tile-grid-builders

## Step 1: Create `tests/grids.py` with internal helpers

Write the module skeleton with imports, constants, and internal helpers:
- `FILL_DEPTH = 4`
- `_wrap(tiles)` — dict-to-TileLookup wrapper
- `_fill_below(tiles, tx, ground_row)` — adds fill rows
- `_slope_height_array(angle_byte, col_offset)` — computes height array from angle

**Verify:** Import the module from a Python REPL; no import errors.

## Step 2: Implement `build_flat`

Simplest builder. Place flat tiles at `ground_row`, fill below.

**Verify:** Write `TestBuildFlat` in `tests/test_grids.py`:
- Surface tile count == width_tiles
- All surface tiles have height=[16]*16, angle=0, solidity=FULL
- Fill tiles exist at ground_row+1 through ground_row+4
- Lookup returns None outside the grid

## Step 3: Implement `build_gap`

Flat approach, empty gap, flat landing. No complex geometry.

**Verify:** Write `TestBuildGap`:
- Approach tiles present and flat
- Gap coordinates return None
- Landing tiles present and flat
- Fill below approach and landing, not below gap

## Step 4: Implement `build_slope`

Constant-angle slope. Uses `_slope_height_array`.

**Verify:** Write `TestBuildSlope`:
- Approach tiles flat
- Slope tiles have the specified angle
- Height arrays are monotonically increasing or decreasing (depending on angle sign)
- All heights in [0, 16]

## Step 5: Implement `build_ramp`

Linear angle interpolation across ramp tiles. Uses `_slope_height_array`.

**Verify:** Write `TestBuildRamp`:
- Approach tiles flat
- Ramp tile angles progress from start_angle toward end_angle
- First ramp tile angle close to start_angle, last close to end_angle
- Height arrays vary tile-to-tile

## Step 6: Implement `build_loop`

Circle geometry for full 360° loop. Most complex builder.

Sub-steps:
1. Flat approach section
2. Circle math: for each pixel column, compute top/bottom arc positions
3. Map pixel positions to tile grid, set height_array columns to 16
4. Assign solidity: TOP_ONLY for upper arc tiles, FULL for lower
5. Set tile_type = SURFACE_LOOP on all loop tiles
6. Leave interior hollow (no tiles between upper and lower arcs)
7. Fill below the lowest loop tile per column
8. Optional ramp_radius: add quarter-circle entry/exit ramps
9. Flat exit section

**Verify:** Write `TestBuildLoop`:
- Approach tiles flat
- Loop tiles have tile_type == SURFACE_LOOP
- Upper arc tiles have solidity == TOP_ONLY
- Lower arc tiles have solidity == FULL
- Interior tiles are None (hollow)
- Fill below loop exists
- With ramp_radius: transition tiles exist between approach and loop
- Angle range covers all quadrants (0–255 spread)

## Step 7: Run full test suite

```
uv run pytest tests/ -x
```

Verify no regressions in existing tests, all new tests pass.

## Testing strategy

- **Unit tests per builder** in `tests/test_grids.py`
- Each test class covers:
  - Correct tile presence (surface layer has tiles, outside is None)
  - Correct tile properties (height_array, angle, solidity, tile_type)
  - Fill below surface exists
  - Edge cases: 1-tile width, angle=0 (degenerate ramp/slope)
- **No integration tests** needed — these are test utilities, not game code
- **No Pyxel** — all tests run without display

# Review — T-008-02: synthetic-tile-grid-builders

## Summary of changes

### Files created

**`tests/grids.py`** — Synthetic tile-grid builder module (258 lines)
- 5 public builders: `build_flat`, `build_gap`, `build_slope`, `build_ramp`, `build_loop`
- 4 internal helpers: `_wrap`, `_flat_tile`, `_fill_below`, `_slope_height_array`
- 1 module constant: `FILL_DEPTH = 4`
- All builders return `TileLookup` (callable `(tx, ty) -> Tile | None`)
- No Pyxel imports. Depends only on `speednik.terrain`.

**`tests/test_grids.py`** — Tests for the grid builders (199 lines)
- 5 test classes, 27 tests total
- `TestBuildFlat` (5 tests): surface tiles, properties, fill, bounds, edge case
- `TestBuildGap` (4 tests): approach, gap emptiness, landing, fill
- `TestBuildSlope` (5 tests): approach flat, angle, heights in range, fill, zero-angle
- `TestBuildRamp` (5 tests): approach flat, angle progression, heights, single tile, fill
- `TestBuildLoop` (8 tests): approach, loop type, TOP_ONLY, FULL, hollow interior, fill, ramp_radius, angle coverage

### Files modified

None.

## Test coverage

- **27 new tests**, all passing
- **720 total tests** pass (0 failures, 0 regressions)
- Each builder has dedicated tests covering:
  - Tile presence at expected coordinates
  - Tile properties (height_array, angle, solidity, tile_type)
  - Fill below surface exists
  - Boundary conditions (returns None outside grid)

### Coverage gaps

- No test for `build_slope` with negative angles (e.g., downhill slopes using byte angles > 128). The height array computation handles this via `math.tan()` which returns negative values for those angles, but no test explicitly exercises it.
- No test for extremely large radii in `build_loop`. With `radius >> ground_row * TILE_SIZE`, the loop would extend into negative tile rows. The builder doesn't clip to a grid boundary — it just stores negative ty values in the dict, which is fine for TileLookup but might surprise callers.
- No test for `build_ramp` with angle wraparound (e.g., `start_angle=250, end_angle=10`). The linear interpolation in byte-angle space would produce wrong results for this case. Not currently needed by any test scenario, but worth noting.

## Acceptance criteria status

- [x] `build_flat` returns a TileLookup with flat ground + fill below
- [x] `build_ramp` returns a TileLookup with flat approach + angle-interpolated ramp
- [x] `build_loop` returns a TileLookup with flat approach + full 360° loop + flat exit
- [x] `build_loop` with `ramp_radius` includes entry/exit transition arcs
- [x] `build_gap` returns a TileLookup with approach + gap + landing
- [x] `build_slope` returns a TileLookup with approach + constant-angle slope
- [x] All builders produce tiles with correct height arrays for their geometry
- [x] All builders include ground fill below the surface
- [x] No Pyxel imports
- [x] Loop builder: upper arc tiles have `solidity=TOP_ONLY`, lower arc `solidity=FULL`
- [x] Loop builder: interior tiles are absent (hollow)
- [x] Self-tests: each builder's output passes sanity checks
- [x] `uv run pytest tests/ -x` passes

## Open concerns

1. **Byte-angle wraparound in `build_ramp`**: Linear interpolation between angles near the 0/255 boundary (e.g., 250→10) would traverse the long way around. Not needed now, but if future scenarios need this, the interpolation should go through modular arithmetic.

2. **Loop ramp tile placement**: Entry/exit ramp tiles are placed at `ground_row` regardless of the actual arc height. For large ramp radii where the arc surface rises above ground_row, this could place tiles in the wrong row. Works correctly for the expected use case (ramp_radius ≈ radius).

3. **`_slope_height_array` baseline**: The height array centers at height 8 (middle of tile). This means a single flat-angle tile produces `[8]*16` rather than `[16]*16`. This is by design — the slope builders place tiles at `ground_row`, so the surface sits mid-tile. The `build_flat` builder uses `_flat_tile()` directly (which gives `[16]*16`) rather than `_slope_height_array(0)`, so there's no inconsistency in the flat case.

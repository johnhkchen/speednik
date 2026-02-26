# Structure — T-012-06-BUG-03: slope-adhesion-fails-at-byte-angle-35

## Files Modified

### 1. `speednik/grids.py`

**Remove:** `_slope_height_array` function (lines 45–67). Becomes dead code.

**Rewrite:** `build_slope` function (lines 120–151). New implementation uses pixel-column
tracing instead of per-tile height array generation.

#### New `build_slope` Algorithm

```
def build_slope(approach_tiles, slope_tiles, angle, ground_row):
    tiles = {}

    # Flat approach (unchanged)
    for tx in range(approach_tiles):
        tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    # Slope surface: trace pixel by pixel
    angle_rad = angle * 2π / 256
    slope = tan(angle_rad)  # rise per pixel (positive = ascending)
    base_y = (ground_row + 1) * TILE_SIZE  # bottom of ground_row tile = surface baseline
    slope_start_px = approach_tiles * TILE_SIZE

    for i in range(slope_tiles * TILE_SIZE):
        px = slope_start_px + i
        # Surface y: starts at base_y and rises (y decreases in screen coords)
        surface_y = base_y - i * slope

        tx = px // TILE_SIZE
        ty = int(surface_y) // TILE_SIZE
        local_x = px % TILE_SIZE
        tile_bottom_y = (ty + 1) * TILE_SIZE

        # Create tile if needed
        if (tx, ty) not in tiles:
            tiles[(tx, ty)] = Tile(height_array=[0]*16, angle=angle, solidity=FULL)

        # Set height at this column
        h = clamp(round(tile_bottom_y - surface_y), 0, 16)
        tiles[(tx, ty)].height_array[local_x] = max(tiles[(tx, ty)].height_array[local_x], h)

        # Fill below
        _fill_below(tiles, tx, ty)

    return tiles, _wrap(tiles)
```

Key properties:
- Tiles are placed at whatever (tx, ty) the surface falls in — multi-row
- Height arrays computed from actual pixel-level surface position
- Fill below each surface tile
- Tile angle set to the slope's byte angle (constant across all slope tiles)
- `max()` on height ensures overlapping columns in the same tile take the higher value

#### Interface Preservation

`build_slope` signature is unchanged: `(approach_tiles, slope_tiles, angle, ground_row)`.
Return type unchanged: `tuple[dict[tuple[int, int], Tile], TileLookup]`.

The semantic meaning of `slope_tiles` shifts slightly: it now controls the horizontal
extent in tile-widths (slope_tiles * 16 pixels), not the number of tiles placed. This is
consistent with its original meaning (the slope spanned slope_tiles * 16 pixels horizontally
before too).

### 2. `tests/test_mechanic_probes.py`

**Modify:** `TestSlopeAdhesion.test_slope_stays_on_ground` parametrization (lines ~513-526).

- Remove `xfail` marks for angles 35, 40, 45
- Extend test range to cover more angles if desired (but keep existing range as minimum)
- Adjust `slope_start_x` and `slope_end_x` bounds: these are pixel coordinates that
  should remain `5 * TILE_SIZE` to `20 * TILE_SIZE` (approach_tiles=5, total=20 tiles
  of horizontal extent). The player may now be at varying y positions within this x range,
  but the x-based region filter still works.

## Files NOT Modified

- `speednik/terrain.py` — sensor system is correct; the issue was tile data, not sensors
- `speednik/physics.py` — slip/ground physics unchanged
- `speednik/constants.py` — no constant changes needed
- `speednik/player.py` — no changes

## Module Boundaries

- `grids.py` remains a pure data module (no Pyxel imports, no side effects)
- `build_slope` continues to return `(tiles_dict, TileLookup)` — no API changes
- Other callers of `build_slope` (only in tests) are unaffected by the fix since the
  function signature and return type are preserved

## Risk Assessment

- **Low risk**: `build_slope` is only used by test infrastructure (`test_mechanic_probes.py`),
  not by real stage loading. Real stages use artist-authored tiles loaded from `tile_map.json`.
- **Behavioral change**: Slopes at angle >= 35 will now maintain ground contact, which
  changes the test expectations (from xfail to pass). No other tests reference `build_slope`
  at steep angles.
- **Edge case**: At angle 0 (flat), `slope = tan(0) = 0`, so `surface_y = base_y` for all
  pixels. All tiles land in `ground_row` with height=16 (full tile). This matches the
  current flat behavior.

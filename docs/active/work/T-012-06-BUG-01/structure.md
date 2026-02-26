# Structure: T-012-06-BUG-01 — synthetic-loop-no-ceiling-quadrant

## Files Modified

### `speednik/grids.py` — Loop circle generation (Phase 3)

**What changes**: The loop circle section (lines 273-327) is rewritten to produce
geometrically accurate tiles.

**No changes to**: Flat approach (Phase 1), entry ramp (Phase 2), solidity fixup
logic (Phase 4 -- removed, integrated into Phase 3), exit ramp (Phase 5), flat exit.

#### Current loop circle logic (lines 278-327)

```python
for px in range(loop_start, loop_end):
    # ... compute arc positions ...
    tiles[key_b].height_array[local_x] = TILE_SIZE   # BUG: always 16
    tiles[key_b].angle = angle_bottom                  # BUG: overwrites per-pixel
    tiles[key_t].height_array[local_x] = TILE_SIZE   # BUG: always 16
    tiles[key_t].angle = angle_top                     # BUG: overwrites per-pixel
```

#### New loop circle logic

Restructured into two passes:

**Pass 1: Collect per-pixel data**

For each pixel column in `[loop_start, loop_end)`:
- Compute bottom arc Y: `y_bottom = cy + sqrt(r^2 - dx^2)`
- Compute top arc Y: `y_top = cy - dy`
- Store `(px, y_bottom, y_top, angle_bottom, angle_top)` in a list
- Record which tile keys are bottom-arc vs top-arc

**Pass 2: Build tiles from collected data**

For each unique tile key:
- Compute height array from per-pixel arc positions
- Bottom arc tile: `height[col] = clamp(tile_bottom_y - y_bottom, 0, 16)`
- Top arc tile: `height[col] = clamp(y_top - tile_top_y, 0, 16)`
  (solid from bottom = how far down the solid extends from the top)
  Actually: height_array measures solid from the bottom of the tile.
  For ceiling tiles, the solid part is at the top. So:
  `height[col] = clamp(TILE_SIZE - (y_top - tile_top_y), 0, 16)`
  Wait -- let me reconsider. Height array = solid pixels from bottom.
  For a ceiling tile where the surface is at y_top within the tile:
  - tile spans [tile_top, tile_top + 16)
  - solid is from tile_top down to y_top (the "underside" of the ceiling)
  - solid from bottom = 0 if the solid is at the top? No.
  - height_array[col] represents h pixels of solid at the bottom of the tile.
  - For floor tiles: surface at y, solid below. height = tile_bottom - y.
  - For ceiling tiles in a loop: we need the sensor system to find the ceiling
    surface when casting UP. The UP cast looks for `solid_top_y = tile_y * TILE_SIZE + (TILE_SIZE - height)`.
  - So for a ceiling surface at `y_top`: `solid_top_y = y_top` means
    `height = TILE_SIZE - (y_top - tile_top_y)`.
  - Actually: `solid_top_y = tile_top + (16 - height)`, so `height = tile_top + 16 - solid_top_y`.
  - For the ceiling surface at y_top: `height = tile_bottom - y_top` where `tile_bottom = tile_top + 16`.

  **Result**: `height[col] = clamp(tile_bottom_y - y_top, 0, 16)`.
  This is actually the same formula as for floor tiles -- just using y_top instead
  of y_bottom. The height array always measures "solid pixels from the bottom of the tile."

- Compute tile angle from midpoint pixel: use the center pixel column of the tile's
  arc span to get a representative angle.
- Set solidity:
  - Bottom-only tiles: `FULL`
  - Top-only tiles: `FULL` (changed from TOP_ONLY; see Design rationale)
  - Both-arc tiles: `FULL`
- Set `tile_type = SURFACE_LOOP` for all loop circle tiles

#### Solidity fixup (Phase 4) — Simplified

Previous Phase 4 toggled solidity between TOP_ONLY and FULL based on upper_tiles vs
lower_tiles sets. With the new approach, all loop tiles are FULL, so the fixup pass
is simplified or removed.

### `tests/test_mechanic_probes.py` — Remove xfail markers

**What changes**: Remove or adjust `xfail` markers on `test_loop_traverses_all_quadrants`
for radii where the fix enables full traversal.

**Approach**: Run the tests after the fix. Remove xfail for passing radii. If some
radii still fail (e.g., very small radius 32 where tile resolution is too coarse),
keep those xfail markers with updated reasons.

## Files NOT Modified

- `speednik/terrain.py` — No engine changes needed
- `speednik/physics.py` — No physics changes needed
- `speednik/simulation.py` — No simulation changes needed
- `speednik/constants.py` — No constant changes needed
- `speednik/player.py` — No player logic changes needed
- `speednik/invariants.py` — Invariants already exempt SURFACE_LOOP
- `tests/test_elementals.py` — Tests pass or use different grid configuration

## Module Boundaries

The fix is entirely within `build_loop()` in `grids.py`. The function signature and
return type are unchanged. The tiles dictionary and TileLookup callable have the same
shape. The only difference is that the tiles contain **accurate** height arrays and
angles instead of the current all-full/overwritten values.

## Ordering

1. Fix `build_loop()` geometry
2. Run existing tests to verify no regressions
3. Remove xfail markers for tests that now pass
4. Run full test suite

## Interface Contracts

- `Tile.height_array`: 16 ints, each 0-16 (unchanged)
- `Tile.angle`: byte angle 0-255 (unchanged)
- `Tile.solidity`: FULL for all loop tiles (was mixed FULL/TOP_ONLY)
- `Tile.tile_type`: SURFACE_LOOP for all loop tiles (unchanged)
- `build_loop()` return type: `tuple[dict[tuple[int,int], Tile], TileLookup]` (unchanged)

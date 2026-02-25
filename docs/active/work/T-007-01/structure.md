# T-007-01 Structure: Loop Entry/Exit Ramps

## Files Modified

### `tools/svg2stage.py`

**New function: `_rasterize_ramps()`**

Location: New method on the `Rasterizer` class, added between `_rasterize_loop()` and `_fill_interior()`.

```
def _rasterize_ramps(self, cx, cy, r, r_ramp):
    """Generate entry and exit quarter-circle ramp tiles for a loop."""
```

Signature:
- `cx, cy`: Loop circle center (float)
- `r`: Loop circle radius (float)
- `r_ramp`: Ramp arc radius (float), typically equal to `r`

Responsibilities:
1. Compute entry ramp tiles for x range `[cx - r - r_ramp, cx - r]`
2. Compute exit ramp tiles for x range `[cx + r, cx + r + r_ramp]`
3. For each pixel column in range:
   - Compute arc surface y from quarter-circle equation
   - Compute tangent angle using same convention as `_compute_segment_angle`
   - Create tile with `surface_type=SURFACE_SOLID`, computed height_array and angle
4. Fill below each ramp surface tile with fully-solid ground tiles

**Modified function: `_rasterize_loop()`**

Change: Add a call to `self._rasterize_ramps(cx, cy, r, r_ramp)` at the top of the method, BEFORE the existing loop segment rasterization.

The loop radius `r` must be inferred from the shape's segments. The segments are produced by `_ellipse_perimeter_segments(cx, cy, r, r)` which samples points on a circle — the radius can be computed as the distance from the center to any segment point.

Updated flow:
```python
def _rasterize_loop(self, shape):
    cx, cy = shape.center.x, shape.center.y
    # Compute radius from first segment point
    p0 = shape.segments[0].points[0]
    r = math.hypot(p0.x - cx, p0.y - cy)
    r_ramp = r  # ramp radius = loop radius

    # Generate ramps FIRST (loop tiles overwrite at tangent points)
    self._rasterize_ramps(cx, cy, r, r_ramp)

    # Existing loop rasterization (unchanged)
    for seg in shape.segments:
        ...
```

### `tests/test_svg2stage.py`

**New test class: `TestRampRasterization`**

Location: After existing `TestLoopRasterization` class.

Tests:
1. `test_ramp_tiles_created` — Entry and exit ramps produce tiles outside loop x-range
2. `test_ramp_surface_type_solid` — All ramp tiles have `surface_type == SURFACE_SOLID`
3. `test_ramp_entry_angle_progression` — Entry ramp angles increase from ~0 to ~64 left-to-right
4. `test_ramp_exit_angle_progression` — Exit ramp angles decrease from ~192 to ~0 left-to-right
5. `test_ramp_ground_fill` — Tiles below ramp surface are fully solid
6. `test_ramp_loop_junction_no_gap` — No tile gap at entry ramp → loop and loop → exit ramp
7. `test_ramp_height_arrays_nonzero` — Ramp surface tiles have meaningful height values

Test setup: Create a `TerrainShape` with `is_loop=True`, `center=Point(200,100)` using `_ellipse_perimeter_segments(200, 100, 64, 64)`. Rasterize with adequate grid dimensions. Inspect tiles in expected ramp regions.

## Files NOT Modified

- `speednik/terrain.py` — No changes. Wall angle gate already handles ramp angles ≤ 48.
- `speednik/level.py` — No changes. Reads tile_map.json format unchanged.
- `speednik/physics.py` — No changes.
- `speednik/constants.py` — No changes.
- `stages/hillside_rush.svg` — No changes. Same SVG source, pipeline produces better output.

## Module Boundaries

The ramp logic is entirely contained within `tools/svg2stage.py`:
- `_rasterize_ramps()` is a private method of `Rasterizer`, called only from `_rasterize_loop()`
- No new public API surfaces
- No new constants needed (uses existing `SURFACE_SOLID`, `FULL`, `TILE_SIZE`)
- No new data classes needed (uses existing `TileData`)

## Ordering of Changes

1. Add `_rasterize_ramps()` method to `Rasterizer` class
2. Modify `_rasterize_loop()` to compute radius and call `_rasterize_ramps()`
3. Add tests to `tests/test_svg2stage.py`
4. Run pipeline on `hillside_rush.svg` to verify output
5. Run `pytest tests/test_svg2stage.py` to verify tests pass

## Data Flow

```
SVG circle element
  → SVGParser._parse_circle()
    → TerrainShape(is_loop=True, center=Point(cx,cy), segments=[...])
      → Rasterizer._rasterize_shape()
        → Rasterizer._rasterize_loop()
          → NEW: Rasterizer._rasterize_ramps(cx, cy, r, r_ramp)
            → Places SURFACE_SOLID tiles for entry arc
            → Places SURFACE_SOLID tiles for exit arc
            → Fills below ramp tiles with solid ground
          → Existing: loop segment rasterization (overwrites at tangent points)
            → Places SURFACE_LOOP tiles for loop circle
      → StageWriter.write()
        → tile_map.json: ramp tiles appear as type=1 (SOLID), loop tiles as type=5 (LOOP)
        → collision.json: ramp tiles = 2 (FULL), loop tiles = 2 or 1 (FULL/TOP_ONLY)
```

# Plan — T-010-16: directional-terrain-raycast

## Step 1: Add `_pixel_is_solid` helper to terrain.py

**What**: Add a module-private function that checks whether an integer pixel coordinate is
inside solid terrain, using the tile lookup and height array.

**Where**: `speednik/terrain.py`, in a new section before "Top-level collision resolution"
(before the `_GROUND_SNAP_DISTANCE` constant, around line 681).

**Logic**:
```
floor-divide px, py to get tile_x, tile_y, col, row
tile = tile_lookup(tile_x, tile_y)
if tile is None or tile.solidity == NOT_SOLID → (False, 0)
height = tile.height_array[col]
solid if row >= TILE_SIZE - height → (True, tile.angle)
else → (False, 0)
```

**Verify**: No test needed for the private helper directly. It's verified through Step 2.

---

## Step 2: Add `cast_terrain_ray` to terrain.py

**What**: Add the public raycast function immediately after `_pixel_is_solid`.

**Logic**:
```
Convert angle_deg to radians
Compute dx = cos(rad), dy = sin(rad)
Walk step=0 to int(max_range):
    px = floor(origin_x + step * dx)
    py = floor(origin_y + step * dy)
    if _pixel_is_solid(tile_lookup, px, py):
        distance = step (integer, but as float)
        return (distance, surface_angle)
return (max_range, 0)
```

Note: Using step as the distance (integer increments of 1 pixel along the ray) is an
approximation. The true Euclidean distance from origin to (px, py) is `step` since we move
1 unit along the direction vector per step (cos²+sin²=1). So `step` IS the Euclidean
distance. This is exact.

**Verify**: Manual check — `step * (cos² + sin²) = step * 1 = step`. Correct.

---

## Step 3: Add `TestCastTerrainRay` to test_terrain.py

**Import**: Add `cast_terrain_ray` to the import block.

**Test cases** (each is a separate test method):

### 3a: `test_ray_down_to_flat_ground`
- Flat tile at grid (0, 2). Surface at y=32.
- Origin (8, 16), angle=90° (straight down), max_range=128.
- Expected: distance=16.0 (from y=16 to y=32), angle=tile's angle.

### 3b: `test_ray_horizontal_no_obstacle`
- No tiles in the grid (empty lookup).
- Origin (8, 8), angle=0° (right), max_range=128.
- Expected: (128.0, 0) — nothing found.

### 3c: `test_ray_horizontal_into_wall`
- Full tile at grid (2, 0). Left edge at x=32.
- Origin (8, 8), angle=0° (right), max_range=128.
- Expected: distance=24.0 (from x=8 to x=32), angle=tile's angle.

### 3d: `test_ray_open_air`
- Empty grid, any angle.
- Expected: (max_range, 0).

### 3e: `test_ray_45_degrees_down_right`
- Flat tile at grid (3, 3). Surface at y=48.
- Origin (8, 8), angle=45°, max_range=128.
- Ray hits surface when py reaches 48. At 45°, dy=sin(45°)≈0.707.
- Steps needed: (48-8)/0.707 ≈ 56.6 → step 57 (approximately).
- Test with approximate assertion (±2 pixels for floating-point stepping).

### 3f: `test_ray_origin_inside_solid`
- Full tile at grid (0, 0) covering (0,0)-(16,16).
- Origin (8, 8), angle=0°, max_range=128.
- Expected: distance ≈ 0 (first pixel is already solid), angle=tile's angle.

### 3g: `test_ray_down_to_half_height_tile`
- Half-height tile (height=8) at grid (0, 1). Surface at y=16+(16-8)=24.
- Origin (8, 8), angle=90° (down), max_range=128.
- Expected: distance=16.0 (from y=8 to y=24), angle=tile's angle.

### 3h: `test_surface_angle_returned`
- Tile with angle=42 at a known position.
- Ray hits the tile.
- Assert returned surface_angle == 42.

### 3i: `test_max_range_clamp`
- Tile at a position beyond max_range.
- max_range=32, surface at distance 48.
- Expected: (32.0, 0) — not reached.

### 3j: `test_ray_up`
- Ceiling tile at grid (0, 0). Full tile, bottom at y=16.
- Origin (8, 24), angle=270° (straight up), max_range=128.
- Expected: distance=8.0 (from y=24 up to y=16), angle=tile's angle.

---

## Step 4: Run full test suite

```
uv run pytest tests/ -x
```

All existing tests must pass (no regressions). All new tests must pass.

---

## Testing Strategy

- **Unit tests**: All in `TestCastTerrainRay` class using synthetic tile grids (same pattern
  as existing tests: `make_tile_lookup`, `flat_tile`, `half_height_tile`).
- **Geometric correctness**: Tests verify distance values against hand-computed expected
  values for known configurations.
- **Edge cases**: Empty grid (miss), origin inside solid (immediate hit), max_range exceeded.
- **Angle propagation**: Verify the tile's byte angle is returned, not a computed value.
- **No integration tests needed**: The function is pure (no side effects, no state mutation).
  Observation integration is T-010-17's scope.

---

## Commit Plan

Single commit after all code and tests pass:
```
feat: add cast_terrain_ray for directional observation raycasts (T-010-16)
```

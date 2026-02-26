# Progress — T-010-16: directional-terrain-raycast

## Completed

### Step 1: Added `_pixel_is_solid` helper (terrain.py:684–699)
- Module-private function that checks if an integer pixel coordinate is inside solid terrain
- Uses `tile_lookup`, `height_array`, and `TILE_SIZE` to determine occupancy
- Returns `(is_solid, tile_angle)` tuple
- Treats NOT_SOLID tiles as empty; all other solidity flags (FULL, TOP_ONLY, LRB_ONLY) are solid

### Step 2: Added `cast_terrain_ray` function (terrain.py:702–727)
- Public function with signature matching the ticket spec
- Step-based raycasting: walks 1 pixel at a time along the ray direction
- Converts angle_deg to radians, computes dx/dy from cos/sin
- At each step, floors the position and calls `_pixel_is_solid`
- Returns `(float(step), angle)` on hit, or `(max_range, 0)` on miss
- Default max_range=128.0

### Step 3: Added `TestCastTerrainRay` test class (test_terrain.py:817–900)
- 12 test methods covering all acceptance criteria:
  - `test_ray_down_to_flat_ground` — 90° ray, exact distance
  - `test_ray_horizontal_no_obstacle` — empty grid, returns max_range
  - `test_ray_horizontal_into_wall` — 0° ray hits wall
  - `test_ray_open_air` — empty grid, 45° angle
  - `test_ray_45_degrees_down_right` — diagonal ray, approximate distance
  - `test_ray_origin_inside_solid` — immediate hit, distance=0
  - `test_ray_down_to_half_height_tile` — partial-height tile
  - `test_surface_angle_returned` — angle propagation
  - `test_max_range_clamp` — surface beyond max_range not detected
  - `test_ray_up_to_ceiling` — 270° ray upward
  - `test_not_solid_tile_ignored` — NOT_SOLID tiles are invisible
  - `test_top_only_tile_is_solid_for_rays` — one-way platforms visible to rays

### Step 4: Full test suite verification
- `uv run pytest tests/ -x` → 1147 passed, 16 skipped, 5 xfailed, 0 failures
- No regressions in any existing tests

## Deviations from Plan

None. Implementation followed the plan exactly.

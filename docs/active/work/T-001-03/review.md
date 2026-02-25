# T-001-03 Review: Tile Collision System

## Summary of Changes

### Files Created
- **speednik/terrain.py** (~480 lines) — Complete tile collision system
- **tests/test_terrain.py** (~390 lines) — 61 unit tests

### Files Modified
- None. physics.py and constants.py unchanged.

## Architecture

The collision system follows the same pattern established by T-001-02: dataclasses for data, module functions for logic, mutation in place.

**Data structures:**
- `Tile` — 16×16 collision tile with height_array (16 ints), angle (0–255), solidity flag
- `SensorResult` — found flag, distance to surface, tile angle
- `TileLookup` — callable type alias for tile map access

**Core flow:**
1. `resolve_collision(state, tile_lookup)` — entry point, steps 5–7 of frame loop
2. Calls `find_floor()`, `find_wall_push()`, `find_ceiling()` in priority order
3. Each sensor function computes sensor positions based on quadrant and radii
4. Each cast dispatches to `_sensor_cast_down/up/left/right` based on direction
5. Each cast reads height_array (or width_array), handles extension/regression, returns distance

**Quadrant rotation** is the key design insight: `get_quadrant(angle)` maps byte angle to 0–3, and a lookup table rotates sensor directions. The same sensor code handles floor, wall, ceiling, and loop traversal.

## Acceptance Criteria Coverage

| Criterion | Status | Tests |
|-----------|--------|-------|
| Tile data structure (height_array, angle, solidity) | ✓ | TestTile (5 tests) |
| Top-only tile behavior | ✓ | TestSensorCastDown (2), TestFloorSensors (2), TestResolveCollision (1) |
| Height array lookup | ✓ | TestSensorCastDown (7 tests) |
| Width array (rotated 90°) | ✓ | TestTile (4), TestSensorCastHorizontal (3) |
| A/B floor sensors with A-wins-ties | ✓ | TestFloorSensors (6 tests) |
| C/D ceiling sensors | ✓ | TestCeilingSensors (3 tests) |
| E/F wall sensors, disabled when moving away | ✓ | TestWallSensors (4 tests) |
| Sensor positions respect state (standing vs rolling) | ✓ | TestWallSensors::test_rolling |
| Sensor range 32px max | ✓ | TestSensorCastDown::test_beyond_max_range |
| Angle quadrant mode switching | ✓ | TestAngleQuadrantSwitching (4 tests), TestGetQuadrant (14 tests) |
| Tile-boundary crossing | ✓ | TestFloorSensors::test_tile_boundary_crossing |
| Landing: snap angle, recalculate speed | ✓ | TestLanding (2), TestResolveCollision (2) |
| Unit tests for all required scenarios | ✓ | 61 tests total |

## Test Coverage

**61 tests across 12 test classes:**
- TestTile: 5 (data structure, width_array computation)
- TestGetQuadrant: 14 (all four quadrants, all boundaries)
- TestSensorCastDown: 9 (flat, empty, full, slope, extension, regression, top-only, range)
- TestSensorCastUp: 3 (ceiling, no ceiling, top-only filter)
- TestSensorCastHorizontal: 3 (wall left, wall right, no wall)
- TestFloorSensors: 6 (flat ground, boundary, ties, top-only, B-closer)
- TestCeilingSensors: 3 (detected, none, top-only)
- TestWallSensors: 4 (right, disabled, left, rolling)
- TestResolveCollision: 8 (grounded, ledge, landing, angle snap, slope, wall, ceiling, top-only)
- TestAngleQuadrantSwitching: 4 (all modes, loop traversal)
- TestLanding: 2 (angle snap, speed recalculation)

**Regression:** All 37 pre-existing physics tests still pass. 98 total.

## Design Decisions Worth Noting

1. **TileLookup as callable:** Tests use `dict.get` wrapped in a lambda. Level loader will implement this interface when built. Clean decoupling.

2. **Width array computed, not stored:** `Tile.width_array()` computes on each call. Only called for wall sensors (2 calls/frame). Trade-off: no sync bugs, trivially cheap.

3. **Landing threshold (_AIR_LAND_DISTANCE = 16px):** Airborne players use rolling radii, so their feet are higher than standing. A strict `distance <= 0` check misses landings where the player is slightly above the surface. 16px provides reasonable snap range.

## Open Concerns

1. **Width array directionality:** The current `width_array()` counts consecutive solid columns from the LEFT. This works for walls where the solid region starts from one edge, but for walls with complex geometry (e.g., a slope viewed from the side), this could produce incorrect widths. Real Sonic 2 uses pre-authored width arrays per tile, not computed ones. This will need validation when real level data is available.

2. **Ceiling sensor upward cast:** The `_sensor_cast_up` function has complex coordinate math for determining the surface position. The comments inline show the reasoning, but this area deserves extra scrutiny during integration with real levels.

3. **Wall sensor direction in non-normal quadrants:** In quadrants 1 and 3, wall sensors cast vertically and the "moving away" check uses y_vel. This is correct per spec but hasn't been integration-tested with actual loop geometry.

4. **No angle 255 sentinel handling:** The spec says angle 255 means "use nearest 90° cardinal direction." The current implementation treats 255 as a normal angle (which maps to quadrant 0 / ~359°). This will need a special case when levels use this sentinel.

5. **LRB_ONLY solidity:** Defined as a constant but not specifically tested. It passes through _no_top_only_filter (returns True since it's not NOT_SOLID or TOP_ONLY). Correct behavior, but a dedicated test would add confidence.

6. **Negative coordinate handling:** `int(sensor_x) // TILE_SIZE` with negative coordinates gives floor division, which is correct. But `int(sensor_x) % TILE_SIZE` with negative x gives negative remainders in some cases. This shouldn't matter in practice (levels start at x=0) but could be a subtle bug source.

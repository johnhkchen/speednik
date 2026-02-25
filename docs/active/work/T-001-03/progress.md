# T-001-03 Progress: Tile Collision System

## Completed Steps

### Step 1–2: Tile data structures + Quadrant mapping ✓
- Created `speednik/terrain.py` with Tile dataclass (height_array, angle, solidity, width_array method)
- SensorResult dataclass
- TileLookup type alias
- Solidity constants (NOT_SOLID, TOP_ONLY, FULL, LRB_ONLY)
- Direction constants (DOWN, RIGHT, UP, LEFT)
- `get_quadrant(angle)` mapping byte angles to quadrants 0–3

### Step 3–4: Vertical + Horizontal sensor casts ✓
- `_sensor_cast_down` with extension (height=0 → tile below) and regression (height=16 → tile above)
- `_sensor_cast_up` — mirror of down cast for ceiling detection
- `_sensor_cast_right` and `_sensor_cast_left` using width_array
- All casts enforce MAX_SENSOR_RANGE (32px)
- Dispatcher `_sensor_cast()` maps direction constant to cast function

### Step 5: Floor sensor resolution (A/B) ✓
- `find_floor()` computes A/B positions based on quadrant and current radii
- Both sensors cast independently
- Shorter distance wins; A wins ties (deterministic)
- Top-only filter: skip when y_vel < 0

### Step 6: Ceiling sensor resolution (C/D) ✓
- `find_ceiling()` — mirror of floor, C/D at head position
- Top-only tiles never collide with ceiling sensors

### Step 7: Wall sensor resolution (E/F) ✓
- `find_wall_push()` for left/right wall detection
- Disabled when moving away from wall
- Uses WALL_SENSOR_EXTENT for position

### Step 8: Collision resolution ✓
- `resolve_collision()` — top-level function (steps 5–7 of frame loop)
- Floor: snap when on ground, land when airborne with y_vel >= 0 and surface in range
- Detach when no floor found while on ground
- Wall: push out, zero velocity toward wall
- Ceiling: push down, zero upward velocity
- Landing: snap angle to tile, call `calculate_landing_speed()` from physics.py

### Step 9: Integration verification ✓
- 98 tests total (37 physics + 61 terrain), all passing
- Zero regressions in test_physics.py

## Deviations from Plan

1. **Landing threshold:** Changed from `distance <= 0` (strictly at/past surface) to `distance <= _AIR_LAND_DISTANCE (16px)`. This is necessary because airborne players use rolling radii (shorter), and the sensor distance can be positive even when the player should land. The 16px threshold provides a reasonable snap range matching Sonic 2 behavior.

2. **Steps combined:** Steps 1+2 and 3+4 were implemented together since they were small and tightly coupled. Plan called for separate commits but combined implementation was more efficient.

## Commit

- `a6431a8` — Add tile collision system with sensors, quadrant rotation, and resolution (T-001-03)

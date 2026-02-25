# T-001-03 Structure: Tile Collision System

## File Changes

### New: speednik/terrain.py

The sole new production file. Contains all collision logic.

#### Constants & Types (top of file)

```python
# Solidity flags
NOT_SOLID = 0
TOP_ONLY = 1
FULL = 2
LRB_ONLY = 3

# Cast directions
DOWN = 0
RIGHT = 1
UP = 2
LEFT = 3

# Tile size
TILE_SIZE = 16

# Max sensor range (current tile + one adjacent)
MAX_SENSOR_RANGE = 32
```

Type alias:
```python
TileLookup = Callable[[int, int], Tile | None]
```

#### Dataclasses

**Tile:**
```python
@dataclass
class Tile:
    height_array: list[int]  # 16 values, 0–16
    angle: int               # 0–255 byte angle
    solidity: int            # NOT_SOLID / TOP_ONLY / FULL / LRB_ONLY

    def width_array(self) -> list[int]:
        """Height array rotated 90° for wall detection."""
```

**SensorResult:**
```python
@dataclass
class SensorResult:
    found: bool         # whether a surface was detected
    distance: float     # distance from sensor origin to surface
    tile_angle: int     # angle of the hit tile (for snapping)
```

#### Core Functions (internal)

**`get_quadrant(angle: int) -> int`**
Maps byte angle to quadrant 0–3:
- 0: 0–32, 224–255 (normal/floor mode)
- 1: 33–96 (right wall mode)
- 2: 97–160 (ceiling mode)
- 3: 161–223 (left wall mode)

**`_sensor_cast_vertical(sensor_x: float, sensor_y: float, direction: int, tile_lookup: TileLookup, solidity_filter: Callable) -> SensorResult`**
Single vertical sensor ray cast (for floor/ceiling sensors in normal/ceiling mode, wall sensors in wall modes).
- Determines which tile the sensor origin is in
- Reads height_array at the sensor's column within the tile
- Handles extension (height=0) and regression (height=16)
- Computes distance from sensor to detected surface
- Respects MAX_SENSOR_RANGE
- `solidity_filter` determines which tiles to collide with (handles top-only logic)

**`_sensor_cast_horizontal(sensor_x: float, sensor_y: float, direction: int, tile_lookup: TileLookup, solidity_filter: Callable) -> SensorResult`**
Single horizontal sensor ray cast (for wall sensors in normal/ceiling mode, floor/ceiling sensors in wall modes).
- Same logic as vertical but uses width_array and horizontal axis
- Extension/regression along horizontal axis

#### Public Sensor Functions

**`find_floor(state: PhysicsState, tile_lookup: TileLookup) -> SensorResult`**
- Computes A and B sensor positions based on quadrant and current radii
- Casts both sensors in the floor direction for the current quadrant
- Applies solidity filter: skip TOP_ONLY tiles when y_vel < 0
- Returns the result with shorter distance; A wins ties

**`find_ceiling(state: PhysicsState, tile_lookup: TileLookup) -> SensorResult`**
- Computes C and D sensor positions
- Casts in ceiling direction for current quadrant
- TOP_ONLY tiles never collide with ceiling sensors
- Returns shorter of C/D

**`find_wall_push(state: PhysicsState, tile_lookup: TileLookup, direction: int) -> SensorResult`**
- Computes E (left) or F (right) sensor position
- Casts in the wall direction for the current quadrant
- Disabled when moving away from the wall (check x_vel sign vs direction)
- TOP_ONLY tiles never collide with wall sensors
- Returns result for the single sensor

#### Top-Level Resolution

**`resolve_collision(state: PhysicsState, tile_lookup: TileLookup) -> None`**
The main entry point, called as step 5–7 of the frame loop.

1. Get current quadrant from state.angle
2. Run floor sensors (find_floor)
   - If on_ground and floor found within snap range: snap y, update angle
   - If on_ground and no floor: detach (on_ground = False, angle = 0)
   - If airborne and floor found at distance ≤ 0: land (on_ground = True, snap angle, call calculate_landing_speed)
3. Run wall sensors (find_wall_push for LEFT and RIGHT)
   - If wall found: push player out, zero velocity component toward wall
4. Run ceiling sensors (find_ceiling)
   - If ceiling found at distance ≤ 0: push down, zero upward velocity

Mutates `state` in place (consistent with physics.py pattern).

### New: tests/test_terrain.py

Test file for the collision system. Structure mirrors test_physics.py.

#### Test Classes

**TestTile:**
- height_array stores correct values
- width_array() computes correctly for flat, 45° slope, and full tiles

**TestGetQuadrant:**
- Angle 0 → quadrant 0 (normal)
- Angle 64 → quadrant 1 (right wall)
- Angle 128 → quadrant 2 (ceiling)
- Angle 192 → quadrant 3 (left wall)
- Boundary angles (32, 33, 96, 97, etc.)

**TestSensorCast:**
- Flat ground: sensor above flat tile returns correct distance
- Empty tile: extension to tile below
- Full tile: regression to tile above
- No tile found: returns found=False beyond 32px
- 45° slope: correct height at each column

**TestFloorSensors:**
- Standing on flat ground: A/B both find floor, snap correctly
- Tile boundary: A on one tile, B on next, smooth transition
- A wins ties: when A and B equidistant, result uses A's tile angle
- Top-only platform: pass through when y_vel < 0, land when y_vel >= 0

**TestCeilingSensors:**
- Hit ceiling: push down, zero y_vel
- No ceiling: no effect

**TestWallSensors:**
- Wall on right: push left
- Wall on left: push right
- Moving away: sensor disabled, no push
- Rolling narrows detection width

**TestResolveCollision:**
- Flat ground walking: stays on ground, angle = 0
- 45° slope adherence: angle snaps to slope tile's angle
- Landing from air: on_ground set, angle snapped, ground_speed recalculated
- Falling off edge: on_ground cleared, angle reset to 0
- Top-only pass-through: jumping through platform from below

**TestAngleQuadrantSwitching:**
- Right wall mode: sensors rotated, floor sensors cast right
- Ceiling mode: floor sensors cast up
- Loop traversal: continuous angle change through all four quadrants

### Modified: speednik/physics.py

**No modifications to existing functions.** The `calculate_landing_speed()` function is already public and will be called from terrain.py's `resolve_collision()`.

One import will be needed in terrain.py:
```python
from speednik.physics import PhysicsState, calculate_landing_speed, byte_angle_to_rad
```

### Modified: speednik/constants.py

No changes needed. All sensor constants already exist.

## Module Dependency Graph

```
constants.py ──→ physics.py ──→ (no collision dependency)
     │                ↑
     │                │
     └──→ terrain.py ─┘
              ↑
         test_terrain.py
```

terrain.py imports from both constants.py and physics.py. No circular dependencies.

## Public Interface Summary

Consumers of terrain.py use:
1. `Tile` — to construct tile maps
2. `TileLookup` — type alias for tile access callable
3. `resolve_collision(state, tile_lookup)` — the main integration point
4. Individual `find_floor`, `find_ceiling`, `find_wall_push` — for testing and advanced use
5. Solidity constants: `NOT_SOLID`, `TOP_ONLY`, `FULL`, `LRB_ONLY`

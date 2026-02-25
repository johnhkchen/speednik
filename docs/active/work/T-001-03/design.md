# T-001-03 Design: Tile Collision System

## Decision 1: Tile Data Representation

### Options

**A. Dataclass with stored width_array**
Store both height_array and width_array as fields. Pre-compute width_array on creation.
- Pro: Fast lookup, no per-frame computation.
- Con: Redundant data, width_array must stay synchronized.

**B. Dataclass with computed width_array property**
Store only height_array. Compute width_array on demand via a method.
- Pro: Single source of truth, no sync bugs.
- Con: Recomputation each call. But width_array is only needed for wall sensors (2 per frame), and it's 16 values — trivially cheap.

**C. Named tuple / plain dict**
Lightweight, no methods.
- Con: No type safety, no validation, inconsistent with PhysicsState pattern (dataclass).

### Decision: **B — Dataclass with computed width_array**

Follows T-001-02's pattern (dataclasses for data, functions for logic). Width array computation is trivial and infrequent. Single source of truth prevents sync bugs.

```python
@dataclass
class Tile:
    height_array: list[int]  # 16 values, 0–16
    angle: int               # 0–255
    solidity: int            # 0=not_solid, 1=top_only, 2=full, 3=lrb_only

    def width_array(self) -> list[int]: ...
```

## Decision 2: Tile Map Interface

### Options

**A. Concrete 2D array in terrain.py**
terrain.py owns a `TileMap` class wrapping a 2D list of `Tile | None`.
- Pro: Simple, self-contained.
- Con: Couples collision to storage format. Level loading may want different backing.

**B. Protocol / callback for tile lookup**
Collision functions accept a callable `(tile_x: int, tile_y: int) -> Tile | None`.
- Pro: Collision system is decoupled from storage. Tests pass lambdas or dicts. Level loader implements however it wants.
- Con: Slightly more abstract.

**C. Abstract base class**
- Con: Over-engineered for a callable. Python ABCs add ceremony.

### Decision: **B — Callable for tile lookup**

Type alias: `TileLookup = Callable[[int, int], Tile | None]`. Collision functions accept this. Tests construct simple dict-based lookups. Level.py will later provide the real implementation. This is the minimum viable interface.

## Decision 3: Sensor System Architecture

### Options

**A. Monolithic collision function**
One large function handles all sensors, all quadrants, all resolution.
- Con: Untestable, unreadable, unmaintainable.

**B. Sensor-per-function with quadrant dispatch**
- `sensor_cast(origin_x, origin_y, direction, tile_lookup) -> SensorResult`
- Direction encodes both axis and sign (down, up, left, right)
- Quadrant lookup maps player angle to sensor directions
- Floor/ceiling/wall resolution are separate functions that call sensor_cast

- Pro: Each sensor cast is testable in isolation. Quadrant rotation is a data table, not branching code. The spec's claim that "the same sensor code" works for all orientations is literally true.
- Con: More functions, but each is small and testable.

**C. OOP sensor objects**
- Con: Violates project pattern. PhysicsState is a dataclass, not an object graph.

### Decision: **B — Sensor-per-function with quadrant dispatch**

The key insight from the spec: "the player runs along walls and through loops using the exact same sensor code — the sensors rotate with the angle." This means one `sensor_cast()` function that works in any direction, with a quadrant table that maps angle ranges to sensor directions. The rotation is data, not code.

### SensorResult

```python
@dataclass
class SensorResult:
    found: bool
    distance: float    # signed distance to surface (negative = inside solid)
    tile_angle: int    # angle of the tile hit (for angle snapping)
    tile_x: int        # tile grid position
    tile_y: int        # tile grid position
```

## Decision 4: Quadrant Representation

The spec defines four angle ranges that rotate the sensor rig. In byte angles (0–255):
- Normal: 0–32, 224–255 (floor=down)
- Right wall: 33–96 (floor=right)
- Ceiling: 97–160 (floor=up)
- Left wall: 161–223 (floor=left)

Each quadrant defines directions for floor, ceiling, and wall sensors. Represent as an enum or constants mapping to (dx, dy) direction vectors.

### Decision: Integer constants + lookup table

```python
# Directions
DOWN, RIGHT, UP, LEFT = 0, 1, 2, 3

# Quadrant → (floor_dir, ceiling_dir, wall_axis)
QUADRANT_TABLE = {
    0: (DOWN, UP, "horizontal"),
    1: (RIGHT, LEFT, "vertical"),
    2: (UP, DOWN, "horizontal"),
    3: (LEFT, RIGHT, "vertical"),
}
```

Function `get_quadrant(angle: int) -> int` returns 0–3.

## Decision 5: Collision Resolution Strategy

### Options

**A. Resolve in priority order: floor → wall → ceiling**
- Pro: Matches Sonic 2 behavior. Floor sensors dominate when on ground.
- Con: Must handle transitions carefully.

**B. Resolve all simultaneously, pick minimum push**
- Con: Doesn't match the original. Wall and floor can conflict.

### Decision: **A — Priority order**

Floor sensors run first. If floor is found within range, snap to surface, set on_ground. Wall sensors run next, push out horizontally. Ceiling sensors last, push down and zero y_vel.

For airborne: all three run, but floor detection triggers landing (angle snap + ground_speed recalculation). The `calculate_landing_speed()` from physics.py handles the speed recalculation — we call it when transitioning to on_ground.

## Decision 6: Module Boundary

### What goes in terrain.py:
- `Tile` dataclass
- `SensorResult` dataclass
- `TileLookup` type alias
- Solidity constants (NOT_SOLID, TOP_ONLY, FULL, LRB_ONLY)
- `get_quadrant(angle)` — angle-to-quadrant mapping
- `sensor_cast(x, y, direction, tile_lookup, ...)` — single sensor ray
- `find_floor(state, tile_lookup)` — A/B floor resolution (returns winning SensorResult)
- `find_ceiling(state, tile_lookup)` — C/D ceiling resolution
- `find_wall_left(state, tile_lookup)` — E sensor
- `find_wall_right(state, tile_lookup)` — F sensor
- `resolve_collision(state, tile_lookup)` — top-level function: runs all sensors, modifies PhysicsState

### What stays in physics.py:
- `calculate_landing_speed(state)` — already there, called by resolve_collision on landing

### What goes in constants.py:
- Nothing new. All sensor constants already exist.

## Decision 7: Top-Only Tile Handling

Top-only tiles are ignored when `y_vel < 0` (rising). This check happens inside `sensor_cast` when reading the solidity flag. The sensor simply skips top_only tiles when the cast direction is "upward" (or when y_vel < 0 for floor sensors in normal mode).

More precisely: top-only tiles only collide with floor sensors (A/B) when the player's y_vel >= 0. They never collide with ceiling or wall sensors. This is checked per-sensor-cast based on the sensor type and player velocity.

## Decision 8: Extension/Regression

When sensor_cast hits a tile:
- height_array value at sensor column = 0 → extend to next tile in cast direction (one more tile)
- height_array value at sensor column = 16 → regress to previous tile against cast direction (one more tile)
- Otherwise → surface found, compute distance

Max range: 32px (current tile + one adjacent). If the extended/regressed tile also fails, return "not found."

## Rejected Alternatives

1. **Pixel-perfect collision (no height arrays):** Doesn't match spec. Height arrays are the core data structure.
2. **SAT (Separating Axis Theorem):** Over-engineered for tile-based collision. Height arrays are simpler and match the original engine.
3. **Separate CollisionState dataclass:** Unnecessary. PhysicsState already has all needed fields (x, y, angle, on_ground). Adding another dataclass creates sync problems.
4. **Async/event-based collision:** Collision is synchronous step 5–7 of the frame loop. No events needed.

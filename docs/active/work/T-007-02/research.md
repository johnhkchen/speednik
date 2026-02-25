# Research — T-007-02: exempt-loop-tiles-from-wall-push

## Tile Dataclass (`speednik/terrain.py:55–61`)

```python
@dataclass
class Tile:
    height_array: list[int]  # 16 values, 0–16
    angle: int               # byte angle 0–255
    solidity: int            # NOT_SOLID / TOP_ONLY / FULL / LRB_ONLY
```

Three fields. No knowledge of surface type. The `width_array()` method derives wall
collision widths from the height_array. Tile is constructed in `level.py:_build_tiles`
and consumed by every sensor cast in terrain.py.

## SensorResult Dataclass (`speednik/terrain.py:82–88`)

```python
@dataclass
class SensorResult:
    found: bool
    distance: float
    tile_angle: int
```

Three fields. Returned by all `_sensor_cast_*` functions, consumed by `find_floor`,
`find_ceiling`, `find_wall_push`, and `resolve_collision`. No tile type info propagated.

## Sensor Cast Functions (`terrain.py:128–489`)

Four directional casts: `_sensor_cast_down`, `_sensor_cast_up`, `_sensor_cast_right`,
`_sensor_cast_left`. All return `SensorResult(found=True, distance=..., tile_angle=tile.angle)`
on hit. The dispatching `_sensor_cast` function at line 481 delegates to the direction
functions. None of these functions reference or propagate tile type.

## `find_wall_push` (`terrain.py:627–670`)

This is the function the ticket targets. Flow:

1. **Moving-away gate** (lines 639–648): disables sensor if player moves away from wall.
2. **Sensor position calculation** (lines 651–659): places sensor at ±WALL_SENSOR_EXTENT.
3. **Cast** (line 661): delegates to `_sensor_cast` with `_no_top_only_filter`.
4. **Angle gate** (lines 665–668): if hit found and tile angle is in floor range
   (`<= 48` or `>= 208`), discard the result.
5. **Return** (line 670): returns the (potentially filtered) result.

The loop tile exemption would be inserted after the angle gate (step 4), adding a second
filter based on the tile's surface type.

## Level Loading (`speednik/level.py:97–112`)

```python
def _build_tiles(tile_map, collision):
    tiles = {}
    for ty, (tm_row, col_row) in enumerate(zip(tile_map, collision)):
        for tx, (cell, sol) in enumerate(zip(tm_row, col_row)):
            if cell is None:
                continue
            tiles[(tx, ty)] = Tile(
                height_array=cell["height_array"],
                angle=cell["angle"],
                solidity=sol,
            )
    return tiles
```

Reads `height_array` and `angle` from each cell dict but ignores the `type` field.
The `solidity` comes from the separate collision.json grid, not from the cell.

## tile_map.json Cell Format

Every non-null cell has a `type` field (verified across all 3 stages):
- hillside: types {1, 5} (1=solid, 5=loop). 1893 total tiles.
- pipeworks: types {1, 2, 3}. 13461 total tiles.
- skybridge: types {1, 2}. 4531 total tiles.

Example loop tile cell:
```json
{"type": 5, "height_array": [0,0,0,0,0,0,0,0,0,1,2,4,5,6,7,8], "angle": 36}
```

Example non-loop cell:
```json
{"type": 1, "height_array": [16,16,...,16], "angle": 0}
```

All cells have the `type` field. No backward-compat concern for missing `type`.

## SURFACE_LOOP Constant

`SURFACE_LOOP = 5` is defined in `tools/svg2stage.py:36` and used throughout the
pipeline tools. It is NOT in `speednik/constants.py` or `speednik/terrain.py`. The
runtime has no concept of this value today.

## Wall Angle Threshold (`speednik/constants.py:121–123`)

```python
WALL_ANGLE_THRESHOLD = 48
```

Tiles with angle ≤ 48 or ≥ 208 are floor-range. The angle gate in `find_wall_push`
already filters these. But loop arc tiles can have angles in the 49–207 range (wall-like
angles), which is exactly the problem: their steep angles pass the existing gate and
create false wall collisions.

## Existing Test Coverage (`tests/test_terrain.py`)

- 69 tests pass.
- `TestWallSensorAngleGate` (lines 679–755): tests the angle gate with shallow/steep tiles.
  None of these tests use `tile_type` — the concept doesn't exist yet.
- Helper functions: `flat_tile()`, `empty_tile()`, `slope_45_tile()`, `half_height_tile()`.
  All construct `Tile(height_array=..., angle=..., solidity=...)` — no `tile_type` param.

## Downstream Consumers of Tile and SensorResult

- `resolve_collision` reads `result.found`, `result.distance`, `result.tile_angle`.
- `_snap_to_floor` reads `result.distance`, `result.tile_angle`.
- `find_floor`, `find_ceiling` read `result.found`, `result.distance`, `result.tile_angle`.
- No consumer currently reads a `tile_type` field.

## Key Constraints

1. `Tile` is a `@dataclass`. Adding a new field with a default is backward-compatible:
   existing constructors that don't pass `tile_type` will get the default.
2. `SensorResult` is also a `@dataclass`. Same: adding `tile_type: int = 0` is safe.
3. The sensor cast functions construct `SensorResult` positionally in some cases and by
   keyword in others. Need to check each construction site for compatibility.
4. All `SensorResult` constructors in the four cast functions use positional args:
   `SensorResult(found=True, distance=dist, tile_angle=tile.angle)` and
   `SensorResult(found=False, distance=0.0, tile_angle=0)`. All use keyword syntax,
   so adding a 4th field with default is safe without modifying these call sites.
5. The tile variable is available at every `SensorResult(found=True, ...)` site.
   We need to propagate `tile.tile_type` in those sites.

## Summary

The change is narrow: add a field to two dataclasses, thread `type` through loading and
sensor casts, and add a single conditional in `find_wall_push`. The existing angle gate
is necessary but insufficient for loop tiles with steep angles. The tile type exemption
is the safety net.

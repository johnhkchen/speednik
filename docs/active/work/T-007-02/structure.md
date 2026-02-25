# Structure — T-007-02: exempt-loop-tiles-from-wall-push

## Files Modified

### `speednik/terrain.py`

**New constant (after existing solidity constants, ~line 33):**
```
SURFACE_LOOP = 5
```

**Tile dataclass (line 56):**
- Add field `tile_type: int = 0` after `solidity`.

**SensorResult dataclass (line 83):**
- Add field `tile_type: int = 0` after `tile_angle`.

**`_sensor_cast_down` (lines 128–203):**
- Every `SensorResult(found=True, ...)` call: add `tile_type=<hit_tile>.tile_type`.
- Sites: ~6 (current tile hit, extension hit, regression hit, each with the appropriate
  tile variable: `tile`, `tile_below`, `tile_above`).

**`_sensor_cast_up` (lines 206–321):**
- Same pattern: add `tile_type=<hit_tile>.tile_type` to all `found=True` sites.
- Sites: ~6 (tile, tile_above, tile_below).

**`_sensor_cast_right` (lines 328–399):**
- Same pattern. Sites: ~5 (tile, tile_right, tile_left).

**`_sensor_cast_left` (lines 402–466):**
- Same pattern. Sites: ~5 (tile, tile_left, tile_right).

**`find_wall_push` (lines 627–670):**
- After the angle gate block (line 668), add loop tile exemption:
  ```python
  if result.tile_type == SURFACE_LOOP:
      return SensorResult(found=False, distance=0.0, tile_angle=0)
  ```

**No changes to:**
- `find_floor`, `find_ceiling`, `resolve_collision`, `_snap_to_floor` — these don't
  need tile_type awareness.
- Solidity filters — unchanged.
- Quadrant tables — unchanged.

### `speednik/level.py`

**`_build_tiles` (lines 97–112):**
- Read `cell.get("type", 0)` and pass as `tile_type=` to the Tile constructor:
  ```python
  tiles[(tx, ty)] = Tile(
      height_array=cell["height_array"],
      angle=cell["angle"],
      solidity=sol,
      tile_type=cell.get("type", 0),
  )
  ```

### `tests/test_terrain.py`

**Imports:**
- Add `SURFACE_LOOP` to the import from `speednik.terrain`.

**New test class or tests in `TestWallSensorAngleGate`:**

Two new tests:

1. `test_loop_tile_at_wall_angle_not_blocked`:
   - Tile: `angle=64, solidity=FULL, tile_type=SURFACE_LOOP`.
   - Player moving right, sensor hits the tile.
   - Assert `result.found is False`.

2. `test_non_loop_tile_at_wall_angle_blocked`:
   - Tile: `angle=64, solidity=FULL, tile_type=1` (SURFACE_SOLID or default).
   - Player moving right, sensor hits the tile.
   - Assert `result.found is True`.

Uses existing `_state_moving_right()` and `_lookup_at_sensor()` helpers from
`TestWallSensorAngleGate`.

## Files NOT Modified

- `speednik/constants.py` — SURFACE_LOOP is placed in terrain.py with other tile
  constants, not in the physics constants module.
- `tools/svg2stage.py`, `tools/profile2stage.py` — pipeline tools already define
  SURFACE_LOOP=5 independently; no coupling needed.
- `speednik/physics.py` — no changes.
- Other test files — no impact.

## Module Boundaries

- `terrain.py` owns all tile collision types: `Tile`, `SensorResult`, solidity constants,
  and now `SURFACE_LOOP`. This is where tile semantics live.
- `level.py` is the bridge between JSON data and runtime Tile objects. It reads one more
  field from the JSON and passes it through.
- Tests import `SURFACE_LOOP` from `terrain` alongside existing constants.

## Ordering

1. Add `SURFACE_LOOP` constant and dataclass fields first (terrain.py).
2. Update sensor cast functions to propagate tile_type.
3. Add the exemption in `find_wall_push`.
4. Update `_build_tiles` in level.py.
5. Add tests.

Steps 1–3 are in the same file. Step 4 is independent. Step 5 depends on all prior.

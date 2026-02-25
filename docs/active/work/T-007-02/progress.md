# Progress — T-007-02: exempt-loop-tiles-from-wall-push

## Completed Steps

### Step 1: Add SURFACE_LOOP constant and extend Tile dataclass
- Added `SURFACE_LOOP = 5` constant to `speednik/terrain.py` (after solidity constants).
- Added `tile_type: int = 0` field to the `Tile` dataclass.
- Existing tests pass (default value preserves backward compat).

### Step 2: Extend SensorResult dataclass
- Added `tile_type: int = 0` field to the `SensorResult` dataclass.
- All existing keyword-arg constructors remain valid.

### Step 3: Propagate tile_type through sensor cast functions
- Updated all `SensorResult(found=True, ...)` sites in four functions:
  - `_sensor_cast_down`: 7 sites (tile, tile_below ×2, tile_above ×3, tile ×1).
  - `_sensor_cast_up`: 5 sites (tile_above, tile_below, tile ×3).
  - `_sensor_cast_right`: 5 sites (tile_right ×2, tile_left, tile ×2).
  - `_sensor_cast_left`: 5 sites (tile_left ×2, tile_right, tile ×2).
- All `found=False` sites left unchanged (default tile_type=0 correct).

### Step 4: Add loop tile exemption in find_wall_push
- Added check after the angle gate: `if result.tile_type == SURFACE_LOOP:` returns
  `SensorResult(found=False, ...)`.
- Loop tiles are unconditionally exempt from wall push-back.

### Step 5: Load tile type in _build_tiles
- Changed `level.py:_build_tiles` to read `cell.get("type", 0)` and pass as
  `tile_type=` to the `Tile` constructor.

### Step 6: Add new tests
- Added `SURFACE_LOOP` to test imports.
- Added `test_loop_tile_at_wall_angle_not_blocked` — loop tile with angle=64 is exempt.
- Added `test_non_loop_tile_at_wall_angle_blocked` — non-loop tile with angle=64 blocks.

### Step 7: Full test suite
- `uv run pytest -x`: 651 passed in 1.02s. Zero failures.

## Deviations from Plan

None. All steps executed as planned.

## Remaining Work

None. All acceptance criteria met.

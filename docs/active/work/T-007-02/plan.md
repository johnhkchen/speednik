# Plan — T-007-02: exempt-loop-tiles-from-wall-push

## Step 1: Add SURFACE_LOOP constant and extend Tile dataclass

**File:** `speednik/terrain.py`

- Add `SURFACE_LOOP = 5` after the existing solidity constants (line ~33).
- Add `tile_type: int = 0` field to the `Tile` dataclass (after `solidity`).

**Verification:** Existing tests pass (`uv run pytest tests/test_terrain.py -x`).
The default value means no existing Tile constructor breaks.

## Step 2: Extend SensorResult dataclass

**File:** `speednik/terrain.py`

- Add `tile_type: int = 0` field to `SensorResult` (after `tile_angle`).

**Verification:** Existing tests pass. All existing SensorResult constructors use
keyword args, so the default value keeps them valid.

## Step 3: Propagate tile_type through sensor cast functions

**File:** `speednik/terrain.py`

Update every `SensorResult(found=True, ...)` construction to include
`tile_type=<hit_tile>.tile_type`:

- `_sensor_cast_down`: 6 sites (tile, tile_below, tile_above).
- `_sensor_cast_up`: 6 sites (tile, tile_above, tile_below).
- `_sensor_cast_right`: 5 sites (tile, tile_right, tile_left).
- `_sensor_cast_left`: 5 sites (tile, tile_left, tile_right).

The `found=False` returns are left unchanged (default tile_type=0 is correct).

**Verification:** Existing tests pass. Behavior is unchanged because no consumer
reads tile_type yet.

## Step 4: Add loop tile exemption in find_wall_push

**File:** `speednik/terrain.py`

After the angle gate block (line ~668), add:

```python
    # Loop tile exemption: loop surfaces should not block as walls
    if result.tile_type == SURFACE_LOOP:
        return SensorResult(found=False, distance=0.0, tile_angle=0)
```

**Verification:** Existing tests pass. No existing test uses loop tiles, so behavior
for all current test cases is unchanged.

## Step 5: Load tile type in _build_tiles

**File:** `speednik/level.py`

Change the Tile constructor call in `_build_tiles`:

```python
tiles[(tx, ty)] = Tile(
    height_array=cell["height_array"],
    angle=cell["angle"],
    solidity=sol,
    tile_type=cell.get("type", 0),
)
```

**Verification:** Existing tests pass. Run `uv run pytest -x` for full suite.

## Step 6: Add new tests

**File:** `tests/test_terrain.py`

Add `SURFACE_LOOP` to imports.

Add two tests to `TestWallSensorAngleGate`:

1. `test_loop_tile_at_wall_angle_not_blocked`:
   - Create `Tile(height_array=[16]*16, angle=64, solidity=FULL, tile_type=SURFACE_LOOP)`.
   - Use existing `_state_moving_right()` and `_lookup_at_sensor()`.
   - `find_wall_push(state, lookup, RIGHT)` → assert `not result.found`.

2. `test_non_loop_tile_at_wall_angle_blocked`:
   - Create `Tile(height_array=[16]*16, angle=64, solidity=FULL, tile_type=1)`.
   - Same setup.
   - `find_wall_push(state, lookup, RIGHT)` → assert `result.found`.
   - This confirms existing behavior is preserved for non-loop tiles.

**Verification:** `uv run pytest tests/test_terrain.py -x -v` — all tests pass including
the two new ones.

## Step 7: Full test suite

Run `uv run pytest -x` to verify nothing else breaks across the entire test suite.

## Testing Strategy Summary

| Test | What it verifies |
|------|-----------------|
| test_loop_tile_at_wall_angle_not_blocked | Loop tiles exempt from wall push |
| test_non_loop_tile_at_wall_angle_blocked | Non-loop tiles still blocked (regression) |
| Existing 69 tests | No regressions from dataclass changes |

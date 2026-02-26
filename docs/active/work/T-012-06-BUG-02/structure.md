# Structure: T-012-06-BUG-02 — large-loop-exit-overshoot

## Files Modified

### 1. `speednik/terrain.py` — Sensor cast fix

**Function**: `_sensor_cast_up()` (line ~255, height==0 branch)

**Change**: After checking tile above and finding no surface, add a fallback
check of the tile below. Uses the same pattern as the existing tile-below
regression check in the height==TILE_SIZE branch.

New code inserted between the tile-above check and the `return found=False`:
```python
tile_below = tile_lookup(tile_x, tile_y + 1)
if tile_below is not None and tile_below.solidity != NOT_SOLID and solidity_filter(tile_below.solidity):
    height_below = tile_below.height_array[col]
    if height_below > 0:
        solid_top_y = (tile_y + 1) * TILE_SIZE + (TILE_SIZE - height_below)
        dist = sensor_y - solid_top_y
        if abs(dist) <= MAX_SENSOR_RANGE:
            return SensorResult(found=True, distance=dist,
                                tile_angle=tile_below.angle,
                                tile_type=tile_below.tile_type)
```

### 2. `speednik/grids.py` — Exit tile scaling

**Function**: `build_loop()`, flat exit section

**Change**: Scale exit tile count by loop radius to provide adequate landing
zone for large-radius loops.

```python
# Before:
for i in range(approach_tiles):
# After:
exit_tile_count = approach_tiles + 2 * ((radius + TILE_SIZE - 1) // TILE_SIZE)
for i in range(exit_tile_count):
```

### 3. `tests/test_mechanic_probes.py` — Remove xfail markers

**Function**: `TestLoopEntry.test_loop_traverses_all_quadrants`

**Change**: Remove `pytest.mark.xfail` from all 4 radius params (r32, r48,
r64, r96). These were marked xfail for BUG-01 but now pass with both BUG-01
and BUG-02 fixes applied.

### 4. `tests/test_elementals.py` — Update xfail reasons

**Tests**: `test_loop_ramps_exit`, `test_loop_walk_speed_less_progress`

**Change**: Update xfail reason strings from "BUG-02" to "r=128 loop trapping"
since BUG-02 is fixed for r=64/96 but r=128 has a separate issue.

## Files NOT Modified

- `speednik/physics.py` — No physics changes needed
- `speednik/player.py` — No player logic changes needed
- `speednik/constants.py` — No constant changes needed
- `tests/test_grids.py` — Loop grid tests already pass

## Module Boundaries

The sensor fix is within `_sensor_cast_up` only. The public interface
(`find_floor`, `resolve_collision`) is unchanged. The exit tile scaling is
internal to `build_loop()`.

# Structure — T-012-02-BUG-01: hillside-wall-at-x601

## Files Modified

### 1. `speednik/stages/hillside/tile_map.json` (DATA FIX)

**Change**: Single value edit in the JSON array.

- **Location**: Row 38, column 37 → `tile_map[38][37]["angle"]`
- **Before**: `64`
- **After**: `2`
- **All other fields unchanged**: height_array, type, and solidity stay as-is.

This is the only production file that changes. No Python source files are
modified.

### 2. `tests/test_terrain.py` (NEW TEST — optional but recommended)

**Change**: Add a targeted regression test for the hillside tile at (37, 38).

- Add a test class `TestHillsideTile37_38` or a standalone function
  `test_hillside_tile_37_38_angle_is_floor`.
- Loads the hillside stage via `create_sim("hillside")` and inspects the
  tile at grid (37, 38).
- Asserts `tile.angle <= 5` (floor-range, not wall-range).
- Asserts the tile exists and has the expected height_array pattern.

This test prevents regression if the data pipeline ever re-generates the tile
map and re-introduces the bad angle.

### 3. `tests/test_simulation.py` (NEW TEST — integration)

**Change**: Add a walker-progress test that verifies a hold-right strategy
can traverse past x=601 on hillside.

- Add `test_hillside_walker_passes_x601()`.
- Creates hillside sim, runs hold-right for 600 frames.
- Asserts `sim.player.physics.x > 650` (comfortably past the former wall).
- Lightweight — doesn't need the full QA framework.

## Files NOT Modified

| File                | Reason                                           |
|---------------------|--------------------------------------------------|
| `speednik/terrain.py`      | Engine is correct; data was wrong         |
| `speednik/level.py`        | Loader is correct; data was wrong         |
| `speednik/physics.py`      | No physics changes needed                 |
| `speednik/simulation.py`   | No simulation logic changes               |
| `speednik/constants.py`    | Constants are correct                     |
| `collision.json`           | Solidity=2 (FULL) is correct for this tile|

## Module Boundaries

No module boundaries change. The fix is entirely within the data layer
(`tile_map.json`). The test additions are in existing test files and import
only existing public APIs.

## Ordering

1. Fix `tile_map.json` first — this is the production fix.
2. Add tests second — they verify the fix and prevent regression.
3. Order between the two test files doesn't matter (independent).

## Risk Assessment

- **Blast radius**: One JSON value in one stage data file. No code changes.
- **Regression risk**: Near zero. The value 64 was wrong; changing it to 2
  aligns it with the height_array geometry and adjacent tiles.
- **Test isolation**: New tests are additive — they don't modify or depend on
  each other or on any existing test.

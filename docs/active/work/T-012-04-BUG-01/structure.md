# Structure — T-012-04-BUG-01: skybridge-bottomless-pit-at-x170

## Files Modified

### 1. `speednik/stages/skybridge/tile_map.json`

**Rows 31 and 32, column 11**: Replace `null` with a tile object.

Row 31, col 11:
```json
{
  "type": 2,
  "height_array": [12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12],
  "angle": 0
}
```

Row 32, col 11:
```json
{
  "type": 2,
  "height_array": [16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16],
  "angle": 0
}
```

Type=2 matches cols 12-18 (bridge segment). Angle=0 is flat. Heights match adjacent
tiles (12 for row 31, 16 for row 32).

**Row 31, col 10**: Fix trailing-edge artifact. Change from:
```json
{"type": 1, "height_array": [12,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], "angle": 192}
```
to:
```json
{"type": 1, "height_array": [12,12,12,12,12,12,12,12,12,12,12,12,12,12,12,12], "angle": 0}
```

**Row 32, col 10**: Same fix. Change from:
```json
{"type": 1, "height_array": [16,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], "angle": 192}
```
to:
```json
{"type": 1, "height_array": [16,16,16,16,16,16,16,16,16,16,16,16,16,16,16,16], "angle": 0}
```

### 2. `speednik/stages/skybridge/collision.json`

**Rows 31 and 32, column 11**: Change from `0` to `1` (TOP_ONLY).

This matches the collision type of the adjacent bridge segment (cols 12-18 are
TOP_ONLY at row 31). TOP_ONLY allows the player to jump up through the tile from
below, which is consistent with bridge/platform behavior.

### 3. `tests/test_audit_skybridge.py`

Remove all 6 `@pytest.mark.xfail(strict=True, reason="BUG: T-012-04-BUG-01 ...")`
decorators. The tests should run as normal tests after the collision fix. If other
bugs cause them to fail, those are separate issues.

## Files NOT Modified

- `speednik/simulation.py` — pit death already implemented by T-013-01
- `speednik/constants.py` — PIT_DEATH_MARGIN already exists
- `speednik/level.py` — tile loading logic is correct; it just needs correct data
- `speednik/terrain.py` — collision resolution works correctly with valid tile data
- `speednik/player.py` — no changes needed

## Verification Approach

After modifying the JSON data:
1. Verify tile_map[31][11] and tile_map[32][11] are no longer None
2. Verify collision[31][11] and collision[32][11] are 1
3. Verify tile_map[31][10] and tile_map[32][10] have flat heights
4. Run `test_audit_skybridge.py` — tests should no longer xfail for this bug
5. Run the walker archetype simulation and confirm it passes x=170 without falling

## Impact Scope

- Only skybridge stage data is affected
- No code changes to the engine
- No changes to other stages
- The fix restores the intended bridge surface; other gaps remain as designed

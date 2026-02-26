# Structure — T-012-03-BUG-01: pipeworks-slope-wall-blocks-progress

## Files Modified

### 1. `speednik/stages/pipeworks/tile_map.json`

**Change**: 4 angle values from 64 to 0.

Tiles affected:
- `tile_map[13][32]["angle"]`: 64 → 0
- `tile_map[14][32]["angle"]`: 64 → 0
- `tile_map[15][32]["angle"]`: 64 → 0
- `tile_map[16][32]["angle"]`: 64 → 0

No other fields change. Height arrays, types, and collision data stay the same.
Rows 10–12 at column 32 retain angle=64 (legitimate pipe wall geometry).

### 2. `tests/test_terrain.py`

**Change**: Add one regression test function at the end of the file.

```python
def test_pipeworks_col32_underground_not_wall_angle():
    """Fully-solid tiles at col 32, rows 13-16 must not have wall angle (T-012-03-BUG-01)."""
```

Pattern matches `test_hillside_tile_37_38_not_wall_angle`:
- Load pipeworks via `create_sim("pipeworks")`
- For each tile (32, row) where row in [13, 14, 15, 16]:
  - Assert tile exists
  - Assert `tile.angle <= 5` (floor-range)

### 3. `tests/test_simulation.py`

**Change**: Add one integration test function at the end of the file.

```python
def test_pipeworks_jumper_passes_slope_wall():
    """Jumper must pass x=520 on pipeworks (formerly blocked by wall-angle tiles)."""
```

Pattern matches `test_hillside_walker_passes_x601`:
- Create pipeworks sim
- Run Jumper archetype inputs for sufficient frames
- Assert `max_x_reached > 600` (previously stuck at 518)

### 4. `tests/test_audit_pipeworks.py`

**Change**: Evaluate whether xfail annotations on BUG-01-related tests need
updating. Four tests reference BUG-01:
- `test_pipeworks_jumper` — xfail reason mentions BUG-01
- `test_pipeworks_speed_demon` — xfail reason mentions BUG-01
- `test_pipeworks_cautious` — xfail reason mentions BUG-01
- `test_pipeworks_chaos` — xfail reason mentions BUG-01

After the tile fix, these archetypes will pass the slope wall. If they still
fail for other reasons (downstream obstacles, other bugs), the xfail reason
text should be updated. If they pass entirely, the xfail should be removed.

This will be determined empirically after the data fix by running the tests.

## Files NOT Modified

| File | Reason |
|------|--------|
| `speednik/terrain.py` | Engine is correct; data is wrong |
| `speednik/physics.py` | No physics bug |
| `speednik/simulation.py` | No simulation bug |
| `speednik/stages/pipeworks/collision.json` | Solidity=2 (FULL) is correct |
| `speednik/stages/pipeworks/meta.json` | No change needed |

## Module Boundaries

No new modules, classes, or interfaces. The fix is purely data + tests.

## Ordering

1. Fix tile_map.json first (the data fix)
2. Add regression tests (tests depend on the data being correct)
3. Evaluate/update audit xfail annotations (depends on running tests post-fix)
4. Run full test suite for regression check

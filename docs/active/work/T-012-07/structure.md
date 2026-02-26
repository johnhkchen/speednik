# Structure — T-012-07: svg2stage angle fix and regenerate

## Files Modified

### `tools/svg2stage.py`

**New function: `_smooth_accidental_walls(grid: TileGrid) -> int`**
- Location: After `_is_steep()` (line ~988), before `class Validator`.
- Scans entire grid for isolated steep tiles with non-steep horizontal neighbors.
- Replaces outlier angles with circular mean of non-steep neighbors.
- Skips None tiles and `is_loop_upper` tiles.
- Returns count of smoothed tiles (for logging).

**Modified function: `Validator._check_accidental_walls()`**
- Add a second pass after the existing run-length check.
- New pass: for each steep tile with run_count <= MAX_STEEP_RUN, check if at least one
  horizontal neighbor is non-steep and non-loop. If so, flag it.
- Since smoothing runs first, this pass should find zero issues. It exists as a safety net.

**Modified function: `main()`**
- Insert call to `_smooth_accidental_walls(grid)` between rasterization and validation.
- Print count of smoothed tiles.

### Generated files (regenerated, not hand-edited)

- `speednik/stages/hillside/tile_map.json`
- `speednik/stages/hillside/collision.json`
- `speednik/stages/hillside/entities.json`
- `speednik/stages/hillside/meta.json`
- `speednik/stages/hillside/validation_report.txt`
- `speednik/stages/pipeworks/tile_map.json`
- `speednik/stages/pipeworks/collision.json`
- `speednik/stages/pipeworks/entities.json`
- `speednik/stages/pipeworks/meta.json`
- `speednik/stages/pipeworks/validation_report.txt`
- `speednik/stages/skybridge/tile_map.json`
- `speednik/stages/skybridge/collision.json`
- `speednik/stages/skybridge/entities.json`
- `speednik/stages/skybridge/meta.json`
- `speednik/stages/skybridge/validation_report.txt`

### `tests/test_audit_hillside.py`

- Remove `@pytest.mark.xfail(...)` from `test_hillside_walker` (lines 100-103).
- Remove `@pytest.mark.xfail(...)` from `test_hillside_cautious` (lines 128-131).
- Remove `@pytest.mark.xfail(...)` from `test_hillside_wall_hugger` (lines 138-141).
- Keep xfails on `test_hillside_speed_demon` and `test_hillside_chaos` (separate bugs).

### Files NOT modified

- `speednik/terrain.py` — No changes. This is the runtime terrain system; the fix is
  entirely in the pipeline tool.
- `speednik/grids.py` — Synthetic grids, unrelated.
- `tests/test_audit_pipeworks.py` — BUG-01 already fixed. No xfail changes needed.
- `tests/test_audit_skybridge.py` — Bottomless pit bug is unrelated. No changes.

## Module Boundaries

The smoothing pass is a pipeline concern (`tools/svg2stage.py`), not a runtime concern.
It runs during stage generation, not during gameplay. No runtime modules are affected.

## Interface

`_smooth_accidental_walls(grid: TileGrid) -> int`
- Input: mutable TileGrid (modified in place).
- Output: count of tiles smoothed.
- Uses existing helpers: `_is_steep()`, `TileGrid.get_tile()`.
- New helper needed: none — circular mean is 3 lines inline.

## Ordering

1. Add smoothing function to svg2stage.py
2. Update validator to detect isolated steep tiles
3. Update main() to call smoothing
4. Regenerate all 3 stages
5. Verify hillside BUG-01 tiles are fixed
6. Remove xfail markers from hillside tests
7. Run full test suite

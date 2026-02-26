# Plan — T-012-07: svg2stage angle fix and regenerate

## Step 1: Add `_smooth_accidental_walls()` to svg2stage.py

Insert after `_is_steep()` (line ~988), before `SURFACE_NAMES`:

```python
def _smooth_accidental_walls(grid: TileGrid) -> int:
    """Post-process: replace isolated wall-angle tiles with neighbor average.

    Scans for steep tiles (angle in wall quadrant) that have at least one
    non-steep horizontal neighbor. Replaces the outlier angle with the
    circular mean of non-steep neighbor angles. Loop tiles are excluded.

    Returns the number of tiles smoothed.
    """
    smoothed = 0
    for ty in range(grid.rows):
        for tx in range(grid.cols):
            tile = grid.get_tile(tx, ty)
            if tile is None or tile.is_loop_upper:
                continue
            if not _is_steep(tile.angle):
                continue
            neighbors = []
            for dtx in [-1, 1]:
                n = grid.get_tile(tx + dtx, ty)
                if n is not None and not _is_steep(n.angle) and not n.is_loop_upper:
                    neighbors.append(n.angle)
            if len(neighbors) >= 1:
                # Circular mean to handle wraparound at 0/256 boundary
                sin_sum = sum(math.sin(a * 2 * math.pi / 256) for a in neighbors)
                cos_sum = sum(math.cos(a * 2 * math.pi / 256) for a in neighbors)
                tile.angle = round(math.atan2(sin_sum, cos_sum) * 256 / (2 * math.pi)) % 256
                smoothed += 1
    return smoothed
```

Verify: function uses existing `_is_steep()`, `TileGrid.get_tile()`, `math` (already imported).

## Step 2: Update `Validator._check_accidental_walls()` to flag isolated steep tiles

After the existing run-length logic, add a second scan for isolated steep tiles
(run_count 1) with non-steep horizontal neighbors. This is a safety net — the smoothing
pass should have already fixed these.

Add to the end of `_check_accidental_walls`, after the existing row-scanning loop:

```python
# Also flag isolated steep tiles with non-steep neighbors (safety net)
for ty in range(self.grid.rows):
    for tx in range(self.grid.cols):
        tile = self.grid.get_tile(tx, ty)
        if tile is None or tile.is_loop_upper:
            continue
        if not _is_steep(tile.angle):
            continue
        has_non_steep_neighbor = False
        for dtx in [-1, 1]:
            n = self.grid.get_tile(tx + dtx, ty)
            if n is not None and not _is_steep(n.angle) and not n.is_loop_upper:
                has_non_steep_neighbor = True
                break
        if has_non_steep_neighbor:
            ctx = self._shape_context(tx, ty)
            issues.append(
                f"Isolated steep tile at ({tx},{ty}): angle={tile.angle} "
                f"with non-steep neighbor{ctx}"
            )
```

## Step 3: Update `main()` to call smoothing between rasterize and validate

After `grid = rasterizer.rasterize(shapes)` and the tile count print, add:

```python
smoothed = _smooth_accidental_walls(grid)
if smoothed:
    print(f"Smoothed: {smoothed} isolated wall-angle tiles")
```

## Step 4: Regenerate all 3 stages

```bash
uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/
uv run python tools/svg2stage.py stages/pipe_works.svg speednik/stages/pipeworks/
uv run python tools/svg2stage.py stages/skybridge_gauntlet.svg speednik/stages/skybridge/
```

## Step 5: Verify hillside BUG-01 fix

Check that the problematic tiles no longer have angle=64. Use a quick python snippet to
load tile_map.json and inspect the relevant coordinates.

## Step 6: Remove BUG-01 xfail markers from hillside tests

In `tests/test_audit_hillside.py`:
- Remove xfail decorator from `test_hillside_walker` (lines 100-103)
- Remove xfail decorator from `test_hillside_cautious` (lines 128-131)
- Remove xfail decorator from `test_hillside_wall_hugger` (lines 138-141)

## Step 7: Run full test suite

```bash
uv run pytest tests/ -x
```

Expected outcomes:
- Hillside walker, cautious, wall_hugger now pass (BUG-01 fixed)
- Hillside speed_demon and chaos still xfail (separate bugs)
- Pipeworks tests unchanged (BUG-01 already fixed)
- Skybridge tests still xfail cleanly (bottomless pit bug unrelated)
- All other tests pass

## Testing Strategy

- **Pipeline correctness**: Regenerated stages verified by inspection of specific tiles.
- **Integration**: Full test suite run with `pytest tests/ -x`.
- **Safety net**: Validator now catches isolated steep tiles — validation_report.txt
  should show zero issues after smoothing.
- **Regression**: All 3 stages regenerated; any unexpected changes would cause test failures.

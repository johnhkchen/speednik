# Plan: T-012-06-BUG-01 — synthetic-loop-no-ceiling-quadrant

## Step 1: Rewrite loop circle generation in `build_loop()`

### Changes to `speednik/grids.py`

Replace the loop circle section (lines 273-337) with a two-phase approach:

**Phase A: Collect per-pixel arc data**

For each pixel column `px` in `[loop_start, loop_end)`:
- `dx = px - cx + 0.5`
- `dy = sqrt(r^2 - dx^2)`
- `y_bottom = cy + dy` (bottom arc surface Y)
- `y_top = cy - dy` (top arc surface Y)
- `angle_bottom = round(-atan2(dx, dy) * 256 / (2*pi)) % 256`
- `angle_top = round(-atan2(-dx, -dy) * 256 / (2*pi)) % 256`

Group by tile key `(tx, ty)` for both arcs. For each tile, collect per-column data:
`(local_x, surface_y, angle)`.

**Phase B: Build tiles from grouped data**

For each tile key with collected pixel data:
- Build `height_array`: for each `local_x`, compute
  `height = clamp(tile_bottom_y - surface_y, 0, 16)` where
  `tile_bottom_y = (ty + 1) * TILE_SIZE`.
- Compute tile angle: use the angle at the midpoint local_x of the tile's columns
  (or the median column if the tile has an even number of arc pixels).
- Set `solidity = FULL`, `tile_type = SURFACE_LOOP`.

**Phase C: Solidity fixup (simplified)**

All loop circle tiles get `FULL` solidity. Remove the old upper_tiles/lower_tiles
set logic. The existing fixup pass (lines 328-337) is replaced or removed.

### Verification

Run `test_mechanic_probes.py::TestLoopEntry` tests. The xfail tests should now
pass (meaning they'll fail as xfail -- we need to remove the markers).

## Step 2: Run existing tests, check for regressions

```bash
uv run pytest tests/test_mechanic_probes.py -v
uv run pytest tests/test_elementals.py -v
uv run pytest tests/test_geometry_probes.py -v
```

Expected:
- `TestLoopEntry::test_loop_traverses_all_quadrants` — should pass (currently xfail,
  so pytest will report XPASS if the xfail is strict, which means we need to remove
  the markers).
- `TestRampEntry`, `TestGapClearable`, `TestSpringLaunch`, `TestSlopeAdhesion` — no changes.
- Elemental loop tests may change behavior but should remain valid.

## Step 3: Update xfail markers in test_mechanic_probes.py

Based on Step 2 results:
- Remove `xfail` from `test_loop_traverses_all_quadrants` for radii that now pass.
- For `test_loop_exit_positive_speed` and `test_loop_exit_on_ground`: the r=64/96
  xfails are for T-012-06-BUG-02 (separate bug). Keep those unless they now pass.
- Keep any xfails that still fail with updated reasons.

## Step 4: Run full test suite

```bash
uv run pytest tests/ -v
```

Verify no regressions across all test files.

## Testing Strategy

### Unit-level verification (built into the fix)
- The `build_loop()` output tiles should have height arrays with values in 0-16
  that match the circle arc geometry (not all-16).
- Tile angles should be smooth across tile boundaries (no jumps > ~20 byte angles
  between adjacent tiles).

### Integration verification (existing tests)
- `test_loop_traverses_all_quadrants`: quadrants_visited == {0, 1, 2, 3}
- `test_loop_exit_positive_speed`: positive ground_speed after loop (r=32,48)
- `test_loop_exit_on_ground`: player on_ground after loop (r=32,48)

### Regression verification
- All other test classes in test_mechanic_probes.py pass unchanged
- test_elementals.py loop tests continue to pass
- test_geometry_probes.py (real hillside stage) unaffected
- test_invariants.py unchanged

## Commit Plan

1. Single commit: fix `build_loop()` geometry + update test xfail markers

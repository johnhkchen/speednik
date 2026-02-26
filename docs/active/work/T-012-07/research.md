# Research — T-012-07: svg2stage angle fix and regenerate

## Problem Summary

`tools/svg2stage.py` produces angle=64 (wall quadrant, 90°) tiles on terrain that should
be gently sloped or flat. This blocks player archetypes in both hillside and pipeworks
stages. The ticket requires adding a smoothing post-process, strengthening the validator,
and regenerating all 3 stages.

## Relevant Files

### Pipeline

- **`tools/svg2stage.py`** (1253 lines) — The SVG-to-stage conversion pipeline. Contains:
  - `_compute_segment_angle(p1, p2)` (line 602): Converts segment direction to byte angle
    via `atan2`. Degenerate/near-vertical segments produce angle=64.
  - `Rasterizer._rasterize_line_segment()` (line 697): Walks segments at 1px intervals,
    sets `tile.angle = angle` on every step. Last segment to touch a tile wins — no
    averaging, no smoothing.
  - `_is_steep(angle)` (line 984): Returns True for byte angles 32-96 or 160-224
    (steeper than 45° in either wall quadrant).
  - `Validator._check_accidental_walls()` (line 1081): Scans rows for runs of steep
    tiles longer than `MAX_STEEP_RUN=3`. Misses isolated tiles (run length 1-3).
  - `TileData` dataclass (line 130): Has `is_loop_upper` flag that must be respected.
  - `Rasterizer.rasterize()` (line 671): Entry point — loops shapes, returns grid.
    No post-processing step exists between rasterization and validation.

### Stage Data (Generated)

- `speednik/stages/hillside/tile_map.json` — 45×300 grid. Tile (37,38) currently has
  angle=2 (fixed in an earlier commit). But tile (37,39) below it has angle=64 with a
  degenerate height_array `[0,0,0,0,0,0,0,0,16,0,0,0,0,0,0,0]` — a single solid column
  amid zeros. This is the BUG-01 wall tile.
- `speednik/stages/pipeworks/tile_map.json` — 64×350 grid. Column tx=32 has a steep
  45-degree slope (angle=32 at row 12), but no angle=64 tiles in current data. Earlier
  BUG-01 xfails for pipeworks are already noted as fixed in test comments.
- `speednik/stages/skybridge/tile_map.json` — 56×325 grid. Contains angle=64 tiles
  (8 distinct angle values including 64). May have similar isolated wall tile issues.

### SVG Source Files

- `stages/hillside_rush.svg` — Source for hillside stage
- `stages/pipe_works.svg` — Source for pipeworks stage
- `stages/skybridge_gauntlet.svg` — Source for skybridge stage

### Terrain System

- `speednik/terrain.py`: `Tile` dataclass with `height_array`, `angle`, `solidity`,
  `tile_type`. `get_quadrant(angle)`: quadrant 1 (right wall) = angles 33-96.
  `WALL_ANGLE_THRESHOLD=48` in constants.py gates wall sensor detection.
- `speednik/grids.py`: Synthetic grid builders. Not affected by this change.

### Test Files

- `tests/test_audit_hillside.py`: 3 tests xfailed for BUG-01 (walker, cautious,
  wall_hugger at x≈601). Speed demon and chaos xfailed for separate bugs.
- `tests/test_audit_pipeworks.py`: BUG-01 already noted as fixed in comments. Remaining
  xfails are for 45-degree slope difficulty (jumper, speed_demon, cautious, chaos) — NOT
  BUG-01 related.
- `tests/test_audit_skybridge.py`: All 6 tests xfailed for T-012-04-BUG-01 (bottomless
  pit), unrelated to angle issues.

## Key Observations

1. **The rasterizer's "last write wins" policy** is the root cause. When multiple SVG
   segments touch the same tile, the last segment's angle overwrites all previous values.
   A short near-vertical edge crossing a tile boundary produces angle=64 even if the
   dominant surface is flat.

2. **The smoothing pass described in the ticket** is conservative: only fixes tiles where
   at least one horizontal neighbor is non-steep. This preserves legitimate wall tiles
   (vertical surfaces with steep neighbors). Loop tiles (`is_loop_upper`) are excluded.

3. **The validator gap**: `_check_accidental_walls` only flags runs > `MAX_STEEP_RUN=3`.
   A single isolated wall tile (run=1) or a short run (2-3) passes validation silently.
   The fix adds detection of isolated steep tiles with non-steep neighbors.

4. **Pipeworks BUG-01 appears already fixed** — test comments say "BUG-01 (slope wall)
   is fixed" and walker/wall_hugger tests pass. The remaining xfails are for the 45-degree
   slope difficulty, which is a game design issue, not a pipeline bug. The regeneration
   should not change these tests' status.

5. **Hillside BUG-01 is the active target**. The 3 xfailed tests (walker, cautious,
   wall_hugger) reference BUG-01 at x≈601. After the fix, these should pass.

6. **`main()` flow** (line 1215): parse → rasterize → validate → write. The smoothing
   pass must be inserted between rasterize and validate, so the validator sees clean data.

7. **Angle averaging on a circular scale**: Byte angles wrap at 256. Averaging angles 2
   and 0 is trivial (=1), but averaging angles near 0 and 255 requires circular mean.
   For the specific use case (non-steep neighbors, values near 0 or near 128), simple
   arithmetic average mod 256 works because non-steep neighbors are by definition in the
   floor quadrant (0-32 or 224-255) — close enough on the circle that wrapping isn't an
   issue. However, a proper circular mean is safer.

8. **The smoothing only checks horizontal neighbors** (dtx ∈ {-1, 1}). Vertical neighbors
   are not checked. This is intentional: wall tiles are typically in rows, and checking
   only horizontal neighbors avoids smoothing tiles that are vertically adjacent to
   legitimate walls.

## Constraints

- The fix must not alter loop tiles (`is_loop_upper`).
- The fix must not alter tiles whose neighbors are also steep (legitimate walls).
- All 3 stages must be regenerated from their SVG sources.
- After regeneration, `uv run pytest tests/ -x` must pass.
- The skybridge tests are xfailed for an unrelated bottomless pit bug — regeneration
  must not break them (they should still xfail cleanly).

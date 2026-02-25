# T-007-04 Research: Regenerate Hillside & Verify Loop

## Purpose

Integration verification for S-007 (make-loop-traversable). Dependencies T-007-01
(svg2stage ramp generation), T-007-02 (physics loop tile wall exemption), and T-007-03
(profile2stage ramp generation) are all done. This ticket regenerates hillside stage data,
validates the output, runs the full test suite, and confirms in-game traversal.

---

## Relevant Files & Systems

### Pipeline Entry Point
- `tools/svg2stage.py` (~1200 lines) — SVG-to-stage-data converter
  - `SVGParser` → `Rasterizer` → `Validator` → `StageWriter`
  - Invoked: `uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/`

### SVG Source
- `stages/hillside_rush.svg` — hillside stage definition
  - Loop circle: `cx=3600, cy=508, r=128`, green stroke `#00AA00`
  - Ground level: y=636 (loop bottom tangent = cy + r = 508 + 128 = 636)
  - Approach ground: x=[3200, 3472], exit ground: x=[3728, 4000]
  - Ground beneath loop: x=[3472, 3728]
  - 20 rings inside the loop, 5 approach rings

### Generated Stage Data
- `speednik/stages/hillside/tile_map.json` — 300×45 grid of {type, height_array, angle}
- `speednik/stages/hillside/collision.json` — 300×45 solidity grid (0/1/2)
- `speednik/stages/hillside/entities.json` — player start, rings, enemies, etc.
- `speednik/stages/hillside/meta.json` — dimensions, player start, checkpoints
- `speednik/stages/hillside/validation_report.txt` — warnings/errors from Validator

### Physics System
- `speednik/terrain.py` (~784 lines) — tile queries, sensor casts, collision resolution
  - `SURFACE_LOOP = 5` — constant matching svg2stage
  - `Tile` dataclass: `height_array`, `angle`, `solidity`, `tile_type`
  - Wall sensors: angle gate (≤48 or ≥208 → floor-range, ignored) + loop exemption
  - Quadrant system: 256-step angles → Q0/Q1/Q2/Q3 sensor directions
- `speednik/level.py` (~120 lines) — `load_stage()` builds Tile objects from JSON
  - `_build_tiles()`: `tile_type=cell.get("type", 0)` propagates loop type to runtime

### Constants
- `speednik/constants.py` — `WALL_ANGLE_THRESHOLD=48`, `ANGLE_STEPS=256`,
  `WALL_SENSOR_EXTENT=10`, standing/rolling radii

### Test Files
- `tests/test_svg2stage.py` (~1800 lines, 98 tests) — includes `TestRampRasterization` (7 tests)
- `tests/test_terrain.py` (~814 lines) — includes wall sensor angle gate + loop exemption tests
- `tests/test_profile2stage.py` (~2400 lines, 88 tests) — includes ramp tests

---

## Loop Region Geometry (Tile Coordinates)

With `TILE_SIZE = 16`:
- Loop center: tile col 225 (3600/16), tile row ~31.75 (508/16)
- Loop circle: cols 217–233 (x: 3472–3728), rows 23–39 (y: 380–636)
- Entry ramp: cols 209–216 (x: 3344–3472)
- Exit ramp: cols 233–241 (x: 3728–3856)
- Ground level: row 39 (y: 636/16 = 39.75)

---

## Current State of Generated Data

The committed hillside stage data reflects T-007-01 changes (ramp generation).
Current `validation_report.txt` (209 lines) contains:

### Impassable Gaps in Loop/Ramp Region
- Cols 213–216, 220, 229, 233 — 12px and 2px gaps at various y positions
- These arise from overlap between ramp surface tiles and SVG ground polygon tiles
- T-007-01 review classified these as informational (gaps between separate overlapping
  surfaces, not true impassable terrain)

### Accidental Wall Warnings
- Row 35, tiles 215–218: 4 consecutive steep non-loop tiles
- Row 35, tiles 231–234: 4 consecutive steep non-loop tiles
- These are the steepest ramp tiles near the loop tangent points
- Wall angle gate (threshold 48) handles these at runtime — they won't block the player

### Angle Inconsistencies
- ~193 warnings across the stage, many at SVG shape boundaries
- Loop region: discontinuities at ramp-to-loop junctions (tiles 216–217, 232–233)
- Inherent to discrete tile approximation of continuous curves

---

## Key Integration Points

1. **SURFACE_LOOP constant alignment**: Defined as 5 in terrain.py:35, svg2stage.py:36,
   profile2stage.py (imports from svg2stage). Consistent but fragile.

2. **tile_type propagation chain**: svg2stage writes `"type": SURFACE_LOOP` to tile_map.json
   → level.py reads `cell.get("type", 0)` → Tile.tile_type → SensorResult.tile_type →
   wall sensor exemption in `find_wall_push`. Any break in this chain = wall blocking.

3. **Collision solidity for loop tiles**: Upper loop tiles (above center) get `TOP_ONLY` (1)
   solidity so the player can enter from below. Lower loop tiles get `FULL` (2) solidity.
   Combined with wall exemption, this should allow 360° traversal.

4. **Ramp-to-loop junction**: Entry ramp last tile is SURFACE_SOLID, first loop tile is
   SURFACE_LOOP. The angle transition at this boundary is the most likely failure point
   for angle-based quadrant switching.

5. **Ground fill continuity**: Ramps have ground fill beneath them. The SVG also defines
   ground polygons beneath the loop. These may produce overlapping tiles at the junction,
   which causes the "impassable gap" warnings but doesn't affect gameplay.

---

## Acceptance Criteria Mapping

| Criterion | Verification Method |
|-----------|-------------------|
| svg2stage completes without errors | Run pipeline, check exit code |
| Zero impassable gap errors in loop+ramp region | Parse validation report |
| Ramp tiles visible with smooth angle progression | Inspect tile_map.json cols 209–241 |
| All tests pass (`uv run pytest -x`) | Run test suite |
| Manual playtest: traverse loop | Run game, drive through loop |

---

## Open Questions

1. **Acceptance criteria strictness**: The ticket says "zero impassable gap errors in the
   loop+ramp region." Current data has 7 such warnings. Are these true errors (player gets
   stuck) or validator noise from overlapping surfaces? Need to investigate whether these
   gaps exist in actual tile geometry or are artifacts of the validation algorithm.

2. **Accidental wall warnings**: Similarly, 2 warnings exist. The wall angle gate should
   prevent these from blocking the player. Need to verify this is the case.

3. **Manual playtest feasibility**: The game runs via Pyxel (graphical). In a headless
   context, we can verify everything except the visual playtest. The physics-level
   verification via test suite is the best automated proxy.

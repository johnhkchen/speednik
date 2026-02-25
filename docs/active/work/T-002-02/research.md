# Research — T-002-02: Stage 1 Hillside Rush

## 1. What This Ticket Requires

Create the Hillside Rush SVG file (`stages/hillside_rush.svg`), run it through the
svg2stage pipeline to produce JSON level data, validate the output, then build a
`speednik/stages/hillside.py` loader that exposes the data to the engine.

Reference: specification.md section 7.1

## 2. Pipeline Tool — tools/svg2stage.py (1073 lines)

Fully implemented and tested (70 tests in test_svg2stage.py). Accepts an SVG file and
an output directory. Produces 5 files: tile_map.json, collision.json, entities.json,
meta.json, validation_report.txt.

### SVG Drawing Conventions (from spec 4.1)

- **Terrain:** Polygons/polylines with stroke color → surface type mapping:
  - `#00AA00` → SOLID (1), `#0000FF` → TOP_ONLY (2), `#FF8800` → SLOPE (3), `#FF0000` → HAZARD (4)
- **Loops:** Circles/ellipses with terrain stroke color → LOOP (5)
  - Pipeline walks the ellipse perimeter at 16px intervals, assigns continuous angles
  - Upper-half tiles flagged with `is_loop_upper` for quadrant mode switching
- **Entities:** `<circle>` or `<rect>` elements with `id` attribute prefix-matching:
  `player_start`, `ring`, `enemy_crab`, `enemy_buzzer`, `spring_up`, `spring_right`,
  `checkpoint`, `goal`, `pipe_h`, `pipe_v`, `liquid_trigger`, `enemy_chopper`
- **ViewBox:** 1:1 mapping to world pixels. 4800x720 viewBox = 4800x720 world.
- **Fill color is ignored.** Only stroke color and geometry matter for terrain.

### Pipeline Internals

- SVGParser reads XML, resolves transforms, extracts TerrainShape and Entity objects
- Rasterizer converts terrain shapes to a TileGrid of TileData objects
  - Walks line segments at 1px resolution, computes per-column height arrays
  - Interior fill: for non-TOP_ONLY shapes, fills below topmost surface as solid
  - Loop handler: walks ellipse perimeter using Ramanujan arc-length approximation
- Validator checks: angle consistency (>21 byte-angle jump), impassable gaps (<18px),
  accidental walls (>3 consecutive steep tiles without loop flag)
- StageWriter outputs the 5 JSON/text files

### Known Pipeline Limitations (from T-002-01 review)

1. Interior fill heuristic may fail on complex concave shapes with overhangs
2. Height array precision issues at exact tile boundaries (zero-height columns)
3. No SVG arc (`A`) command support — avoid arcs in path data
4. Entity ID on terrain-colored shape treated as entity, not terrain

## 3. Stage Specification — Section 7.1

Dimensions: ~4800x720 (300x45 tiles). Single path, left to right.

| Section | X Range      | Content                                                 |
|---------|--------------|---------------------------------------------------------|
| 1       | 0–600        | Flat runway, player_start at x=64, ring arcs            |
| 2       | 600–1600     | Undulating terrain, 25° hills/valleys, 2–3 crabs, rings |
| 3       | 1600–2400    | 3 U-shaped half-pipe valleys, rings at crests, checkpoint|
| 4       | 2400–3200    | Long flat/slight downhill, continuous ring line          |
| 5       | 3200–4000    | Full 360° loop r=128, flat approach, rings inside loop  |
| 6       | 4000–4800    | Gentle downhill, scattered rings, one enemy, goal       |

Objects: ~200 rings, 1 spring at half-pipe exit, checkpoint at section 3, goal post.
Enemies: crab (stationary/patrol), buzzer (hover).

## 4. Terrain Module — speednik/terrain.py

The runtime consumer of pipeline output. Key types:

```python
@dataclass
class Tile:
    height_array: list[int]       # 16 values, 0-16
    width_array: list[int]        # rotated height_array
    angle: int                     # 0-255 byte angle
    solidity: int                  # NOT_SOLID=0, TOP_ONLY=1, FULL=2, LRB_ONLY=3

TileLookup = Callable[[int, int], Optional[Tile]]
```

The `Tile` constructor computes `width_array` from `height_array` automatically.
Solidity constants: NOT_SOLID=0, TOP_ONLY=1, FULL=2, LRB_ONLY=3.

The physics system calls `resolve_collision(state, lookup)` which uses `TileLookup`
to cast floor/ceiling/wall sensors and resolve position.

## 5. Current Runtime Integration — speednik/main.py

Uses a hardcoded `_build_demo_level()` that:
1. Creates a dict `tiles: dict[tuple[int, int], Tile]`
2. Manually constructs Tile objects for a small flat demo area
3. Returns a closure `lookup(tx, ty) -> Tile | None` that reads from the dict

No `level.py` or `stages/hillside.py` exist yet. The stages/ directory contains only
an empty `__init__.py`.

## 6. Camera Integration — speednik/camera.py

`create_camera(level_width, level_height, start_x, start_y)` needs world dimensions
from `meta.json` output. Camera boundary clamping uses `level_width - SCREEN_WIDTH`
and `level_height - SCREEN_HEIGHT`.

## 7. Test Infrastructure

- tests/test_svg2stage.py: 70 tests covering parser, rasterizer, validator, writer, E2E
- tests/fixtures/minimal_test.svg: 320x160 test SVG (the only SVG in the project)
- Tests use pytest, run via `uv run pytest`

## 8. Dependency: T-002-01 (SVG Pipeline)

Status: done. The pipeline is fully implemented and tested. This ticket depends on it
and can proceed.

## 9. Key Constraints and Risks

1. **No arc commands:** The pipeline doesn't support SVG `A` commands. Loops must use
   `<ellipse>` or `<circle>` elements, not path arcs. Curved terrain must use cubic
   bezier `C` commands or polyline approximations.
2. **Interior fill heuristic:** Complex concave half-pipe shapes may need to be split
   into simpler polygons to avoid fill errors.
3. **Angle continuity:** Adjacent terrain tiles should not differ by >21 byte-angle units
   to avoid validator flags. Slope transitions must be gradual.
4. **No level.py yet:** We need to build the runtime loader as part of this ticket
   (acceptance criterion: `speednik/stages/hillside.py` loads pipeline output).
5. **Ring count:** Target ~200 rings across all 6 sections.
6. **Loop geometry:** The loop in section 5 must have correct continuous angle values.
   Using a `<circle>` element with `r=128` and stroke `#00AA00` will invoke the
   pipeline's dedicated loop handler.

## 10. What Exists vs What Must Be Created

| Artifact                          | Status     |
|-----------------------------------|------------|
| tools/svg2stage.py                | Exists     |
| tests/test_svg2stage.py           | Exists     |
| stages/hillside_rush.svg          | Must create|
| Pipeline output (4 JSON + report) | Must generate|
| speednik/stages/hillside.py       | Must create|
| Test for stage loader             | Must create|

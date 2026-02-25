# Research — T-002-03: Stage 2 Pipe Works SVG Layout

## 1. Specification Requirements (Section 7.2)

Stage 2 — "Pipe Works" is an industrial interior with three horizontal routes.

- **Dimensions:** 5600x1024 world pixels (350x64 tiles at 16px/tile)
- **Three routes:** Low (y=768–1024), Mid (y=384–640), High (y=0–256)
- **Five sections:**
  - S1 (0–800): Entry hall, all routes visible, player starts mid
  - S2 (800–2800): Diverged paths — low (enemies, top-only over liquid), mid (gaps, 4 launch pipes), high (fast path, dense rings, 2 drop-down shortcuts)
  - S3 (2800–3800): Liquid rise zone with liquid_trigger entity
  - S4 (3800–4800): Reconvergence, downhill
  - S5 (4800–5600): Goal
- **Entities:** ~300 rings, springs at route transitions, 4 pipe entities, 2 checkpoints, player_start, goal
- **Unique mechanics:** Launch pipes (pipe_h/pipe_v), liquid_trigger, enemy_chopper

## 2. Pipeline Architecture (tools/svg2stage.py)

The pipeline is a standalone 1109-line CLI with zero game imports:

```
SVG file → SVGParser.parse() → Rasterizer.rasterize() → Validator.validate() → StageWriter.write()
```

### SVG Conventions Established by Stage 1

- **Terrain:** `<polygon>`/`<polyline>` with stroke color = surface type. Fill is ignored.
  - `#00AA00` → SURFACE_SOLID (solidity=FULL)
  - `#0000FF` → SURFACE_TOP_ONLY (solidity=TOP_ONLY)
  - `#FF8800` → SURFACE_SLOPE
  - `#FF0000` → SURFACE_HAZARD
- **Terrain closure:** Polygons close to y=world_height for interior fill
- **Loops:** `<circle>`/`<ellipse>` with terrain stroke (no entity `id`)
- **Entities:** SVG elements with `id` matching `typename` or `typename_N` pattern
  - `<circle>` for point entities (rings, player_start, checkpoint, etc.)
  - `<rect>` for box entities (enemies, springs, pipes, goal)
- **Entity ID matching:** Longest-first prefix match from ENTITY_TYPES list

### Supported Entity Types

All needed types are already in the pipeline:
- `player_start`, `ring`, `checkpoint`, `goal` — standard
- `enemy_crab`, `enemy_buzzer`, `enemy_chopper` — all enemies
- `spring_up`, `spring_right` — springs
- `pipe_h`, `pipe_v` — launch pipes (horizontal/vertical)
- `liquid_trigger` — liquid rise zone marker

### Rasterization Details

- Edge-walk at 1px resolution → height arrays + angles per tile
- Interior fill below topmost surface tile (fully solid [16]*16)
- TOP_ONLY tiles exempt from interior fill
- Loop tiles via circle/ellipse handler with `is_loop_upper` flag
- Angle: byte-angle 0–255 (0=flat-right, counter-clockwise)

### Validation Checks

1. Angle consistency: >21 byte-angle diff between neighbors → warning
2. Impassable gaps: 0–18px gaps between solid ranges → warning
3. Accidental walls: >3 consecutive steep tiles (not in loop) → warning

## 3. Stage 1 Reference (hillside_rush.svg)

Stage 1 SVG is 338 lines, viewBox `0 0 4800 720`:
- 9 terrain shapes (polygons + 1 circle for the loop)
- 208 entity elements
- Section-by-section terrain polygons, each closing to y=720
- All rings are individual `<circle>` elements with `id="ring_NNN"`
- Enemies are `<rect>` elements
- Clean separation: terrain has stroke only, entities have fill only

## 4. Stage Loader Pattern (speednik/stages/hillside.py)

The loader is 69 lines:
- `StageData` dataclass: `tile_lookup`, `entities`, `player_start`, `checkpoints`, `level_width`, `level_height`
- `load()` function: reads 4 JSON files from data directory
- Builds `dict[(tx, ty), Tile]` for O(1) lookup via closure
- Lazy loading (no file I/O at import time)

`pipeworks.py` will follow this exact pattern with `_DATA_DIR = Path(__file__).parent / "pipeworks"`.

## 5. Test Pattern (tests/test_hillside.py)

129 lines, 21 tests organized by concern:
- `TestLoadReturnsStageData` — type/shape checks on load()
- `TestTileLookup` — spot-checks at known tile coordinates
- `TestEntities` — exact counts per entity type
- `TestPlayerStart` — exact coordinates
- `TestLevelDimensions` — exact width/height
- `TestLoopGeometry` — tiles exist in loop region, varied angles

Tests for pipeworks will mirror this with Stage 2 specific values:
- Three routes mean testing tile existence at low/mid/high y ranges
- Top-only tiles need solidity verification
- Entity counts: ~300 rings, 4 pipes, 2 checkpoints, enemy types

## 6. Key Constraints & Risks

### SVG Design Constraints
- **Three-route separation:** Each route needs its own terrain polygons. Routes cannot overlap vertically or the rasterizer will produce incorrect height arrays.
- **Top-only platforms:** Blue stroke (`#0000FF`) creates TOP_ONLY solidity — needed for low route over liquid and high route drop-downs.
- **Pipe entities:** `<rect>` with `id="pipe_h_N"` — the pipeline matches by prefix. These are trigger zones, not terrain.
- **liquid_trigger:** Single point entity at x=2800. The game code handles the mechanic.
- **Interior fill behavior:** Polygons must close to y=1024 (bottom of world) for solid ground. Routes that don't reach world bottom need explicit floor polygons.

### Route Geometry
- **Low (768–1024):** 256px tall band. Ground at ~y=900, platforms above. Liquid at y=960.
- **Mid (384–640):** 256px tall band. Ground surfaces + gaps for pipe mechanics. Player starts here.
- **High (0–256):** 256px tall band. Near-continuous flat surface. Reached via spindash off slope.
- **Connecting shafts:** Vertical terrain gaps where routes are accessible. Entry hall (0–800) must allow vertical traversal.

### Slope Entry to High Route
The spec says "spindash off 45° slope" to reach high route. This requires a slope polygon in the entry hall with correct angle (~32 byte-angle for 45° ascending). The slope must launch the player upward with enough vertical velocity to reach y=0–256 from mid route at y=384–640.

### Pipeline Compatibility
- No SVG arc commands (use `<polygon>` and `<polyline>` only)
- Transforms are supported but Stage 1 doesn't use them — keep consistent
- ViewBox must match world dimensions exactly: `0 0 5600 1024`

## 7. Dependencies

T-002-02 (Stage 1 Hillside Rush) is complete. The pipeline, terrain module, and loader pattern are all established. No new pipeline features are needed — all entity types exist.

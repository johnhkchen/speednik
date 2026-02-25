# Research — T-002-04: Skybridge Gauntlet SVG Layout

## Scope

Stage 3 SVG creation, pipeline execution, loader module, and tests. Elevated sky platforms
with build/launch/clear/ascend rhythm escalating over three iterations, path split, boss arena.

## Existing Infrastructure

### Pipeline (`tools/svg2stage.py`, 1074 lines)

Four-layer architecture: SVGParser → Rasterizer → Validator → StageWriter. Fully tested
(70 tests in `tests/test_svg2stage.py`). Accepts SVG, outputs 5 files to a target directory:
tile_map.json, collision.json, entities.json, meta.json, validation_report.txt.

Usage: `uv run python tools/svg2stage.py stages/<input>.svg speednik/stages/<output>/`

### SVG Conventions (from specification §4 and hillside_rush.svg reference)

**Terrain stroke colors:**
- `#00AA00` — solid ground (type 1, FULL solidity)
- `#0000FF` — top-only platform (type 2, jump-through)
- `#FF8800` — slope surface (type 3)
- `#FF0000` — hazard/death (type 4)

**Entity ID prefixes:** player_start, ring, enemy_crab, enemy_buzzer, enemy_chopper,
spring_up, spring_right, checkpoint, goal, pipe_h, pipe_v, liquid_trigger.

**Circles** = entities (ring, checkpoint, player_start, enemy_buzzer).
**Rects** = entities (enemy_crab, spring_up, spring_right, goal).
**Polygons with terrain stroke** = terrain shapes. Fill is ignored.

### Reference Implementation: Hillside Rush

- SVG: `stages/hillside_rush.svg` — 4800×720 viewBox, 6 sections, ~200 rings
- Loader: `speednik/stages/hillside.py` — 69 lines, reads JSON, returns StageData
- Tests: `tests/test_hillside.py` — 129 lines, 11 test classes
- Output: `speednik/stages/hillside/` — tile_map.json, collision.json, entities.json, meta.json

Pattern: section-by-section polygons (not one massive polygon). Each section is a
separate `<polygon>` element. Interior fill is automatic below topmost surface.

### Loader Architecture (`speednik/stages/hillside.py`)

`StageData` dataclass holds: tile_lookup (callable), entities (list[dict]),
player_start (tuple), checkpoints (list), level_width, level_height.

`load()` reads 4 JSON files, constructs Tile objects from tile_map + collision,
returns StageData. Path resolved via `Path(__file__).parent / "hillside"`.

### Terrain Module (`speednik/terrain.py`)

Tile dataclass: height_array (16 ints), angle (0–255), solidity (NOT_SOLID/TOP_ONLY/FULL).
TileLookup type alias: `Callable[[int, int], Optional[Tile]]`.

## Specification Analysis (§7.3)

### Dimensions

5200×896 px = 325×56 tiles. Taller than Hillside (720px) to accommodate elevated platforms.

### Section Layout

| Section | X Range | Content | Key Geometry |
|---------|---------|---------|-------------|
| 1 | 0–800 | Opening bridges | Narrow platforms, gaps 32→48→64px, enemies on bridges |
| 2 | 800–1600 | Rhythm ×1 | 30° ramp, 80px gap, 2 enemies, ascend platform |
| 3 | 1600–2400 | Rhythm ×2 | 35° ramp, 112px gap, 3 enemies |
| 4 | 2400–3200 | Rhythm ×3 | 40° ramp, 144px gap, 4 enemies, requires spindash |
| 5 | 3200–4000 | Path split | Guardian enemy, low detour vs fast spindash-through |
| 6 | 4000–5200 | Boss arena | Flat enclosed, 20 rings |

### Entities Required

- ~250 rings total
- 2 checkpoints: before rhythm ×1 (~x=780), before boss (~x=3980)
- Springs under gaps (safety nets)
- Enemies: crabs, buzzers across sections 1–5
- 1 goal post at stage end

### Angle Calculations for Ramps

Pipeline computes angles from segment geometry. Key byte angles:
- 30° = byte angle ~21 (30 × 256/360 ≈ 21.3)
- 35° = byte angle ~25 (35 × 256/360 ≈ 24.9)
- 40° = byte angle ~28 (40 × 256/360 ≈ 28.4)

For ramp polygons, the slope is defined by the polygon points. A 30° ramp rising
over horizontal distance D has vertical rise D×tan(30°) ≈ D×0.577.

### Coordinate System

Y=0 at top, Y=896 at bottom. Ground level for elevated platforms needs to be
well above Y=896 to leave room for pits below. Suggest main bridge level at ~y=500
with pits dropping to ~y=800+ and higher platforms at ~y=350–450.

## Ramp Launch Physics

The gap distances (80px, 112px, 144px) combined with ramp angles determine required
launch speeds. The pipeline only handles geometry — launch physics are handled by the
engine. The SVG must provide ramps at correct angles and landing platforms at correct
positions so that the engine physics produce viable trajectories.

**Projectile approximation** (gravity = 0.21875 px/frame²):
- 30° ramp, speed ~6: horizontal_v ≈ 5.2, vertical_v ≈ 3.0 → range ≈ 143px (clears 80px)
- 35° ramp, speed ~7: horizontal_v ≈ 5.7, vertical_v ≈ 4.0 → range ≈ 210px (clears 112px)
- 40° ramp, speed ~8+: horizontal_v ≈ 6.1, vertical_v ≈ 5.1 → range ≈ 286px (clears 144px)

These ranges are generous because landing platforms should be reachable at comfortable
speeds. The "requires spindash" constraint for section 4 means regular top_speed (6.0)
won't clear the 144px gap at 40° — player needs spindash boost (~8+).

## Path Split Design (Section 5)

Two routes around a guardian enemy:
- **Main bridge (fast):** Narrow platform with guardian blocking. Spindash at speed ≥ 8 breaks through.
- **Low detour (safe):** Platforms below the bridge. Narrow gaps, slower but safe.

Both routes converge before the boss arena entrance.

## Files to Create/Modify

1. `stages/skybridge_gauntlet.svg` — New SVG with 5200×896 viewBox
2. `speednik/stages/skybridge/` — Pipeline output directory (generated)
3. `speednik/stages/skybridge.py` — Loader module (new, following hillside.py pattern)
4. `tests/test_skybridge.py` — Loader tests (new, following test_hillside.py pattern)

## Constraints and Risks

- **Top-only platforms (`#0000FF` stroke):** Essential for narrow bridges over pits.
  Player can jump through from below but lands on them from above.
- **Interior fill:** Pipeline fills below topmost surface. For elevated platforms over
  empty space, use TOP_ONLY type to avoid filling the entire column below.
- **Polygon complexity:** Keep each polygon simple (convex or mildly concave). Break
  complex shapes into multiple polygons to avoid interior fill issues.
- **Validation warnings:** Complex terrain will generate angle inconsistency warnings
  at section boundaries. Acceptable if < ~200. Impassable gaps should be near zero
  for intended geometry.

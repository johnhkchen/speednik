# Review: T-002-01 svg-to-stage-pipeline

## Summary of Changes

### Files Created
- **`tools/svg2stage.py`** (~580 lines) — Standalone CLI tool converting SVG level designs to stage data
- **`tests/test_svg2stage.py`** (~470 lines) — 70 tests across 10 test classes
- **`tests/fixtures/minimal_test.svg`** — Minimal test fixture with flat ground, slope, and entities

### Files Deleted
- **`tools/.gitkeep`** — Replaced by actual tool implementation

### Files Unchanged
- All existing source files (`speednik/*.py`, `tests/test_physics.py`, `tests/test_terrain.py`)
- `pyproject.toml` — No new dependencies needed (stdlib-only tool)

## Architecture

The tool is a single self-contained Python file with no imports from the `speednik` package. It uses only stdlib: `xml.etree.ElementTree`, `math`, `json`, `argparse`, `re`, `os`, `sys`. Four layers:

1. **SVGParser** — Reads SVG XML, extracts terrain shapes (polygons, paths, circles/ellipses) and entities (circles, rects with id attributes). Handles SVG transforms (translate, scale, rotate, matrix) via 3×3 affine matrix accumulation.

2. **Rasterizer** — Converts terrain shapes into a 2D TileGrid. Walks segment edges at 1px resolution, computes per-column height arrays and byte angles. Fills interior below surface as fully solid. Handles loops (circle/ellipse) with perimeter walking and upper-half flagging.

3. **Validator** — Post-processing checks: angle inconsistency (>30° between neighbors), impassable gaps (<18px), accidental walls (>3 steep tiles without loop flag).

4. **StageWriter** — Outputs 5 JSON/text files: tile_map.json, collision.json, entities.json, meta.json, validation_report.txt.

## Test Coverage

| Component | Tests | Coverage |
|-----------|-------|----------|
| Path parser (M/L/H/V/C/Q/Z, relative) | 11 | All SVG path commands, relative mode, close, implicit lineto |
| SVG parser (polygon, path, circle, rect, transforms) | 16 | Stroke extraction, entity matching, viewbox, transforms |
| Rasterizer (segments, angles, fill) | 11 | Flat/slope rasterization, angle computation, interior fill, top-only skip |
| Loop rasterization | 3 | Tile creation, upper-half flagging, surface type |
| Validator | 10 | All three checks + clean grid, wrap-around, top-only exemption |
| Stage writer | 7 | All 5 output formats, clean/dirty validation reports |
| Tile grid | 4 | Init, get/set, bounds checking |
| Constants | 2 | Color map completeness, solidity mapping |
| End-to-end | 3 | Fixture parsing, full pipeline, CLI subprocess |
| **Total** | **70** | |

Full suite: 200 tests pass (70 new + 130 existing).

## Acceptance Criteria Coverage

| Criterion | Status | Notes |
|-----------|--------|-------|
| Standalone CLI at `tools/svg2stage.py` | ✓ | `python tools/svg2stage.py input.svg output_dir/` |
| Parses SVG terrain (polygon/polyline + stroke color) | ✓ | 4 stroke colors → 4 surface types |
| Parses SVG loops (circle/ellipse) | ✓ | Perimeter walk with tangent angles |
| Parses SVG entities (circle/rect with id) | ✓ | All 12 entity types, prefix matching |
| ViewBox → world pixel space at 1:1 | ✓ | Direct mapping |
| Straight segment rasterization with angles | ✓ | 1px-resolution walk, atan2 → byte angle |
| Curved path sampling at 16px intervals | ✓ | Cubic/quadratic bezier sampling |
| Loop perimeter walk at 16px intervals | ✓ | Ramanujan approximation for step count |
| Height arrays from geometry occupancy | ✓ | Per-column surface y → height computation |
| Output: tile_map.json | ✓ | 2D array of {type, height_array, angle} |
| Output: collision.json | ✓ | 2D array of solidity flags |
| Output: entities.json | ✓ | Flat array of {type, x, y} |
| Output: meta.json | ✓ | Stage dimensions, player_start, checkpoints |
| Output: validation_report.txt | ✓ | All flagged issues |
| Validation: angle inconsistency > 30° | ✓ | Threshold 21 byte-angle units |
| Validation: terrain gaps < 18px | ✓ | Column-based scan |
| Validation: slope > 45° for > 3 tiles | ✓ | Loop flag exemption |
| Test with minimal SVG fixture | ✓ | Flat ground + slope + 4 entities |

## Open Concerns

1. **Interior fill heuristic:** The current fill strategy fills all tiles below the topmost surface tile in each column as solid. This works for simple terrain shapes (flat ground, slopes, hills) but may produce incorrect results for complex concave shapes where the interior should have gaps (e.g., terrain with overhangs). Real Sonic 2 levels don't typically have this complexity, but if they did, a proper polygon scanline fill would be needed.

2. **Height array precision at tile boundaries:** When a segment crosses exactly at a tile boundary (y = N*16), the height computes to 0 for that column. This means boundary-aligned horizontal surfaces produce tiles with zero-height columns at the boundary. In practice this is rarely visible because the interior fill below provides solid tiles, and floor sensors extend to adjacent tiles. But it could cause subtle one-pixel-off issues in edge cases.

3. **No SVG arc (`A`) command support:** The path parser handles M, L, H, V, C, Q, Z but not the SVG arc command (`A`/`a`). Inkscape sometimes uses arcs for rounded rectangles. If a designer uses arc-based paths for terrain, they would be ignored. Adding arc support would require implementing the SVG arc-to-bezier conversion algorithm.

4. **Transform edge cases:** The transform parser handles `translate`, `scale`, `rotate`, and `matrix`. It does not handle `skewX` or `skewY`, which are rare in level design SVGs but technically valid. Also, `rotate(angle, cx, cy)` with 3 arguments is handled but not tested.

5. **Entity type collision:** If an SVG element has both a terrain stroke color AND an entity-matching `id`, the circle/ellipse parsers prioritize entity over terrain. This is the correct behavior (entities are the more specific intent), but it means a designer cannot use entity IDs on terrain-colored shapes. This edge case is documented in the design but not explicitly tested.

6. **No `level.py` consumer yet:** The output format is designed to match `terrain.Tile` fields, but there's no actual loader to validate compatibility end-to-end. The `level.py` module (future ticket) will be the real integration test. Surface type → solidity mapping and height_array semantics should be validated when level.py is implemented.

7. **Performance:** The 1px-resolution segment walk is simple but O(segment_length) per segment. For very long level SVGs (e.g., Stage 2 at 5600px wide), this could be slow. In practice, even a 5600×1024 level with many segments should process in under a second on modern hardware.

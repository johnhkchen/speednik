# Design: T-002-01 svg-to-stage-pipeline

## Decision 1: SVG Parsing Approach

### Option A: stdlib xml.etree + custom path parser
- Pro: Zero external dependencies; tool remains self-contained
- Pro: Full control over parsing behavior; easier to debug
- Con: Must implement SVG path `d` attribute parsing (M, L, C, Q, A, Z commands)
- Con: Must handle transform attribute accumulation manually

### Option B: svgpathtools library
- Pro: Mature path parsing, bezier math, arc handling
- Con: Adds a dependency to pyproject.toml (dev or runtime for tools)
- Con: Overkill — we don't need most of its features

### Option C: svgelements library
- Pro: Handles paths, transforms, and shape-to-path conversion
- Con: Another dependency; API is broad and complex

### Decision: Option A — stdlib + custom parsing

Rationale: The SVG subset we support is narrow. We need:
1. XML tree traversal with transform accumulation — straightforward with ElementTree
2. `<polygon>` / `<polyline>` `points` attribute — trivial comma/space split
3. `<path>` `d` attribute — only M, L, C, Q, Z for terrain; A for arcs
4. `<circle>` / `<ellipse>` / `<rect>` for entities and loops

A focused path parser (~100 lines) covering our subset is better than a general-purpose library. If the SVG subset grows later, we can swap in a library.

## Decision 2: Rasterization Strategy

### Option A: Scanline fill per polygon
- Walk each polygon edge segment, determine which tile columns it intersects
- For each tile column, compute the height of the intersection
- Pro: Handles arbitrary closed polygons cleanly
- Con: Complex for non-convex shapes

### Option B: Segment-by-segment rasterization
- Process each line segment or curve sample independently
- For each segment sample point, mark the tile it occupies and compute local height
- Pro: Simpler, works uniformly for straight and curved paths
- Con: May miss interior fill for thick terrain blocks

### Option C: Hybrid — segment walk + polygon interior fill
- Walk polygon edges segment by segment to establish surface profiles
- Fill interior tiles below the surface as fully solid (height_array = [16]*16)
- Pro: Captures both surface detail and interior solidity
- Con: Slightly more complex

### Decision: Option C — Hybrid approach

Rationale: Terrain in Sonic-style games has both a surface (where angles and height arrays matter) and a bulk interior (fully solid). The surface defines the gameplay; the interior just needs to be solid. Walking edges gives us surface tiles with correct height arrays and angles. Flood-filling below gives us solid interior tiles.

Implementation:
1. For each terrain polygon, walk each edge as a series of line segments (or sampled curve points at 16px intervals)
2. For each tile the edge crosses, compute the height_array column values from the edge's intersection with that column
3. Assign angle from the segment's slope direction (in byte-angle 0–255)
4. After surface pass, fill all tiles below the surface that are inside the polygon as fully solid (height_array=[16]*16, angle inherited from surface above)

## Decision 3: Loop Handling

### Option A: Detect ellipse elements and generate tiles along perimeter
- Parse `<circle>` and `<ellipse>` with terrain stroke colors
- Walk the perimeter at 16px arc-length intervals
- Generate tiles with tangent angles at each point
- Flag upper-half tiles for quadrant mode switching

### Option B: Treat loops as regular polygons (let designers approximate with polylines)
- Simpler but shifts burden to the designer
- Loses smooth angle continuity

### Decision: Option A — Dedicated loop handler

Rationale: Loops are a core Sonic mechanic. Smooth angle transitions around the loop are critical for physics. The pipeline should handle this automatically from circle/ellipse elements.

Implementation:
1. Detect `<circle>`/`<ellipse>` elements with terrain stroke colors (not entity IDs)
2. Walk perimeter at 16px arc-length intervals
3. At each point: compute tangent angle → byte angle, determine tile coords, compute height_array from local geometry
4. Flag tiles in upper half (y < ellipse center y) with a loop marker for quadrant switching

## Decision 4: Output Type Field Semantics

The spec shows `"type": 1` in tile_map.json but doesn't define mappings explicitly.

### Decision: Type maps to surface type, not solidity

```
0 = empty (no tile)
1 = solid ground  (#00AA00)
2 = top-only      (#0000FF)
3 = slope          (#FF8800)
4 = hazard         (#FF0000)
5 = loop           (circle/ellipse terrain)
```

Solidity is derived from type (in collision.json): types 1,3,4,5 → FULL; type 2 → TOP_ONLY.

This separation lets the renderer use type for visual theming while the physics engine uses collision.json for solidity.

## Decision 5: Entity ID Matching

### Option A: Exact match
- `id="ring"` only — no numbering
- Problem: SVG requires unique IDs, so can't have two elements both `id="ring"`

### Option B: Prefix match
- `id="ring"`, `id="ring_1"`, `id="ring_42"` all match as "ring"
- Split on underscore, take first token, match against known types

### Option C: Regex match
- `id` starts with known type name, followed by optional separator + digits

### Decision: Option B — Prefix match with underscore separator

Match strategy: strip trailing `_N` (digits) from `id`, compare against known entity types. This is how designers naturally number duplicate entities in SVG editors.

Known types: `player_start`, `ring`, `enemy_crab`, `enemy_buzzer`, `enemy_chopper`, `spring_up`, `spring_right`, `goal`, `checkpoint`, `pipe_h`, `pipe_v`, `liquid_trigger`.

Complication: `player_start` has an underscore in it. Solution: match against the full set of known types greedily — try longest match first.

## Decision 6: Height Array Computation for Angled Segments

For a line segment crossing a tile column at position `col`:
1. Compute where the segment enters and exits the column's x-range `[tile_x*16 + col, tile_x*16 + col + 1]`
2. The height at this column = how far the segment is from the tile's bottom edge
3. Specifically: `height = max(0, min(16, tile_bottom_y - segment_y_at_column))`
4. Where `segment_y_at_column` is the y-coordinate of the segment at the column's center x

This naturally produces:
- Flat segment → all heights equal (e.g., [16]*16 for segment at tile bottom)
- 45° slope → linear ramp [0, 1, 2, ..., 15] or [16, 15, ..., 1]
- Shallow slope → gradual ramp

## Decision 7: Angle Computation

Segment slope to byte angle:
```python
# atan2 gives angle in radians, clockwise from right in screen coords
rad = math.atan2(-(y2 - y1), x2 - x1)  # negate dy because screen y is inverted
byte_angle = round(rad * 256 / (2 * math.pi)) % 256
```

Convention: byte angle 0 = flat floor (rightward), 64 = right wall (downward in screen), 128 = ceiling, 192 = left wall. This matches the engine's quadrant system in terrain.py.

## Decision 8: Validation Implementation

All three checks run as a post-processing pass after rasterization:

1. **Angle inconsistency:** For each tile with angle A, check 4-neighbors. If any neighbor has angle B and `min(|A-B|, 256-|A-B|) > 21` (≈30°), flag it.

2. **Impassable gaps:** Scan each column top-to-bottom. If there's a gap between two solid tiles < 18px and neither is TOP_ONLY, flag it.

3. **Accidental walls:** Scan horizontally. Track consecutive tiles with angle in the steep range (byte angles ~32–96 or ~160–224, i.e., > 45°). If > 3 consecutive without a loop flag, flag it.

## Rejected Alternatives

- **Runtime SVG parsing:** Loading SVGs at game start would be slow and require SVG parsing in the game. Build-time conversion is correct.
- **Binary output format:** JSON is human-readable, debuggable, and fast enough for level data. Binary adds complexity with no real gain at this scale.
- **Numpy for rasterization:** Would be faster but adds a heavy dependency for a build tool that runs once per level edit.
- **Separate parser module:** A single `svg2stage.py` file keeps the tool self-contained and easy to run from any context.

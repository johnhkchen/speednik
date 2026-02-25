# Design — T-002-02: Stage 1 Hillside Rush

## Decision 1: SVG Terrain Representation Strategy

### Options

**A. Single continuous polygon for all terrain.**
One massive polygon tracing the entire ground surface from x=0 to x=4800. Simple but
impossible to manage — the point list would be hundreds of entries, and the interior
fill heuristic may fail on complex concave shapes (half-pipes, loop entry/exit).

**B. Section-by-section polygons with shared boundary edges.**
Each section (1–6) as a separate closed polygon. Polygons share boundary Y coordinates
at section edges. Simpler shapes reduce fill heuristic risk. The pipeline handles
multiple overlapping terrain shapes by last-write-wins on the tile grid.

**C. Hybrid: polylines for surface contour + separate fill rectangles.**
Polylines define the surface shape, rectangles provide solid ground beneath. Most
control but more SVG elements to manage.

### Decision: Option B — Section-by-section polygons

Rationale: Each section has distinct geometry (flat, slopes, half-pipes, loop approach).
Separate polygons keep each shape simple enough for the interior fill heuristic.
The loop in section 5 is a dedicated `<circle>` element handled by the pipeline's
loop handler. Shared boundary Y values ensure seamless terrain.

## Decision 2: Loop Implementation

### Options

**A. `<circle>` element with terrain stroke color.**
The pipeline has a dedicated loop handler that recognizes circles/ellipses with terrain
stroke. It walks the perimeter at 16px intervals and generates tiles with continuous
angles. Upper-half tiles get `is_loop_upper` flag for quadrant switching.

**B. Approximate with bezier curves in a `<path>` element.**
Manual control of every point. Loses the loop handler's automatic angle continuity
and upper-half flagging.

### Decision: Option A — `<circle>` element

Rationale: The pipeline's loop handler is purpose-built for this. A `<circle cx="3600"
cy="360" r="128" stroke="#00AA00">` generates correct continuous angles and upper-half
flags automatically. The flat approach runway connects to the loop entry/exit with
separate terrain polygons.

## Decision 3: Half-Pipe Valley Geometry (Section 3)

### Options

**A. Polyline approximation of U-shapes.**
Define each half-pipe as a polyline with ~8-12 points tracing the curve. Produces
piecewise-linear terrain. Angles change discretely at each point, which the validator
accepts if steps are ≤21 byte-angle units.

**B. Bezier curves via `<path>` elements.**
Smooth curves via cubic beziers. The rasterizer samples these at ~16px intervals.
Better angle continuity but more complex SVG.

### Decision: Option A — Polyline approximation

Rationale: Half-pipes at the scale described (depths increasing from ~80px to ~160px
over 256px widths) produce gentle slopes where polyline segments of 32-48px produce
angle changes well within the 21 byte-angle threshold. Simpler to author and debug.
Polylines also avoid any curve sampling edge cases.

## Decision 4: Ring Placement Strategy

### Options

**A. Individual `<circle>` elements for each ring.**
~200 circles with `id="ring_N"`. Explicit positioning. The pipeline extracts each as
an entity.

**B. Ring arcs/patterns using SVG `<g>` groups.**
Groups of rings, relying on group transforms. But the pipeline accumulates transforms,
so grouped circles work correctly. However, this doesn't reduce the element count.

### Decision: Option A — Individual circles

Rationale: The pipeline handles individual circles perfectly. Entity extraction uses
prefix matching on `id`, so `ring_1` through `ring_200` all match. No benefit to
grouping since the pipeline flattens everything. Individual placement gives precise
control over ring positions matching terrain contours.

## Decision 5: Stage Loader Architecture

### Options

**A. Load JSON at import time (module-level).**
`hillside.py` reads JSON files in a known relative path at import time, constructing
Tile objects and the TileLookup eagerly.

**B. Lazy loading via a function.**
`hillside.py` exports a `load()` function that reads and parses JSON on demand.
Avoids file I/O at import time. Returns a structured stage data object.

**C. Embed pipeline output as Python data literals.**
Run the pipeline, then convert JSON to Python dict/list literals baked into hillside.py.
No runtime JSON dependency. But couples the source file to pipeline output format.

### Decision: Option B — Lazy loading via function

Rationale: Import-time I/O (option A) is fragile and makes testing harder. Embedded
literals (option C) create a maintenance burden when the pipeline is re-run. A `load()`
function is clean, testable, and follows the pattern the demo level already uses (a
function that returns tiles + metadata). The function returns a dataclass with
`tile_lookup`, `entities`, `meta`, and `level_width`/`level_height`.

## Decision 6: Pipeline Output Location

### Options

**A. Output to `speednik/stages/hillside/` (inside the Python package).**
Files ship with the package. `hillside.py` uses `importlib.resources` or `__file__`
relative paths to find them.

**B. Output to a top-level `stages/` directory (outside the package).**
Separate data from code. Requires a path configuration mechanism.

### Decision: Option A — Inside the package at `speednik/stages/hillside/`

Rationale: The spec lists `speednik/stages/hillside.py` as the loader. Having the JSON
data alongside in `speednik/stages/hillside/` keeps data and loader co-located. Using
`Path(__file__).parent / "hillside"` for path resolution is simple and works for both
development and packaged distributions.

## Decision 7: SVG Coordinate Strategy

The viewBox is `0 0 4800 720`. Y=0 is top of world, Y=720 is bottom. Ground level
is near y=620-640 for most sections (leaving ~80-100px of sky above). This gives room
for the loop (center ~y=360, radius 128, top at y=232, bottom at y=488) and half-pipe
valleys (deepest at ~y=640).

Player start at (64, ~610) — standing on flat ground at section 1.

## Decision 8: Enemy and Entity Placement

Per spec 7.1:
- Section 2: 2–3 crab enemies on flat sections between slopes
- Section 3: Checkpoint at entry
- Section 5: Rings inside the loop
- Section 6: One enemy (buzzer for variety), goal post
- 1 spring at half-pipe exit (section 3 end, facing up to help slow players escape)
- ~200 rings distributed across sections with density matching terrain features

## Summary of Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Terrain representation | Section-by-section polygons |
| 2 | Loop implementation | `<circle>` element with pipeline loop handler |
| 3 | Half-pipe geometry | Polyline approximation of U-shapes |
| 4 | Ring placement | Individual `<circle>` entities |
| 5 | Stage loader | Lazy `load()` function returning structured data |
| 6 | Output location | `speednik/stages/hillside/` inside package |
| 7 | Coordinate strategy | viewBox 0 0 4800 720, ground ~y=620 |
| 8 | Entity placement | Per spec, distributed across sections |

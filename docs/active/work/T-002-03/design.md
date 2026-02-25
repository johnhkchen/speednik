# Design — T-002-03: Stage 2 Pipe Works SVG Layout

## 1. Core Design Challenge

Stage 2 has a fundamentally different structure from Stage 1. Stage 1 is a single linear path. Stage 2 is three parallel horizontal routes stacked vertically in a 5600x1024 world, converging at sections 1, 3, 4, and 5.

The SVG must produce valid terrain for all three routes simultaneously without vertical overlap that would confuse the rasterizer's interior fill heuristic.

## 2. Approach Options

### Option A: Single Monolithic SVG with Section Groups
One SVG file. Use `<g>` groups per section. Each route within a section gets its own polygon(s). Terrain closes to route-local floor, not always y=1024.

**Pros:** All in one file, easy to reason about coordinates.
**Cons:** Complex polygon management for three routes with separate floor levels.

### Option B: Route-Separated Polygons with Explicit Floors
One SVG file. Each route's terrain is a separate polygon closing to a local floor. Explicit floor polygons bridge from route floor down to y=1024 where needed (entry hall, convergence zones).

**Pros:** Clean route separation, rasterizer fill works correctly per polygon. Matches Stage 1 pattern.
**Cons:** More polygons, need to ensure no vertical overlap between route geometries.

### Option C: SVG Groups with Transforms
Use `<g transform="translate(0, offset)">` for each route, designing each route in a local coordinate space.

**Pros:** Each route designed independently.
**Cons:** Breaks mental model of absolute world coordinates, harder to coordinate connecting shafts.

### Decision: Option B — Route-Separated Polygons with Explicit Floors

This matches the Stage 1 pattern of section-by-section polygons closing to the bottom. The key adaptation: each route's polygon closes to its own floor level, and explicit solid-fill rectangles provide the ground below each route where needed.

Rationale:
- The rasterizer's interior fill walks downward from the topmost surface tile. If a mid-route polygon closes to y=1024, it would create solid fill through the low route's airspace. Route polygons must close to their route's floor instead.
- The entry hall (S1) and convergence zones (S3/S4/S5) where all routes merge need full-height terrain from surface down to y=1024.
- Connecting shafts between routes are simply gaps in the terrain — vertical spaces where no polygon exists.

## 3. SVG Structure Design

### ViewBox
`0 0 5600 1024` — matches world dimensions exactly.

### Route Floor Levels
- **High route floor:** y=256 (bottom of 0–256 band). Polygons close to y=256.
- **Mid route floor:** y=640 (bottom of 384–640 band). Polygons close to y=640.
- **Low route floor:** y=1024 (world bottom). Polygons close to y=1024.
- **Full-height sections** (S1, S3, S4, S5): Polygons close to y=1024.

### Section 1 — Entry Hall (0–800)

All three routes visible. This is a single tall room.

**Terrain polygons:**
1. **Left wall + ceiling:** Polygon forming the room boundary at x=0 from y=0 to y=1024
2. **Mid ground:** Flat platform at y=520 (mid route surface), x=100 to x=800. This is where the player starts.
3. **45° slope ramp:** Ascending slope from mid ground to high route. Located at x=200–400, going from y=520 up toward y=200. Uses `#FF8800` (SLOPE) stroke for correct angle.
4. **Low ground:** Floor at y=900, x=0 to x=800. Closes to y=1024.
5. **Top-only platforms:** Blue-stroke platforms creating the drop-down from mid to low.

**Key geometry:** The 45° slope for high route access. From mid surface (~y=520) ascending to high route entry (~y=200) requires a slope over ~320px vertical rise. At 45°, that's 320px horizontal = x=200 to x=520. The byte-angle for a 45° ascending-right slope is 32.

### Section 2 — Diverged Paths (800–2800)

Three independent route geometries for 2000px.

**High route (y=0–256):**
- Near-flat surface at y=160, x=800 to x=2800. One polygon closing to y=256.
- Dense rings (~100 rings along this path).
- Two drop-down shortcuts to mid route: top-only platforms at x=1600 and x=2200. These are blue-stroke `#0000FF` thin platforms that allow falling through from above.

**Mid route (y=384–640):**
- Platform segments with gaps between them. 4 pipe_h entities bridge the gaps.
- Platforms: x=800–1200, x=1300–1700, x=1800–2200, x=2300–2800. Each closing to y=640.
- pipe_h rects positioned at the gaps.
- Moderate rings (~80 rings), some enemy_buzzers at gap crossings.

**Low route (y=768–1024):**
- Floor at y=900, x=800 to x=2800. Closes to y=1024.
- Top-only platforms at y=880 over liquid areas (liquid at y=960).
- enemy_crab and enemy_chopper entities.
- Fewer rings (~40 rings).

### Section 3 — Liquid Rise Zone (2800–3800)

Routes converge into a single tall room. The geometry funnels all three routes into one vertical space.

**Terrain:** Tall room with floor at y=960, walls at x=2800 and x=3800. Platforms at various heights for vertical traversal. Closes to y=1024.

**Entity:** `liquid_trigger` at x=2800. Checkpoint at x=2820.

### Section 4 — Reconvergence (3800–4800)

Single path. Downhill slopes from y=400 to y=800. Enemy cluster. Closes to y=1024.

### Section 5 — Goal (4800–5600)

Flat approach at y=800. Goal post. Second checkpoint at entry (x=4820).

## 4. Entity Placement Strategy

### Rings (~300 total)
- High route S2: ~100 (dense reward, spaced ~20px)
- Mid route S2: ~80 (moderate, near platforms)
- Low route S2: ~40 (sparse)
- S1 entry: ~20
- S3 convergence: ~20
- S4 downhill: ~25
- S5 goal: ~15

### Pipes (4 total)
All `pipe_h` (horizontal), placed at mid-route gaps in S2:
- pipe_h_1: x=1200, y=520 (gap between platforms 1 and 2)
- pipe_h_2: x=1700, y=520 (gap between platforms 2 and 3)
- pipe_h_3: x=2200, y=520 (gap between platforms 3 and 4)
- pipe_h_4: x=2300, y=520 (alternate gap)

### Springs
- spring_up at high route entry (top of slope, S1)
- spring_right at mid-to-low transition points

### Checkpoints (2)
- checkpoint_1: x=2820 (S3 entry — liquid rise zone)
- checkpoint_2: x=4820 (S5 entry — goal approach)

### Enemies
- enemy_crab: 4–5 on low route S2, 2 in S4
- enemy_buzzer: 2–3 at mid route gaps in S2
- enemy_chopper: 2 in S3 liquid zone

## 5. Top-Only Platform Design

Top-only platforms (`#0000FF` stroke) serve two purposes:
1. **Low route over liquid:** Platforms at y=880 in low route S2 let the player walk over liquid (y=960) while allowing upward traversal.
2. **High route drop-downs:** Thin platforms in high route at x=1600 and x=2200 that the player can drop through to reach mid route.

These are small polygons (e.g., 64px wide, 16px tall) with blue stroke.

## 6. Rejected Approaches

- **Transforms for route offset:** Rejected. Absolute coordinates are clearer and match Stage 1 pattern.
- **Single polygon per route:** Rejected. Route terrain within a section may need multiple polygons (platforms with gaps in mid route).
- **Shared interior fill across routes:** Rejected. Each route polygon must close to its own floor level, not y=1024, to prevent filling through lower routes' airspace.
- **Bezier curves for slopes:** Rejected. Stage 1 uses polygon vertices only. Beziers would add complexity without visual benefit at 16px tile resolution.

## 7. Validation Expectations

Expected warnings (non-critical):
- Angle inconsistencies at polygon joins (same as Stage 1)
- Possible impassable gap warnings at route transitions
- No accidental walls expected (no steep multi-tile runs outside loops)

Zero critical flags expected. No loops in this stage.

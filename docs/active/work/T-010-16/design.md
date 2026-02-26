# Design — T-010-16: directional-terrain-raycast

## Decision: Step-Based Raycasting (Option A)

### Options Evaluated

**Option A: Step-based raycasting** — Walk along the ray in fixed pixel increments, check
tile occupancy at each step.

Pros:
- Simple to implement (~30 lines of logic)
- Directly uses existing `TileLookup` and `Tile.height_array`
- Easy to reason about correctness
- No new algorithmic complexity

Cons:
- More iterations than DDA (checks every step, not just tile boundaries)
- At step=1, max 128 iterations per ray; at step=2, max 64

**Option B: DDA (Digital Differential Analyzer)** — Classic grid-traversal that jumps from
tile boundary to tile boundary.

Pros:
- Fewer iterations (max_range/16 ≈ 8 tile crossings per ray)
- Classic, well-understood algorithm

Cons:
- More complex: need to track separate x/y step distances, handle tile-boundary crossings
- Within each tile, still need sub-tile height check (DDA only tells you which tile, not
  whether the ray hits solid within that tile)
- The height_array means tiles aren't fully solid/empty — slopes create partial occupancy.
  DDA gives you the tile, but you still need per-column/row checks within it.
- Significantly more code (~80-100 lines) for marginal speedup in pure Python

**Option C: Reuse existing axis-aligned sensors** — Decompose the angled ray into x/y
components and combine existing sensor casts.

Pros:
- Reuses proven code

Cons:
- Doesn't actually work for arbitrary angles — the existing sensors cast in one axis only
- Would require projecting results, losing accuracy on diagonal rays
- Conceptually wrong for the problem

### Decision: Option A

The ticket recommends Option A and the research confirms it. Key reasons:

1. **Height arrays create sub-tile complexity.** Even with DDA, you'd need per-pixel checks
   within each tile to handle slopes. DDA's advantage (skipping empty tiles) is reduced
   because you can't skip to the next tile boundary — you need to check if the ray hits
   the slope surface within the current tile.

2. **Performance is fine.** 7 × 128 = 896 tile lookups. A tile lookup is a dict.get() —
   nanoseconds. Total is well under 1ms even in CPython.

3. **Simplicity wins.** The function needs to be correct and testable. Step-based is easier
   to validate against known geometric scenarios.

4. **Optimize later.** If profiling shows this is a bottleneck (unlikely), DDA can replace
   the inner loop without changing the interface.

---

## Step Size: 1 Pixel

Use step=1 for maximum accuracy. At max_range=128, that's 128 iterations — still fast.
The height_array has 1-pixel column resolution, so step=2 could miss a 1-pixel-wide solid
column. For observation quality, 1px accuracy is worth the minimal extra cost.

---

## Pixel-in-Solid Test

The core primitive needed is: "Is pixel (px, py) inside solid terrain?"

```
tile_x = int(px) // TILE_SIZE
tile_y = int(py) // TILE_SIZE
col = int(px) % TILE_SIZE
row = int(py) % TILE_SIZE
tile = tile_lookup(tile_x, tile_y)
if tile is None or tile.solidity == NOT_SOLID:
    → not solid
height = tile.height_array[col]
is_solid = (row >= TILE_SIZE - height)
```

This is derived directly from the height_array semantics: solid fills the bottom `height`
pixels of the tile, so rows `[16-height, 16)` are solid.

### Solidity Filter

For observation rays, use a permissive solidity filter: treat FULL, TOP_ONLY, and LRB_ONLY
all as solid. The player can see all terrain regardless of one-way platform behavior.
Only NOT_SOLID (0) tiles are invisible to rays.

---

## Surface Angle Extraction

When a solid pixel is found, the surface angle is `tile.angle`. This is the byte angle
(0–255) stored on the tile, representing the surface orientation. Return it directly.

---

## Ray Direction Computation

Input: `angle_deg` in the ticket's convention (0=right, positive=downward).

In screen coordinates (Y-down), this is a clockwise angle from +X:
- `dx = cos(angle_deg * π/180)`
- `dy = sin(angle_deg * π/180)`

For left-facing rays, the caller (observation module in T-010-17) will mirror the angle
before calling. The raycast function itself is facing-agnostic.

---

## Return Value

`(distance: float, surface_angle: int)`

- `distance`: Euclidean distance from origin to hit point, clamped to [0, max_range].
  If no surface found, returns `max_range`.
- `surface_angle`: byte angle (0–255) of the hit tile. If no surface found, returns 0.

This matches the ticket's proposed signature exactly.

---

## Handling Negative/OOB Coordinates

Python's `//` operator does floor division, so `int(-1.5) // 16 = 0 // 16 = 0` is wrong
for negative values since `int(-1.5) = -1` and `-1 // 16 = -1` which is correct.

But `int()` truncates toward zero: `int(-0.5) = 0`, `int(-1.5) = -1`. For fractional
negatives close to zero, `int(-0.5) = 0` but `math.floor(-0.5) = -1`. Need to use
`math.floor()` for correct tile coordinate computation with negative positions.

Use: `tile_x = math.floor(px) // TILE_SIZE` — no, that double-floors.
Actually: `tile_x = int(math.floor(px)) // TILE_SIZE` is also wrong for non-integer px.

The correct approach: `tile_x = math.floor(px / TILE_SIZE)` or equivalently
`tile_x = int(math.floor(px)) // TILE_SIZE` since `math.floor` gives the true floor and
then `//` on the resulting integer gives correct tile index.

Simpler: convert to integer first via `math.floor`, then use integer `//` and `%`:
```python
ipx = math.floor(px)
tile_x = ipx // TILE_SIZE  # correct floor division for negative ints
col = ipx % TILE_SIZE       # correct modulo for negative ints (Python % is floored)
```

This handles all cases correctly because Python's `//` and `%` are floored for integers.

---

## What Was Rejected

- **DDA**: Overkill for this use case. Sub-tile slope geometry negates DDA's main advantage.
- **Step=2**: Risks missing 1px-wide features. Not worth the 2× speedup given the total
  cost is already negligible.
- **Reusing axis-aligned sensors**: Conceptually doesn't work for arbitrary angles.
- **Placing in observation.py**: Terrain raycast is terrain logic. It uses TileLookup and
  Tile directly. Keeping it in terrain.py maintains module cohesion.

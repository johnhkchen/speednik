# Research: T-013-03-BUG-01 — skybridge-terrain-pocket-trap-x413

## Actual Behavior (differs from ticket description)

The ticket describes the walker getting trapped at x≈413 oscillating between on_ground and
jumping. Simulation tracing reveals a **different mechanism**: the walker transitions into
ceiling-walking mode (angle=128, quadrant 2) on the underside of the bridge platform, walks
backwards (leftward at ~6.0 px/frame), hits an enemy around x=416 at frame 329, takes
damage, and falls into the left pillar at (284, 612), then drops to a pit death.

The **spring at x=304 is never touched**. The problem occurs entirely on the bridge platform.

## Root Cause: Wall-Angle Tiles at Platform Gap Edges

### Bridge platform layout (rows 31-32, y=496-527)

The skybridge stage uses TOP_ONLY (solidity=1) tiles at rows 31-32 for the bridge deck.
At each gap in the bridge, the tiles flanking the gap have wall angles:

| Position       | Angle | Quadrant | Role       |
|---------------|-------|----------|------------|
| Right of gap  | 64    | 1 (R wall)| Left edge |
| Left of gap   | 192   | 3 (L wall)| Right edge|
| Interior      | 0     | 0 (floor) | Normal    |
| Interior (r32)| 128   | 2 (ceil)  | Underside |

Gaps in row 31:
- cols 19 (x=304-319), width 1 tile
- cols 27-28 (x=432-463), width 2 tiles
- cols 36-38 (x=576-623), width 3 tiles
- cols 73-76 (x=1168-1231), width 4 tiles

### Transition sequence (traced from simulation)

1. Walker runs right on flat bridge at y=480 (angle=0, quadrant 0)
2. Steps onto edge tile with angle=64 → quadrant 1 (right wall mode)
3. In wall mode, "floor" sensors point RIGHT, ground_speed converts to y_vel (upward)
4. Walker rides the pillar edge upward until losing ground (falls off top of pillar)
5. Falls back to platform, repeats at next gap edge
6. At column 35 (x=569.8), angle=192 → quadrant 3 (left wall mode)
7. Rides down the pillar, transitions to angle=128 → quadrant 2 (ceiling mode)
8. Now walking upside-down on row 32 underside at y=503.4, moving leftward at full speed
9. Hits enemy at x≈416, takes damage knockback, falls into left pillar, pit death

### Why angle=64/192 exist on these tiles

Row 31 edge tiles use angle=64 (right wall) and angle=192 (left wall) likely inherited
from the pillar geometry below (rows 38-42). The collision pipeline probably assigned wall
angles to all tiles on pillar columns, including the TOP_ONLY bridge deck tiles that
happen to share x-coordinates with pillar edges. These angles are correct for the FULL
solidity pillar tiles below, but wrong for the TOP_ONLY bridge deck tiles.

## Relevant Files

| File | Role |
|------|------|
| `speednik/stages/skybridge/tile_map.json` | Tile definitions (height_array, angle, type) |
| `speednik/stages/skybridge/collision.json` | Solidity grid (0=none, 1=top-only, 2=full) |
| `speednik/terrain.py` | Sensor casts, quadrant mapping, collision resolution |
| `speednik/constants.py` | Physics constants (SPRING_UP_VELOCITY=-10.0) |
| `speednik/objects.py` | Spring collision handler |
| `speednik/qa.py` | Archetype definitions (walker, wall_hugger) |
| `speednik/simulation.py` | Headless simulation step |
| `speednik/level.py` | `_build_tiles()` loads tile_map + collision into Tile objects |

## Key Observations

1. **Row 31 has 8 edge tiles** with wall angles (4 gaps × 2 edges) that need correction
2. **Row 32 has the same pattern** — same columns have angle=64/128 at gap edges
3. The row 32 tiles use angle=128 (ceiling) for interior tiles, which is intentional
   for the bridge underside. But edge tiles at row 32 also have angle=64, which is wrong.
4. The pillar tiles at rows 38-42 with angle=64/192 are **correct** — they define the
   pillar walls and should remain unchanged.
5. The spring at x=304 is not part of this bug — it sits below the bridge (y=608) and
   the walker never reaches it because it ceiling-walks backwards and dies first.

## Constraints

- Only tile_map.json needs to change (angles of specific tiles)
- collision.json solidity values are correct — TOP_ONLY for bridge, FULL for pillars
- No code changes needed — the terrain engine correctly implements quadrant rotation;
  the data is wrong, not the engine
- Fix must not affect pillar collision behavior (rows 38+)

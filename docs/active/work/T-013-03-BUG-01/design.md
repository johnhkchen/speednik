# Design: T-013-03-BUG-01 — skybridge-terrain-pocket-trap-x413

## Problem Statement

Bridge deck tiles at gap edges in tile_map.json have wall angles (64/192) that cause the
walker to transition from floor mode into wall/ceiling mode. The walker then walks upside-down
on the bridge underside, hits enemies, and falls to death. The angles should be 0 (flat floor)
for row 31 edge tiles so the player walks off the edge and falls through the gap normally.

## Options Considered

### Option A: Fix tile angles in tile_map.json (data fix)

Change the `angle` field of bridge deck edge tiles from wall angles to floor angles:
- Row 31 edge tiles: angle 64 → 0, angle 192 → 0
- Row 32 edge tiles: angle 64 → 0 (keep 128 for interior underside tiles)

**Pros:**
- Directly fixes the root cause
- No code changes needed
- Minimal risk — only affects the specific tiles causing the bug
- Matches how the same tiles should behave: flat platforms

**Cons:**
- Manual data edit in a large JSON file
- Must identify all affected tiles precisely

### Option B: Add angle clamping in terrain.py for TOP_ONLY tiles

Add logic in `resolve_collision()` to force angle=0 when landing on TOP_ONLY tiles,
preventing wall-mode transitions on platform surfaces.

**Pros:**
- Systemic fix — prevents this class of bug globally
- No data file edits needed

**Cons:**
- TOP_ONLY tiles with non-zero angles may be intentional in other contexts (ramps, slopes)
- Adds runtime overhead for a data error
- Violates the principle that the engine trusts tile data
- Risk of breaking other stages that intentionally use angled TOP_ONLY tiles

### Option C: Fix the collision pipeline that generated wrong angles

Find and fix the pipeline tool that assigned wall angles to bridge deck tiles.

**Pros:**
- Prevents recurrence when regenerating tile data

**Cons:**
- Pipeline may not exist or may be external
- Still need to fix the current data anyway
- Out of scope for this bug ticket

## Decision: Option A — Fix tile angles in tile_map.json

**Rationale:**
1. The data is wrong, not the engine. The engine correctly handles quadrant rotation;
   it's the tile data that incorrectly labels flat platform edges as walls.
2. Option B would mask data errors and risk breaking legitimate angled TOP_ONLY tiles
   (slopes, ramps) in other stages.
3. The fix is precise, auditable, and low-risk.

## Tiles to Fix

### Row 31 (y=496-511) — bridge deck top layer

| Column | Current Angle | Fix To | Position |
|--------|--------------|--------|----------|
| 12     | 64           | 0      | Right of gap (col 11) |
| 20     | 64           | 0      | Right of gap (cols 18-19) |
| 29     | 64           | 0      | Right of gap (cols 26-28) |
| 39     | 64           | 0      | Right of gap (cols 35-38) |
| 18     | 192          | 0      | Left of gap (col 19) |
| 26     | 192          | 0      | Left of gap (cols 27-28) |
| 35     | 192          | 0      | Left of gap (cols 36-38) |

For consistency, also check col 50 (angle=64) and any other edge tiles beyond col 50.

### Row 32 (y=512-527) — bridge deck bottom layer

| Column | Current Angle | Fix To | Position |
|--------|--------------|--------|----------|
| 12     | 64           | 0      | Right of gap |
| 20     | 64           | 0      | Right of gap |
| 29     | 64           | 0      | Right of gap |
| 39     | 64           | 0      | Right of gap |

Row 32 left-edge tiles (cols 18, 26, 35) already have angle=128 which is correct for the
underside. But since they're at gap edges, they may also cause issues — verify during testing.

### What NOT to fix

- Pillar tiles at rows 38-42 with angle=64/192 — these are correct wall definitions
- Row 32 interior tiles with angle=128 — correct underside angle
- Any tiles beyond the identified gaps

## Verification Strategy

1. Run walker archetype on skybridge: walker should fall through gaps (not wall-walk)
2. Walker should reach well past x=413 (reaching at least x=600+)
3. No quadrant_diagonal_jump warnings in the gap regions
4. Springs at x=304, x=440, x=592 should still function if player lands on them
5. Pillar collision (rows 38+) should be unaffected

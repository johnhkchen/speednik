# Design — T-013-03-BUG-03: Speed Demon Pit Death on Skybridge

## Problem Statement

Speed demon dies at x≈1590 on Skybridge. The player rolls down the first slope
(cols 50-75, x=800-1200), launches off the upslope exit at x≈1162, flies over bridge
segment 5 (cols 76-99) entirely, hits a FULL-solidity wall at x=1600 (col 100), gets
x_vel zeroed, and falls to pit death.

The death repeats infinitely because the checkpoint (x=780) is before the slope, so
the player always re-enters the same trajectory.

## Root Cause Analysis

Two contributing factors:

1. **Aerial trajectory overshoots the bridge**: The player exits the upslope at x≈1162
   with ~8.4 px/frame horizontal + air acceleration. The bridge (cols 76-99, x=1216-1584)
   spans 368px. At 8+ px/frame with air acceleration building to 11+ px/frame, the
   player's y increases faster than the bridge can catch them. The bridge is at y=486
   (row 31 surface) but the player is already at y=496+ and descending — the floor
   sensor only checks one tile extension, so it can't detect the bridge surface
   while the player is in the air gap region (y=496-608).

2. **FULL wall at col 100 blocks passage**: Even if the player could survive the flight,
   the FULL solidity at col 100, row 31 creates a wall that zeroes horizontal velocity.
   The slope tiles at cols 100-101 have `collision=2 (FULL)` but `tile_map type=1 (TOP_ONLY)`.
   This solidity mismatch means the slope acts as a wall instead of a traversable slope.

## Options

### Option A: Fix collision solidity at transition tiles (TOP_ONLY)

Change the FULL (2) tiles at the bridge-to-slope transitions (cols 100-101, 150-152) to
TOP_ONLY (1) in collision.json to match the tile_map type field.

**Pros:**
- Directly fixes the wall collision that kills the player
- Matches the tile_map's intent (type=1 → TOP_ONLY)
- The slope tiles have descending height arrays; TOP_ONLY is correct for slopes the
  player walks/rolls over (collision from above only)
- Addresses the same pattern at all 3 transitions (cols 50, 100, 150)

**Cons:**
- Only fixes the wall. The player still overshoots the bridge during aerial arc.
- The pillar below the slope (rows 33-55) genuinely needs FULL solidity for structural
  support; only the slope surface tiles (rows 31-32) should be TOP_ONLY.

### Option B: Add a spring between bridge end and slope

Place a spring at x≈1190 (col 74, just before bridge 5) to catch the player and redirect
upward. This would interrupt the ballistic arc and put the player back on the bridge.

**Pros:**
- Springs are the stage's primary recovery mechanism
- Matches the existing pattern (springs at x=304, 440, 592 bridge gaps)

**Cons:**
- Doesn't fix the wall collision issue at col 100
- Player may still overshoot due to preserved horizontal momentum from spring bounce
- Adds an entity rather than fixing the structural collision problem

### Option C: Fix collision solidity + add a recovery spring

Combine option A (fix solidity) with a spring at x≈1190, y=608 to ensure the player
reliably transitions to bridge 5 after the slope descent.

**Pros:**
- Fixes both the wall and the trajectory overshoot
- Belt and suspenders: even if the player trajectory changes, the spring provides
  guaranteed recovery

**Cons:**
- Two changes instead of one; more surface area for regressions

### Option D: Extend bridge 5 leftward to cover the gap

Add TOP_ONLY tiles at cols 72-75 (x=1152-1200) to catch the player exiting the slope.

**Pros:**
- Extends the landing zone without changing existing tiles

**Cons:**
- Doesn't fix the FULL wall at col 100
- May not be sufficient if the player overshoots due to high speed

## Decision: Option C

Fix collision solidity at the transition tiles AND add a recovery spring.

**Rationale:**
1. The FULL→TOP_ONLY fix at the slope tiles is clearly correct: the tile_map declares
   these as type=1, and slope surfaces should only collide from above. This is a data
   bug in collision.json that should be fixed regardless.

2. The spring at x≈1190 provides trajectory recovery for the aerial arc off the slope.
   The existing spring pattern (every 400-800px along the stage) has a gap from x=592
   to x=1200 — 608px with no spring. Adding one at the slope exit fills this gap.

3. The same FULL→TOP_ONLY fix should be applied to ALL three transition points
   (col 50, col 100, col 150) for consistency, even though col 50 currently works
   (the player arrives on ground there). The col 50 transition would fail at higher
   speeds or different approach angles.

## Scope

**Files modified:**
- `speednik/stages/skybridge/collision.json` — fix FULL→TOP_ONLY at slope transition tiles
- `speednik/stages/skybridge/entities.json` — add recovery spring

**Files NOT modified:**
- No physics code changes — the physics engine correctly handles TOP_ONLY slopes
- No tile_map changes — the tile_map already has the correct type values
- No test changes in this ticket — the parent ticket T-013-03 handles audit test updates

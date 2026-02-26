# Design — T-012-04-BUG-01: skybridge-bottomless-pit-at-x170

## Problem

Column 11 at row 31 in skybridge has no tile_map or collision data, creating a
31-pixel-wide gap (x=161 to x=191) in the first segment of the walking surface.
This is the first obstacle in the stage and has no recovery below, making it an
immediate death trap for all archetypes.

## Options

### Option A: Fill the gap — add solid tile at (31,11) and (32,11)

Insert tile_map data and collision data for column 11 at rows 31-32, making the
walking surface continuous from col 0 through col 11. This closes the gap entirely.

Tile data would match the surrounding flat bridge: angle=0, heights all 12,
collision=1 (TOP_ONLY, matching cols 12-18 which form the next bridge segment).

**Pros:**
- Eliminates the death trap completely
- Simple data change, no code modifications
- The intended first gap becomes col 19 (px 304-320), which has a floor at row 38

**Cons:**
- Changes level design — removes a gap that may have been intentional
- But: the gap has no recovery mechanism, unlike every other gap with a floor below

### Option B: Add recovery floor below column 11

Insert solid tiles at rows 38+ below column 11, matching the pattern of cols 19 and
27-28 which have floors at row 38. This preserves the gap as a pit but makes it
survivable with the pit death mechanism triggering a respawn.

**Pros:**
- Preserves the gap as a level hazard
- Consistent with other gap depths in the stage

**Cons:**
- The player still falls, dies, and respawns at the start — losing progress and rings
- For all 6 archetypes, this means dying on the first obstacle with no rings to
  cushion the fall — they respawn at (64,490) and walk right back into the same gap
- The walker/cautious archetypes will loop forever: walk → fall → die → respawn → walk
- Does not solve the audit failures (min_x_progress not met)

### Option C: Fix the trailing edge on column 10

Column 10 has heights=[12,0,...,0] which makes most of its surface non-solid. Change
it to heights=all 12 to extend the solid surface to x=175, reducing the gap to just
col 11 (16px). The player sensors (±9px) could bridge a 16px gap if one foot is on
the solid edge.

**Pros:**
- Minimal data change
- Reduces gap from 31px to 16px

**Cons:**
- 16px gap is still larger than the sensor spread (18px), so players likely still fall
- The angle=192 on col 10 is a design element (slope down to gap edge) — removing it
  changes the visual/physics feel
- Half-measure that may not fix the bug

## Decision: Option A — Fill the gap

The gap at col 11 is the only gap in the entire row-31 surface that has no floor
below it. Every other gap has a lower path (floor at row 38) or is part of a larger
section with alternative routes. The col 11 gap appears to be a data error:

1. It has trailing/leading edge tiles (cols 10 and 12) identical to intentional gaps,
   but unlike those gaps, there is absolutely nothing below — col 11 is empty through
   all 56 rows
2. There are no springs, platforms, or alternative paths near x=170
3. The first intentional gap with recovery (col 19, floor at row 38) is designed as
   the real first hazard
4. Having an instant-death trap 106 pixels into a stage with no way to avoid it is
   not viable game design

The fix: Add tile data to column 11 at rows 31-32, and set collision to 1 (TOP_ONLY)
to match the adjacent bridge segment (cols 12-18). This makes the first bridge
segment run continuously from col 0 through col 18, with col 19 as the first real gap.

Additionally, col 10's height_array should be fixed. The trailing-edge pattern
(heights=[12,0,...,0]) on col 10 makes no sense when col 11 is being filled — it
would create a depression within a bridge. Change col 10 to have flat heights (all 12)
and angle=0 to match the rest of the bridge.

### What about the xfail tests?

After fixing the collision gap, the xfail markers referencing T-012-04-BUG-01 should
be removed from `tests/test_audit_skybridge.py`. The tests may still fail for other
reasons (skybridge is the hardest stage), but they should no longer xfail for *this*
specific bug.

However: the tests have strict expectations (min_x_progress=2500 for walker, etc.)
that may not be met even after this fix. There may be other gaps or enemies that stop
progress. The correct approach is to remove the xfail markers and let the tests run —
if they still fail, those are separate bugs for separate tickets.

We should remove `strict=True` xfail markers but leave the tests as regular tests.
If they pass, great. If they fail, that surfaces new bugs.

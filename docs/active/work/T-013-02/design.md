# T-013-02 Design — skybridge-collision-gap-fix

## Decision

**Patch collision.json directly** to set col 11, rows 31–32 to `1` (TOP_ONLY).

## Options Considered

### Option A: Fix the SVG and regenerate via pipeline

Extend the SOLID polygon's right edge from x=160 to x=192 (or add a new
polygon covering x=176–192) in `skybridge_gauntlet.svg`, then rerun
`svg2stage.py` to regenerate both collision.json and tile_map.json.

Pros:
- Keeps SVG as the single source of truth
- Both collision.json and tile_map.json stay in sync automatically

Cons:
- Regeneration may introduce unintended changes elsewhere in the collision
  data if the pipeline has evolved since the last run
- tile_map.json already has the correct data for col 11 — regeneration might
  overwrite it with different values depending on the polygon type used
- Requires verifying the entire stage after regeneration, not just col 11
- The SVG/pipeline mismatch (tile_map has data, collision doesn't) suggests
  an earlier pipeline run already handled this — only collision.json drifted

Rejected: High blast radius, risk of regression elsewhere.

### Option B: Patch collision.json directly (chosen)

Set `collision[31][11] = 1` and `collision[32][11] = 1`. This brings
collision.json into alignment with tile_map.json, which already expects col 11
to be a TOP_ONLY surface at these rows.

Pros:
- Minimal, surgical change — exactly two integer values
- Matches the tile_map.json data that already exists for col 11
- No risk of pipeline regression
- Can be verified by running the walker archetype test

Cons:
- SVG source remains out of sync (still has the 32px gap)
- Creates a manual override that could be lost if pipeline reruns from SVG

Accepted: Lowest risk, directly addresses the bug, matches existing tile_map
data. SVG fix can be tracked as a separate follow-up if desired.

### Option C: Add a recovery spring below the gap

Place a spring at approximately x=180, y=608 (below the gap) to catch players
who fall through col 11, similar to the springs at x=304, 440, 592.

Pros:
- Doesn't modify collision data
- Handles the gap as a design feature rather than a bug

Cons:
- The gap is clearly accidental (tile_map has data, rings span across it)
- Adding a spring doesn't fix the root cause
- Creates awkward gameplay at the start of the level

Rejected: The gap is not intentional. A spring patches symptoms.

## Value Choice: TOP_ONLY (1) vs FULL (2)

Col 10 (ground block) uses FULL (2). Col 12 (first platform) uses TOP_ONLY (1).
tile_map.json has col 11 as type=2 (SURFACE_TOP_ONLY). Using TOP_ONLY (1)
for collision matches:
- The tile_map type already stored for col 11
- The adjacent col 12 surface type
- The transition from solid ground to platform

FULL (2) would also work functionally — the player walks on top either way.
But TOP_ONLY is correct because the tile_map already declared this as a
TOP_ONLY surface, and consistency matters for sensors that check solidity type.

## Formatting Decision

The working tree has minified collision.json to a single line, creating a
massive diff (18k line deletion + 1 line addition). For this ticket, the fix
should preserve the original multi-line formatting to keep diffs reviewable.
The semantic change is two values; the diff should show exactly two values.

## Test Strategy

The fix is verified by running skybridge audit tests:
- `test_skybridge_walker`: walker should traverse past x=300 without falling
- All 6 archetype tests: no `position_y_below_world` errors in first 500 frames
- Direct data assertion: collision[31][11] == 1, collision[32][11] == 1

## SVG Follow-Up

The SVG source should be fixed separately (extend solid polygon to x=192 or
add a bridging polygon). This is tracked but out of scope for this ticket.
The collision.json patch is the immediate fix.

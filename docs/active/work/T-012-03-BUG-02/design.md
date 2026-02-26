# Design: T-012-03-BUG-02 — Pipeworks Solid Tile Clipping

## Problem Summary

The player at high speed (>10 px/frame) lands on pipe structure roofs, runs across
them, falls off the edge, and enters the solid interior of the next pipe. Once inside,
collision resolution oscillates instead of ejecting the player cleanly. This produces
1438 `inside_solid_tile` invariant errors.

## Approach 1: Tile Data Fix — Make Pipe Interiors Non-Solid or TOP_ONLY

Change the solid fill tiles inside pipe structures from `FULL` to `TOP_ONLY` or reduce
their solidity. The invariant checker only fires on `FULL` tiles, so TOP_ONLY tiles
would suppress errors. The pipe cap/ceiling tiles would remain FULL to provide the
actual collision surface.

**Pros:** Simple, no code changes, just tile data. Directly prevents the invariant.
**Cons:** Doesn't fix the physics root cause. Player would still clip through, just
without detection. TOP_ONLY tiles would let the player pass through from below, which
breaks pipe floor collision. Masking, not fixing.

**Rejected:** This is a masking approach, not a fix.

## Approach 2: Sweep-Based Collision (CCD)

Replace the single-step movement in `apply_movement()` with a continuous collision
detection sweep that advances the player in small increments, checking collision at
each step.

**Pros:** Completely prevents tunneling at any speed. Physically correct.
**Cons:** Major refactor of the physics pipeline. Performance cost from multiple
collision checks per frame. Violates the Sonic 2 sensor-based collision model that
the codebase is built around. Over-engineered for this specific bug.

**Rejected:** Too invasive, violates the game's physics architecture.

## Approach 3: Emergency Solid Ejection

Add a post-collision check: if the player's center is still inside a FULL solid tile
after `resolve_collision()`, eject them to the nearest free position. This is a safety
net that catches cases where the normal sensor resolution fails.

**Pros:** Targeted fix. Handles the exact failure mode. Doesn't change normal collision
behavior — only activates when the player is already in an invalid state.
**Cons:** Could cause visual pops if ejection distance is large. Need to choose
ejection direction carefully. Adds complexity to the collision path.

**Assessment:** Viable as a secondary safety net, but doesn't prevent entry.

## Approach 4: Velocity-Scaled Wall Detection

Extend the wall sensor range or add pre-movement wall checks when the player's speed
exceeds a threshold. Before `apply_movement()`, check if the movement vector would
cross a solid boundary, and clamp velocity to prevent penetration.

**Pros:** Prevents entry rather than recovering after. Targeted to high-speed cases.
**Cons:** Would need to detect tile boundaries along the movement vector. Complex
geometry for diagonal movement. Could interfere with intended high-speed movement
through gaps and pipes.

**Assessment:** Partially viable but complex and risk of side effects.

## Approach 5: Solid Ejection in resolve_collision()

After the three-pass resolution (floor/wall/ceiling), check if the player center is
inside a FULL solid tile. If so, use floor/ceiling/wall sensors to find the nearest
non-solid surface and push the player there. This is Approach 3 integrated into the
existing collision resolution function.

**Pros:** Contained within `resolve_collision()`. Uses existing sensor infrastructure.
Runs every frame, so even if the player enters solid in one frame, they're ejected
by the next. Doesn't change normal-case behavior (the check is only active when
already inside solid).

**Cons:** Similar to Approach 3 — visual pops possible. Must avoid infinite loops if
sensors can't find a free surface.

**Assessment:** This is the most pragmatic approach.

## Chosen Approach: Approach 5 — Solid Ejection in resolve_collision()

### Design

After the existing floor → wall → ceiling resolution passes in `resolve_collision()`,
add a solid-tile ejection pass:

1. Check if player center `(x, y)` is inside a FULL solid tile (same logic as
   `_check_inside_solid` in invariants.py).

2. If inside solid, try ejection in priority order:
   a. **Upward:** Cast sensor up from player center. If free surface found within
      MAX_SENSOR_RANGE, move player to that surface (y = surface_y - height_radius).
   b. **Downward:** Cast sensor down. If free surface found, snap to it.
   c. **Left/Right:** Cast wall sensors. Push to nearest free side.

3. After ejection, re-check if still inside solid. If so (pathological case), fall
   back to setting player airborne with zero velocity at the last known good position
   (or just above the current position with a forced upward push).

4. Cap the ejection to one attempt per frame to avoid infinite loops.

### Key Invariant

The ejection only fires when the player center is *already* inside a FULL solid tile.
This means it never alters normal collision behavior — it's purely a recovery mechanism
for states the primary collision resolution couldn't handle.

### Edge Cases

- **Pipe tunnels:** The pipe interior between cap (row 25) and ceiling (row 26) for
  Pipe A is only 1 tile tall (16px). The player standing height is 40px. There is
  no valid position inside the pipe. Ejection should push upward above the cap.

- **Solid from all directions:** If all sensors find solid within range, the player
  is deeply embedded. In this case, push upward by a fixed amount and set airborne.
  This prevents getting permanently stuck.

- **Performance:** One extra `tile_lookup` call per frame in the common case (check
  if inside solid = false, early return). Only the rare inside-solid case runs the
  full ejection logic.

### Why Not Fix the Root Cause?

The root cause is that `apply_movement()` teleports the player in a single step,
allowing it to skip over thin walls. A full fix would require continuous collision
detection (Approach 2), which is a major architectural change. The ejection approach
is the standard solution for Sonic-style engines: the sensor system handles normal
cases, and an ejection pass handles edge cases where the sensor missed.

The original Sonic 2 engine had similar issues at extreme speeds (hence the top speed
cap). The ejection pass is a pragmatic compromise that keeps the sensor architecture
intact while preventing the invariant violation.

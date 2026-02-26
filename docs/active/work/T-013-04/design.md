# Design: T-013-04 — Solid Tile Push-Out Hardening

## Problem Summary

After `resolve_collision()` runs its three sensor passes (floor/wall/ceiling), the
player center can still be inside a FULL solid tile. No recovery exists. The player
oscillates between conflicting sensor corrections indefinitely.

## Approach 1: Continuous Collision Detection (CCD)

Replace single-step movement with sweep-based detection that advances in small
increments, checking collision at each step.

**Pros:** Completely prevents tunneling. Physically correct.
**Cons:** Major refactor of the physics pipeline. Violates the Sonic 2 sensor model
that the codebase is built around. Performance cost from multiple collision checks
per frame.

**Rejected:** Too invasive. The sensor architecture is fundamental to the game design.

## Approach 2: Velocity-Scaled Wall Detection

Before `apply_movement()`, extend wall sensor range proportional to velocity. Check
if movement vector would cross a solid boundary; clamp velocity to prevent penetration.

**Pros:** Prevents entry rather than recovering after.
**Cons:** Complex geometry for diagonal movement. Could interfere with intended
high-speed movement through gaps. Doesn't handle cases where the player is already
inside solid (e.g., after respawn or pipe exit).

**Rejected:** Only prevents one entry vector. Doesn't handle existing inside-solid states.

## Approach 3: Post-Resolution Solid Ejection

After the three-pass resolution in `resolve_collision()`, check if the player center
is inside a FULL solid tile. If so, search nearby for the nearest non-solid position
and reposition the player there.

**Pros:** Targeted safety net. Doesn't change normal collision behavior. Handles all
entry vectors (high speed, respawn, pipe exit, etc.). Uses existing tile_lookup
infrastructure. Cheap in common case (one tile lookup = not inside solid = early return).

**Cons:** Can cause visual pops when ejection distance is large. Must choose ejection
direction carefully to avoid placing player in another solid region. Need bounded search
to avoid infinite loops.

**Assessment:** Most pragmatic approach. Aligns with BUG-02 design (which was reviewed
and approved but never committed).

## Chosen Approach: Approach 3 — Post-Resolution Solid Ejection

### Design Details

#### 1. Detection: `_is_inside_solid(state, tile_lookup) -> bool`

Same logic as invariants.py `_check_inside_solid()`:
- Get tile at player center `(int(x) // 16, int(y) // 16)`
- If tile is FULL, not SURFACE_LOOP, and `y >= solid_top` → inside solid

#### 2. Ejection: `_eject_from_solid(state, tile_lookup)`

Priority-ordered search for nearest free position:

1. **Upward scan**: from player's tile row, scan upward row by row (up to 3 tiles =
   48 px). For each row, check if the tile at `(tx, ty-N)` is non-solid or has
   `height_array[col] == 0`. If found, place player at `(ty-N+1)*16 - 1` (just above
   the solid surface). Set airborne, zero velocity.

2. **Horizontal scan** (left then right): from player's tile column, scan outward up
   to 3 tiles. Check if `(tx +/- N, ty)` is non-solid. If found, push player to the
   boundary.

3. **Fallback**: if no free position found within 3 tiles in any direction, treat as
   crush — push player up by `TILE_SIZE`, set airborne, zero velocity. This prevents
   permanent trapping.

#### 3. Integration Point

At the end of `resolve_collision()`, after the ceiling pass:
```python
if _is_inside_solid(state, tile_lookup):
    _eject_from_solid(state, tile_lookup)
```

#### 4. Oscillation Guard

To prevent the player from bouncing between solid corrections across frames, track
whether ejection fired. If the player is ejected, force `on_ground = False` and zero
all velocity. This breaks the oscillation cycle by converting the trapped state into
a clean airborne state.

### Design Decisions

**3-tile search radius (not 8):** The ticket specifies 3 tiles. The BUG-02 design
used 8 tiles but this is excessive for a safety net. 3 tiles (48 px) covers the
player height (40 px standing) and handles the pipe structures in Pipeworks. If no
free space within 3 tiles, the geometry is too dense for safe placement — treat as
crush.

**Upward priority over horizontal:** Upward ejection is safest in a platformer. It
places the player above terrain, where gravity naturally brings them back to a valid
surface. Horizontal ejection could push into another solid region. Matches the BUG-02
reviewed design.

**Force airborne on ejection:** Critical for breaking oscillation. If the player is
left on_ground after ejection, the next frame's floor sensors may snap them back into
the solid region. Setting airborne lets gravity resolve the landing naturally.

**No crush/death:** The ticket says "treat as crush/death" if no free position found
within 3 tiles. However, implementing death here adds complexity (damage system
coupling) and the fallback push-up-by-TILE_SIZE is safer. If needed, death can be
added later.

### Edge Cases

- **SURFACE_LOOP tiles:** Excluded from inside-solid check (same as invariant checker).
  Loop interiors should not trigger ejection.
- **TOP_ONLY tiles:** Not checked (solidity != FULL). Platform tiles don't cause
  trapping.
- **Pipe tunnels:** Narrow pipe interiors where ceiling and floor are both solid. The
  upward scan finds the first non-solid tile above the ceiling. Player is placed above
  the pipe structure.
- **Level boundaries:** tile_lookup returns None for out-of-bounds positions, so the
  scan naturally treats boundaries as free space.

### Expected Impact

- Zero `inside_solid_tile` invariant errors on Pipeworks for all archetypes
- No regressions on Hillside or Skybridge (the check only fires in edge cases)
- Possible trajectory changes for runs that previously exploited solid clipping

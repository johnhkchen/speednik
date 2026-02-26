# Structure — T-013-03-BUG-03: Speed Demon Pit Death on Skybridge

## Changes Overview

Two files modified, zero files created or deleted.

### 1. `speednik/stages/skybridge/collision.json`

**Change**: Fix solidity values at all three bridge-to-slope transition pillars.

Affected tile positions (where collision=FULL but tile_map type=TOP_ONLY):

**Transition 1 — col 50-55 (x=800-880), rows 31-39:**
- All tiles in this region that have collision=2 and tile_map type=1
- Change from FULL (2) → TOP_ONLY (1)
- Scope: cols 50-55, rows 31-39

**Transition 2 — col 100-107 (x=1600-1712), rows 31-39:**
- Same pattern: FULL→TOP_ONLY for all tiles with tile_map type=1
- Scope: cols 100-107, rows 31-39

**Transition 3 — col 150-157 (x=2400-2512), rows 31-39:**
- Same pattern
- Scope: cols 150-157, rows 31-39

Total cells changed: ~150 cells (2→1)

The fix is mechanical: wherever tile_map declares type=1 (TOP_ONLY) and collision.json
has 2 (FULL), change collision.json to 1 to match. This restores the intended behavior
where slope surfaces are walkable from above but don't block horizontal movement.

### 2. `speednik/stages/skybridge/entities.json`

**Change**: Add one recovery spring to break the aerial trajectory after the first slope.

New entity:
```json
{
  "type": "spring_up",
  "x": 1190,
  "y": 608
}
```

Position rationale:
- x=1190 is at col 74, just before bridge segment 5 starts at col 76 (x=1216)
- y=608 matches all other springs in the stage (sitting on row 38 ground level)
- The existing spring gap from x=592 to x=1200 is 608px — the largest in the stage
- This spring at x=1190 splits that gap and catches airborne players exiting the slope
- Placed at the base of the slope descent, where the player's trajectory passes through

## Module Boundaries

No module or interface changes. Both modifications are pure data changes to JSON files.
The physics engine, terrain system, and QA framework are unchanged.

## Ordering

1. Fix collision.json first (the primary fix)
2. Add spring to entities.json second (the recovery mechanism)
3. Verify with audit run

The two changes are independent but should be committed together as they address the
same bug from different angles.

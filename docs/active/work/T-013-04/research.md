# Research: T-013-04 — Solid Tile Push-Out Hardening

## Problem

Players clip into solid tiles in Pipeworks and enter a bounce oscillation they cannot
escape. Walker and Wall Hugger get trapped at x~3040 (150+ invariant errors). Chaos
clips at x~100 (8 errors). The collision system fails in regions with dense FULL-solidity
tiles (angle=64 walls adjacent to angle=128 ceilings).

## Collision Pipeline

`player_update()` in `player.py:109` runs this sequence per frame:

1. `_pre_physics()` — state transitions
2. `apply_input()` — acceleration
3. `apply_slope_factor()` — gravity on slopes
4. `apply_gravity()` — airborne: `y_vel += 0.21875`
5. `apply_movement()` — **single-step teleport**: `x += x_vel; y += y_vel`
6. `resolve_collision()` — sensor-based snap/push
7. `update_slip_timer()`
8. `_post_physics()` — landing/falling sync

Critical gap: step 5 teleports in one step. At >10 px/frame the player crosses multiple
tiles before step 6 runs.

## resolve_collision() — terrain.py:691-784

Three passes in order:

1. **Floor sensors (A/B)** via `find_floor()` — snap within `_GROUND_SNAP_DISTANCE=14`.
   Two-pass quadrant correction if angle changes.
2. **Wall sensors (E/F)** via `find_wall_push()` — push out if `distance < 0`. Angle
   gate ignores tiles with angle <= 48 or >= 208. Disabled when moving away from wall.
3. **Ceiling sensors (C/D)** via `find_ceiling()` — push down if `distance < 0`, only
   when airborne or non-zero quadrant.

No post-resolution check for player-still-inside-solid.

## Sensor Architecture

Each sensor cast checks at most 2 tiles (current + one adjacent). Constants:
- `TILE_SIZE = 16`
- `MAX_SENSOR_RANGE = 32`
- `WALL_SENSOR_EXTENT = 10` px from center
- `STANDING_HEIGHT_RADIUS = 20`, `ROLLING_HEIGHT_RADIUS = 14`
- `STANDING_WIDTH_RADIUS = 9`, `ROLLING_WIDTH_RADIUS = 7`

## Tile Solidity System

```python
NOT_SOLID = 0    # No collision
TOP_ONLY = 1     # Floor sensors only (platforms)
FULL = 2         # All directions
LRB_ONLY = 3     # Left/Right/Bottom only
SURFACE_LOOP = 5 # Loop tiles — exempt from wall angle gate
```

Tiles with angle=64 are 90-degree walls. Tiles with angle=128 are ceilings. In
Pipeworks, dense regions of these are adjacent, creating zones where all sensor
directions find solid surfaces.

## width_array() Limitation — terrain.py:67-83

`width_array()` counts consecutive solid columns from the left edge. If solid pixels
are not contiguous from column 0, width is reported as zero. This means wall sensors
miss non-left-anchored solid patterns. Affects thin wall posts like column 6 in
Pipeworks.

## Invariant Checker — invariants.py:109-132

`_check_inside_solid()` checks the player center `(x, y)`:
- Finds tile at `(int(x)//16, int(y)//16)`
- If tile is FULL and not SURFACE_LOOP
- Computes `solid_top = (ty+1)*16 - height`
- Violation when `y >= solid_top`

Center-point only check; FULL tiles only; SURFACE_LOOP exempt.

## Root Causes of Clipping

1. **No sweep detection**: `apply_movement()` teleports; at 11+ px/frame the player
   skips wall boundaries entirely.
2. **Wall sensor range too narrow**: sensors check at x +/- 10 from center; deep
   inside solid, no wall boundary is within range.
3. **Conflicting corrections**: once inside, floor/ceiling/wall sensors fire
   simultaneously with opposing corrections, causing oscillation.
4. **No safety-net ejection**: after `resolve_collision()`, there is no check for
   whether the player center is still inside a solid tile.

## Prior Work: T-012-03-BUG-02

A solid ejection approach was fully designed and reviewed in BUG-02 docs. Functions
`_is_inside_solid()` and `_eject_from_solid()` were described but **never committed
to the codebase**. The design scans upward up to 8 tiles to find free space.

BUG-03 extended this with horizontal ejection for vertically-continuous columns.
Also not committed.

## Pipeworks Problem Zones

- **x~3040** (tiles 190-195, rows 40-41): angle=64 walls + angle=128 ceilings, all
  FULL solidity. Walker and Wall Hugger land here and oscillate.
- **x~100** (tiles ~6): thin 1px wall post. Chaos clips here.

## Regression Suite State

`test_regression.py` explicitly excludes `inside_solid_tile` from its invariant
checks (line 234). The regression suite is blind to this class of bug.

## Existing Tests

- `test_audit_pipeworks.py`: 6 archetypes, all xfail with documented reasons
- `test_audit_hillside.py`: mix of pass and xfail
- `test_terrain.py`: sensor unit tests, resolve_collision tests
- `test_invariants.py`: invariant checker unit tests

## Key Files

| File | Relevance |
|------|-----------|
| `speednik/terrain.py` | `resolve_collision()`, all sensor functions |
| `speednik/physics.py` | `apply_movement()` — the single-step teleport |
| `speednik/player.py` | `player_update()` — pipeline orchestrator |
| `speednik/invariants.py` | `_check_inside_solid()` — detection logic |
| `speednik/simulation.py` | `sim_step()` — frame driver |
| `speednik/constants.py` | Sensor radii, angle thresholds |
| `tests/test_audit_pipeworks.py` | Acceptance criteria validation |
| `tests/test_regression.py` | Regression safety net |

# Research — T-012-03-BUG-03: pipeworks-chaos-early-clipping

## Bug Summary

Chaos archetype (seed=42) clips into solid tiles in Pipeworks, generating
`inside_solid_tile` invariant errors. After BUG-02's ejection fix, the error
count is reduced from the original 8 to **2 errors** (frames 369 and 413),
both at player center (100.0, 484.0) inside tile (6,30).

## Collision Pipeline

Frame update order in `player_update()` → `resolve_collision()`:

1. `apply_movement()` — single-step teleport: `x += x_vel; y += y_vel`
2. `resolve_collision()`:
   - Floor sensors (A/B) — snap/land
   - Wall sensors (E/F) — push away, angle-gated (≤48 or ≥208 ignored)
   - Ceiling sensors (C/D) — airborne only
   - **Solid ejection** (added by BUG-02) — `_is_inside_solid()` check →
     `_eject_from_solid()` scan upward up to 8 tiles

## Clipping Location: Tile Column 6

### Tile geometry

Column 6 is a thin vertical wall post running all 40 tile rows (0–39). Every
tile has the same structure:

```
tile(6, 0..39): solidity=FULL(2), angle=192, type=1
  height_array = [0,0,0,0,16,0,0,0,0,0,0,0,0,0,0,0]
```

Only pixel column 4 within the tile (absolute x = 96 + 4 = 100) is solid to
full height 16. All other columns are empty. This represents the right edge
of the solid block at column 5 (which is fully solid: h=[16]*16 for all rows).

Exception: tile (6,32) has additional solid columns:
```
h=[0,0,0,0,16,8,8,8,8,8,8,8,8,8,8,8]
```

### Why the player enters this tile

The Chaos archetype's random movement drives the player leftward from start
position (200, 510) toward x=100. At x=100.0, the player center sits exactly
on pixel column 4 of tile column 6. Since this column has h[4]=16 in every
row, `_is_inside_solid()` detects the player is inside the solid region.

### Why ejection fails

`_eject_from_solid()` scans upward from the player's tile, checking each tile
above for free space. The scan checks column `col = int(100) % 16 = 4`:

- For every tile in column 6 rows 0–39, `h[4] = 16` (full height)
- The scan finds 8 consecutive fully-solid tiles and exhausts
  `_EJECT_SCAN_TILES = 8`
- Falls back to `state.y -= TILE_SIZE` (push up by 16px)
- New position y=484 is still inside tile (6,30) because `solid_top = 480`,
  and 484 ≥ 480

The fallback push is insufficient because the column is solid for its entire
height — there's no free space to eject into vertically.

### Why wall sensors miss this tile

Wall sensors (E/F) use `width_array()` which counts contiguous solid columns
from the left edge. For tile (6, N):
```
h = [0,0,0,0,16,0,...,0]
width_array computation: at each row, scan from col 0 rightward.
  h[0]=0 → stop immediately → width=0 for all rows
```

The width array is all zeros because the solid column (4) is not at the left
edge. Wall sensors see nothing.

### Why floor sensors don't prevent entry

The player approaches from the right (column 7 area, which is empty) moving
left. Floor sensors A/B are positioned at `x ± width_radius` (9px from center).
With player center at x=100, sensor A at x=91 (col 11 of tile 5, fully solid)
and sensor B at x=109 (col 13 of tile 6, h[13]=0 → empty). The floor sensor
finds solid surface from sensor A, snaps the player to the floor — but this
doesn't prevent horizontal entry into the thin column.

## Clipping Location: Tile (18,26)

### Tile geometry

```
tile(18,26): solidity=FULL, angle=32, type=3
  h=[0,2,3,3,5,5,7,8,9,10,10,12,13,14,15,15]
```

This is a 45° slope tile (pipe terrain). At col 14 (x=302): h=15, solid_top=417.
Player at y=424 → 7px inside solid. At col 9 (x=297): h=10, solid_top=422.
Player at y=429 → 7px inside.

### Why ejection works here

Tile (18,25) is None (empty), so `_eject_from_solid` finds free space on the
first upward scan step. The violations are transient (1 frame each).

### Current state

The original ticket reports these clips at frames 1007 and 1747. Current audit
shows **zero errors** at tile (18,26) — the BUG-02 ejection fix already handles
these. Only the column 6 clips remain.

## Key Files

| File | Role |
|------|------|
| `speednik/terrain.py` | `_is_inside_solid`, `_eject_from_solid`, `resolve_collision` |
| `speednik/terrain.py:761` | `_eject_from_solid` — 8-tile upward scan + fallback |
| `speednik/stages/pipeworks/tile_map.json` | Tile height arrays and angles |
| `speednik/stages/pipeworks/collision.json` | Tile solidity values |
| `speednik/invariants.py:109` | `_check_inside_solid` — detection logic |
| `tests/test_audit_pipeworks.py:165` | xfail test for chaos archetype |

## Constraints

1. The solid ejection mechanism was introduced by BUG-02 and already handles
   most clipping cases. Column 6 is the only remaining failure because the
   ejection scan cannot find free space when the entire column is solid.
2. The tile data represents a genuine 1-pixel-wide wall post extending the
   right edge of column 5. The geometry is architecturally intentional (pipe
   wall boundary).
3. The player width radius is 9px (standing) or 7px (rolling/airborne). The
   player can only reach x=100 with its center on the exact solid column.
4. The `_eject_from_solid` fallback (`y -= TILE_SIZE`) is the only escape path
   when the upward scan fails, and it's insufficient for columns solid from
   top to bottom.

## Observations

- The root issue is that `_eject_from_solid` only scans upward. For a
  vertically-continuous solid column, horizontal ejection would immediately
  escape (columns 0–3 and 5–15 of the tile are empty).
- The BUG-02 design document noted this: "Could cause visual pops if ejection
  distance is large" and the structure document specified upward-only scan as
  the implementation, with a fixed upward push as fallback.
- Horizontal ejection for vertically-solid but horizontally-thin geometry is
  the natural escape direction.

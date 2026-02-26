# Structure: T-013-04 — Solid Tile Push-Out Hardening

## Files Modified

### 1. `speednik/terrain.py`

**New functions** (added before `resolve_collision()`):

#### `_is_inside_solid(state: PhysicsState, tile_lookup: TileLookup) -> bool`
- Pure detection function
- Gets tile at `(int(state.x) // TILE_SIZE, int(state.y) // TILE_SIZE)`
- Returns True if tile is FULL, not SURFACE_LOOP, and `state.y >= solid_top`
- Mirrors invariants.py `_check_inside_solid()` logic exactly

#### `_eject_from_solid(state: PhysicsState, tile_lookup: TileLookup) -> None`
- Mutates state to move player to nearest free position
- Search priority: upward (1-3 tiles), left (1-3 tiles), right (1-3 tiles)
- On success: set `on_ground = False`, `angle = 0`, zero `x_vel`, `y_vel`, `ground_speed`
- On failure (no free space in 3 tiles any direction): push up by TILE_SIZE, same state reset

**Module constant:**

#### `_EJECT_SCAN_TILES = 3`
- Max tiles to scan in each direction for ejection

**Modified function:**

#### `resolve_collision()` — lines 691-784
- Add ejection pass after the ceiling sensor pass (after line 771)
- Call: `if _is_inside_solid(state, tile_lookup): _eject_from_solid(state, tile_lookup)`

### 2. No other files modified

The fix is entirely within terrain.py. No changes to:
- `invariants.py` — the checker already detects the issue; the fix prevents it
- `player.py` — the ejection happens within `resolve_collision()`, called from `player_update()`
- `simulation.py` — no changes to sim_step
- `constants.py` — `_EJECT_SCAN_TILES` is local to terrain.py, not a cross-module constant

## Module Boundaries

```
player.py::player_update()
  └─ terrain.py::resolve_collision()
       ├─ find_floor()          # existing pass 1
       ├─ find_wall_push()      # existing pass 2
       ├─ find_ceiling()        # existing pass 3
       └─ _is_inside_solid()    # NEW pass 4
            └─ _eject_from_solid()  # NEW recovery
```

The new functions are private to terrain.py (prefixed with `_`). They are not exported
or used by other modules. The only interface change is the behavior of
`resolve_collision()`, which now guarantees the player is not inside a solid tile
when it returns (best-effort — the fallback push may still leave a transient overlap
that the next frame resolves).

## Component Design

### `_is_inside_solid`

```
Input:  PhysicsState, TileLookup
Output: bool

1. tx = int(state.x) // TILE_SIZE
2. ty = int(state.y) // TILE_SIZE
3. col = int(state.x) % TILE_SIZE
4. tile = tile_lookup(tx, ty)
5. if tile is None or tile.solidity != FULL or tile.tile_type == SURFACE_LOOP:
     return False
6. height = tile.height_array[col]
7. solid_top = (ty + 1) * TILE_SIZE - height
8. return state.y >= solid_top
```

### `_eject_from_solid`

```
Input:  PhysicsState, TileLookup (mutates state)

1. tx = int(state.x) // TILE_SIZE
2. ty = int(state.y) // TILE_SIZE
3. col = int(state.x) % TILE_SIZE

4. # Upward scan
   for dy in range(1, _EJECT_SCAN_TILES + 1):
     check_ty = ty - dy
     tile = tile_lookup(tx, check_ty)
     if tile is None or tile.solidity != FULL:
       state.y = (check_ty + 1) * TILE_SIZE - 1
       _reset_to_airborne(state)
       return
     if tile.height_array[col] < TILE_SIZE:
       solid_top = (check_ty + 1) * TILE_SIZE - tile.height_array[col]
       if state.y >= solid_top:  # still inside this tile too
         continue
       state.y = solid_top - 1
       _reset_to_airborne(state)
       return

5. # Horizontal scan (left then right)
   for dx in range(1, _EJECT_SCAN_TILES + 1):
     # Left
     tile_l = tile_lookup(tx - dx, ty)
     if tile_l is None or tile_l.solidity != FULL:
       state.x = (tx - dx + 1) * TILE_SIZE - 1  # just inside free tile
       _reset_to_airborne(state)
       return
     # Right
     tile_r = tile_lookup(tx + dx, ty)
     if tile_r is None or tile_r.solidity != FULL:
       state.x = (tx + dx) * TILE_SIZE  # just inside free tile
       _reset_to_airborne(state)
       return

6. # Fallback: force push up
   state.y -= TILE_SIZE
   _reset_to_airborne(state)
```

### `_reset_to_airborne` (inline helper)

```
state.on_ground = False
state.angle = 0
state.x_vel = 0.0
state.y_vel = 0.0
state.ground_speed = 0.0
```

## Change Ordering

Single atomic change: all three functions added to terrain.py and the ejection call
inserted into `resolve_collision()` in one commit. No ordering dependencies.

## Test Strategy (Structure-Level)

New test functions in `tests/test_terrain.py`:
- `test_eject_from_solid_upward` — player inside full tile, free space above
- `test_eject_from_solid_horizontal` — column of solid tiles, free space to the side
- `test_eject_from_solid_fallback` — surrounded by solid, verify fallback push
- `test_is_inside_solid_loop_exempt` — SURFACE_LOOP tiles don't trigger ejection
- `test_resolve_collision_ejects` — integration: full resolve_collision ejects player

Integration validation via existing audit/regression tests on Pipeworks.

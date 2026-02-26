# Structure: T-012-03-BUG-02 — Pipeworks Solid Tile Clipping

## Files Modified

### 1. `speednik/terrain.py`

**Changes:**
- Add `_is_inside_solid()` helper function (private) that checks whether a pixel
  position `(x, y)` is inside the solid region of a FULL-solidity tile. Returns
  `(is_inside: bool, tile: Tile | None, tile_x: int, tile_y: int)`.

- Add `_eject_from_solid()` helper function (private) that attempts to eject the
  player from a solid tile. Uses upward sensor cast first (most common escape
  direction for falling-into-solid scenarios), then downward, then lateral. Returns
  True if ejection succeeded.

- Modify `resolve_collision()`: after the existing three passes (floor, wall,
  ceiling), call `_is_inside_solid()`. If True, call `_eject_from_solid()`. If
  ejection fails, force the player airborne with zero velocity and push upward by
  `TILE_SIZE` pixels.

**New functions:**
```
_is_inside_solid(state: PhysicsState, tile_lookup: TileLookup) -> bool
_eject_from_solid(state: PhysicsState, tile_lookup: TileLookup) -> bool
```

**Interface changes:** None. `resolve_collision()` signature unchanged.

### 2. `tests/test_terrain.py`

**Changes:**
- Add test `test_eject_from_solid_tile()`: place player center inside a FULL solid
  tile, call `resolve_collision()`, verify player center is no longer inside solid.

- Add test `test_eject_from_solid_upward()`: place player inside solid with free
  space above, verify ejection moves player upward.

- Add test `test_no_eject_when_not_inside_solid()`: verify normal collision
  resolution is unaffected (player at surface, not inside, stays at surface).

### 3. `tests/test_audit_pipeworks.py`

**Changes:**
- Remove `xfail` decorators from `test_pipeworks_walker()` and
  `test_pipeworks_wall_hugger()` if the fix resolves all invariant errors for
  those archetypes. If they fail for other reasons (e.g., not reaching min_x),
  update the xfail reason.

## Files NOT Modified

- `speednik/physics.py` — No changes to movement mechanics.
- `speednik/simulation.py` — No changes to frame update order.
- `speednik/invariants.py` — The checker is correct; the fix is in collision.
- `speednik/player.py` — No changes to state machine or update order.
- `speednik/level.py` — No changes to tile loading.
- `speednik/stages/pipeworks/tile_map.json` — Tile data is not modified.
- `speednik/stages/pipeworks/collision.json` — Solidity data is not modified.

## Module Boundaries

The ejection logic is entirely within `speednik/terrain.py`, which already owns
`resolve_collision()`. No new module dependencies are introduced. The helper
functions use the same `TileLookup` and `PhysicsState` types already in scope.

## Ordering

1. Implement `_is_inside_solid()` and `_eject_from_solid()` in terrain.py
2. Add the ejection pass to `resolve_collision()`
3. Add unit tests in test_terrain.py
4. Run the full test suite to verify no regressions
5. Run the Pipeworks audit specifically to verify the fix
6. Update test_audit_pipeworks.py xfail markers as needed

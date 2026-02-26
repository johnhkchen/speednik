# Plan: T-012-03-BUG-02 — Pipeworks Solid Tile Clipping

## Step 1: Add `_is_inside_solid()` helper to terrain.py

Add a private function that checks if the player center is inside a FULL solid tile.
Reuses the same logic as `_check_inside_solid` in invariants.py but operates on
`PhysicsState` and returns a boolean.

```python
def _is_inside_solid(state: PhysicsState, tile_lookup: TileLookup) -> bool:
    tx = int(state.x) // TILE_SIZE
    ty = int(state.y) // TILE_SIZE
    col = int(state.x) % TILE_SIZE
    tile = tile_lookup(tx, ty)
    if tile is None or tile.solidity != FULL:
        return False
    height = tile.height_array[col]
    solid_top = (ty + 1) * TILE_SIZE - height
    return state.y >= solid_top
```

**Verify:** Unit test that a point inside a FULL tile returns True, and a point
outside returns False.

## Step 2: Add `_eject_from_solid()` helper to terrain.py

Add a private function that attempts to move the player out of solid terrain.
Strategy: try vertical ejection first (up, then down), then horizontal.

For upward ejection: scan upward from player center tile-by-tile until finding
a non-solid position, then place the player just below that free tile
(y = free_tile_bottom - 1). Cap the search at MAX_SENSOR_RANGE * 2 pixels.

For downward ejection: scan downward similarly, place player at surface.

If vertical ejection fails, try horizontal (left then right).

If all fail, force the player upward by TILE_SIZE pixels and set airborne.

```python
def _eject_from_solid(state: PhysicsState, tile_lookup: TileLookup) -> None:
    # Try upward first (most common: player fell into solid from above)
    # Scan tiles upward from player's current tile
    start_tx = int(state.x) // TILE_SIZE
    start_ty = int(state.y) // TILE_SIZE
    col = int(state.x) % TILE_SIZE

    for dy in range(1, 5):  # Check up to 4 tiles upward
        check_ty = start_ty - dy
        tile = tile_lookup(start_tx, check_ty)
        if tile is None or tile.solidity == NOT_SOLID:
            # Free space found — place player at bottom of this free tile
            state.y = float((check_ty + 1) * TILE_SIZE - 1)
            state.on_ground = False
            state.angle = 0
            state.y_vel = 0.0
            return
        height = tile.height_array[col]
        if height < TILE_SIZE:
            solid_top = (check_ty + 1) * TILE_SIZE - height
            if solid_top > check_ty * TILE_SIZE:
                # There's free space above the solid region in this tile
                state.y = float(solid_top - 1)
                state.on_ground = False
                state.angle = 0
                state.y_vel = 0.0
                return

    # Fallback: push upward by TILE_SIZE
    state.y -= TILE_SIZE
    state.on_ground = False
    state.angle = 0
    state.y_vel = 0.0
```

**Verify:** Unit test with player inside a column of solid tiles with free space
above.

## Step 3: Integrate ejection into resolve_collision()

At the end of `resolve_collision()`, after the ceiling sensor pass, add:

```python
# --- Solid ejection pass ---
if _is_inside_solid(state, tile_lookup):
    _eject_from_solid(state, tile_lookup)
```

**Verify:** Run existing test_terrain.py tests to ensure no regressions.

## Step 4: Add unit tests for ejection

In `tests/test_terrain.py`, add:

1. `test_eject_from_solid_tile`: Create a grid with a column of FULL solid tiles
   and empty space above. Place player inside solid. Call `resolve_collision()`.
   Assert player center is no longer inside solid.

2. `test_no_eject_normal_surface`: Player standing on a normal flat surface. Call
   `resolve_collision()`. Assert player stays at the surface (no spurious ejection).

3. `test_eject_preserves_x`: After ejection, x position should be unchanged
   (upward ejection is vertical only).

**Verify:** All new tests pass.

## Step 5: Run full test suite

Run `uv run pytest` to check for regressions across all test files.

**Verify:** No new failures. Existing xfail tests still xfail as expected.

## Step 6: Run Pipeworks audit and update xfail markers

Run the Walker and Wall Hugger audits specifically. If invariant errors drop to 0:
- Remove the `xfail` from `test_pipeworks_walker` and `test_pipeworks_wall_hugger`
- If the test still fails for other reasons (e.g., min_x_progress not met), update
  the xfail reason or adjust the expectation.

If errors are reduced but not eliminated, investigate remaining cases.

**Verify:** `test_pipeworks_walker` and `test_pipeworks_wall_hugger` pass or have
accurate xfail markers.

## Testing Strategy

- **Unit tests:** `_is_inside_solid()` and ejection behavior via synthetic grids
- **Integration test:** Full Pipeworks audit via `run_audit()` for Walker/Wall Hugger
- **Regression:** Full `pytest` run to catch collateral damage
- **Acceptance criteria:** Zero `inside_solid_tile` invariant errors for Walker and
  Wall Hugger archetypes on Pipeworks

# Plan — T-012-03-BUG-03: pipeworks-chaos-early-clipping

## Step 1: Add horizontal ejection fallback in `_eject_from_solid()`

**File:** `speednik/terrain.py`, function `_eject_from_solid()` (lines 761–798)

Insert a horizontal ejection block between the upward scan loop (line 791)
and the final `y -= TILE_SIZE` fallback (line 794). Logic:

```
# After upward scan loop completes without returning:
# Try horizontal ejection
tile = tile_lookup(start_tx, start_ty)
if tile is not None:
    # Scan left from col for nearest free column
    best_dx = None
    for dc in range(1, TILE_SIZE):
        # Check left
        left_col = col - dc
        if left_col >= 0:
            h = tile.height_array[left_col]
            solid_top = (start_ty + 1) * TILE_SIZE - h
            if h == 0 or state.y < solid_top:
                new_x = start_tx * TILE_SIZE + left_col
                best_dx = new_x
                break
        # Check right
        right_col = col + dc
        if right_col < TILE_SIZE:
            h = tile.height_array[right_col]
            solid_top = (start_ty + 1) * TILE_SIZE - h
            if h == 0 or state.y < solid_top:
                new_x = start_tx * TILE_SIZE + right_col
                best_dx = new_x
                break
    if best_dx is not None:
        state.x = float(best_dx)
        state.on_ground = False
        state.angle = 0
        state.y_vel = 0.0
        state.x_vel = 0.0
        return
```

The loop alternates checking left and right columns outward from the current
position (dc=1,2,...,15), so it finds the nearest free column in either
direction. This ensures minimal displacement.

**Verify:** `_eject_from_solid()` still returns normally for all existing cases
(upward scan succeeds before reaching the new code).

## Step 2: Add unit test for horizontal ejection

**File:** `tests/test_terrain.py`

Add `test_eject_from_solid_horizontal()`:
1. Create a synthetic tile grid with a thin solid column — e.g., a 3-tile-tall
   stack where only column 4 is solid (h=[0,0,0,0,16,0,...,0]).
2. Place player at x = tile_x * 16 + 4 (on the solid column), y inside the
   solid region.
3. Call `resolve_collision(state, tile_lookup)`.
4. Assert player center is no longer inside solid.
5. Assert player was pushed horizontally (x changed, not on the solid column).

## Step 3: Run full test suite

```
uv run python -m pytest tests/ -x -q
```

All existing tests must pass. No regressions in walker, wall_hugger, or other
passing archetypes.

## Step 4: Run pipeworks chaos audit

```python
from speednik.qa import BehaviorExpectation, run_audit, make_chaos
exp = BehaviorExpectation(
    name='pipeworks_chaos', stage='pipeworks', archetype='chaos',
    min_x_progress=800, max_deaths=3, require_goal=False,
    max_frames=3600, invariant_errors_ok=0,
)
findings, result = run_audit('pipeworks', make_chaos(42), exp)
inv_errors = [v for v in result.violations if v.severity == 'error']
assert len(inv_errors) == 0
```

## Step 5: Update test_audit_pipeworks.py xfail

If chaos audit has 0 invariant errors but still fails on min_x_progress
(max_x≈488 < 800), update the xfail reason to remove BUG-03 reference:

```python
@pytest.mark.xfail(
    strict=True,
    reason="Chaos max_x≈488 below 800 target (no invariant errors)",
)
```

If chaos now passes entirely, remove the xfail decorator.

## Testing Strategy

| Test | Type | Verifies |
|------|------|----------|
| `test_eject_from_solid_horizontal` | Unit | Horizontal ejection works |
| `test_pipeworks_walker` | Integration | No regression |
| `test_pipeworks_wall_hugger` | Integration | No regression |
| `test_pipeworks_chaos` | Integration | BUG-03 fixed |
| Full test suite | Regression | No side effects |

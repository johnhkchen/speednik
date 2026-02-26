# Plan — T-012-02-BUG-03: hillside-no-left-boundary-clamp

## Step 1: Add left boundary clamp to `sim_step()`

**File:** `speednik/simulation.py`

Insert after `player_update(sim.player, inp, sim.tile_lookup)` (line 231):
```python
# Left boundary clamp (T-012-02-BUG-03)
p = sim.player.physics
if p.x < 0.0:
    p.x = 0.0
    if p.x_vel < 0.0:
        p.x_vel = 0.0
    if p.on_ground and p.ground_speed < 0.0:
        p.ground_speed = 0.0
```

**Verify:** Run `pytest tests/test_simulation.py -x` — existing tests still pass.

## Step 2: Add left boundary clamp to `_update_gameplay()`

**File:** `speednik/main.py`

Insert after `player_update(self.player, inp, self.tile_lookup)` (line 361):
```python
# Left boundary clamp (T-012-02-BUG-03)
p = self.player.physics
if p.x < 0.0:
    p.x = 0.0
    if p.x_vel < 0.0:
        p.x_vel = 0.0
    if p.on_ground and p.ground_speed < 0.0:
        p.ground_speed = 0.0
```

**Verify:** Code review only (requires Pyxel for runtime).

## Step 3: Add direct unit test for left boundary clamping

**File:** `tests/test_simulation.py`

Add `test_left_boundary_clamp`:
- Use `create_sim_from_lookup` with a flat ground grid
- Start player at x=32 (near left edge)
- Feed `InputState(left=True)` for 300 frames
- Assert `sim.player.physics.x >= 0.0` every frame
- After final frame, assert velocity is not negative

**Verify:** `pytest tests/test_simulation.py::test_left_boundary_clamp -v`

## Step 4: Remove `xfail` from `test_left_edge_escape`

**File:** `tests/test_levels.py`

Remove the `@pytest.mark.xfail(...)` decorator from `test_left_edge_escape` (lines 232-235).

**Verify:** `pytest tests/test_levels.py::TestBoundaryEscape::test_left_edge_escape -v`

## Step 5: Remove `xfail` from `test_hillside_chaos`

**File:** `tests/test_audit_hillside.py`

Remove the `@pytest.mark.xfail(...)` decorator from `test_hillside_chaos` (lines 150-153).

**Verify:** `pytest tests/test_audit_hillside.py::test_hillside_chaos -v`

## Step 6: Check regression test exclusion

**File:** `tests/test_regression.py`

Line 234 excludes `position_x_negative` from invariant error checks. Verify whether this
exclusion is still needed. If the chaos archetype no longer produces any `position_x_negative`
violations, the exclusion can be removed. If other tests still produce minor violations (e.g.,
single-frame overshoot before clamp), leave it.

**Verify:** `pytest tests/test_regression.py -v`

## Step 7: Run full test suite

**Command:** `pytest tests/ -v`

All tests should pass. Key expectations:
- `test_left_boundary_clamp` — new, should pass
- `test_left_edge_escape` — was xfail, now passes normally
- `test_hillside_chaos` — was xfail, now passes normally
- All other tests — unchanged behavior

## Testing Strategy

| Test | Type | What it verifies |
|------|------|-----------------|
| `test_left_boundary_clamp` | Unit | Direct: clamp works in `sim_step` |
| `test_left_edge_escape` | Integration | hold_left never escapes on any stage |
| `test_hillside_chaos` | Integration | chaos archetype produces 0 invariant errors |
| Existing `test_simulation.py` | Regression | Nothing broke in sim pipeline |
| Existing `test_levels.py` | Regression | Other boundary tests unaffected |

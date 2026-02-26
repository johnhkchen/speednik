# T-013-05 Structure: Loop and Slope Surface Adhesion

## Files Modified

### 1. `speednik/constants.py`

**Change**: Add `FALL_SPEED_THRESHOLD` constant.

```python
FALL_SPEED_THRESHOLD = 2.5  # Min |ground_speed| to stay attached on steep surfaces
```

Place in the "Slip" constants section alongside SLIP_SPEED_THRESHOLD. These are
conceptually related (both gate behavior on steep surfaces).

### 2. `speednik/terrain.py`

**Change**: Modify `resolve_collision` to add speed-based adhesion guard.

Location: The `on_ground` branch, lines 776-791, specifically the `else` clause
(no floor found → detach).

Current:
```python
if state.on_ground:
    if floor_result.found and abs(floor_result.distance) <= _GROUND_SNAP_DISTANCE:
        _snap_to_floor(...)
    else:
        state.on_ground = False  # unconditional
        state.angle = 0
```

New:
```python
if state.on_ground:
    if floor_result.found and abs(floor_result.distance) <= _GROUND_SNAP_DISTANCE:
        _snap_to_floor(...)
    else:
        # Speed-based adhesion: don't detach at high speed on steep surfaces
        quadrant = get_quadrant(state.angle)
        if quadrant != 0 and abs(state.ground_speed) >= FALL_SPEED_THRESHOLD:
            pass  # stay attached, preserve angle
        else:
            state.on_ground = False
            state.angle = 0
```

Import: Add `FALL_SPEED_THRESHOLD` to the import from `speednik.constants`.

**Rationale**: `quadrant != 0` means angle is in Q1 (33-96), Q2 (97-160), or
Q3 (161-223), covering the steep range. For Q0 (flat/gentle slopes), detachment
works normally — running off a cliff at high speed still detaches.

### 3. `tests/test_mechanic_probes.py`

**Change**: No code changes needed. Tests already assert the correct behavior:
- `TestLoopEntry.test_loop_traverses_all_quadrants`: Expects `{0,1,2,3}`
- `TestSlopeAdhesion.test_slope_stays_on_ground`: Expects ≥80% on_ground

These tests are currently failing and should pass after the fix.

### 4. `tests/test_geometry_probes.py`

**Change**: Remove `@pytest.mark.xfail` decorators from hillside loop tests
if they now pass. The three xfail tests:
- `test_crosses_loop_region`
- `test_exits_with_positive_speed`
- `test_returns_to_ground_level`

Decision: Run tests first, only remove xfail if tests actually pass. The hillside
loop has additional complexity (hand-placed tiles, different geometry) that may
require separate fixes.

## Files NOT Modified

- `speednik/physics.py`: No changes. Slip system is correct as-is. The adhesion
  guard in terrain.py handles the root cause.

- `speednik/grids.py`: No changes. Loop geometry is correct. The problem was in
  the physics engine, not the tile generation.

- `speednik/player.py`: No changes. State machine doesn't interact with the
  adhesion fix.

## Module Boundaries

The fix is entirely within the collision resolution layer (`terrain.py`). The
physics layer (`physics.py`) continues to handle slope factors, slip detection,
and movement decomposition. The adhesion guard sits between them — it prevents
the collision system from overriding the physics system's ground state when the
physics state (high speed) indicates the player should stay attached.

## Interface Changes

None. No public function signatures change. The behavioral change is internal to
`resolve_collision`:
- Previously: detach whenever floor sensor fails
- Now: detach only when speed < 2.5 OR angle is in flat range (Q0)

## Ordering

1. Add constant to `constants.py` (no dependencies)
2. Modify `resolve_collision` in `terrain.py` (depends on constant)
3. Run tests to verify
4. Update xfail markers if applicable

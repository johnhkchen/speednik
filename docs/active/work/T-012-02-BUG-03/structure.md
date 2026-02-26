# Structure — T-012-02-BUG-03: hillside-no-left-boundary-clamp

## Files Modified

### 1. `speednik/simulation.py`

**Change:** Add left boundary clamping after `player_update()` call in `sim_step()`.

Location: After line 231 (`player_update(sim.player, inp, sim.tile_lookup)`), before
line 234 (`sim.frame += 1`).

New code block (~6 lines):
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

Placed between player physics and frame counter. No new imports. No signature changes.

### 2. `speednik/main.py`

**Change:** Add identical left boundary clamping after `player_update()` in `_update_gameplay()`.

Location: After line 361 (`player_update(self.player, inp, self.tile_lookup)`), before
line 362 (`self.timer_frames += 1`).

Identical logic to simulation.py for parity:
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

### 3. `tests/test_levels.py`

**Change:** Remove `xfail` from `test_left_edge_escape` (lines 232-235).

Before:
```python
@pytest.mark.xfail(
    reason="No kill plane or position clamping exists yet",
    strict=False,
)
def test_left_edge_escape(self):
```

After:
```python
def test_left_edge_escape(self):
```

Note: `test_right_edge_escape` and `test_bottom_edge_escape` keep their `xfail` markers —
those are separate tickets.

### 4. `tests/test_audit_hillside.py`

**Change:** Remove `xfail` from `test_hillside_chaos` (lines 150-153).

Before:
```python
@pytest.mark.xfail(
    strict=True,
    reason="BUG: T-012-02-BUG-03 no left boundary clamp, invariant error flood",
)
def test_hillside_chaos():
```

After:
```python
def test_hillside_chaos():
```

### 5. `tests/test_simulation.py`

**Change:** Add a new test function `test_left_boundary_clamp` that directly verifies the
clamping behavior.

Test outline:
- Create a sim via `create_sim_from_lookup` with a flat ground grid
- Place player near x=0
- Feed leftward input for N frames
- Assert `player.physics.x >= 0` on every frame
- Assert `player.physics.x_vel >= 0` after clamping triggers

## Files NOT Modified

| File | Reason |
|------|--------|
| `speednik/physics.py` | Physics stays dimension-agnostic |
| `speednik/player.py` | No signature change, no boundary logic |
| `speednik/terrain.py` | Collision sensors unchanged |
| `speednik/invariants.py` | Detection logic unchanged — fewer violations to detect is the goal |
| `speednik/camera.py` | Camera clamping already works correctly |

## Module Boundaries

- **Boundary enforcement** lives at simulation layer (`sim_step`, `_update_gameplay`)
- **Physics engine** (`physics.py`) remains pure — no level dimensions
- **Player module** (`player.py`) remains unchanged — orchestrates physics, not policy
- **Tests** verify enforcement at the simulation layer

## Ordering

1. `simulation.py` clamp (core fix)
2. `main.py` clamp (parity)
3. `tests/test_simulation.py` new test
4. `tests/test_levels.py` xfail removal
5. `tests/test_audit_hillside.py` xfail removal
6. Run full test suite to verify

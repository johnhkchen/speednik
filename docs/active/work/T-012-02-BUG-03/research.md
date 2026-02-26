# Research — T-012-02-BUG-03: hillside-no-left-boundary-clamp

## Bug Summary

Chaos archetype (seed=42) drifts to x=-49488 on Hillside Rush. 10,526 `position_x_negative`
invariant errors. No left boundary clamp exists anywhere in the player physics pipeline.

## Architecture: Player Position Update Chain

Per-frame update order (matches `_update_gameplay` in `main.py:361` and `sim_step` in
`simulation.py:231`):

1. `player_update(player, inp, tile_lookup)` — `player.py:109`
   - `_pre_physics()` — state machine transitions (jump, roll, spindash)
   - `apply_input()` — acceleration/deceleration/friction — `physics.py:98`
   - `apply_slope_factor()` — ground_speed adjustment for slopes — `physics.py:223`
   - `apply_gravity()` — airborne gravity — `physics.py:251`
   - **`apply_movement()`** — position update — `physics.py:262`
   - `resolve_collision()` — sensor-based terrain collision — `terrain.py:740`
   - `_post_physics()` — state sync
2. Frame counter increment
3. Entity interactions (rings, springs, checkpoints, pipes, enemies)
4. Metrics update (`max_x_reached`)

## Position Update: No Clamping

`apply_movement()` at `physics.py:262`:
```python
def apply_movement(state: PhysicsState) -> None:
    if state.on_ground:
        angle_rad = byte_angle_to_rad(state.angle)
        state.x_vel = state.ground_speed * math.cos(angle_rad)
        state.y_vel = state.ground_speed * -math.sin(angle_rad)
    state.x += state.x_vel    # <-- raw addition, no bounds check
    state.y += state.y_vel
```

Velocity is hard-clamped to ±16.0 (`MAX_X_SPEED`) in `apply_input()` at `physics.py:113-117`,
but **position is never clamped**.

## Collision Resolution: Fails at Negative X

`resolve_collision()` uses sensor casts that call `tile_lookup(tx, ty)` — a dict lookup:
```python
def tile_lookup(tx: int, ty: int) -> Optional[Tile]:
    return tiles.get((tx, ty))
```

Hillside tiles exist only for `tx ∈ [0, 299]`, `ty ∈ [0, 44]`. When `x < 0`:
- `tx = int(x) // TILE_SIZE` → negative values
- `tile_lookup(-1, ty)` → `None`
- All sensors return `found=False` → no wall, no floor, no ceiling
- Player treated as in empty space — no collision stops leftward movement

## Camera: Has Boundary Clamping (Pattern to Follow)

`camera.py:164`:
```python
def _clamp_to_bounds(camera: Camera) -> None:
    max_x = max(0, camera.level_width - SCREEN_WIDTH)
    max_y = max(0, camera.level_height - SCREEN_HEIGHT)
    camera.x = max(0.0, min(camera.x, float(max_x)))
    camera.y = max(0.0, min(camera.y, float(max_y)))
```

The camera is clamped to `[0, level_width - SCREEN_WIDTH]`. This only affects the viewport,
NOT the player position. But it establishes the pattern.

## Invariants: Detection Only, No Enforcement

`invariants.py:71-106` detects `position_x_negative` (x < 0), `position_y_below_world`
(y > level_height + 64), and `position_x_beyond_right` (x > level_width + 64). These are
post-hoc checks on recorded trajectories — they flag violations but do NOT prevent them.

## Level Dimensions

Hillside Rush: 4800×720 pixels (300×45 tiles). Player starts at (64, 610).

## Existing Test Coverage

| Test | File | Status |
|------|------|--------|
| `test_hillside_chaos` | `test_audit_hillside.py:154` | `xfail(strict=True)` — expects BUG-03 failure |
| `test_left_edge_escape` | `test_levels.py:236` | `xfail(strict=False)` — all stages, hold_left |
| `test_right_edge_escape` | `test_levels.py:219` | `xfail(strict=False)` — all stages, multiple strategies |
| `test_bottom_edge_escape` | `test_levels.py:250` | `xfail(strict=False)` — all stages |
| `TestPositionInvariants` | `test_invariants.py:86-92` | Passes — tests invariant detection |

The `xfail` markers document the known defect. Once boundary clamping is added, the `xfail`s
should be removed and the tests should pass.

## Right Boundary: Also Missing (Separate Ticket)

`T-012-02-BUG-02` covers the right boundary. `test_hillside_jumper` in `test_audit_hillside.py:112`
is xfail for right boundary escape. This ticket (BUG-03) is left boundary only.

## SimState: Has Level Dimensions

`SimState` at `simulation.py:92` carries `level_width: int` and `level_height: int`.
`sim_step()` has direct access to these. `player_update()` does NOT receive level dimensions —
it only gets `(player, inp, tile_lookup)`.

## Key Constraint

This ticket is scoped to the **left boundary only** (x ≥ 0 clamp). The right boundary is
T-012-02-BUG-02. However, the implementation location may naturally support both boundaries
if the fix goes in `sim_step()`.

## Files Involved

| File | Role | Needs Change? |
|------|------|---------------|
| `speednik/simulation.py` | `sim_step()` — has level dimensions | **Yes** — add clamping |
| `speednik/main.py` | Live game loop — calls `player_update()` | **Maybe** — parity |
| `speednik/physics.py` | `apply_movement()` — position math | No change needed |
| `speednik/player.py` | `player_update()` — orchestration | No change needed |
| `speednik/terrain.py` | Collision sensors | No change needed |
| `speednik/invariants.py` | Violation detection | No change needed |
| `tests/test_levels.py` | `xfail` boundary tests | **Yes** — remove xfail for left |
| `tests/test_audit_hillside.py` | `xfail` chaos test | **Yes** — remove xfail |

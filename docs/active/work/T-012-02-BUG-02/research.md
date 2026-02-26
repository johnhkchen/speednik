# Research — T-012-02-BUG-02: hillside-no-right-boundary-clamp

## Summary

The jumper archetype exits the right level boundary on Hillside Rush, reaching
x=34023 when level_width=4800. No position clamping exists anywhere in the
simulation pipeline for the right edge. The invariant checker in `invariants.py`
detects the violation post-hoc but nothing prevents it at runtime.

## Player Position Update Pipeline

The position update flows through three modules in sequence:

1. **`player.py:player_update()`** (line 109) — orchestrator
   - Calls `apply_input`, `apply_slope_factor`, `apply_gravity`, `apply_movement`
   - Then `resolve_collision` for tile-based collision resolution
   - Signature: `player_update(player, inp, tile_lookup)` — no level dimensions
   - No boundary clamping anywhere in this function

2. **`physics.py:apply_movement()`** (line 262) — position update
   - On ground: decomposes `ground_speed` via angle into `x_vel`/`y_vel`
   - Then unconditionally: `state.x += state.x_vel; state.y += state.y_vel`
   - Velocity is clamped (line 113-117) to `MAX_X_SPEED` but position is not

3. **`simulation.py:sim_step()`** (line 217) — frame advance
   - Calls `player_update(sim.player, inp, sim.tile_lookup)` at line 231
   - Tracks `max_x_reached` at line 279 but does not clamp
   - Has access to `sim.level_width` and `sim.level_height`

## Existing Boundary Handling

### Left boundary (x < 0)
- **Not clamped in physics or simulation**. Only detected:
  - `invariants.py:77-83`: flags `position_x_negative` when `snap.x < 0`
  - BUG-03 documents the same missing-clamp problem for the left edge

### Right boundary (x > level_width)
- **Not clamped in physics or simulation**. Only detected:
  - `invariants.py:95-105`: flags `position_x_beyond_right` when
    `snap.x > sim.level_width + POSITION_MARGIN` (margin = 64px)

### Bottom boundary (y > level_height)
- **Not clamped**. Only detected in `invariants.py:84-94`.

### Camera boundary
- **Properly clamped** in `camera.py:_clamp_to_bounds()` (line 164).
  Camera x is clamped to `[0, level_width - SCREEN_WIDTH]`.

## Collision System

`terrain.py:resolve_collision()` uses tile-based sensor casts:
- Floor sensors (DOWN) detect ground surfaces
- Wall sensors (LEFT/RIGHT) detect solid tile walls
- Ceiling sensors (UP) detect ceilings

The collision system only detects **solid tiles**. Beyond the tile map there are
no tiles, so there is no collision data to stop the player. The player sails
through empty space indefinitely.

## Where level_width Is Available

| Location | Access | Notes |
|---|---|---|
| `SimState` | `sim.level_width` | Set from `stage.level_width` in factory |
| `sim_step()` | `sim.level_width` | Direct access via sim parameter |
| `player_update()` | **Not available** | Only receives `player`, `inp`, `tile_lookup` |
| `apply_movement()` | **Not available** | Only receives `PhysicsState` |
| `SpeednikEnv.step()` | `self.sim.level_width` | Via sim reference |

## Related Tickets

- **T-012-02-BUG-01** (done): Wall-angle tile at x=601 — tile data fix, unrelated
- **T-012-02-BUG-03** (open): Same issue but for left boundary (x goes negative)
  - Identical root cause, mirror fix needed
  - Both bugs should use the same clamping mechanism

## Invariant Definition

```python
POSITION_MARGIN = 64  # pixels beyond boundary before flagging

if snap.x > sim.level_width + POSITION_MARGIN:
    # flags "position_x_beyond_right"
```

The margin allows 64px past level_width before reporting. The fix should prevent
the player from reaching that threshold at all.

## Root Cause

No position clamping exists in the runtime simulation loop. The camera is
properly clamped (`camera.py:164`), but the player physics state has no
corresponding enforcement. When the player moves past the tile map edge, the
collision system finds no tiles and applies no push-back, so the player
continues at whatever velocity it had indefinitely.

## Key Constraint

This is a **headless simulation** bug — `simulation.py` and `physics.py` have
no Pyxel imports. The fix must remain in the headless layer. `main.py` does not
add boundary clamping either; the rendered game has the same bug.

## Scope Note

This ticket covers **right boundary only**. BUG-03 covers the left boundary.
However, the fix location and pattern should be designed so BUG-03 can use the
same approach symmetrically.

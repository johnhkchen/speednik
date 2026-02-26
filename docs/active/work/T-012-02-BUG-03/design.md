# Design — T-012-02-BUG-03: hillside-no-left-boundary-clamp

## Problem

Player X position is never clamped to x ≥ 0. Random inputs drive the player into unbounded
negative X territory, causing 10,526 invariant errors per 3600-frame run.

## Requirements

1. Player X must never go below 0.
2. When clamped, leftward velocity must be zeroed to prevent "pressing against wall" accumulation.
3. Fix must apply in both `sim_step()` (headless) and `main.py` (live game) to maintain parity.
4. Scope: **left boundary only** (x ≥ 0). Right boundary is T-012-02-BUG-02.

## Options Evaluated

### Option A: Clamp in `sim_step()` after `player_update()`

Add clamping logic in `simulation.py:sim_step()` after the `player_update()` call (line 231).
SimState already has `level_width` and `level_height`. Clamp `player.physics.x` to `max(0.0, x)`
and zero leftward velocity when clamped.

**Pros:**
- `sim_step()` already has level dimensions
- No signature changes to `player_update()` or any physics functions
- Clean separation: physics engine is dimension-agnostic, boundary enforcement is simulation-level

**Cons:**
- Must mirror the same logic in `main.py:_update_gameplay()` for live game parity
- Clamping happens after collision resolution, which is the correct order but means one frame
  of "overshoot" is corrected post-hoc

### Option B: Clamp in `apply_movement()` (physics.py)

Add level bounds to `PhysicsState` and clamp position after velocity addition.

**Pros:**
- Centralized — works everywhere physics runs

**Cons:**
- `PhysicsState` would need `level_width`/`level_height` fields, polluting the pure physics model
- Every `PhysicsState` constructor call would need updating
- Mixes concerns: physics module becomes aware of level geometry

### Option C: Clamp in `player_update()` (player.py)

Add level dimensions as parameters to `player_update()`.

**Pros:**
- Player module already orchestrates physics + collision

**Cons:**
- Signature change to `player_update()` — touches every call site (simulation.py, main.py, tests)
- `player_update` is player-level orchestration, not level-level policy

### Option D: Clamp in `resolve_collision()` (terrain.py)

Synthesize wall collisions at boundaries.

**Pros:**
- Collision resolution is the "right" conceptual layer

**Cons:**
- `resolve_collision()` uses tile sensor casts — boundary enforcement doesn't fit the sensor model
- Would need level dimensions passed to every collision call
- Overcomplicates an already complex module

## Decision: Option A — Clamp in `sim_step()` and `_update_gameplay()`

Rationale:
1. **No signature changes.** `sim_step()` already has `sim.level_width`/`sim.level_height`.
   `_update_gameplay()` already has `self.level_width` etc. on the App instance.
2. **Correct layering.** Boundary enforcement is a simulation/game-level policy, not a physics
   engine concern. The camera already handles its own boundary clamping at the same layer.
3. **Minimal diff.** ~5 lines in `sim_step()`, ~5 parallel lines in `main.py`. No test fixture
   changes.
4. **Parity.** Both headless and live paths get identical clamping at the same logical point.

## Clamping Behavior

When `x < 0` after `player_update()` returns:
```
p.x = max(0.0, p.x)
if p.x == 0.0 and p.x_vel < 0:
    p.x_vel = 0.0
    if p.on_ground:
        p.ground_speed = 0.0
```

This ensures:
- Position is clamped to 0
- Leftward velocity is killed (prevents "pressing against wall" energy)
- Ground speed is zeroed on ground (prevents slope factor from regenerating leftward velocity)

## Scope Boundary

This ticket adds **left boundary clamping only** (x ≥ 0). The same pattern can be extended for
the right boundary (x ≤ level_width) in T-012-02-BUG-02, but that is out of scope here.

## Test Impact

- `test_left_edge_escape` in `test_levels.py:236` — remove `xfail`, should now pass
- `test_hillside_chaos` in `test_audit_hillside.py:154` — remove `xfail`, should now pass
- `test_regression.py:234` — `position_x_negative` exclusion may become unnecessary (verify)
- Add a direct unit test: `sim_step` with forced leftward input, assert x never goes negative

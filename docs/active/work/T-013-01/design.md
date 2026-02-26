# T-013-01 Design: World Boundary System

## Decision: Boundary Enforcement in sim_step

### Option A: Boundary clamping inside player_update (physics layer)

Add boundary checks after `apply_movement()` but before `resolve_collision()`.

Pros:
- Co-located with other physics logic
- `player_update` already owns position updates

Cons:
- `player_update` doesn't have access to `level_width`/`level_height` — would need
  to thread those through as parameters (breaking change to signature)
- Pit death requires setting `player.state = DEAD` and notifying the sim layer of
  the event — mixing concerns between physics and game logic
- The harness's `run_scenario()` calls `player_update` directly without a SimState,
  so it would also need boundary info threaded through

Rejected: Too invasive. Boundary enforcement is game-level policy, not physics.

### Option B: Boundary enforcement in sim_step (chosen)

Add boundary checks in `sim_step()` after `player_update()` returns but before entity
collision checks.

Pros:
- `sim_step` already has access to `sim.level_width` and `sim.level_height`
- Natural place for game-level policy (death trigger, respawn)
- All consumers (headless, Gymnasium, live game) go through sim_step
- No signature changes to player_update

Cons:
- Boundary check runs one frame after position update — player briefly at illegal
  position before correction. Acceptable because the correction is immediate before
  any entity collision checks.

**Chosen.** This is the cleanest integration point.

### Option C: Boundary clamping in physics.py apply_movement

Add position clamp right after `state.x += state.x_vel`.

Rejected: apply_movement has no access to level dimensions. Would require passing
level bounds into every physics function or storing them on PhysicsState.

## Design Decisions

### 1. Left boundary: Hard clamp at x=0

After player_update:
```
if p.x < 0:
    p.x = 0
    if p.x_vel < 0: p.x_vel = 0
    if p.ground_speed < 0: p.ground_speed = 0
```

No death. Just a wall. Zero velocity to prevent oscillation.

### 2. Right boundary: Hard clamp at x=level_width

Same pattern as left:
```
if p.x > sim.level_width:
    p.x = sim.level_width
    if p.x_vel > 0: p.x_vel = 0
    if p.ground_speed > 0: p.ground_speed = 0
```

### 3. Pit death: Kill at y > level_height + PIT_DEATH_MARGIN

New constant `PIT_DEATH_MARGIN = 32` in constants.py.

When triggered:
- Call `damage_player(sim.player)` which handles ring scattering + DEAD state
- But for pit death, player should die regardless of rings — immediate death
- So: directly set `player.state = PlayerState.DEAD`
- Emit `DeathEvent`
- Increment `sim.deaths`

### 4. Death should NOT set sim.player_dead

The `sim.player_dead` flag in SimState currently serves as a permanent stop. Pit death
should allow respawn. Instead of using that flag, we should check `player.state ==
PlayerState.DEAD` in the early return and handle respawn.

Wait — reviewing `sim_step`:
```python
if sim.player_dead:
    return events
```

And `player_update`:
```python
if player.state == PlayerState.DEAD:
    return
```

Currently, when the player is DEAD, `player_update` is a no-op, but `sim_step` continues
processing entity collisions on a dead player (springs, enemies, etc.). That's wasteful
but not harmful.

For this ticket: we'll add the boundary checks BEFORE entity collisions, and the DEAD
check in player_update already prevents further movement. We don't need to touch
sim.player_dead — respawn is handled by the caller (main.py or Gymnasium env).

### 5. Headless respawn for sim_step

The ticket says "player should respawn at the last checkpoint." Currently respawn only
exists in main.py (`_respawn_player`). For headless sim / Gymnasium, we need a sim-layer
respawn.

Design: Add a `respawn_player(sim)` function in simulation.py that resets the player
to their checkpoint position, similar to main.py's `_respawn_player`. The caller
(Gymnasium env, test harness) decides when to call it.

Actually — re-reading the requirements: "Kill the player via the existing damage_player /
death mechanism. The player should respawn at the last checkpoint (or stage start)."

The Gymnasium env already handles death/respawn in its step function. The live game
handles it in main.py. For the headless audit/test harness, death just means the player
stops. So: we just need to trigger death, not implement respawn in sim_step.

### 6. create_sim_from_lookup kwargs

Add `level_width` and `level_height` optional kwargs with defaults matching current
hardcoded values (99999). This fixes the broken test calls without changing behavior
for callers that don't pass them.

## Summary of Changes

1. **constants.py**: Add `PIT_DEATH_MARGIN = 32`
2. **simulation.py** `sim_step()`: Add boundary enforcement block after player_update
3. **simulation.py** `create_sim_from_lookup()`: Add optional level_width/level_height kwargs
4. **New tests**: Test boundary clamping and pit death via sim_step

## Rejected Alternatives

- **Boundary in terrain.py**: Would mix tile collision with level boundaries. Different
  concerns.
- **Using sim.player_dead for pit death**: That flag is permanent/terminal. Death should
  be a normal game state that allows respawn.
- **Separate boundary enforcement module**: Over-engineering for ~15 lines of logic.
- **Y-top boundary (y < 0)**: Not in requirements. Players jumping above the screen is
  normal Sonic behavior — gravity brings them back.

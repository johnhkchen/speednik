# T-011-05 Research: Entity Interaction Tests

## Scope

Test the full entity lifecycle through `sim_step` on real stages: ring collection,
damage/scatter/recollection, death-with-zero-rings, springs, enemy bounce vs enemy
damage, checkpoints, and goal detection.

## Relevant Modules

### speednik/simulation.py
- `SimState` — holds all game state: player, entity lists (rings, springs, checkpoints,
  pipes, liquid_zones, enemies), goal position, counters (frame, rings_collected, deaths),
  flags (goal_reached, player_dead).
- `create_sim(stage_name)` — loads a real stage ("hillside", "pipeworks", "skybridge"),
  creates player at stage.player_start, loads all entities, sets goal position.
- `create_sim_from_lookup(tile_lookup, start_x, start_y)` — creates sim with empty entity
  lists from a synthetic tile grid. Used for parity testing.
- `sim_step(sim, inp) -> list[Event]` — advances one frame. Order:
  1. Death guard (returns [DeathEvent()] if DEAD)
  2. player_update
  3. frame++
  4. Ring collection → RingCollectedEvent
  5. Spring collision → SpringEvent
  6. Checkpoint collision → CheckpointEvent
  7. Pipe travel (side effects)
  8. Liquid zones → DamageEvent
  9. Enemy update + collision → DamageEvent
  10. Spring cooldowns
  11. Goal collision → GoalReachedEvent
  12. Metrics (max_x, rings_collected)

### speednik/objects.py
- `Ring(x, y, collected=False)` — distance-based collection (RING_COLLECTION_RADIUS=16).
- `Spring(x, y, direction, cooldown=0)` — AABB collision, sets y_vel=-10 (up) or
  x_vel=10 (right), cooldown=8 frames.
- `Checkpoint(x, y, activated=False)` — distance-based (CHECKPOINT_ACTIVATION_RADIUS=20),
  sets player respawn point.
- Goal — distance-based (GOAL_ACTIVATION_RADIUS=24), sets sim.goal_reached=True.

### speednik/enemies.py
- `Enemy(x, y, enemy_type, alive, ...)` — types: crab, chopper, buzzer, guardian,
  egg_piston. Hitboxes centered on position, sizes vary by type.
- `check_enemy_collision(player, enemies)` — skips dead/hurt player. For each alive enemy:
  - Spindash kill: is_rolling AND |ground_speed| >= 8.0 → DESTROYED
  - Bounce kill: player center above enemy AND (rolling or y_vel > 0) → BOUNCE + DESTROYED,
    y_vel set to -6.5
  - Side/below contact (invuln timer <= 0): damage_player() → PLAYER_DAMAGED
- Only first hit per frame is processed (breaks after PLAYER_DAMAGED or BOUNCE).

### speednik/player.py
- `Player(physics, state, rings, lives, invulnerability_timer, scattered_rings, ...)`
- `PlayerState` enum: STANDING, RUNNING, JUMPING, ROLLING, SPINDASH, HURT, DEAD
- `damage_player(player)`:
  - If invuln timer > 0 or DEAD: no-op
  - If rings > 0: scatter rings, rings=0, state=HURT, invuln=120, knockback
  - If rings == 0: state=DEAD, knockback
- `get_player_rect(player)` — returns (x, y, w, h) AABB for collision.
  Rolling/airborne: 14×28. Standing: 18×40.

### speednik/physics.py
- `InputState(left, right, jump_pressed, jump_held, down_held, up_held)` — frame input.
- `PhysicsState(x, y, x_vel, y_vel, ground_speed, angle, on_ground, is_rolling, ...)`

### speednik/constants.py
Key values: ENEMY_BOUNCE_VELOCITY=-6.5, SPRING_UP_VELOCITY=-10.0,
SPRING_COOLDOWN_FRAMES=8, RING_COLLECTION_RADIUS=16, CHECKPOINT_ACTIVATION_RADIUS=20,
GOAL_ACTIVATION_RADIUS=24, INVULNERABILITY_DURATION=120.

## Existing Test Patterns

### tests/test_simulation.py
- Real stage tests: `create_sim("hillside")`, run N frames with InputState, collect events.
- Direct state manipulation: teleport player to goal, force DEAD state.
- Entity injection: not done yet — entities come from stage load only.
- Event filtering: `[e for e in all_events if isinstance(e, EventType)]`.

### tests/harness.py
- Strategy functions: `hold_right()`, `spindash_right()`, `idle()`.
- `run_scenario(tile_lookup, ...)` / `run_on_stage(stage_name, ...)` — player-only,
  no entity interactions (uses raw player_update, not sim_step).

## Key Constraints

1. **No entity mutation helper**: `create_sim_from_lookup` gives empty entity lists.
   For controlled tests (e.g. "damage with 0 rings"), either:
   - Mutate SimState after `create_sim("hillside")` (set player.rings = 0)
   - Append synthetic entities to `sim.enemies`, `sim.rings`, etc.
2. **Event types have no fields**: Events are markers only — no payload.
3. **Invulnerability blocks subsequent damage**: 120 frames between hits.
4. **Scattered ring recollection**: Handled inside player_update via
   `_check_ring_collection`. Scattered rings are in `player.scattered_rings`.
5. **Bounce vs damage**: Depends on player_center_y < enemy_center_y AND
   (is_rolling or y_vel > 0). Not just "jumping".

## Stage Entity Inventory (hillside)

From `create_sim("hillside")`:
- Rings: >0 (placed along the path)
- Springs: >0 (up and right variants)
- Enemies: >0 (crabs, choppers, guardians)
- Checkpoints: >0
- Goal: (4758, 642)
- No pipes, no liquid zones (those are pipeworks)

## Risks

- Some tests (scattered ring recollection) depend on physics timing — rings scatter
  in a fan pattern with limited lifetime (180 frames). Recollection requires the player
  to be near scattered ring positions, which is non-deterministic on real stages.
- Enemy encounters depend on running far enough — hold_right for 1800 frames reaches
  enemies on hillside but may die before collecting enough data.
- Spring encounters require reaching spring positions on the stage.

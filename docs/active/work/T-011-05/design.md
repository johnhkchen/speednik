# T-011-05 Design: Entity Interaction Tests

## Approach Options

### Option A: Pure Real-Stage Tests
Run hold_right / spindash_right on hillside for enough frames and assert events appear.

**Pros**: Tests the real game. Minimal setup.
**Cons**: Non-deterministic timing. Can't test "damage with 0 rings" without
state injection. Hard to guarantee specific interactions (e.g. spring hit, bounce kill).
Some scenarios may require thousands of frames.

### Option B: Synthetic Entity Injection
Use `create_sim_from_lookup` with synthetic tile grids and manually place entities
at known positions relative to the player.

**Pros**: Fully deterministic. Each test controls exactly what happens.
**Cons**: Doesn't test real stage geometry. `create_sim_from_lookup` returns empty
entities, but we can mutate the SimState after creation.

### Option C: Hybrid — Real Stage + Controlled State Injection (Chosen)
Use `create_sim("hillside")` for the real physics and entity environment. For tests
that need controlled setups (damage with 0 rings, enemy bounce, spring collision),
either:
1. Teleport player near known entities, or
2. Inject synthetic entities near player start, or
3. Manipulate player state (e.g. rings=0) before running.

**Pros**: Real stage geometry + deterministic controlled tests. Best coverage.
**Cons**: Slightly more setup per test.

## Decision: Option C

Real-stage tests verify the full pipeline. Controlled injection covers edge cases.
This matches the existing pattern in test_simulation.py (teleport-to-goal test).

## Test Design by Scenario

### 1. Ring collection (real stage)
- `create_sim("hillside")`, hold_right for 600 frames.
- Assert RingCollectedEvent appears and rings_collected > 0.
- Already partially covered by `test_full_sim_ring_collection_hillside` — this test
  adds the entity-interaction focus (verifying player.rings increments).

### 2. Damage with rings (ring scatter)
- `create_sim("hillside")`, give player rings (player.rings = 5).
- Place a buzzer enemy directly in front of player (simple, stationary).
- Run until DamageEvent fires.
- Assert player.rings == 0 and len(player.scattered_rings) > 0.

### 3. Ring death (damage with 0 rings)
- `create_sim("hillside")`, set player.rings = 0.
- Place a buzzer enemy directly ahead.
- Run until DeathEvent or DamageEvent → then step one more.
- Assert sim.player_dead is True.

### 4. Scattered ring recollection
- After damage, scattered rings exist. If player moves through them, they get
  recollected. Use direct state setup: create sim, damage player manually
  (set state=HURT, scatter rings at player position), let invuln expire,
  then check if rings get collected during player_update.
- Alternative: place enemy, run until damage, continue running, check if
  rings_collected increases after damage frame.

### 5. Spring behavior
- `create_sim("hillside")`, find first spring from sim.springs.
- Teleport player near the spring.
- Run frames until SpringEvent.
- Assert y_vel < 0 (for up spring) or x_vel > 0 (for right spring).
- Assert spring.cooldown == SPRING_COOLDOWN_FRAMES after trigger.
- Step 8 more frames, verify cooldown returns to 0.

### 6. Enemy bounce (jump onto enemy)
- `create_sim("hillside")`, place buzzer at known position.
- Set player airborne above enemy: physics.y above enemy.y, y_vel > 0 (descending),
  on_ground=False, state=JUMPING.
- Run sim_step until contact.
- Assert enemy.alive == False and y_vel == ENEMY_BOUNCE_VELOCITY.

### 7. Enemy walk-into (grounded contact)
- `create_sim("hillside")`, place buzzer ahead.
- Hold right. Assert DamageEvent fires (not bounce).

### 8. Checkpoint activation
- `create_sim("hillside")`, find first checkpoint.
- Teleport player near checkpoint.
- Step. Assert CheckpointEvent fires, checkpoint.activated == True,
  player.respawn_x/y == checkpoint position.

### 9. Goal detection
- `create_sim("hillside")`, teleport to goal.
- Step. Assert GoalReachedEvent, sim.goal_reached == True.
- Already in test_simulation.py but included here for completeness.

## Rejected Approaches

- **Mocking collision functions**: Would test the mock, not the system.
- **Parametrized stage matrix**: Overkill — hillside has all entity types needed.
- **Using harness.py strategies**: Those call player_update, not sim_step, so they
  bypass entity interactions entirely.

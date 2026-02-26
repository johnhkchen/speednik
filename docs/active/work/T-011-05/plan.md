# T-011-05 Plan: Entity Interaction Tests

## Step 1: Create test file with helpers

Create `tests/test_entity_interactions.py` with:
- All imports
- `_place_buzzer(sim, dx, dy)` helper
- `_run_until_event(sim, inp, event_type, max_frames)` helper
- `_run_frames(sim, inp, n)` helper

**Verify**: File imports without error (`uv run python -c "import tests.test_entity_interactions"`)

## Step 2: Ring collection tests

Add `test_ring_collection_on_hillside`:
- create_sim("hillside"), hold_right 600 frames
- Assert RingCollectedEvent in events
- Assert sim.rings_collected > 0 and sim.player.rings > 0

Add `test_ring_collection_increments_player_rings`:
- create_sim("hillside"), inject Ring at player.x + 20, player.y
- Step with hold_right until ring collected
- Assert player.rings increased

**Verify**: `uv run pytest tests/test_entity_interactions.py -x -k ring_collection`

## Step 3: Damage and scatter tests

Add `test_damage_scatters_rings`:
- create_sim("hillside"), set player.rings = 5
- Place buzzer 40px ahead of player
- Hold right until DamageEvent
- Assert player.rings == 0, len(player.scattered_rings) > 0

Add `test_damage_with_zero_rings_causes_death`:
- create_sim("hillside"), player.rings = 0
- Place buzzer 40px ahead
- Run until death (DamageEvent causes DEAD state, next sim_step produces DeathEvent)
- Assert sim.player_dead is True, sim.deaths == 1

Add `test_scattered_ring_recollection`:
- create_sim("hillside"), give 5 rings
- Place buzzer ahead, run until damage
- Note rings_collected at damage point
- Continue running 300 more frames
- Assert rings_collected increased (scattered rings picked up)

**Verify**: `uv run pytest tests/test_entity_interactions.py -x -k damage`

## Step 4: Spring tests

Add `test_spring_produces_event_and_upward_velocity`:
- create_sim("hillside"), find first up-spring from sim.springs
- Teleport player to spring.x, spring.y (within hitbox)
- Step once → SpringEvent, y_vel == SPRING_UP_VELOCITY

Add `test_spring_cooldown_prevents_retrigger`:
- After triggering spring, assert spring.cooldown == SPRING_COOLDOWN_FRAMES
- Step SPRING_COOLDOWN_FRAMES times, assert cooldown == 0

Add `test_spring_right_sets_horizontal_velocity`:
- Find right-spring in sim.springs, or inject one
- Teleport player, step → x_vel > 0

**Verify**: `uv run pytest tests/test_entity_interactions.py -x -k spring`

## Step 5: Enemy bounce and damage tests

Add `test_enemy_bounce_destroys_enemy`:
- create_sim("hillside"), place buzzer at known position
- Set player above enemy: physics.y = enemy.y - 30, physics.y_vel = 5.0 (descending),
  on_ground=False, state=JUMPING
- Set physics.x = enemy.x (aligned horizontally)
- Step → assert enemy.alive == False
- Assert y_vel == ENEMY_BOUNCE_VELOCITY

Add `test_enemy_walk_into_causes_damage`:
- create_sim("hillside"), player.rings = 3
- Place buzzer 30px ahead
- Hold right until DamageEvent
- Assert player.rings == 0, player.state == HURT

**Verify**: `uv run pytest tests/test_entity_interactions.py -x -k enemy`

## Step 6: Checkpoint and goal tests

Add `test_checkpoint_activation`:
- create_sim("hillside"), find first checkpoint
- Teleport player to checkpoint position
- Step → CheckpointEvent
- Assert checkpoint.activated == True
- Assert player.respawn_x == checkpoint.x, player.respawn_y == checkpoint.y

Add `test_goal_reached`:
- create_sim("hillside"), teleport to goal
- Step → GoalReachedEvent, sim.goal_reached == True

**Verify**: `uv run pytest tests/test_entity_interactions.py -x -k "checkpoint or goal"`

## Step 7: Full test suite run

**Verify**: `uv run pytest tests/test_entity_interactions.py -x -v`

All tests green. Commit.

## Testing Strategy

- **Unit-level**: Each test isolates one interaction type.
- **Integration**: Real stage geometry via create_sim("hillside").
- **Edge cases**: 0-ring death, spring cooldown, bounce vs walk-into.
- **No mocking**: All tests use real collision code paths.
- **Deterministic**: Teleportation and entity injection ensure reproducibility.

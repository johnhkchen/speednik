# T-011-05 Progress: Entity Interaction Tests

## Completed

### Step 1: Create test file with helpers
- Created `tests/test_entity_interactions.py`
- Implemented `_place_buzzer`, `_run_frames`, `_run_until_event` helpers
- Verified imports

### Step 2: Ring collection tests
- `test_ring_collection_on_hillside` — hold_right 600 frames, verifies RingCollectedEvent
- `test_ring_collection_increments_player_rings` — inject Ring near player, verify collection

### Step 3: Damage and scatter tests
- `test_damage_scatters_rings` — give rings, walk into buzzer, verify scatter
- `test_damage_with_zero_rings_causes_death` — 0 rings + buzzer = DeathEvent
- `test_scattered_ring_recollection` — after damage, continue running, verify recollection

### Step 4: Spring tests
- `test_spring_produces_event_and_upward_velocity` — teleport to spring, verify event + y_vel
- `test_spring_cooldown_prevents_retrigger` — verify cooldown timer behavior
- `test_spring_right_sets_horizontal_velocity` — right spring sets x_vel > 0

### Step 5: Enemy bounce and damage tests
- `test_enemy_bounce_destroys_enemy` — jump arc onto buzzer on flat grid, verify kill + bounce velocity
- `test_enemy_walk_into_causes_damage` — grounded contact = DamageEvent, enemy survives

### Step 6: Checkpoint and goal tests
- `test_checkpoint_activation` — teleport to checkpoint, verify event + respawn update
- `test_goal_reached` — teleport to goal, verify GoalReachedEvent + flag

### Step 7: Full test suite run
- 12/12 tests pass in 0.06s

## Deviations from Plan

- **Enemy bounce test**: Originally planned to use `create_sim("hillside")` with direct
  position manipulation. Terrain collision resolved the player to the ground before enemy
  contact could occur. Switched to `create_sim_from_lookup` with a flat grid for the
  bounce test, which gives deterministic jump arcs without terrain interference.

## Remaining

None — all planned tests implemented and passing.

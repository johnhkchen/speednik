# T-011-05 Structure: Entity Interaction Tests

## Files

### Created
- `tests/test_entity_interactions.py` — all entity interaction tests

### Modified
- None

### Deleted
- None

## Module Layout

```
tests/test_entity_interactions.py
├── Imports
│   ├── speednik.simulation: create_sim, sim_step, Event types
│   ├── speednik.physics: InputState
│   ├── speednik.player: PlayerState
│   ├── speednik.enemies: Enemy, ENEMY_BOUNCE_VELOCITY (for assertion)
│   ├── speednik.objects: Ring, Spring, Checkpoint
│   └── speednik.constants: SPRING_COOLDOWN_FRAMES, SPRING_UP_VELOCITY, etc.
│
├── Helpers
│   ├── _place_buzzer(sim, dx, dy) -> Enemy
│   │     Inject a stationary buzzer at player.x + dx, player.y + dy.
│   │     Appends to sim.enemies, returns the enemy.
│   │
│   ├── _run_until_event(sim, inp, event_type, max_frames) -> (events, frame)
│   │     Step sim until event_type appears or max_frames reached.
│   │     Returns (all_events, frame_of_first_match).
│   │
│   └── _run_frames(sim, inp, n) -> list[Event]
│         Step sim n frames, return all events.
│
├── Ring collection tests
│   ├── test_ring_collection_on_hillside()
│   │     hold_right 600 frames → RingCollectedEvent, player.rings > 0,
│   │     sim.rings_collected > 0
│   │
│   └── test_ring_collection_increments_player_rings()
│         Place a Ring near player, step → player.rings == 1
│
├── Damage & scatter tests
│   ├── test_damage_scatters_rings()
│   │     Give player rings, place buzzer ahead, run → DamageEvent,
│   │     player.rings == 0, scattered_rings > 0
│   │
│   ├── test_damage_with_zero_rings_causes_death()
│   │     player.rings = 0, place buzzer → DeathEvent, player_dead = True
│   │
│   └── test_scattered_ring_recollection()
│         After damage, continue running → rings_collected increases
│         (scattered rings recollected by player_update internal logic)
│
├── Spring tests
│   ├── test_spring_produces_event_and_upward_velocity()
│   │     Teleport near up-spring → SpringEvent, y_vel < 0
│   │
│   ├── test_spring_cooldown_prevents_retrigger()
│   │     After spring fires, cooldown > 0. Step SPRING_COOLDOWN_FRAMES,
│   │     cooldown returns to 0.
│   │
│   └── test_spring_right_sets_horizontal_velocity()
│         Find right-spring or inject one → x_vel > 0
│
├── Enemy tests
│   ├── test_enemy_bounce_destroys_enemy()
│   │     Place buzzer, position player above, descending → DESTROYED,
│   │     y_vel == ENEMY_BOUNCE_VELOCITY
│   │
│   └── test_enemy_walk_into_causes_damage()
│         Place buzzer ahead, hold_right → DamageEvent (not destroy)
│
├── Checkpoint tests
│   └── test_checkpoint_activation()
│         Teleport near checkpoint → CheckpointEvent, activated == True,
│         respawn updated
│
└── Goal tests
    └── test_goal_reached()
          Teleport to goal → GoalReachedEvent, goal_reached == True
```

## Interface Boundaries

- Tests only call public API: `create_sim`, `sim_step`, `InputState`.
- Entity injection uses direct mutation of SimState lists (`sim.enemies.append(...)`,
  `sim.rings.append(...)`).
- Player state manipulation: direct attribute assignment (`sim.player.rings = 5`).
- No mocking. No patching. No private imports beyond constants for assertions.

## Helpers Rationale

`_place_buzzer`: Buzzer is the simplest enemy — stationary, no special behavior,
standard hitbox. Using it as the default test enemy avoids crab patrol timing and
chopper jump timing complications.

`_run_until_event`: Avoids magic frame counts in tests. Makes intent clear:
"run until this happens." Returns early, so tests don't waste frames.

`_run_frames`: Simple multi-step runner. Returns all events for filtering.

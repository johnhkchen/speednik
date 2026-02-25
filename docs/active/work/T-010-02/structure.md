# Structure — T-010-02: sim-step-and-event-system

## 1. Files Modified

### `speednik/simulation.py` — Primary change

**New imports** (added to existing import block):

```python
from speednik.enemies import (
    EnemyEvent,
    check_enemy_collision,
    update_enemies,
)
from speednik.objects import (
    CheckpointEvent as ObjCheckpointEvent,
    GoalEvent as ObjGoalEvent,
    LiquidEvent as ObjLiquidEvent,
    RingEvent as ObjRingEvent,
    SpringEvent as ObjSpringEvent,
    check_checkpoint_collision,
    check_goal_collision,
    check_ring_collection,
    check_spring_collision,
    update_liquid_zones,
    update_pipe_travel,
    update_spring_cooldowns,
)
from speednik.physics import InputState
from speednik.player import PlayerState, player_update
```

**New function**: `sim_step(sim: SimState, inp: InputState) -> list[Event]`

Located after the `create_sim` factory, before module end. ~50 lines.

Internal structure:
1. Death guard block (check `player.state == DEAD`, set flags, return early)
2. `player_update()` call
3. Frame increment
4. Event collection loop (ring → spring → checkpoint → pipe → liquid → enemies → spring cooldowns)
5. Goal collision check
6. Metrics update
7. Return events

**No new classes or dataclasses** — all event types already exist from T-010-01.

### `tests/test_simulation.py` — Test additions

New test functions appended to the existing file:

- `test_sim_step_hold_right_advances_player()` — 60 frames, hold right, x increases
- `test_sim_step_frame_counter_increments()` — N steps, frame == N
- `test_sim_step_death_detection()` — manually kill player, step, assert DeathEvent + flags
- `test_sim_step_death_persistent()` — dead player stays dead on subsequent steps
- `test_sim_step_ring_collection()` — position near ring, step, assert RingCollectedEvent
- `test_sim_step_spring_collision()` — position near spring, step, assert SpringEvent
- `test_sim_step_checkpoint_collision()` — position near checkpoint, assert CheckpointEvent
- `test_sim_step_goal_detection()` — position near goal, step, assert GoalReachedEvent + flag
- `test_sim_step_max_x_tracking()` — verify max_x_reached updates
- `test_sim_step_rings_collected_metric()` — verify rings_collected counter
- `test_sim_step_enemy_damage()` — position near enemy, step, assert DamageEvent
- `test_sim_step_enemy_update()` — verify enemies move (crab patrol changes x)
- `test_sim_step_order_matches_main()` — structural test: verify function calls exist in order

## 2. Files NOT Modified

- `speednik/main.py` — No changes. sim_step mirrors but doesn't modify main.py.
- `speednik/objects.py` — No changes. All functions used as-is.
- `speednik/enemies.py` — No changes. All functions used as-is.
- `speednik/physics.py` — No changes.
- `speednik/player.py` — No changes.
- `tests/harness.py` — Not modified. sim_step replaces its role for full-game testing.

## 3. Module Boundaries

```
speednik/simulation.py
├── Event types (existing): RingCollectedEvent, DamageEvent, DeathEvent, etc.
├── SimState (existing): Complete headless state
├── create_sim() (existing): Factory
└── sim_step() (NEW): Frame advance
    ├── Calls: player_update (from player.py)
    ├── Calls: check_ring_collection, check_spring_collision, etc. (from objects.py)
    ├── Calls: update_enemies, check_enemy_collision (from enemies.py)
    └── Returns: list[Event] (translated from game core events)
```

## 4. Public Interface After This Ticket

```python
# speednik/simulation.py exports:
SimState                # dataclass
Event                   # type union
RingCollectedEvent      # dataclass
DamageEvent             # dataclass
DeathEvent              # dataclass
SpringEvent             # dataclass (note: shadows objects.SpringEvent via alias)
GoalReachedEvent        # dataclass
CheckpointEvent         # dataclass (note: shadows objects.CheckpointEvent via alias)
create_sim(stage_name)  # factory → SimState
sim_step(sim, inp)      # NEW: frame advance → list[Event]
```

Downstream consumers (gym env, scenario runner) import only from `speednik.simulation`.
They never import from `objects.py` or `enemies.py` directly.

## 5. Ordering Constraints

The sim_step implementation must follow the exact sequence from main.py _update_gameplay.
This is a hard constraint. The order within sim_step:

```
1. Death guard        → DeathEvent
2. player_update      → (side effects on player)
3. frame += 1
4. ring collection    → RingCollectedEvent
5. spring collision   → SpringEvent
6. checkpoint         → CheckpointEvent
7. pipe travel        → (side effects only)
8. liquid zones       → DamageEvent
9. update_enemies     → (side effects on enemies)
10. enemy collision   → DamageEvent
11. spring cooldowns  → (side effects on springs)
12. goal collision    → GoalReachedEvent
13. metrics update
```

## 6. Test File Organization

Tests grouped by concern in test_simulation.py:
- Existing tests: `create_sim`, event types, no-pyxel, defaults (unchanged)
- New section header: `# sim_step — frame advance`
- Smoke tests first (hold_right)
- Then per-feature tests (rings, springs, checkpoints, enemies, goal, death)
- Then metrics tests
- Then structural/ordering tests

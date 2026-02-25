# Design — T-010-02: sim-step-and-event-system

## 1. Core Decision: Event Translation Strategy

### Option A: Translate game core events to simulation events
`sim_step` calls game core functions (which return `RingEvent`, `SpringEvent`, etc.), then maps
each to the corresponding simulation event type (`RingCollectedEvent`, `SpringEvent`, etc.).

**Pros**: Clean separation — simulation has its own event vocabulary. Callers never see game
core internals.
**Cons**: Name collision between `simulation.SpringEvent` (dataclass) and `objects.SpringEvent`
(enum) requires import aliasing. Extra translation boilerplate.

### Option B: Return game core events directly
Change `Event` union to include the existing enum types from `objects.py` and `enemies.py`.
`sim_step` just returns whatever the game core functions return.

**Pros**: Zero translation code, no name collisions if we drop the simulation dataclasses.
**Cons**: Leaks game core internals into the simulation API. Callers must know about
`RingEvent.COLLECTED`, `EnemyEvent.PLAYER_DAMAGED`, etc. Tighter coupling.

### Option C: Hybrid — translate only where semantically distinct
Keep the simulation event dataclasses for the "big" events (death, goal, damage) that callers
care about, but include game core enums in the Event union for lower-level events.

**Cons**: Inconsistent API — some events are dataclasses, some are enums.

### Decision: **Option A — Full Translation**

Rationale:
- The spec (§2.3) explicitly defines simulation-specific event types.
- T-010-01 already created the dataclass event types — they exist in the codebase.
- The simulation layer is meant to be a clean API boundary (Layer 2 in the architecture).
- Name collision is trivially solved with import aliases (`from speednik.objects import SpringEvent as ObjSpringEvent`).
- Translation is ~15 lines of straightforward mapping.

## 2. Death Detection Approach

### Option A: Check at top of sim_step (matches main.py)
If `player.state == DEAD` at the start of the frame, return `[DeathEvent()]`, set flags, and
don't run physics. This mirrors main.py's early return.

### Option B: Check after enemy collision
Detect death *after* the collision that causes it, within the same frame.

### Decision: **Option A — Check at top**

Rationale:
- Main.py checks at the top (line 345). Order must match.
- Death from enemy collision on frame N means the player enters DEAD state on frame N. The
  DEAD state is detected at the top of frame N+1. This is how main.py works.
- The ticket spec confirms: "Check if player is dead → return DeathEvent, set player_dead" is
  step 1 in the sequence.

**Additional**: On the frame where death is first detected, set `sim.player_dead = True` and
increment `sim.deaths`. On subsequent frames, still return early with `[DeathEvent()]` — the
player stays dead until the caller resets.

## 3. Metrics Update Location

Update `max_x_reached` and `rings_collected` at the end of each non-dead frame, after all
collision processing. This matches the spec's step 13 and ensures metrics reflect the
current frame's events.

## 4. Import Aliasing Strategy

The simulation module already defines `SpringEvent` and `CheckpointEvent` as dataclasses.
The objects module exports identically-named enums. Solution:

```python
from speednik.objects import (
    RingEvent as ObjRingEvent,
    SpringEvent as ObjSpringEvent,
    CheckpointEvent as ObjCheckpointEvent,
    GoalEvent as ObjGoalEvent,
    LiquidEvent as ObjLiquidEvent,
    PipeEvent as ObjPipeEvent,
    check_ring_collection,
    check_spring_collision,
    check_checkpoint_collision,
    update_pipe_travel,
    update_liquid_zones,
    update_spring_cooldowns,
    check_goal_collision,
)
from speednik.enemies import (
    EnemyEvent,
    check_enemy_collision,
    update_enemies,
)
```

## 5. Event Mapping Table

```python
# Ring events
ObjRingEvent.COLLECTED     → RingCollectedEvent()
ObjRingEvent.EXTRA_LIFE    → (skip — tracked via player.lives)

# Spring events
ObjSpringEvent.LAUNCHED    → SpringEvent()

# Checkpoint events
ObjCheckpointEvent.ACTIVATED → CheckpointEvent()

# Enemy events
EnemyEvent.PLAYER_DAMAGED  → DamageEvent()
EnemyEvent.DESTROYED       → (skip — internal detail)
EnemyEvent.BOUNCE          → (skip — internal detail)
EnemyEvent.SHIELD_BREAK    → (skip — internal detail)
EnemyEvent.BOSS_HIT        → (skip — internal detail)
EnemyEvent.BOSS_DEFEATED   → (skip — could add later)

# Liquid events
ObjLiquidEvent.DAMAGE      → DamageEvent()
ObjLiquidEvent.STARTED_RISING → (skip — audio only)

# Goal
ObjGoalEvent.REACHED       → GoalReachedEvent()

# Death (detected at frame start, not from game core events)
player.state == DEAD        → DeathEvent()
```

## 6. Pipe/Liquid Events in sim_step

`update_pipe_travel()` is called for side effects only. Its `PipeEvent` return values are not
translated to simulation events (no corresponding type in the Event union, and pipe events are
internal transport mechanics, not observable game outcomes).

`update_liquid_zones()` produces `LiquidEvent.DAMAGE` which maps to `DamageEvent()`. The
`STARTED_RISING` event is audio-only; skip.

## 7. sim_step Pseudo-Code

```
def sim_step(sim, inp):
    # 1. Death guard
    if player.state == DEAD:
        if not sim.player_dead:  # first detection
            sim.player_dead = True
            sim.deaths += 1
        return [DeathEvent()]

    # 2. Player physics
    player_update(player, inp, tile_lookup)

    # 3. Frame counter
    sim.frame += 1

    # 4-12. Object/enemy processing (exact main.py order)
    events = []
    ... ring collection → RingCollectedEvent
    ... spring collision → SpringEvent
    ... checkpoint collision → CheckpointEvent
    ... pipe travel (side effects only)
    ... liquid zones → DamageEvent
    ... update_enemies
    ... check_enemy_collision → DamageEvent
    ... spring cooldowns

    # 13. Goal collision
    if goal reached:
        sim.goal_reached = True
        events.append(GoalReachedEvent())

    # 14. Metrics
    sim.max_x_reached = max(sim.max_x_reached, player.physics.x)
    sim.rings_collected += count of RingCollectedEvent in events

    return events
```

## 8. Test Strategy

- **Smoke test**: 60 frames hold_right on hillside, assert x increases.
- **Ring collection**: Position player near a known ring, step once, assert RingCollectedEvent.
- **Death detection**: Create sim, kill player manually, step, assert DeathEvent + flags.
- **Goal detection**: Position player near goal, step, assert GoalReachedEvent + flag.
- **Frame counter**: Step N times, assert sim.frame == N.
- **Metrics**: Step and verify max_x_reached updates.
- **No Pyxel**: Already tested by existing test.

## 9. Rejected Alternatives

- **Returning raw game core events**: Rejected for coupling reasons (Option B above).
- **Adding PipeEvent/LiquidEvent to simulation Event union**: Not needed by any downstream
  consumer (gym env, scenario runner). YAGNI.
- **Auto-respawn in sim_step**: Rejected per ticket spec. Caller controls lifecycle.
- **Checking death after enemy collision in same frame**: Doesn't match main.py order.

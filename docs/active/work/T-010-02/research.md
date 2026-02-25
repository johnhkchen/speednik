# Research — T-010-02: sim-step-and-event-system

## 1. Ticket Objective

Implement `sim_step()` in `speednik/simulation.py` — the function that advances the headless
simulation by one frame. It mirrors `main.py:_update_gameplay()` without rendering or audio.
Returns a list of `Event` objects. This is the core of Layer 2 in the scenario testing system.

## 2. Source of Truth: `main.py:_update_gameplay()` (lines 343–441)

The exact sequence in `_update_gameplay()`:

1. **Death guard** (343–357): If `player.state == DEAD`, increment `death_timer`, handle
   respawn/game-over after `DEATH_DELAY_FRAMES`. Returns early — no physics run.
2. **Input** (360): `_read_input()` → `InputState` (Pyxel-specific, replaced by caller-provided input).
3. **Player update** (361): `player_update(player, inp, tile_lookup)`.
4. **Timer** (362): `self.timer_frames += 1`.
5. **Ring collection** (365–371): `check_ring_collection(player, rings)` → SFX on events.
6. **Spring collision** (374–376): `check_spring_collision(player, springs)` → SFX.
7. **Checkpoint collision** (379–382): `check_checkpoint_collision(player, checkpoints)` → SFX.
8. **Pipe travel** (385): `update_pipe_travel(player, pipes)`.
9. **Liquid zones** (388–392): `update_liquid_zones(player, liquid_zones)` → SFX.
10. **Enemy update** (395): `update_enemies(enemies)`.
11. **Enemy collision** (396–416): `check_enemy_collision(player, enemies)` → SFX, death_timer
    reset on PLAYER_DAMAGED leading to DEAD, boss_defeated flag.
12. **Spring cooldowns** (419): `update_spring_cooldowns(springs)`.
13. **Boss music trigger** (422–427): Stage-3-specific, audio only — **skip in headless**.
14. **Goal collision** (430–436): `check_goal_collision(player, goal_x, goal_y)` → on REACHED,
    transition to results state.
15. **Lives sync** (439): `self.lives = self.player.lives`.
16. **Camera update** (442): `camera_update(camera, player, inp)` — **skip in headless**.

## 3. Existing Simulation Module (`speednik/simulation.py`)

T-010-01 delivered:
- `SimState` dataclass with all needed fields (player, tile_lookup, entity lists, goal coords,
  level dimensions, frame counter, metrics, terminal flags).
- `create_sim(stage_name)` factory that loads a stage and populates SimState. Boss injection for
  skybridge included.
- Event types: `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`,
  `GoalReachedEvent`, `CheckpointEvent`.
- `Event` type union.
- No `sim_step()` function yet — that's this ticket.

## 4. Game Core Functions (all Pyxel-free)

### `player_update(player, inp, tile_lookup)` — player.py:109
Full frame update: pre-physics state machine → physics steps 1–4 → collision → slip timer →
post-physics sync → invulnerability → scattered rings → ring recollection → animation.
Handles DEAD state (early return), pipe travel (early return), HURT (skip input but runs physics).

### `check_ring_collection(player, rings)` — objects.py:208
Returns `list[RingEvent]`. Events: `COLLECTED`, `EXTRA_LIFE`. Skips if DEAD/HURT.
Mutates: `ring.collected = True`, `player.rings += 1`, `player.lives += 1`.

### `check_spring_collision(player, springs)` — objects.py:245
Returns `list[SpringEvent]`. Events: `LAUNCHED`. Skips if DEAD/HURT.
Mutates: player velocity, spring cooldown.

### `check_checkpoint_collision(player, checkpoints)` — objects.py:302
Returns `list[CheckpointEvent]`. Events: `ACTIVATED`. Skips if DEAD/HURT.
Mutates: `cp.activated`, player respawn data.

### `update_pipe_travel(player, pipes)` — objects.py:333
Returns `list[PipeEvent]`. Handles entry/travel/exit.
Mutates: player position/velocity, `player.in_pipe`.

### `update_liquid_zones(player, zones)` — objects.py:411
Returns `list[LiquidEvent]`. Events: `STARTED_RISING`, `DAMAGE`.
Mutates: zone activation/rise, calls `damage_player()`.

### `update_enemies(enemies)` — enemies.py:151
No return value. Updates crab patrol, chopper jump, egg piston state machine.

### `check_enemy_collision(player, enemies)` — enemies.py:273
Returns `list[EnemyEvent]`. Events: `DESTROYED`, `BOUNCE`, `PLAYER_DAMAGED`, `SHIELD_BREAK`,
`BOSS_HIT`, `BOSS_DEFEATED`. Skips if DEAD/HURT.
Mutates: enemy.alive, player damage, boss HP.

### `update_spring_cooldowns(springs)` — objects.py:291
No return value. Decrements cooldown timers.

### `check_goal_collision(player, goal_x, goal_y)` — objects.py:452
Returns `GoalEvent | None`. Events: `REACHED`. Skips if DEAD/HURT.

## 5. Event System Mapping

The spec's event types (`simulation.py`) differ from the game core's enums (`objects.py`,
`enemies.py`). The sim_step must translate:

| Game Core Event              | Simulation Event       |
|------------------------------|------------------------|
| `RingEvent.COLLECTED`        | `RingCollectedEvent()` |
| `RingEvent.EXTRA_LIFE`       | (no separate sim event — rings_collected metric suffices) |
| `SpringEvent.LAUNCHED`       | `SpringEvent()`        |
| `CheckpointEvent.ACTIVATED`  | `CheckpointEvent()`    |
| `EnemyEvent.PLAYER_DAMAGED`  | `DamageEvent()`        |
| `EnemyEvent.DESTROYED`       | (no separate sim event needed for basic sim) |
| `EnemyEvent.BOUNCE`          | (no separate sim event needed) |
| `EnemyEvent.BOSS_HIT`        | (no separate sim event needed) |
| `EnemyEvent.BOSS_DEFEATED`   | (could map but not in current Event union) |
| `GoalEvent.REACHED`          | `GoalReachedEvent()`   |
| Player DEAD state detected   | `DeathEvent()`         |
| `LiquidEvent.DAMAGE`         | `DamageEvent()`        |

**Name collision**: `simulation.SpringEvent` and `simulation.CheckpointEvent` shadow the
`objects.py` enum names. Need import aliasing or renaming.

## 6. Death Handling Differences

`main.py` has a death timer + respawn/game-over logic. The spec says headless sim should:
- Set `sim.player_dead = True` and increment `sim.deaths`.
- NOT auto-respawn — caller decides.
- Return `DeathEvent` when death is first detected.

This means `sim_step` checks `player.state == DEAD` at the top, sets flags, and returns early
with `[DeathEvent()]`. No further physics or collision on dead frames. Matches main.py's early
return pattern.

## 7. Metrics Tracking

Per spec §2.3:
- `sim.max_x_reached = max(sim.max_x_reached, player.physics.x)`
- `sim.rings_collected += count of RingEvent.COLLECTED in this frame`

These update at the end of each non-dead frame.

## 8. Test Infrastructure

Existing tests (`test_simulation.py`) cover `create_sim` and event type instantiation.
No `sim_step` tests yet. The acceptance criteria require:
- 60 frames of hold_right on hillside → player x increases.
- Full pytest suite passes.
- No Pyxel imports.

The harness (`tests/harness.py`) provides `hold_right()` strategy returning `InputState(right=True)`.
For `sim_step` tests, we just pass `InputState(right=True)` directly.

## 9. Pipe and Liquid Events

`update_pipe_travel` returns `list[PipeEvent]` but the current `Event` union doesn't include
a pipe event type. The spec's reference code doesn't show pipe events being collected either.
We should still call `update_pipe_travel` for its side effects (player position mutation) but
can ignore its return events for the `Event` list, OR add a `PipeEvent` to the union.

`update_liquid_zones` returns `list[LiquidEvent]`. `LiquidEvent.DAMAGE` should map to
`DamageEvent()`. `LiquidEvent.STARTED_RISING` is audio-only — no sim event needed.

## 10. Boss-Specific Concerns

The boss state machine (`_update_egg_piston`) runs purely on frame timers. No Pyxel dependency.
The boss music trigger (lines 422–427 in main.py) is audio-only — skip in headless.
`EnemyEvent.BOSS_DEFEATED` sets a flag in main.py but doesn't have a corresponding sim event
in the current union. Could add one or just track via enemy.alive status.

## 11. Key Constraints

- **Order must match main.py exactly** — physics/collision outcomes will diverge otherwise.
- **No Pyxel imports** — already enforced by existing test.
- **Deterministic** — same inputs → same outputs, frame-perfectly reproducible.
- `sim_step` must be callable repeatedly; caller controls the loop.

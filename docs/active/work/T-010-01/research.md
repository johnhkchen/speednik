# Research — T-010-01: SimState and create_sim

## Scope

Build `SimState` dataclass + `create_sim()` factory + event types in `speednik/simulation.py`.
This is Layer 2 of the scenario testing architecture — headless game state without Pyxel.

## Existing Stage Loading Pipeline

### `speednik/level.py`

- `load_stage(stage_name: str) -> StageData` loads from `speednik/stages/{name}/` JSON files.
- `StageData` fields: `tile_lookup`, `tiles_dict`, `entities`, `player_start`, `checkpoints`, `level_width`, `level_height`.
- `tile_lookup` is a closure `Callable[[int, int], Optional[Tile]]` created inline in `load_stage`.
- Three stages recognized: `"hillside"`, `"pipeworks"`, `"skybridge"`.

### `speednik/main.py:_load_stage()` (lines 287–337)

The authoritative entity loading sequence. This is what `create_sim` must mirror:

1. `load_stage(stage_name)` → `StageData`
2. `create_player(sx, sy)` from `stage.player_start`
3. `load_rings(stage.entities)` → `list[Ring]`
4. `load_springs(stage.entities)` → `list[Spring]`
5. `load_checkpoints(stage.entities)` → `list[Checkpoint]`
6. `load_pipes(stage.entities)` → `list[LaunchPipe]`
7. `load_liquid_zones(stage.entities)` → `list[LiquidZone]`
8. `load_enemies(stage.entities)` → `list[Enemy]`
9. Goal extraction: iterate `stage.entities` for `type == "goal"`, take first match `(x, y)`.
10. Stage 3 boss injection: if `stage_num == 3`, append `load_enemies([{"type": "enemy_egg_piston", "x": BOSS_SPAWN_X, "y": BOSS_SPAWN_Y}])`.

**Key difference**: `_load_stage` takes a `stage_num` (1, 2, 3) and maps to name via `_STAGE_LOADER_NAMES`. `create_sim` takes a `stage_name` string directly.

### Boss injection trigger

In `main.py`, boss injection is keyed on `stage_num == 3`. The mapping is:
- `1 → "hillside"`, `2 → "pipeworks"`, `3 → "skybridge"`

`create_sim` receives a string name, so must detect `stage_name == "skybridge"` for boss injection.

## Entity Types and Imports

All from `speednik/objects.py`:
- `Ring`, `Spring`, `Checkpoint`, `LaunchPipe`, `LiquidZone`
- `load_rings`, `load_springs`, `load_checkpoints`, `load_pipes`, `load_liquid_zones`
- Event enums: `RingEvent`, `SpringEvent`, `CheckpointEvent`, `PipeEvent`, `GoalEvent`, `LiquidEvent`

From `speednik/enemies.py`:
- `Enemy`
- `load_enemies`
- `EnemyEvent`

From `speednik/player.py`:
- `Player`, `PlayerState`, `create_player`

From `speednik/physics.py`:
- `InputState`, `PhysicsState`

From `speednik/terrain.py`:
- `TileLookup`

From `speednik/level.py`:
- `load_stage`

From `speednik/constants.py`:
- `BOSS_SPAWN_X = 4800.0`, `BOSS_SPAWN_Y = 480.0`

## Stage Entity Data

### Verified per-stage entity types:
- **hillside**: checkpoint, enemy_buzzer, enemy_crab, goal, player_start, ring, spring_up
- **pipeworks**: checkpoint, enemy_buzzer, enemy_chopper, enemy_crab, goal, liquid_trigger, pipe_h, player_start, ring, spring_right, spring_up
- **skybridge**: checkpoint, enemy_buzzer, enemy_crab, goal, player_start, ring, spring_up

All three stages have exactly one `goal` entity.

### Goal coordinates:
- hillside: `(4758, 642)`
- pipeworks: `(5558, 782)`
- skybridge: `(5158, 482)`

## Event Types (ticket spec)

The ticket defines a parallel set of event dataclasses for `sim_step` (T-010-02):
- `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`, `GoalReachedEvent`, `CheckpointEvent`
- Union type: `Event = RingCollectedEvent | DamageEvent | ...`

These are distinct from the existing enum-based events (`RingEvent`, `SpringEvent`, etc.) in `objects.py`/`enemies.py`. The spec in `scenario-testing-system.md` §2.3 `sim_step` actually uses the existing enum events (`RingEvent.COLLECTED`, `GoalEvent.REACHED`), not new dataclasses.

**Tension**: The ticket body defines new dataclass events. The spec uses existing enums. The existing enums are already Pyxel-free and work fine for headless use.

## Existing Test Infrastructure

### `tests/harness.py`
- Player-only simulation: `player_update` + `tile_lookup`, no objects/enemies.
- Strategies are `Callable[[int, Player], InputState]`.
- `run_on_stage(stage_name, strategy, frames)` loads stage and runs.
- No imports from Pyxel.

### Existing tests that load stages:
- `tests/test_harness.py` — uses `run_on_stage` for physics tests.
- `tests/test_hillside_integration.py` — integration tests with real stage data.

## Constraints

1. **No Pyxel imports** — critical requirement. All source modules used (`level.py`, `objects.py`, `enemies.py`, `player.py`, `physics.py`, `terrain.py`) are already Pyxel-free.
2. **Single new file**: `speednik/simulation.py`.
3. **Deterministic**: Given same stage and inputs, must produce identical results.
4. `tiles_dict` is NOT needed for SimState — only `tile_lookup` is needed for physics. `tiles_dict` is only used by `renderer.draw_terrain()`.
5. `level_width` and `level_height` come from `StageData.level_width/level_height`.

## Open Questions

1. Should `create_sim` accept `stage_name` only, or also stage number? Ticket says `stage_name: str`.
2. The spec shows `create_sim` doesn't take a `stage_num` — so boss injection must use name matching.
3. Event dataclass types: define them as per ticket spec even though `sim_step` (T-010-02) will decide how to use them.

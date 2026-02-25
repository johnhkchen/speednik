# Structure — T-010-01: SimState and create_sim

## Files Created

### `speednik/simulation.py`

New module. The headless simulation layer (Layer 2).

**Sections in order:**

1. **Imports** — from `level`, `physics`, `player`, `terrain`, `objects`, `enemies`, `constants`. No Pyxel.

2. **Event dataclasses** — Six `@dataclass` types:
   - `RingCollectedEvent`
   - `DamageEvent`
   - `DeathEvent`
   - `SpringEvent`
   - `GoalReachedEvent`
   - `CheckpointEvent`
   - Type alias: `Event = RingCollectedEvent | DamageEvent | DeathEvent | SpringEvent | GoalReachedEvent | CheckpointEvent`

3. **SimState dataclass** — All fields from ticket spec:
   ```
   player, tile_lookup, rings, springs, checkpoints, pipes,
   liquid_zones, enemies, goal_x, goal_y, level_width, level_height,
   frame, max_x_reached, rings_collected, deaths, goal_reached, player_dead
   ```

4. **create_sim factory** — `def create_sim(stage_name: str) -> SimState:`
   - Calls `load_stage(stage_name)`
   - Creates player from `stage.player_start`
   - Loads all entity types from `stage.entities`
   - Extracts goal position from entities (first `type == "goal"`)
   - Injects boss for skybridge stage
   - Returns populated `SimState`

### `tests/test_simulation.py`

New test file.

**Test functions:**

1. `test_create_sim_hillside` — Validates all fields populated for hillside.
2. `test_create_sim_pipeworks` — Pipeworks loads successfully, has pipes and liquid zones.
3. `test_create_sim_skybridge` — Skybridge loads, boss enemy present.
4. `test_goal_positions` — Goal coordinates match known entity data for each stage.
5. `test_skybridge_boss_injection` — Enemy list contains enemy_egg_piston for skybridge only.
6. `test_entity_lists_populated` — Rings, springs, enemies non-empty for hillside.
7. `test_event_types` — Event dataclasses instantiable, union type works.
8. `test_no_pyxel_import` — `simulation.py` module source has no `import pyxel` / `from pyxel`.

## Files Modified

None. This is a new module with no changes to existing files.

## Module Boundaries

### Public interface of `speednik/simulation.py`:
- `SimState` — dataclass, exported
- `create_sim` — factory function, exported
- `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`, `GoalReachedEvent`, `CheckpointEvent` — event types, exported
- `Event` — type alias, exported

### Dependencies (all downward into Layer 1):
```
simulation.py
  ├── level.py (load_stage)
  ├── player.py (Player, create_player)
  ├── physics.py (InputState — for Event type hints only)
  ├── terrain.py (TileLookup — type annotation only)
  ├── objects.py (Ring, Spring, Checkpoint, LaunchPipe, LiquidZone, load_*)
  ├── enemies.py (Enemy, load_enemies)
  └── constants.py (BOSS_SPAWN_X, BOSS_SPAWN_Y)
```

No upward dependencies. No lateral dependencies on `main.py`, `renderer.py`, or `audio.py`.

## Ordering

1. Write `speednik/simulation.py` (event types → SimState → create_sim).
2. Write `tests/test_simulation.py`.
3. Run tests to verify.

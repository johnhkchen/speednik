# Plan — T-010-01: SimState and create_sim

## Step 1: Create `speednik/simulation.py` with event types

Write the six event dataclasses and the `Event` union type alias.

**Verification**: Import the module, instantiate each event type.

## Step 2: Add SimState dataclass

Add the `SimState` dataclass with all 18 fields from the ticket spec.
Import `Player`, `TileLookup`, and all entity types.

**Verification**: `SimState` is importable, can be constructed with all required fields.

## Step 3: Implement `create_sim` factory

Implement the full entity loading sequence mirroring `main.py:_load_stage()`:
1. `load_stage(stage_name)` to get StageData
2. `create_player(sx, sy)` from player_start
3. Load all entity types from `stage.entities`
4. Extract goal from entities (first `type == "goal"`, default `(0.0, 0.0)`)
5. Boss injection: `if stage_name == "skybridge"`, append egg_piston enemy
6. Construct and return `SimState`

**Verification**: `create_sim("hillside")` returns a SimState with populated fields.

## Step 4: Write `tests/test_simulation.py`

Test cases:
1. **test_create_sim_hillside**: Load hillside, assert player exists, tile_lookup callable,
   entity lists populated (rings > 0, springs > 0, enemies > 0), goal position = (4758, 642),
   level dimensions > 0, frame = 0, metric accumulators = 0.
2. **test_create_sim_pipeworks**: Load pipeworks, assert pipes non-empty, liquid_zones non-empty,
   goal = (5558, 782).
3. **test_create_sim_skybridge**: Load skybridge, assert goal = (5158, 482).
4. **test_skybridge_boss_injection**: Assert skybridge enemy list contains `enemy_egg_piston`.
   Assert hillside does NOT contain `enemy_egg_piston`.
5. **test_entity_lists_populated**: Hillside has rings, springs, checkpoints, enemies.
6. **test_event_types_instantiable**: Construct each event type, verify isinstance checks,
   verify union type annotation.
7. **test_no_pyxel_import**: Read `simulation.py` source, assert `"import pyxel"` and
   `"from pyxel"` not in source.
8. **test_sim_state_defaults**: Construct SimState, verify default values (frame=0,
   max_x_reached=0.0, rings_collected=0, deaths=0, goal_reached=False, player_dead=False).

**Verification**: `uv run pytest tests/test_simulation.py -x` all pass.

## Step 5: Run full test suite

Run `uv run pytest tests/ -x` to ensure no regressions.

**Verification**: All existing tests pass.

## Testing Strategy

- **Unit tests**: Event type instantiation, SimState defaults.
- **Integration tests**: `create_sim` with real stage data (hillside, pipeworks, skybridge).
  These exercise the full loading pipeline including JSON parsing, tile building, entity extraction.
- **Contract test**: No Pyxel import in simulation.py source.
- All tests are deterministic — no randomness, no timing, no external dependencies.

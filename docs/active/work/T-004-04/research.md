# T-004-04 Research: Integration and Full Game Loop

## Current State

The codebase is feature-complete at the subsystem level. All core modules exist and are independently tested (494 tests, 0 failures). The game state machine (T-004-03) already wires most systems together in `main.py`. This ticket is the final integration pass.

## What Exists

### Module Inventory

| Module | Lines | Purpose | Test Coverage |
|--------|-------|---------|---------------|
| `main.py` | 564 | Game state machine, entry point | `test_game_state.py` (15 tests) |
| `physics.py` | 353 | Sonic 2 physics engine | `test_physics.py` (15 tests) |
| `terrain.py` | 757 | Tile collision, sensors | `test_terrain.py` (50+ tests) |
| `player.py` | 397 | Player state, damage, animation | `test_player.py` (20+ tests) |
| `camera.py` | 170 | Sonic 2 camera | `test_camera.py` (20+ tests) |
| `renderer.py` | 571 | Geometric art rendering | `test_renderer.py` (30+ tests) |
| `audio.py` | 688 | SFX + music engine | (standalone test mode) |
| `enemies.py` | 382 | Enemy types, boss | `test_enemies.py` (40+ tests) |
| `objects.py` | 466 | Rings, springs, pipes, etc. | `test_game_objects.py` (40+ tests) |
| `constants.py` | 137 | All game constants | (used everywhere) |

### Stage Loaders

Three identical-pattern loaders: `hillside.py`, `pipeworks.py`, `skybridge.py`. All read from `{stage_name}/tile_map.json`, `collision.json`, `entities.json`, `meta.json`. Return `StageData` dataclass.

`StageData` is defined in `hillside.py` and imported by the other two. Fields: `tile_lookup`, `tiles_dict`, `entities`, `player_start`, `checkpoints`, `level_width`, `level_height`.

### Stage JSON Data

All three stages have pipeline-generated JSON data present. Each stage directory contains: `tile_map.json`, `collision.json`, `meta.json`. The `entities.json` files contain rings, enemies, springs, checkpoints, pipes, liquid zones, and goal posts as needed per stage.

### Game State Machine (T-004-03)

`main.py` already implements:
- 5 states: TITLE → STAGE_SELECT → GAMEPLAY → RESULTS → GAME_OVER
- Stage loading via `_load_stage()` → reads pipeline JSON, creates player/camera/objects/enemies
- Full gameplay loop: physics, collision, rings, springs, checkpoints, pipes, liquid, enemies, boss, goal
- Death/respawn/lives system
- Audio integration: all 7 music tracks, all 16 SFX
- Rendering: terrain, player, enemies, objects, HUD, particles
- Boss injection for Stage 3

## Gap Analysis vs. Acceptance Criteria

### AC1: `level.py` loads stage data from pipeline output
**Status: Missing.** The specification §1 lists `level.py` as a module. Currently, stage loading lives in the three `stages/*.py` loader files. The `StageData` dataclass is in `hillside.py`. There is no unified `level.py` module.

The acceptance criteria explicitly require `level.py` to "load stage data from pipeline output (tile_map.json, collision.json, entities.json, meta.json) and construct the runtime level representation." Currently `main.py._load_stage()` calls individual stage modules. A `level.py` would centralize this.

### AC2: All three stages playable start to finish
**Status: Functional.** `_load_stage()` loads real pipeline data for all 3 stages. The gameplay loop processes all systems. Needs verification that all three stages' entity data actually loads without errors — JSON files are present but entities.json content needs checking.

### AC3: Death, respawn, checkpoint, game over
**Status: Implemented in T-004-03.** `_update_gameplay()` handles death timer, `_respawn_player()` handles checkpoint respawn, lives decrement to game over. Needs integration test coverage.

### AC4: 100 rings = extra life
**Status: Implemented.** `check_ring_collection()` in `objects.py` handles threshold crossing. `_update_gameplay()` plays SFX_1UP and increments lives. Needs integration test.

### AC5: Camera tracks correctly across all geometries
**Status: Implemented.** `camera.py` handles horizontal borders, vertical focal point, look up/down, boundary clamping. Needs integration test with real stage dimensions.

### AC6: Audio plays correctly
**Status: Implemented.** All music/SFX wired in `_update_gameplay()` and state transitions. Needs verification of correct track-to-state mapping.

### AC7: No physics bugs
**Status: Implemented.** Physics engine follows spec §2.1–2.5 frame order. 494 tests pass. Edge cases in real stage geometry need end-to-end verification.

### AC8: Palette swaps per stage
**Status: Implemented.** `renderer.set_stage_palette()` called in `_load_stage()` with per-stage palette names. Three palettes defined in `renderer.py`.

### AC9: 60fps
**Status: Set.** `pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Speednik", fps=60)` in `App.__init__()`.

### AC10: `uv run python -m speednik.main` launches the game
**Status: Works.** Entry point exists. `if __name__ == "__main__": App()`.

## Key Integration Points

1. **`level.py` gap**: The only structural gap. Need to extract `StageData` and loading logic into a centralized module.
2. **`entities.json` for Stage 3 skybridge**: Needs verification that it includes guardian enemy and boss arena setup correctly. Boss is injected in code via `_load_stage()` when `stage_num == 3`.
3. **Duplication in stage loaders**: All three loaders are nearly identical (copy-paste with different `_DATA_DIR`). A unified `level.py` can eliminate this duplication.
4. **`StageData` location**: Currently in `hillside.py`, imported by `pipeworks.py` and `skybridge.py`. Belongs in `level.py`.

## Test Infrastructure

Tests use pytest, no Pyxel dependency (all game logic is Pyxel-free). Tests mock `pyxel` for rendering/audio tests. Integration tests can verify stage loading, entity parsing, and game state transitions without Pyxel initialization.

## Constraints

- No new dependencies needed
- Must preserve all 494 existing tests
- `StageData` is used by `main.py` and all three stage loaders — moving it requires updating imports
- `level.py` must match the spec's module listing
- Boss injection for Stage 3 happens in `main.py` code, not in stage data

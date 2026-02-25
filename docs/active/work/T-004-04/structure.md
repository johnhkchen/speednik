# T-004-04 Structure: Integration and Full Game Loop

## Files Created

### `speednik/level.py` (~70 lines)

New module matching specification §1.

**Public interface:**
- `StageData` dataclass (moved from `hillside.py`)
- `load_stage(stage_name: str) -> StageData` — unified loader

**Internal:**
- `_STAGES_DIR` — path to `speednik/stages/`
- `_DATA_DIRS` — maps stage name → data directory path
- `_read_json(path)` — JSON file reader
- `_build_tiles(tile_map, collision)` — constructs tile dict and lookup

### `tests/test_integration.py` (~200 lines)

Integration tests for the full game loop.

**Test classes:**
- `TestStageLoading` — each stage loads, returns valid StageData
- `TestEntityParsing` — each stage's entities contain expected types
- `TestPlayerLifecycle` — player creation, physics frame, state sync
- `TestDeathRespawnIntegration` — damage → death → respawn flow
- `TestExtraLife` — 100 ring threshold
- `TestBossIntegration` — Stage 3 boss injection and combat
- `TestGameStateFlow` — state transitions (logic only, no Pyxel)
- `TestCameraIntegration` — camera with real stage dimensions

## Files Modified

### `speednik/stages/hillside.py` (~15 lines)

- Remove `StageData` dataclass definition
- Import `StageData` and `load_stage` from `speednik.level`
- Simplify `load()` to delegate: `return load_stage("hillside")`
- Remove `_read_json()` and all tile-building logic

### `speednik/stages/pipeworks.py` (~10 lines)

- Remove `StageData` import from `hillside`
- Import `load_stage` from `speednik.level`
- Simplify `load()` to delegate: `return load_stage("pipeworks")`
- Remove `_read_json()` and all tile-building logic

### `speednik/stages/skybridge.py` (~10 lines)

- Same pattern as pipeworks

### `speednik/main.py` (~10 lines changed)

- Add import: `from speednik.level import load_stage`
- Replace `_STAGE_MODULES` dict with `_STAGE_LOADER_NAMES` mapping stage number → stage name string
- Update `_load_stage()` to call `load_stage(stage_name)` instead of `module.load()`
- Remove individual stage module imports (hillside, pipeworks, skybridge)

### `tests/test_game_state.py` (~2 lines changed)

- Update `TestStageDataExtension` import if needed (import from `speednik.level` instead of `speednik.stages.hillside`)

## Files Unchanged

All other source files and test files remain as-is. The 494 existing tests must continue to pass.

## Module Dependency Graph (Post-Change)

```
main.py
├── level.py (NEW) ─── terrain.py (for Tile, TileLookup)
├── player.py ─── physics.py, terrain.py
├── camera.py ─── player.py, physics.py
├── renderer.py ─── terrain.py (TILE_SIZE)
├── enemies.py ─── player.py, objects.py (aabb_overlap)
├── objects.py ─── player.py
├── audio.py (standalone)
└── constants.py (leaf)

stages/hillside.py ─── level.py (delegate)
stages/pipeworks.py ─── level.py (delegate)
stages/skybridge.py ─── level.py (delegate)
```

## Import Changes Summary

| File | Removed Import | Added Import |
|------|---------------|-------------|
| `main.py` | `stages.{hillside,pipeworks,skybridge}` | `level.load_stage` |
| `stages/hillside.py` | `terrain.{FULL,NOT_SOLID,TOP_ONLY,Tile,TileLookup}` | `level.{StageData,load_stage}` |
| `stages/pipeworks.py` | `stages.hillside.StageData`, `terrain.Tile` | `level.load_stage` |
| `stages/skybridge.py` | `stages.hillside.StageData`, `terrain.Tile` | `level.load_stage` |
| `test_game_state.py` | `stages.hillside.StageData` | `level.StageData` |

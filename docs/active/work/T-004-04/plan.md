# T-004-04 Plan: Integration and Full Game Loop

## Step 1: Create `speednik/level.py`

Write the new unified stage loader module:
- Move `StageData` dataclass from `hillside.py`
- Implement `load_stage(stage_name: str) -> StageData`
- Internal helpers: `_DATA_DIRS`, `_read_json()`, `_build_tiles()`

**Verify:** `from speednik.level import StageData, load_stage` imports cleanly.

## Step 2: Update stage loaders to delegate

Simplify all three stage loaders:
- `hillside.py`: remove StageData definition, import from level, delegate load()
- `pipeworks.py`: import from level, delegate load()
- `skybridge.py`: import from level, delegate load()

Keep `StageData` re-exported from `hillside.py` for backwards compatibility with existing tests.

**Verify:** `uv run python -m pytest tests/ -q` — all 494 tests pass.

## Step 3: Update `main.py` to use `level.py`

- Import `load_stage` from `speednik.level`
- Replace `_STAGE_MODULES` dict with `_STAGE_LOADER_NAMES` mapping
- Update `_load_stage()` method to call `load_stage(name)` directly
- Remove now-unused stage module imports

**Verify:** `uv run python -m pytest tests/ -q` — all 494 tests pass.

## Step 4: Update `test_game_state.py`

- Update `TestStageDataExtension` to import from `speednik.level`

**Verify:** `uv run python -m pytest tests/test_game_state.py -q` — all pass.

## Step 5: Write integration tests

Create `tests/test_integration.py` with comprehensive integration tests:

### TestStageLoading
- `test_load_hillside` — loads without error, has expected fields
- `test_load_pipeworks` — loads without error
- `test_load_skybridge` — loads without error
- `test_all_stages_have_tiles` — tiles_dict is non-empty
- `test_all_stages_have_entities` — entities list is non-empty
- `test_all_stages_have_goal` — each stage has a goal entity

### TestEntityParsing
- `test_hillside_has_rings` — ring entities present
- `test_pipeworks_has_pipes` — pipe entities present
- `test_skybridge_has_guardian` — guardian enemy present

### TestPlayerLifecycle
- `test_player_runs_on_stage_tiles` — create player at stage start, run physics frames with real tile_lookup
- `test_player_collects_ring_on_stage` — place player near a ring, verify collection

### TestDeathRespawnIntegration
- `test_death_and_respawn_cycle` — damage player with 0 rings, verify dead; create new player at respawn point

### TestExtraLife
- `test_100_rings_grants_extra_life` — set player.rings=99, collect 1 ring, verify lives incremented

### TestBossIntegration
- `test_stage3_boss_injection` — load stage 3 entities, add boss, verify boss enemy exists
- `test_boss_takes_damage` — simulate spindash collision with vulnerable boss

### TestCameraIntegration
- `test_camera_clamps_to_hillside_bounds` — create camera with hillside dimensions, verify clamping

**Verify:** `uv run python -m pytest tests/ -q` — all tests (old + new) pass.

## Step 6: Final verification

- Run full test suite: `uv run python -m pytest tests/ -q`
- Verify import: `uv run python -c "from speednik.level import StageData, load_stage; print('OK')"`
- Verify entry point: `uv run python -c "from speednik.main import App; print('Imports OK')"`

## Test Strategy

All tests are Pyxel-free. Game logic modules are designed to be testable without Pyxel initialization. Integration tests use real stage JSON data but don't initialize the Pyxel window.

- Unit tests: existing 494 tests cover individual subsystems
- Integration tests: new tests verify subsystems work together with real data
- No visual/manual testing required — all acceptance criteria are verifiable through code tests

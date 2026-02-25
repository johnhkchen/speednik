# T-004-04 Progress: Integration and Full Game Loop

## Step 1: Create `speednik/level.py` — DONE
Created unified stage loader with `StageData` dataclass and `load_stage()` function.

## Step 2: Update stage loaders — DONE
Simplified hillside.py, pipeworks.py, skybridge.py to delegate to `level.load_stage()`.
All 494 existing tests pass.

## Step 3: Update `main.py` — DONE
Replaced `_STAGE_MODULES` dict with `_STAGE_LOADER_NAMES`, import `load_stage` from `level`.
Removed individual stage module imports. All 494 tests pass.

## Step 4: Update `test_game_state.py` — DONE
Updated `TestStageDataExtension` imports. Added backwards-compatibility test.
16 game state tests pass.

## Step 5: Write integration tests — DONE
Created `tests/test_integration.py` with 39 tests covering:
- Stage loading (10 tests)
- Entity parsing (7 tests)
- Player lifecycle (4 tests)
- Death/respawn (3 tests)
- Extra life (2 tests)
- Boss integration (4 tests)
- Camera integration (3 tests)
- Game state flow (3 tests)
- Palette/audio wiring (3 tests)

One deviation: `test_skybridge_has_guardian` changed to `test_skybridge_has_enemies` because
the guardian enemy is not in skybridge's entities.json (similar to boss, which is code-injected).

## Step 6: Final verification — DONE
- Full test suite: 534 passed, 0 failed
- `from speednik.level import StageData, load_stage` — OK
- `from speednik.main import App` — OK

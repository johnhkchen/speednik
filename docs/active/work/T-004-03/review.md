# Review — T-004-03: Game State Machine

## Summary of Changes

### Files Modified (4)

| File | Change |
|------|--------|
| `speednik/constants.py` | +7 game-state constants (goal radius, death delay, results duration, game over delay, boss arena/spawn coords) |
| `speednik/main.py` | Complete rewrite: demo level → 5-state game state machine with real stage loading |
| `speednik/objects.py` | Added `GoalEvent` enum and `check_goal_collision()` function |
| `speednik/renderer.py` | Added `clear_particles()` public function |

### Files Modified (stage loaders, 3)

| File | Change |
|------|--------|
| `speednik/stages/hillside.py` | Added `tiles_dict` field to `StageData` dataclass, populated in `load()` |
| `speednik/stages/pipeworks.py` | Passed `tiles_dict=tiles` to StageData constructor |
| `speednik/stages/skybridge.py` | Removed duplicate `StageData` definition, imported from hillside, added `tiles_dict` |

### Files Created (1)

| File | Purpose |
|------|---------|
| `tests/test_game_state.py` | 15 tests for goal collision, StageData extension, death/respawn logic |

### Work Artifacts (5)

`docs/active/work/T-004-03/`: research.md, design.md, structure.md, plan.md, progress.md

## Acceptance Criteria Coverage

| Criterion | Status | Notes |
|-----------|--------|-------|
| TITLE state: title screen, "Press Start", any button → STAGE_SELECT | Done | Title music plays, Z/Return/Space advances |
| STAGE_SELECT: 3 stage options, arrows to select, confirm to start | Done | Only unlocked stages navigable, locked shown as "???" |
| Stage 1 initially unlocked, completing unlocks next | Done | `unlocked_stages` incremented on results auto-advance |
| GAMEPLAY: loads stage, runs all systems | Done | Full physics/collision/rendering/audio pipeline |
| RESULTS: time, ring count, score, auto-advance | Done | Time bonus + ring bonus, 5-second auto-advance |
| GAME_OVER: after losing all lives, game over music | Done | 6-second timer then return to title, lives reset to 3 |
| Lives system: start with 3, death → respawn | Done | 2-second death delay, respawn at checkpoint/start |
| 0 lives → GAME_OVER | Done | Transitions after death delay expires |
| Stage progression unlocks | Done | `unlocked_stages = max(unlocked_stages, active_stage + 1)` |
| Music transitions per state | Done | Title, per-stage, boss (Stage 3), clear jingle, game over jingle |
| Clean state reset on stage start | Done | New player, reset timer, clear particles, fresh object loading |
| Death preserves checkpoint ring count | Done | `respawn_rings` from checkpoint, restored on respawn |

## Test Coverage

**New tests:** 15 tests in `tests/test_game_state.py`

- Goal collision: 8 tests covering at-goal, near, far, boundary, dead/hurt player, diagonal
- StageData extension: 2 tests for field presence and ordering
- Death/respawn data: 4 tests for death trigger, lives preservation, ring scatter, respawn data
- GoalEvent enum: 1 test

**Total suite:** 494 tests, 0 failures, 0 regressions.

**Coverage gaps:**
- State machine transitions are not unit-tested in isolation (would require mocking Pyxel). The state dispatch logic is straightforward string routing with no complex branching.
- Stage loading integration (calling `hillside.load()` etc.) is tested indirectly via existing stage loader tests. The JSON file reads work — confirmed by test_hillside, test_pipeworks, test_skybridge.
- Results scoring (time bonus + ring bonus) is not tested. Formula is simple arithmetic.

## Open Concerns

1. **Boss spawn position hardcoded.** `BOSS_SPAWN_X=4800`, `BOSS_SPAWN_Y=480` are approximate based on the skybridge arena section. If the SVG pipeline changes arena geometry, these will need updating. Consider adding boss placement to skybridge's entities.json instead.

2. **No pause system.** The spec mentions ESC for pause, but the acceptance criteria don't list it. Currently Q quits the game (Pyxel convention). A pause overlay could be added as a follow-up.

3. **Game over is timer-only.** The AC mentions "Continue? prompt or return to TITLE" — the implementation uses timer-only return (no continue prompt). The game over screen shows "PRESS START" after a delay but doesn't actually check for input — it just returns on timer. This is a simplification; adding a continue prompt with limited continues could be a follow-up.

4. **Renderer private access.** `_draw_ring`, `_draw_goal`, `_ENTITY_DRAWERS` are accessed as private members from main.py. This matches the existing demo code pattern but could be cleaned up by making these public or adding a dispatch function.

5. **Lives sync.** Lives are synced between `App.lives` and `Player.lives` each frame. The player module handles extra lives from 100-ring threshold. This bidirectional sync works but is worth noting as a potential source of bugs if either side is modified independently.

## Architecture Notes

The state machine uses simple string dispatch (`self.state = "title"`, etc.) with method routing in `update()` and `draw()`. Each state has a dedicated `_update_*` and `_draw_*` method pair. Stage loading is centralized in `_load_stage()` which handles all initialization from pipeline data.

The demo level (`_build_demo_level`) is entirely removed. The game now boots to a title screen and loads real stages from the pipeline JSON data.

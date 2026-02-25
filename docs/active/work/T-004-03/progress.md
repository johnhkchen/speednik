# Progress — T-004-03: Game State Machine

## Completed Steps

### Step 1: Add Constants ✓
Added 7 new constants to `speednik/constants.py`:
- `GOAL_ACTIVATION_RADIUS`, `DEATH_DELAY_FRAMES`, `RESULTS_DURATION`
- `GAMEOVER_DELAY`, `BOSS_ARENA_START_X`, `BOSS_SPAWN_X`, `BOSS_SPAWN_Y`

### Step 2: Extend StageData and Fix Loaders ✓

**2a: hillside.py** — Added `tiles_dict: dict` field to `StageData`, passed in `load()`.

**2b: pipeworks.py** — Added `tiles_dict=tiles` to `StageData` constructor.

**2c: skybridge.py** — Removed duplicate `StageData` class, imported from `hillside`, added `tiles_dict=tiles`. Cleaned up unused imports.

### Step 3: Add Goal Collision to objects.py ✓
- Added `GoalEvent` enum with `REACHED` value
- Added `check_goal_collision(player, goal_x, goal_y)` function
- Added `GOAL_ACTIVATION_RADIUS` import

### Step 4: Add Particle Cleanup to renderer.py ✓
- Added `clear_particles()` public function

### Step 5: Rewrite main.py ✓
Complete rewrite with 5-state game state machine:
- TITLE: title screen with flashing "PRESS START"
- STAGE_SELECT: navigate 3 stages, lock/unlock system
- GAMEPLAY: full game loop with all collision systems, death/respawn, boss music trigger, goal detection
- RESULTS: stage clear screen with time/ring/score bonuses
- GAME_OVER: game over screen with auto-return to title

Key features:
- Stage loading from real pipeline data (no more demo level)
- Lives system: 3 lives, death → respawn at checkpoint, 0 lives → game over
- Stage progression: completing a stage unlocks the next
- Music transitions: title, per-stage, boss, clear, game over
- Boss injection for Stage 3
- Clean state resets between stages

### Step 6: Write Tests ✓
Added `tests/test_game_state.py` with 15 tests covering:
- Goal collision (8 tests): at goal, near, far, boundary, dead, hurt, diagonal
- StageData extension (2 tests): field presence and ordering
- Death/respawn logic (4 tests): no rings → death, lives preserved, ring scatter, respawn data
- GoalEvent enum (1 test)

## Deviations from Plan

- No pause system implemented (not in acceptance criteria, spec mentions Pyxel default quit)
- Game over returns to title on timer expiry (not a "Continue?" prompt — kept simple per AC)
- Score calculation in results uses time bonus + ring bonus formula (not specified in AC but reasonable)

## Test Results

- 494 tests total (479 existing + 15 new)
- 0 failures
- All existing tests pass (no regressions)

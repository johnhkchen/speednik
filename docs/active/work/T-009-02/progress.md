# Progress — T-009-02: live-bot-runner

## Step 1: Create speednik/devpark.py — LiveBot dataclass
- Status: complete
- Created LiveBot dataclass with all fields.
- Added _compute_level_bounds helper.

## Step 2: Implement LiveBot.update()
- Status: complete
- Implemented: strategy → player_update → camera_update → completion check.

## Step 3: Implement LiveBot.draw()
- Status: complete
- Implemented: pyxel.camera → draw_terrain → draw_player.

## Step 4: Implement factory functions
- Status: complete
- make_bot, make_bots_for_stage, make_bots_for_grid all implemented.
- Deviation: Changed strategy imports from module-level `if DEBUG:` conditional to
  lazy import inside `make_bots_for_stage`. The module-level conditional caused
  NameError in tests (DEBUG=False in test environment). Lazy import is cleaner —
  the import only happens when the function is actually called.

## Step 5: Write unit tests
- Status: complete
- 13 tests in tests/test_devpark.py, all passing.

## Step 6: Full regression check
- Status: complete
- 786 passed, 2 xfailed (pre-existing). Zero regressions.

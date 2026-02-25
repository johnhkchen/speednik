# Plan — T-009-02: live-bot-runner

## Step 1: Create `speednik/devpark.py` — LiveBot dataclass

Write the LiveBot dataclass with all fields: player, strategy, tile_lookup, tiles_dict,
camera, label, max_frames, goal_x, frame, finished.

Add the `_compute_level_bounds` helper that computes (width_px, height_px) from a tiles_dict
by finding max tx/ty.

**Verify:** File parses without syntax errors (`python -c "from speednik.devpark import LiveBot"`).

---

## Step 2: Implement LiveBot.update()

Add the update method:
1. Early return if finished.
2. Call strategy(frame, player) → InputState.
3. Call player_update(player, inp, tile_lookup).
4. Call camera_update(camera, player, inp).
5. Increment frame.
6. Check max_frames completion.
7. Check goal_x completion.

**Verify:** Manual smoke test — construct LiveBot with flat grid + hold_right, call update() 10 times,
check player.physics.x has changed.

---

## Step 3: Implement LiveBot.draw()

Add the draw method:
1. Get cam_x, cam_y from camera.
2. `pyxel.camera(cam_x, cam_y)`
3. `draw_terrain(tiles_dict, cam_x, cam_y)`
4. `draw_player(player, frame)`

This method requires Pyxel — not unit-testable but follows the exact same pattern as
`App._draw_gameplay()`.

**Verify:** Code review against `_draw_gameplay` pattern.

---

## Step 4: Implement factory functions

### make_bot(tiles_dict, tile_lookup, start_x, start_y, strategy, label, max_frames=600, goal_x=None)
- create_player(start_x, start_y)
- _compute_level_bounds(tiles_dict)
- create_camera(width, height, start_x, start_y)
- Return LiveBot(...)

### make_bots_for_stage(stage_name, max_frames=600)
- load_stage(stage_name)
- Get player_start, tiles_dict, tile_lookup from StageData
- Create 4 bots: idle/IDLE, hold_right/HOLD_RIGHT, hold_right_jump/JUMP, spindash/SPINDASH
- Return list of 4 LiveBots

### make_bots_for_grid(tiles_dict, tile_lookup, start_x, start_y, strategies, max_frames=600)
- Create one bot per (strategy, label) pair in strategies list
- Return list of LiveBots

**Verify:** `python -c "from speednik.devpark import make_bot, make_bots_for_stage"` succeeds.

---

## Step 5: Write unit tests (`tests/test_devpark.py`)

### Test fixtures
- Build a flat grid tiles_dict + tile_lookup inline (reuse pattern from grids.py).
- Use idle() and hold_right() strategies.

### TestLiveBotUpdate
- `test_update_advances_frame`: After 1 update, frame == 1.
- `test_update_moves_player`: After 10 updates with hold_right, player.physics.x > start_x.
- `test_finishes_at_max_frames`: Bot with max_frames=5, after 5 updates, finished == True.
- `test_finishes_at_goal_x`: Bot with goal_x=start_x+100, run until finished, check x >= goal_x.
- `test_finished_bot_stops_updating`: After finished, additional update() doesn't change frame.
- `test_finished_bot_preserves_state`: After finished, player position unchanged by update.

### TestMakeBot
- `test_creates_bot_with_correct_label`: make_bot returns LiveBot with matching label.
- `test_creates_bot_at_start_position`: player.physics.x/y match start_x/start_y.

### TestMakeBotsForStage
- `test_creates_four_bots`: Returns list of 4.
- `test_bot_labels`: Labels are ["IDLE", "HOLD_RIGHT", "JUMP", "SPINDASH"].

### TestMakeBotsForGrid
- `test_creates_bots_for_strategies`: Returns correct number of bots.

**Verify:** `uv run pytest tests/test_devpark.py -x -v` all pass.

---

## Step 6: Full regression check

Run `uv run pytest tests/ -x` to ensure no regressions across the full test suite.

**Verify:** All tests pass, zero failures.

# Review — T-009-02: live-bot-runner

## Summary of Changes

### Files Created

- **`speednik/devpark.py`** (~110 lines) — LiveBot dataclass, update/draw methods, and three
  factory functions (make_bot, make_bots_for_stage, make_bots_for_grid).
- **`tests/test_devpark.py`** (~145 lines) — 13 tests across 4 test classes covering LiveBot
  update logic, completion detection, factory correctness, and stage/grid integration.

### Files Modified

None. This is a new, self-contained module with no changes to existing code.

---

## Design Decisions

### tiles_dict + tile_lookup dual storage

LiveBot stores both `tiles_dict: dict` (for `draw_terrain`) and `tile_lookup: TileLookup`
(for `player_update`). This avoids changing the renderer's or terrain's API. For real stages,
both come from `StageData`. For synthetic grids, the caller provides both.

### Lazy import for strategies

Changed from the ticket's suggested `if DEBUG:` conditional module-level import to a lazy
import inside `make_bots_for_stage()`. The module-level conditional failed in tests because
`SPEEDNIK_DEBUG` is not set in the test environment. The lazy import:
- Only executes when `make_bots_for_stage` is actually called.
- Works in both DEBUG and test contexts.
- Keeps `tests/harness.py` as the single source for strategy definitions.

### Camera requires InputState

`camera_update(camera, player, inp)` needs the InputState for look up/down. The LiveBot's
strategy already produces this each frame, so it's passed through naturally. The camera
tracks the bot's player with full look-ahead behavior.

---

## Test Coverage

| Component | Tests | What it covers |
|-----------|-------|----------------|
| `LiveBot.update()` | 5 | Frame advance, player movement, max_frames finish, goal_x finish, finished-stops-updating |
| `make_bot` | 3 | Label correctness, start position, initial state |
| `make_bots_for_stage` | 3 | Count (4 bots), labels, updateability |
| `make_bots_for_grid` | 2 | Count, updateability |

**Full suite**: 786 passed, 2 xfailed (pre-existing). Zero regressions.

---

## Coverage Gaps

- **`LiveBot.draw()`**: Not tested — requires Pyxel initialization. The method is 5 lines
  following the exact same pattern as `App._draw_gameplay()`. Verifiable visually in T-009-03.
- **`_compute_level_bounds`**: Not tested directly, but exercised indirectly by every `make_bot`
  call (camera creation uses the computed bounds).
- **Multiple bots sharing tile data**: Not explicitly tested that bots with shared tiles_dict
  don't interfere. Each bot has its own Player and Camera; tile data is read-only. No
  concurrency concerns.

---

## Acceptance Criteria Verification

- [x] `LiveBot` dataclass with player, strategy, tile_lookup, camera, label, frame counter
  — `LiveBot` has all fields plus `tiles_dict`, `max_frames`, `goal_x`, `finished`.
- [x] `LiveBot.update()` calls strategy → player_update → camera update each frame
  — Implemented and tested (5 tests).
- [x] `LiveBot.draw()` renders terrain and player using the bot's own camera
  — Implemented: sets `pyxel.camera`, calls `draw_terrain`, `draw_player`.
- [x] `make_bot` factory creates a LiveBot from tile_lookup + start position + strategy
  — Implemented and tested (3 tests).
- [x] `make_bots_for_stage` creates 4 bots (idle, hold_right, jump, spindash) for a real stage
  — Implemented and tested with hillside stage (3 tests).
- [x] `make_bots_for_grid` creates bots for a synthetic TileLookup
  — Implemented and tested (2 tests).
- [x] Bot finishes after max_frames or reaching goal_x
  — Both paths tested explicitly.
- [x] Finished bots stop updating but remain drawable
  — Tested: update() is no-op after finished, frame and position unchanged.
- [x] Label string is accessible for HUD rendering
  — `bot.label` field, tested in make_bot and make_bots_for_stage tests.
- [x] Only imported/active when DEBUG is True
  — `make_bots_for_stage` uses lazy import from `tests/harness`. The module itself is only
  imported by dev_park state code (gated by DEBUG in main.py, T-009-03).
- [x] No test regressions — `uv run pytest tests/ -x` passes
  — 786 passed, 2 xfailed.

---

## Open Concerns

- **None blocking.** The implementation is complete and self-contained.
- T-009-03 will integrate devpark.py into main.py's dev_park state for visual rendering.
- T-009-04 will use LiveBot.draw() with `pyxel.clip()` for quad-split multi-view.
- The `tiles_dict` for synthetic grids must be provided by the caller (grid builders in
  `tests/grids.py` return only `TileLookup`). T-009-03 may need to expose the dict from
  grid builders or construct it inline. This is a T-009-03 concern, not T-009-02.

# Progress — T-009-01: debug-flag-and-hud-overlay

## Completed Steps

### Step 1: Create `speednik/debug.py`
- Created `speednik/debug.py` with `DEBUG = os.environ.get("SPEEDNIK_DEBUG", "") == "1"`.
- No deviations.

### Step 2: Add `draw_debug_hud` to `speednik/renderer.py`
- Added function after `draw_hud`. Three lines of text at x=136, y=14/22/30.
- Format matches ticket spec: F, X, Y, GS, A, Q, STATE, GND.
- No deviations.

### Step 3: Modify `speednik/main.py` — debug HUD in gameplay
- Added `from speednik.debug import DEBUG` import.
- Added `if DEBUG: renderer.draw_debug_hud(self.player, self.timer_frames)` after `draw_hud` call.
- No deviations.

### Step 4: Modify `speednik/main.py` — dev park state machine
- Added `_DEV_PARK_STAGE = 0` constant.
- Added "dev_park" to both update and draw dispatch.
- Added `_update_dev_park` (returns to stage select on Z/RETURN) and `_draw_dev_park` (shows centered placeholder text).
- On returning from dev park, `selected_stage` is reset to 1 to avoid being stuck on stage 0.
- No deviations.

### Step 5: Modify `speednik/main.py` — stage select navigation and rendering
- Modified UP navigation: from DEV PARK (0), goes to `unlocked_stages`.
- Modified DOWN navigation: from last unlocked stage, moves to DEV PARK if DEBUG.
- Confirm: stage 0 → "dev_park" state, else normal _load_stage.
- Rendering: DEV PARK entry at `y = 60 + _NUM_STAGES * 24`, labeled "D. DEV PARK".
- No deviations.

### Step 6: Create `tests/test_debug.py`
- 14 tests: 4 for debug flag, 10 for debug HUD rendering.
- All pass.

### Step 7: Run full test suite
- `uv run pytest tests/ -x`: 773 passed, 2 xfailed. Zero regressions.

## Remaining
None — all steps complete.

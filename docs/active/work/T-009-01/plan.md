# Plan — T-009-01: debug-flag-and-hud-overlay

## Step 1: Create `speednik/debug.py`

Create the file with:
```python
import os
DEBUG = os.environ.get("SPEEDNIK_DEBUG", "") == "1"
```

**Verify**: `python -c "from speednik.debug import DEBUG; print(DEBUG)"` prints `False`.

---

## Step 2: Add `draw_debug_hud` to `speednik/renderer.py`

Add a new function after the existing `draw_hud` function:

```python
def draw_debug_hud(player, frame_counter: int) -> None:
```

Three lines of text at x=136, y=14/22/30, color 11:
- Line 1: `F:{frame_counter}  X:{x:.1f}  Y:{y:.1f}`
- Line 2: `GS:{ground_speed:.2f}  A:{angle}  Q:{quadrant}`
- Line 3: `STATE:{state_value}  GND:{"Y" if on_ground else "N"}`

Quadrant = `player.physics.angle // 64`.

**Verify**: Write test, run pytest on the new test file.

---

## Step 3: Modify `speednik/main.py` — debug HUD in gameplay

At the top, add:
```python
from speednik.debug import DEBUG
```

In `_draw_gameplay`, after `renderer.draw_hud(...)` (line 480), add:
```python
if DEBUG:
    renderer.draw_debug_hud(self.player, self.timer_frames)
```

**Verify**: With `SPEEDNIK_DEBUG=1`, run the game and confirm overlay appears.

---

## Step 4: Modify `speednik/main.py` — dev park state machine

Add to `__init__`:
- No new fields needed; `self.state` already supports arbitrary strings.

Add constant at module level:
```python
_DEV_PARK_STAGE = 0
```

Add to `update()` dispatch:
```python
elif self.state == "dev_park":
    self._update_dev_park()
```

Add to `draw()` dispatch:
```python
elif self.state == "dev_park":
    self._draw_dev_park()
```

Add methods:
```python
def _update_dev_park(self):
    if pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_RETURN):
        self.state = "stage_select"

def _draw_dev_park(self):
    pyxel.text(SCREEN_WIDTH // 2 - 20, SCREEN_HEIGHT // 2 - 8, "DEV PARK", 11)
    if pyxel.frame_count % 60 < 40:
        pyxel.text(SCREEN_WIDTH // 2 - 32, SCREEN_HEIGHT // 2 + 16, "PRESS Z TO RETURN", 7)
```

---

## Step 5: Modify `speednik/main.py` — stage select navigation and rendering

**Navigation (`_update_stage_select`)**:

Replace the UP/DOWN logic to handle the DEV PARK entry. The DEV PARK entry is represented by `selected_stage = _DEV_PARK_STAGE (0)`.

- UP: if currently on DEV PARK (0), move to `unlocked_stages`. If on stage > 1, decrement.
- DOWN: if currently on `unlocked_stages` and DEBUG, move to DEV PARK (0). If on stage < `unlocked_stages`, increment.
- Confirm: if `selected_stage == _DEV_PARK_STAGE`, transition to "dev_park" state. Otherwise, load stage.

**Rendering (`_draw_stage_select`)**:

After the existing loop, add:
```python
if DEBUG:
    y = 60 + _NUM_STAGES * 24
    name = "DEV PARK"
    color = 11 if self.selected_stage == _DEV_PARK_STAGE else 7
    prefix = "> " if self.selected_stage == _DEV_PARK_STAGE else "  "
    pyxel.text(60, y, f"{prefix}D. {name}", color)
```

**Verify**: With `SPEEDNIK_DEBUG=1`, run the game, navigate to DEV PARK, confirm selection.

---

## Step 6: Create `tests/test_debug.py`

Test classes:

**TestDebugFlag**:
- `test_debug_false_by_default`: import with clean env, assert `False`.
- `test_debug_true_when_set`: mock `os.environ` with `SPEEDNIK_DEBUG=1`, reimport module, assert `True`.
- `test_debug_false_when_zero`: mock env with `SPEEDNIK_DEBUG=0`, assert `False`.

**TestDebugHUD**:
- `test_draws_three_lines`: mock pyxel, create player, call `draw_debug_hud`, assert 3 `pyxel.text` calls.
- `test_shows_frame_counter`: verify frame counter value appears in text.
- `test_shows_position`: verify X/Y values appear.
- `test_shows_ground_speed`: verify GS value appears.
- `test_shows_state`: verify STATE value appears.
- `test_shows_ground_flag`: verify GND:Y or GND:N appears.

**Verify**: `uv run pytest tests/test_debug.py -x`

---

## Step 7: Run full test suite

```
uv run pytest tests/ -x
```

Confirm no regressions. All existing tests should pass unchanged since DEBUG defaults to False.

---

## Testing Strategy Summary

| What | How | Type |
|------|-----|------|
| DEBUG flag reads env | patch os.environ, reimport | Unit |
| draw_debug_hud output | mock pyxel, check text calls | Unit |
| No debug HUD when DEBUG=False | no calls to draw_debug_hud | Implicit (main.py guards) |
| Stage select DEV PARK visible | functional test via game | Manual + implicit |
| Full regression | `uv run pytest tests/ -x` | Suite |

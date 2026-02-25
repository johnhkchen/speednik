# Structure — T-009-01: debug-flag-and-hud-overlay

## Files Created

### `speednik/debug.py`

New module. ~5 lines.

```
import os
DEBUG = os.environ.get("SPEEDNIK_DEBUG", "") == "1"
```

Single constant. No functions, no classes. Imported by main.py and renderer.py.

### `tests/test_debug.py`

New test file. ~60 lines.

Classes:
- `TestDebugFlag` — tests that DEBUG reads from environment correctly
- `TestDebugHUD` — tests that `draw_debug_hud` renders expected text content
- `TestDevParkPlaceholder` — tests placeholder state logic

---

## Files Modified

### `speednik/renderer.py`

**Add function** `draw_debug_hud(player, frame_counter: int) -> None`:
- Location: after the existing `draw_hud` function, in the HUD section (after line 571).
- Parameters: `player` (Player), `frame_counter` (int — the gameplay frame count).
- Renders 3 lines of debug text at top-right (x=136, y=14/22/30) using `pyxel.text()`.
- Reads: `player.physics.x`, `.y`, `.ground_speed`, `.angle`, `.on_ground`, `player.state.value`.
- Computes quadrant as `player.physics.angle // 64`.

No other changes to renderer.py. The function is self-contained.

### `speednik/main.py`

**Imports added** (top of file):
- `from speednik.debug import DEBUG`

**Stage configuration** (lines 86–90):
- Add `_DEV_PARK_STAGE = 0` constant.

**`_update_stage_select`** method:
- Modify UP navigation: allow moving down to DEV PARK entry when DEBUG is True.
- Modify DOWN navigation: allow selecting DEV PARK (stage 0) below unlocked stages.
- On confirm: if `self.selected_stage == _DEV_PARK_STAGE`, set `self.state = "dev_park"` instead of calling `_load_stage`.
- Implementation: DEV PARK is at position `_NUM_STAGES + 1` visually. When pressing DOWN from the last unlocked stage, if DEBUG, move to `_DEV_PARK_STAGE (0)`. When pressing UP from DEV PARK, move to `unlocked_stages`.

**`_draw_stage_select`** method:
- After the existing stage loop, if DEBUG, draw the DEV PARK entry at `y = 60 + _NUM_STAGES * 24`.
- Use color 11 if selected, 7 otherwise. Always show as selectable (not gated by unlocked_stages).

**`update`** method:
- Add `elif self.state == "dev_park": self._update_dev_park()` to dispatch.

**`draw`** method:
- Add `elif self.state == "dev_park": self._draw_dev_park()` to dispatch.

**New method** `_update_dev_park(self)`:
- If Z or RETURN pressed, return to stage select state.
- ~5 lines.

**New method** `_draw_dev_park(self)`:
- Clear screen, draw "DEV PARK" centered, draw "PRESS Z TO RETURN" below.
- ~5 lines.

**`_draw_gameplay`** method (line 480):
- After `renderer.draw_hud(...)`, add:
  ```python
  if DEBUG:
      renderer.draw_debug_hud(self.player, self.timer_frames)
  ```

---

## Module Boundaries

```
speednik/debug.py  ──(imported by)──→  speednik/main.py
                                        speednik/renderer.py (via main.py call)

speednik/renderer.py  ──(draw_debug_hud)──→  reads Player, PhysicsState
speednik/main.py      ──(calls)──→  renderer.draw_debug_hud()
```

`debug.py` has no internal dependencies — it only uses `os`. This prevents circular imports.

`renderer.py` does NOT import `debug.py`. The DEBUG gate is in `main.py`, which conditionally calls `draw_debug_hud`. The renderer just provides the function.

---

## Change Ordering

1. Create `speednik/debug.py` (no dependencies)
2. Add `draw_debug_hud` to `speednik/renderer.py` (depends on Player/PhysicsState types, already imported)
3. Modify `speednik/main.py` — import DEBUG, add dev_park state, modify stage select, add debug HUD call
4. Create `tests/test_debug.py` — tests for all new functionality

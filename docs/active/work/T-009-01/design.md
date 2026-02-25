# Design — T-009-01: debug-flag-and-hud-overlay

## Decision 1: Debug Flag Module

### Option A: Standalone `speednik/debug.py` (chosen)

A single-file module with one constant:

```python
import os
DEBUG = os.environ.get("SPEEDNIK_DEBUG", "") == "1"
```

Everything else does `from speednik.debug import DEBUG`.

**Pros**: Single source of truth. Clean import. Exactly what the ticket specifies.
**Cons**: None meaningful — this is the obvious approach.

### Option B: Add flag to constants.py

**Rejected.** constants.py is physics/rendering constants, not runtime configuration. Mixing concerns.

---

## Decision 2: Debug HUD Rendering Location

### Option A: New function in `renderer.py` (chosen)

Add `draw_debug_hud(player, frame_counter)` to `renderer.py`. Called from `main.py` after `draw_hud()`, still in screen space.

**Pros**: Consistent with existing `draw_hud` pattern. All rendering stays in renderer. Easy to test with existing mock pattern.
**Cons**: None.

### Option B: Render directly in main.py

**Rejected.** Breaks separation of concerns. main.py handles state logic, renderer.py handles drawing.

### HUD Layout

Existing HUD occupies the top-left: `RINGS: N` at (4, 4), `TIME: M:SS` at (90, 4), lives `xN` at (200, 4). All at y=4.

The debug HUD goes in the **top-right corner**. Three lines of text:

```
F:1234  X:3456.2  Y:512.0     (line 1)
GS:6.00  A:32  Q:0            (line 2)
STATE:running  GND:Y           (line 3)
```

Pyxel's built-in font: 4px per character, 6px line height. The longest line is ~30 chars = 120px. Position at x = `SCREEN_WIDTH - 120` = 136. But 136 overlaps TIME at x=90. Let's check:

- `TIME: 1:30` = 10 chars = 40px, ends at x=130. Safe margin to x=136.
- Actually, lives at x=200 is only `x3` = 2 chars = 8px, ending at 208.

Better approach: right-align by positioning debug HUD starting at y=14 (below the existing HUD line). This avoids any overlap entirely.

**Final position**: x=136, y=14 for line 1; y=22 for line 2; y=30 for line 3. Color: 11 (white).

Wait — the ticket says "top-right corner to avoid overlapping the lives/rings/time HUD in the top-left." The existing HUD is only on y=4. So starting at y=14 in the right half (x≥136) gives clear separation from both the existing HUD and the game view.

---

## Decision 3: Stage Select DEV PARK Entry

### Option A: Dev park as a special entry after real stages (chosen)

Add DEV PARK as the last entry in the stage select, shown only when `DEBUG` is True. Use a sentinel stage number (0) to identify it.

Navigation logic:
- The selectable range becomes `1..unlocked_stages` plus an additional DEV PARK entry.
- DEV PARK appears at `_NUM_STAGES + 1` position visually but maps to stage 0 internally.
- It's always selectable regardless of `unlocked_stages`.
- When selected and confirmed, transition to a "dev_park" state that shows placeholder text.

**Pros**: Minimal changes to existing stage select. Clear separation from real stages. Stage 0 won't collide with real stage numbers.
**Cons**: Need to handle the special case in navigation and rendering.

### Option B: Dev park as stage 0 before real stages

**Rejected.** Disrupts the natural 1-based numbering. Players see real stages shifted down.

### Option C: Separate menu/submenu

**Rejected.** Over-engineered for the current need. T-009-03 will flesh out the dev park further.

### Dev Park Placeholder State

When DEV PARK is selected, instead of calling `_load_stage(0)` (which would fail — no stage data), the app transitions to a new state "dev_park". The draw method shows "DEV PARK" text centered on a black screen. Pressing Z or RETURN returns to stage select.

This keeps `_load_stage` clean — it only handles real stages. T-009-03 will implement the actual dev park gameplay.

---

## Decision 4: Frame Counter Source

The ticket says "F — Frame counter (incremented each gameplay update)." This maps to `timer_frames` in `App`, which is incremented each gameplay update frame. Pass it as a parameter to the debug HUD function.

---

## Decision 5: Testing Strategy

- **`speednik/debug.py`**: Test that `DEBUG` is `False` by default and `True` when `SPEEDNIK_DEBUG=1` is in the environment. Use `unittest.mock.patch.dict(os.environ, ...)`.
- **`draw_debug_hud`**: Test with `@patch("speednik.renderer.pyxel")`, verify `pyxel.text` is called with expected strings containing position, speed, angle, state values.
- **Stage select with DEBUG**: Hard to unit-test the full `App` class (requires Pyxel init). Instead, test the conditional logic in isolation — verify that the DEV PARK entry appears/disappears based on the flag. Functional verification via `uv run pytest`.

# Design — T-009-04: security-camera-quad-split

## Decision summary

Add a `draw_quad_split()` function to `devpark.py` and replace the dev park placeholder in
`main.py` with a live quad-split view running 4 bots on the hillside stage. Use `pyxel.clip()`
for quadrant isolation and the normal camera (Option 3 from ticket) to keep implementation
simple.

## Options evaluated

### Option A: Quad-split as its own function in devpark.py (chosen)

Add `draw_quad_split(bots, frame_count)` to `devpark.py`. The function iterates QUADRANTS,
clips each, sets camera offset, draws terrain/player, then draws labels in screen space.
Main.py creates bots on dev_park entry and calls update+draw each frame.

**Pros:** Self-contained, testable logic split, minimal main.py changes.
**Cons:** None significant.

### Option B: Quad-split as a separate module

Create `speednik/quad_split.py` with the rendering logic.

**Pros:** Clean separation.
**Cons:** Overkill for ~40 lines of rendering code. devpark.py already holds bot logic —
rendering belongs with it.

**Rejected:** Unnecessary file proliferation for a small feature.

### Option C: Full dev park menu with multiple views

Build a dev park sub-menu where users pick between stages and view modes (single-bot vs
quad-split). This matches ticket suggestion "MULTI-VIEW: HILLSIDE", "MULTI-VIEW: RAMP".

**Pros:** Most complete UX.
**Cons:** T-009-03 handles the dev park stage menu. Building a menu here creates overlap.
T-009-04's scope is the quad-split rendering, not the menu system.

**Rejected:** Out of scope. Start with hillside quad-split; menu integration is T-009-03's
job or a follow-up.

## Camera approach

### Option 1: MiniCamera with halved borders
Duplicate camera logic with halved constants. Adds maintenance burden and code duplication.
**Rejected.**

### Option 2: Parameterize Camera with viewport dimensions
Add `viewport_w`, `viewport_h` params to `camera_update` and `_clamp_to_bounds`. Clean but
invasive — changes the camera API for all callers.
**Rejected** for this ticket. Could be done later if the camera lag is jarring.

### Option 3: Use normal camera, accept mismatch (chosen)
Camera borders are designed for 256px but quadrant is 128px. The player may drift off-center
before the camera catches up. For a debug visualization this is acceptable. Zero code changes
to camera.py.

## State management

Bots are created when entering dev_park state. Store them as `self.dev_park_bots` on the
App instance. On exit (X key), clear them and return to stage_select.

Initialization flow:
1. User selects DEV PARK in stage_select.
2. `_update_stage_select()` sets `self.state = "dev_park"`.
3. `_init_dev_park()` creates 4 bots via `make_bots_for_stage("hillside")`.
4. Sets stage palette to hillside.
5. Each frame: update all bots, draw quad-split.
6. X key → clear bots, return to stage_select.

## Rendering approach

```
QUADRANTS = [
    (0,   0,   128, 112),   # top-left: IDLE
    (128, 0,   128, 112),   # top-right: HOLD_RIGHT
    (0,   112, 128, 112),   # bottom-left: JUMP
    (128, 112, 128, 112),   # bottom-right: SPINDASH
]
```

For each quadrant:
1. `pyxel.clip(qx, qy, qw, qh)` — restrict drawing.
2. `pyxel.camera(int(bot.camera.x) - qx, int(bot.camera.y) - qy)` — offset world into quadrant.
3. `draw_terrain(bot.tiles_dict, int(bot.camera.x), int(bot.camera.y))` — draw terrain.
4. `draw_player(bot.player, bot.frame)` — draw player (uses bot.frame for animation).
5. `pyxel.camera()` — reset to screen space.
6. `pyxel.text(qx+2, qy+2, bot.label, 7)` — strategy label.
7. `pyxel.text(qx+2, qy+qh-8, f"X:{bot.player.physics.x:.0f}", 7)` — position readout.

After all quadrants:
- `pyxel.clip()` — reset clipping.
- Draw divider lines at x=128 (vertical) and y=112 (horizontal) in color 11 (white).

## Exit behavior

X key (`pyxel.KEY_X`) exits quad-split back to stage_select. This matches the ticket's
acceptance criterion. The current Z/RETURN binding for the placeholder will be replaced.

## Testing strategy

- **Unit tests**: Test `draw_quad_split` data flow by testing that the QUADRANTS constant
  covers the full screen and has correct dimensions. Test that bots are created with correct
  labels and can update independently. Reuse `_build_flat_test_grid()` fixture.
- **No Pyxel rendering tests**: `draw_quad_split` calls Pyxel functions — can't test without
  Pyxel init. Visual verification only.
- **Integration**: Run `uv run pytest tests/ -x` to ensure no regressions.

## Files affected

- `speednik/devpark.py` — Add QUADRANTS constant, `draw_quad_split()` function.
- `speednik/main.py` — Replace dev park placeholder with bot init + quad-split calls.
- `tests/test_devpark.py` — Add tests for QUADRANTS constant and quad-split bot lifecycle.

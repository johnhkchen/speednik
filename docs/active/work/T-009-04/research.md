# Research — T-009-04: security-camera-quad-split

## Scope

Build a quad-split (2×2) security-camera view rendering four bot strategies simultaneously
on the same terrain. Each 128×112 quadrant runs an independent LiveBot with its own camera.

## Codebase map

### Primary integration points

**`speednik/devpark.py`** — LiveBot class and factory functions (T-009-02 output).
- `LiveBot` dataclass: holds player, strategy, tile_lookup, tiles_dict, camera, label, frame state.
- `LiveBot.update()`: strategy → player_update → camera_update → frame++. Stops at max_frames or goal_x.
- `LiveBot.draw()`: sets pyxel.camera, calls draw_terrain + draw_player. Renders to full screen.
- `make_bot()`: creates one LiveBot from tile data + strategy + position.
- `make_bots_for_stage(stage_name)`: creates 4 bots (idle, hold_right, jump, spindash) on a real stage.
- `make_bots_for_grid(tiles_dict, tile_lookup, ...)`: creates bots for synthetic grids.

**`speednik/main.py`** (lines 266–279) — Dev park placeholder state.
- `_update_dev_park()`: currently only handles Z/RETURN → return to stage select.
- `_draw_dev_park()`: shows "DEV PARK" text + "PRESS Z TO RETURN" flash.
- State entered via stage_select when `selected_stage == _DEV_PARK_STAGE` (0).
- Dev park is gated behind `DEBUG` flag (SPEEDNIK_DEBUG=1).

**`speednik/renderer.py`** — Terrain and player drawing.
- `draw_terrain(tiles, camera_x, camera_y)`: iterates all tiles, viewport-culls using
  `SCREEN_WIDTH`/`SCREEN_HEIGHT` constants (256×224), draws visible tiles.
- `draw_player(player, frame_count)`: draws player at world coordinates. No screen assumptions.
- `set_stage_palette(stage_name)`: sets terrain colors for stages.

**`speednik/camera.py`** — Camera with border tracking and look-ahead.
- `Camera` dataclass: x, y, look_offset, level_width, level_height.
- `create_camera(level_width, level_height, start_x, start_y)`: factory with initial centering.
- `camera_update(camera, player, inp)`: horizontal borders, vertical focal, clamping.
- `_clamp_to_bounds()`: uses `SCREEN_WIDTH` and `SCREEN_HEIGHT` for max bounds.
- Camera assumes full 256×224 viewport for border calculations.

### Screen geometry

- `SCREEN_WIDTH = 256`, `SCREEN_HEIGHT = 224` (constants.py).
- Quad-split: 4 quadrants of 128×112 each. Perfect 2×2 division, no remainder.
- Camera borders: LEFT=144, RIGHT=160 (designed for 256px width). In 128px quadrant,
  the left border alone exceeds the quadrant width. The camera will still track the player
  but borders won't feel tight. Acceptable for debug view per ticket guidance.

### Pyxel drawing primitives

- `pyxel.clip(x, y, w, h)`: restricts all drawing to the specified screen rectangle.
- `pyxel.clip()`: resets clipping to full screen.
- `pyxel.camera(cx, cy)`: offsets subsequent draws by (-cx, -cy). World position P draws at
  screen position (P.x - cx, P.y - cy).
- `pyxel.camera()`: resets camera offset to (0, 0).
- `pyxel.text(x, y, string, color)`: 4×6 pixel font, screen-space when camera is reset.
- `pyxel.line(x1, y1, x2, y2, color)`: line in current coordinate space.

### Camera math for quadrant rendering

To render a bot's world view into quadrant at screen position (qx, qy):

```
pyxel.clip(qx, qy, qw, qh)
cam_offset_x = int(bot.camera.x) - qx
cam_offset_y = int(bot.camera.y) - qy
pyxel.camera(cam_offset_x, cam_offset_y)
```

This maps world position `(wx, wy)` → screen position `(wx - cam.x + qx, wy - cam.y + qy)`,
which places the camera's view origin at the top-left of the quadrant. The clip region
prevents any drawing from leaking outside the quadrant.

### Viewport culling in draw_terrain

`draw_terrain()` culls tiles outside `camera_x..camera_x+SCREEN_WIDTH` (256px range).
In quad-split, only 128px is visible per quadrant. This means ~2× more tiles pass the
culling test than are actually visible, but `pyxel.clip()` discards the off-screen pixels.
Performance impact: minor — extra tile draws are cheap, and clip stops actual pixel writes.

### Test patterns

**`tests/test_devpark.py`** — 13 tests for LiveBot logic. All headless (no Pyxel).
- Uses `_build_flat_test_grid()` to create synthetic flat terrain.
- Tests update/frame advancement, movement, finish conditions, factory functions.
- `draw()` is never tested (requires Pyxel init).
- Pattern: create bot → loop update() → assert state.

### Strategies (from `tests/harness.py`)

- `idle()` — returns empty InputState, player stands still.
- `hold_right()` — holds right, player runs right.
- `hold_right_jump()` — holds right, presses jump on first frame and after each landing.
- `spindash_right(charge_frames=3)` — state machine: crouch → charge → release → run → repeat.
- Each is a closure factory returning `Callable[[int, Player], InputState]`.

### Existing dev park state lifecycle

1. User navigates to DEV PARK in stage select (DEBUG only).
2. `self.state = "dev_park"` in main.py.
3. `_update_dev_park()` and `_draw_dev_park()` called each frame.
4. No bots created, no terrain loaded — just placeholder text.
5. Z/RETURN returns to stage select.

### Dependencies

- T-009-02 (complete): LiveBot, make_bot, make_bots_for_stage, make_bots_for_grid.
- T-009-01 (complete): DEBUG flag, dev_park menu entry in stage select.
- S-008 strategies (complete): idle, hold_right, hold_right_jump, spindash_right.

## Constraints and risks

1. **Camera border mismatch**: Camera LEFT_BORDER=144 > quadrant width 128. Camera will
   still track but the player may drift further off-center before catching. Ticket says
   "probably fine for a debug view."

2. **Viewport culling overhead**: draw_terrain passes 256px-wide culling window but only
   128px is visible. ~2× wasted tile iteration. Acceptable per ticket performance notes.

3. **No `draw()` tests**: Rendering tests require Pyxel init. Can only test update logic
   headlessly. Visual correctness verified by running the game.

4. **X key exit**: Ticket says "X key exits back to dev park menu". Currently Z/RETURN
   returns to stage select. Need to decide: X → stage_select, or X → a dev park menu
   (which doesn't exist yet). T-009-03 may add a menu; for now, X → stage_select is simplest.

5. **State initialization**: Bots must be created when entering dev_park state. Currently
   no initialization hook — creation happens inline in `_update_dev_park` or at state
   transition in `_update_stage_select`.

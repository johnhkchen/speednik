# Structure — T-009-04: security-camera-quad-split

## File changes

### Modified: `speednik/devpark.py`

**New constants (module level, after imports):**

```python
QUADRANTS: list[tuple[int, int, int, int]] = [
    (0,   0,   128, 112),   # top-left
    (128, 0,   128, 112),   # top-right
    (0,   112, 128, 112),   # bottom-left
    (128, 112, 128, 112),   # bottom-right
]
```

**New function: `draw_quad_split(bots, frame_count)`**

Location: After `LiveBot.draw()`, before factory helpers.

```
def draw_quad_split(bots: list[LiveBot], frame_count: int) -> None:
    """Render 4 bots in quad-split security-camera view."""
```

Signature takes explicit `frame_count` because `LiveBot.draw()` uses `self.frame` for
player animation, but the quad-split renderer needs it passed in since it manages camera
and clipping around each bot's draw.

Internal flow:
1. Loop over zip(QUADRANTS, bots):
   a. pyxel.clip(qx, qy, qw, qh)
   b. cam_x = int(bot.camera.x), cam_y = int(bot.camera.y)
   c. pyxel.camera(cam_x - qx, cam_y - qy)
   d. renderer.draw_terrain(bot.tiles_dict, cam_x, cam_y)
   e. renderer.draw_player(bot.player, frame_count)
   f. pyxel.camera()  — reset to screen space
   g. pyxel.text label at (qx+2, qy+2)
   h. pyxel.text position at (qx+2, qy+qh-8)
2. pyxel.clip() — reset
3. Draw divider lines: vertical at x=128, horizontal at y=112, color 11

### Modified: `speednik/main.py`

**New field on App.__init__:**

```python
self.dev_park_bots: list | None = None
```

**New method: `_init_dev_park()`**

Called when entering dev_park state. Creates 4 bots via `make_bots_for_stage("hillside")`.
Sets stage palette. Stores bots in `self.dev_park_bots`.

```python
def _init_dev_park(self):
    from speednik.devpark import make_bots_for_stage
    renderer.set_stage_palette("hillside")
    self.dev_park_bots = make_bots_for_stage("hillside", max_frames=36000)
```

max_frames=36000 = 10 minutes at 60fps. Long enough to observe without auto-stopping.

**Modified: `_update_stage_select()`**

When selecting dev_park, call `_init_dev_park()` before setting state:

```python
if self.selected_stage == _DEV_PARK_STAGE:
    self._init_dev_park()
    self.state = "dev_park"
```

**Replaced: `_update_dev_park()`**

```python
def _update_dev_park(self):
    if pyxel.btnp(pyxel.KEY_X):
        self.dev_park_bots = None
        self.selected_stage = 1
        self.state = "stage_select"
        return
    if self.dev_park_bots:
        for bot in self.dev_park_bots:
            bot.update()
```

Exit on X key. Update all bots each frame.

**Replaced: `_draw_dev_park()`**

```python
def _draw_dev_park(self):
    if self.dev_park_bots:
        from speednik.devpark import draw_quad_split
        draw_quad_split(self.dev_park_bots, pyxel.frame_count)
```

**Import changes:**

Add conditional import at call sites (lazy import pattern already used by `make_bots_for_stage`).
No new top-level imports needed in main.py — devpark is imported lazily to avoid pulling
test harness strategies into production code.

### Modified: `tests/test_devpark.py`

**New test class: `TestQuadSplit`**

Tests the data-layer aspects of quad-split:

1. `test_quadrants_cover_full_screen` — Verify QUADRANTS tiles the 256×224 screen.
2. `test_quadrants_no_overlap` — Verify no quadrant overlaps another.
3. `test_quad_split_bots_update_independently` — Create 4 bots, update all, verify
   positions diverge based on different strategies.
4. `test_quad_split_bot_labels` — Verify `make_bots_for_stage` returns expected labels.

Import: `from speednik.devpark import QUADRANTS`

## Module boundaries

- `devpark.py` owns: QUADRANTS constant, `draw_quad_split()` function, all bot factories.
- `main.py` owns: state management, bot lifecycle (create/destroy), frame dispatch.
- `renderer.py`: unchanged — provides draw_terrain, draw_player as-is.
- `camera.py`: unchanged — provides camera as-is (Option 3).
- `tests/test_devpark.py`: all devpark tests, including quad-split.

## Public interface additions

```python
# speednik/devpark.py
QUADRANTS: list[tuple[int, int, int, int]]  # exported constant
draw_quad_split(bots: list[LiveBot], frame_count: int) -> None  # new function
```

## Ordering

1. Add QUADRANTS and draw_quad_split to devpark.py (no dependencies on main.py changes).
2. Add _init_dev_park and modify _update/_draw_dev_park in main.py.
3. Modify _update_stage_select to call _init_dev_park.
4. Add tests to test_devpark.py.
5. Run full test suite.

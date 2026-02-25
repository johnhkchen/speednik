# Structure — T-009-05 boundary-escape-detection

## Files Modified

### 1. `tests/harness.py` — add hold_left strategy

Add `hold_left()` factory after `hold_right()` (around line 170):

```python
def hold_left() -> Strategy:
    """Strategy: hold left every frame. Tests left-edge boundary escape."""
    def strategy(frame: int, player: Player) -> InputState:
        return InputState(left=True)
    return strategy
```

No other changes to harness.py.

### 2. `tests/test_levels.py` — add TestBoundaryEscape class

**Imports to add**: `hold_left` from harness

**New class**: `TestBoundaryEscape` appended after existing TestStallDetection class

Structure:
- `STAGE_NAMES = ["hillside", "pipeworks", "skybridge"]`
- `ESCAPE_STRATEGIES` dict mapping strategy names to factories
  (hold_right, hold_left, hold_right_jump, spindash_right)

Methods (all `@pytest.mark.xfail(reason="No kill plane...", strict=False)`):

```
test_right_edge_escape()
    For each stage × each right-moving strategy:
        run 3600 frames, assert all snapshots x <= level_width
        Error msg: "{stage}/{strategy}: escaped right at frame {f}, x={x}, level_width={w}"

test_left_edge_escape()
    For each stage × hold_left:
        run 3600 frames, assert all snapshots x >= 0
        Error msg: "{stage}/hold_left: escaped left at frame {f}, x={x}"

test_bottom_edge_escape()
    For each stage × each strategy:
        run 3600 frames, assert all snapshots y <= level_height + 64
        Error msg: "{stage}/{strategy}: fell off bottom at frame {f}, y={y}, level_height={h}"
```

Each method loads stage via `_get_stage()` (existing cached helper), gets
level_width/level_height, runs strategy, checks all snapshots.

### 3. `speednik/renderer.py` — add draw_level_bounds()

New public function after `draw_terrain()` (around line 138):

```python
def draw_level_bounds(
    level_width: int,
    level_height: int,
    camera_x: int,
    camera_y: int,
) -> None:
```

Draws 4 boundary lines in world space:
- Left edge: vertical line x=0 from y=0 to y=level_height
- Right edge: vertical line x=level_width from y=0 to y=level_height
- Top edge: horizontal line y=0 from x=0 to x=level_width
- Bottom edge: horizontal line y=level_height from x=0 to x=level_width

Uses color slot 8 (red, 0xE02020). Only draws lines that intersect the
current viewport (camera_x ± SCREEN_WIDTH, camera_y ± SCREEN_HEIGHT) for
efficiency.

### 4. `speednik/devpark.py` — add BOUNDARY PATROL stage

**New functions**:

`_init_boundary_patrol(stage_index=0)` → list[LiveBot]:
  - Loads stage by index from `["hillside", "pipeworks", "skybridge"]`
  - Creates two bots: hold_right (label "→ RIGHT") and hold_left (label "← LEFT")
  - Uses `load_stage()` for dimensions, `make_bot()` for each bot
  - max_frames=3600 (60 seconds — enough to reach edges)

`_readout_boundary_patrol(bots)`:
  - Shows current stage name
  - For each bot: label, X position, escaped? (x < 0 or x > level_width)
  - Shows "Z=NEXT STAGE  X=BACK" instruction

**Modifications to _draw_running()**:
  - After drawing terrain, call `renderer.draw_level_bounds()` when current
    stage is BOUNDARY PATROL
  - Pass level dimensions from the bot's camera (camera.level_width/height)

**STAGES list**: Add `DevParkStage("BOUNDARY PATROL", ...)` to STAGES

**Module state**: Add `_boundary_stage_index: int = 0` for cycling
**Z-key handler in _update_running()**: When stage is BOUNDARY PATROL, Z
cycles `_boundary_stage_index` through 0-2 and reinits bots

### 5. No files created, no files deleted

## Module Boundaries

- **harness.py** exports `hold_left` — used by test_levels.py and devpark.py
- **renderer.py** exports `draw_level_bounds` — used by devpark.py
- **test_levels.py** imports `hold_left` from harness (alongside existing imports)
- **devpark.py** imports `hold_left` from tests.harness (lazy, like other strategies)

## Ordering

1. harness.py (hold_left) — no dependencies
2. renderer.py (draw_level_bounds) — no dependencies
3. test_levels.py (TestBoundaryEscape) — depends on (1)
4. devpark.py (BOUNDARY PATROL) — depends on (1) and (2)

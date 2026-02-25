# Plan — T-001-05: Camera System

## Step 1: Add Camera Constants

**File:** `speednik/constants.py`

Add 12 camera constants after the existing `ANGLE_STEPS` constant:
- `CAMERA_LEFT_BORDER`, `CAMERA_RIGHT_BORDER`, `CAMERA_H_SCROLL_CAP`
- `CAMERA_FOCAL_Y`, `CAMERA_AIR_BORDER`
- `CAMERA_V_SCROLL_GROUND_SLOW`, `CAMERA_V_SCROLL_GROUND_FAST`, `CAMERA_V_SCROLL_AIR`
- `CAMERA_GROUND_SPEED_THRESHOLD`
- `CAMERA_LOOK_UP_MAX`, `CAMERA_LOOK_DOWN_MAX`, `CAMERA_LOOK_SPEED`

**Verification:** Constants import without error.

## Step 2: Add `up_held` to InputState

**File:** `speednik/physics.py`

Add `up_held: bool = False` to the `InputState` dataclass after `down_held`.

**Verification:** Existing tests still pass (`uv run pytest tests/test_player.py`). All existing InputState usage defaults `up_held=False`, so no breakage.

## Step 3: Create `camera.py`

**File:** `speednik/camera.py` (new)

Implement:
1. `Camera` dataclass with fields: `x`, `y`, `look_offset`, `level_width`, `level_height`
2. `create_camera(level_width, level_height, start_x, start_y)` — factory that initializes camera centered on start position, clamped to bounds
3. `camera_update(camera, player, inp)` — main update calling:
   - `_update_horizontal(camera, player_x)` — border-based horizontal scroll
   - `_update_look_offset(camera, inp, on_ground, ground_speed)` — look up/down
   - `_update_vertical(camera, player_y, on_ground, ground_speed)` — speed-dependent vertical scroll
   - `_clamp_to_bounds(camera)` — enforce level boundaries

Key implementation details:
- Horizontal: compute `screen_x = player_x - camera.x`. If `screen_x < LEFT_BORDER`, scroll left by `min(LEFT_BORDER - screen_x, H_SCROLL_CAP)`. If `screen_x > RIGHT_BORDER`, scroll right by `min(screen_x - RIGHT_BORDER, H_SCROLL_CAP)`.
- Vertical ground: `delta = (player_y - FOCAL_Y + look_offset) - camera.y`. Scroll cap = 6 if `|ground_speed| < 8` else 16. `camera.y += clamp(delta, -cap, cap)`.
- Vertical air: `screen_y = player_y - camera.y`. Upper border = `FOCAL_Y - AIR_BORDER`. Lower border = `FOCAL_Y + AIR_BORDER`. Only scroll if outside borders, capped at 16.
- Look: only when `on_ground and ground_speed == 0`. Up → offset toward +LOOK_UP_MAX. Down → offset toward -LOOK_DOWN_MAX. Release → toward 0. Step size = LOOK_SPEED.
- Bounds: clamp `camera.x` to `[0, max(0, level_width - SCREEN_WIDTH)]`, same for y.

**Verification:** Module imports successfully.

## Step 4: Create `tests/test_camera.py`

**File:** `tests/test_camera.py` (new)

Test classes:
1. `TestCreateCamera` — factory produces correct initial state
2. `TestHorizontalTracking` — dead zone behavior, scroll capping, multi-frame convergence
3. `TestVerticalGround` — slow/fast scroll rates, focal point targeting
4. `TestVerticalAir` — border tolerance, scroll when outside borders
5. `TestLookUpDown` — offset accumulation, release, standing-only constraint, clamping
6. `TestBoundaryClamping` — all four edges, small level edge case

Helper: `make_player(x, y, on_ground=True, ground_speed=0.0)` — creates a Player with specified physics state for testing without needing full game setup.

**Verification:** `uv run pytest tests/test_camera.py` — all tests pass.

## Step 5: Integrate into `main.py`

**File:** `speednik/main.py`

Changes:
1. Add imports: `Camera`, `camera_update`, `create_camera` from `speednik.camera`
2. Add `up_held=pyxel.btn(pyxel.KEY_UP)` to `_read_input()`
3. In `App.__init__`:
   - Compute level dimensions from tile data (max tile coords × TILE_SIZE)
   - Replace `self.cam_x = 0.0` with `self.camera = create_camera(level_w, level_h, start_x, start_y)`
4. In `App.update`:
   - Pass `inp` to `camera_update(self.camera, self.player, inp)` after player_update
5. In `App.draw`:
   - Add `pyxel.camera(int(self.camera.x), int(self.camera.y))` at start of draw
   - Remove all `- cam_x` offsets from tile, player, and ring drawing
   - Add `pyxel.camera()` (reset) before HUD text block
   - Adjust HUD text to draw at screen-relative coords (stays the same since camera is reset)

**Verification:** `uv run python -m speednik.main` — visual test that camera follows player with correct behavior. `uv run pytest` — all tests pass.

## Step 6: Run Full Test Suite

**Verification:** `uv run pytest tests/` — all tests pass (both test_player.py and test_camera.py).

## Testing Strategy Summary

| Area | Test Type | Count |
|------|-----------|-------|
| Camera creation | Unit | 2 |
| Horizontal tracking | Unit | 5 |
| Vertical ground | Unit | 3 |
| Vertical air | Unit | 3 |
| Look up/down | Unit | 5 |
| Boundary clamping | Unit | 5 |
| InputState backward compat | Implicit | via existing tests |
| Visual integration | Manual | run game |

Total: ~23 unit tests + manual visual verification.

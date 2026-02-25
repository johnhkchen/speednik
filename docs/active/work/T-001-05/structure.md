# Structure — T-001-05: Camera System

## Files Modified

### `speednik/constants.py`

Add camera constants block after the existing "Angle system" section:

```python
# Camera horizontal
CAMERA_LEFT_BORDER = 144
CAMERA_RIGHT_BORDER = 160
CAMERA_H_SCROLL_CAP = 16

# Camera vertical
CAMERA_FOCAL_Y = 96
CAMERA_AIR_BORDER = 32
CAMERA_V_SCROLL_GROUND_SLOW = 6
CAMERA_V_SCROLL_GROUND_FAST = 16
CAMERA_V_SCROLL_AIR = 16
CAMERA_GROUND_SPEED_THRESHOLD = 8.0

# Camera look
CAMERA_LOOK_UP_MAX = 104
CAMERA_LOOK_DOWN_MAX = 88
CAMERA_LOOK_SPEED = 2
```

### `speednik/physics.py`

Add one field to `InputState`:
```python
up_held: bool = False
```

No other changes. No existing code reads `up_held`, so this is purely additive.

### `speednik/main.py`

Major changes:
1. **Import** `Camera`, `camera_update`, `create_camera` from `speednik.camera`
2. **Import** `up_held`-aware InputState reading: add `pyxel.btn(pyxel.KEY_UP)` to `_read_input()`
3. **Replace** `self.cam_x` with `self.camera = create_camera(level_width, level_height)`
4. **Update** method: replace cam_x lerp with `camera_update(self.camera, self.player, inp)`
5. **Draw** method:
   - Start with `pyxel.camera(int(self.camera.x), int(self.camera.y))`
   - Remove all `- cam_x` manual offsets from tile/player/ring drawing
   - Add `pyxel.camera()` before HUD text drawing

### `tests/test_player.py`

No changes needed. Existing tests use `InputState()` which defaults `up_held=False`. Backward compatible.

## Files Created

### `speednik/camera.py`

New module. Structure:

```
Module docstring

Imports: constants, PhysicsState, InputState from physics

Camera dataclass:
    x: float
    y: float
    look_offset: float
    level_width: int
    level_height: int

create_camera(level_width, level_height, start_x, start_y) -> Camera
    Factory function. Initializes camera centered on start position.

camera_update(camera, player, inp) -> None
    Main update function. Calls sub-functions in order:
    1. _update_horizontal(camera, player_x)
    2. _update_look_offset(camera, inp, player_on_ground, player_ground_speed)
    3. _update_vertical(camera, player_y, player_on_ground, player_ground_speed)
    4. _clamp_to_bounds(camera)

_update_horizontal(camera, player_x) -> None
    Compute player's screen-relative x.
    If left of left border: scroll left, capped at H_SCROLL_CAP.
    If right of right border: scroll right, capped at H_SCROLL_CAP.

_update_look_offset(camera, inp, on_ground, ground_speed) -> None
    Only active when on_ground and ground_speed == 0.
    Shift look_offset toward target at LOOK_SPEED per frame.
    On release / not standing: return toward 0.

_update_vertical(camera, player_y, on_ground, ground_speed) -> None
    Compute target_y = player_y - FOCAL_Y + look_offset.
    If on_ground: scroll toward target, speed-dependent cap.
    If airborne: border-based with ±AIR_BORDER tolerance.

_clamp_to_bounds(camera) -> None
    Clamp x to [0, level_width - SCREEN_WIDTH].
    Clamp y to [0, level_height - SCREEN_HEIGHT].
```

### `tests/test_camera.py`

New test module. Structure:

```
Imports: Camera, create_camera, camera_update + constants

Helper: make_player(x, y, on_ground, ground_speed) -> Player
    Creates a player with specified physics state for camera testing.

TestCreateCamera:
    - test_initial_position: camera centered on start position
    - test_initial_bounds: level dimensions stored correctly

TestHorizontalTracking:
    - test_player_in_dead_zone_no_scroll: player between borders, camera stays
    - test_player_right_of_border_scrolls_right: camera moves right
    - test_player_left_of_border_scrolls_left: camera moves left
    - test_horizontal_scroll_capped: large delta clamped to 16px
    - test_multiple_frames_catch_up: camera catches up over several frames

TestVerticalGround:
    - test_ground_slow_scroll: |ground_speed| < 8 → 6px/frame cap
    - test_ground_fast_scroll: |ground_speed| >= 8 → 16px/frame cap
    - test_ground_scroll_to_focal: camera settles player at focal Y

TestVerticalAir:
    - test_airborne_within_borders_no_scroll: player within ±32 of focal
    - test_airborne_outside_borders_scroll: player beyond borders → scroll
    - test_airborne_scroll_capped: capped at 16px/frame

TestLookUpDown:
    - test_look_up_shifts_offset: up_held → offset increases toward +104
    - test_look_down_shifts_offset: down_held → offset decreases toward -88
    - test_look_release_returns: releasing → offset returns toward 0
    - test_look_only_when_standing: moving player → no look offset change
    - test_look_max_clamp: offset clamped at maximums

TestBoundaryClamping:
    - test_left_boundary: camera.x never negative
    - test_right_boundary: camera.x <= level_width - SCREEN_WIDTH
    - test_top_boundary: camera.y never negative
    - test_bottom_boundary: camera.y <= level_height - SCREEN_HEIGHT
    - test_small_level: level smaller than screen → camera at 0
```

## Module Boundaries

- `camera.py` **reads from** `player.physics` (x, y, ground_speed, on_ground) and `InputState` (up_held, down_held)
- `camera.py` **never writes to** player or physics state
- `camera.py` **imports** constants from `constants.py`
- `camera.py` **does not import** Pyxel — `pyxel.camera()` is called in `main.py`
- `main.py` **owns** the Pyxel integration: calling `pyxel.camera()`, creating the Camera, calling `camera_update()`

## Ordering of Changes

1. Add constants to `constants.py` (no dependencies)
2. Add `up_held` to `InputState` in `physics.py` (no dependencies)
3. Create `camera.py` (depends on 1, 2)
4. Create `tests/test_camera.py` (depends on 3)
5. Modify `main.py` (depends on 3)

Steps 1–2 can be done in parallel. Steps 3–4 can be done together. Step 5 is last.

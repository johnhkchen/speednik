# Progress — T-001-05: Camera System

## Completed

### Step 1: Add Camera Constants
- Added 12 camera constants to `speednik/constants.py`
- Horizontal: `CAMERA_LEFT_BORDER`, `CAMERA_RIGHT_BORDER`, `CAMERA_H_SCROLL_CAP`
- Vertical: `CAMERA_FOCAL_Y`, `CAMERA_AIR_BORDER`, `CAMERA_V_SCROLL_GROUND_SLOW`, `CAMERA_V_SCROLL_GROUND_FAST`, `CAMERA_V_SCROLL_AIR`, `CAMERA_GROUND_SPEED_THRESHOLD`
- Look: `CAMERA_LOOK_UP_MAX`, `CAMERA_LOOK_DOWN_MAX`, `CAMERA_LOOK_SPEED`

### Step 2: Add `up_held` to InputState
- Added `up_held: bool = False` to `InputState` in `speednik/physics.py`
- All 32 existing player tests pass unchanged (backward compatible)

### Step 3: Create `camera.py`
- Created `speednik/camera.py` with:
  - `Camera` dataclass (x, y, look_offset, level_width, level_height)
  - `create_camera()` factory function
  - `camera_update()` main update function
  - `_update_horizontal()` — border-based horizontal tracking
  - `_update_look_offset()` — look up/down with standing-only constraint
  - `_update_vertical()` — speed-dependent vertical tracking with air borders
  - `_clamp_to_bounds()` — level boundary enforcement

### Step 4: Create `tests/test_camera.py`
- 25 unit tests covering:
  - Camera creation and initialization (3 tests)
  - Horizontal border tracking (5 tests)
  - Vertical ground scroll with speed-dependent caps (3 tests)
  - Vertical airborne border tolerance (3 tests)
  - Look up/down offset accumulation and clamping (6 tests)
  - Level boundary clamping (5 tests)
- All 25 tests pass

### Step 5: Integrate into `main.py`
- Added `up_held` mapping to `_read_input()`
- Replaced `self.cam_x` lerp with `create_camera()` + `camera_update()`
- Switched rendering to `pyxel.camera()` for viewport offset
- Removed manual `- cam_x` subtraction from all draw calls
- Added `pyxel.camera()` reset before HUD drawing
- Added vertical tile culling for viewport optimization
- Computed level dimensions from tile data
- Updated controls help text to mention look up/down

### Step 6: Full Test Suite
- All 225 tests pass (25 camera + 32 player + 34 physics + 76 terrain + 58 svg2stage)

## Deviations from Plan

None. All steps executed as planned.

## Remaining

Implementation complete. Review phase next.

# Design — T-001-05: Camera System

## Approach: Sonic 2 Border-Based Camera

### Option A: Dataclass + Pure Function (Chosen)

A `Camera` dataclass holds camera state (position, look offset, level bounds). A `camera_update()` function takes the camera, player state, and input, then computes the new camera position using the Sonic 2 border system.

**Pros:**
- Matches existing codebase pattern (PhysicsState + functions, Player + functions)
- Fully testable without Pyxel — camera logic is pure math
- Clean separation: camera reads player state but never modifies it
- InputState already decouples input from Pyxel; adding `up_held` is trivial

**Cons:**
- Camera state must be passed around (not encapsulated in a class)

### Option B: Camera as Class with Methods

`Camera` class with `update()` and `apply()` methods.

**Rejected:** Inconsistent with the rest of the codebase. Every other module uses dataclass + functions. Introducing class methods here creates a style split. The functional approach is also easier to test.

### Option C: Camera Logic Inline in main.py

No camera module — put the logic directly in App.update().

**Rejected:** Violates the file layout in the spec (`camera.py` is listed as its own module). The logic is substantial enough (~100 lines) to warrant its own file. Also untestable when inline in App.

## Camera Dataclass

```python
@dataclass
class Camera:
    x: float = 0.0           # viewport left edge in world pixels
    y: float = 0.0           # viewport top edge in world pixels
    look_offset: float = 0.0 # vertical offset from look up/down input
    level_width: int = 0     # total level width in pixels
    level_height: int = 0    # total level height in pixels
```

Minimal state. `look_offset` accumulates the 2px/step shift for look up/down. Level dimensions are set at creation time.

## Horizontal Scrolling Algorithm

The Sonic 2 horizontal camera uses two borders within the screen:
- **Left border**: 144px from left edge → player screen_x should not go below 144
- **Right border**: 160px from left edge → player screen_x should not go above 160

```
Screen (256px wide):
[0...144|   dead zone   |160...255]
  left      16px gap        right
  border                    border
```

When the player's screen-relative x falls outside this range:
1. Compute how far outside: `delta = player_screen_x - border`
2. Clamp delta to ±16px/frame (scroll cap)
3. Shift camera.x by delta

When the player is between the borders: no horizontal scroll.

This creates the characteristic Sonic behavior where the camera "lags behind" during direction changes and catches up smoothly.

## Vertical Scrolling Algorithm

### Focal Point

The target y position places the player at 96px from the top of the screen.

### Ground Mode (on_ground = True)

Camera scrolls toward placing the player at the focal point:
- `target_y = player.y - CAMERA_FOCAL_Y`
- `delta = target_y - camera.y`
- Scroll speed depends on `|ground_speed|`:
  - `|ground_speed| < 8`: cap at 6px/frame
  - `|ground_speed| >= 8`: cap at 16px/frame
- Apply: `camera.y += clamp(delta, -scroll_cap, scroll_cap)`

### Airborne Mode (on_ground = False)

Wider tolerance before scrolling:
- **Upper border**: focal_y - 32 = 64px from top
- **Lower border**: focal_y + 32 = 128px from top
- Only scroll when player is outside these borders
- Scroll capped at 16px/frame

This prevents jittery vertical scrolling during jumps while still tracking large vertical movements.

### Look Up/Down

When the player is standing still (`ground_speed == 0`, `on_ground == True`):
- **Up held**: shift `look_offset` toward -104 at 2px/step per frame
- **Down held**: shift `look_offset` toward +88 at 2px/step per frame
- **Neither held**: return `look_offset` toward 0 at 2px/step per frame

The look_offset is added to the target y calculation:
- `target_y = player.y - CAMERA_FOCAL_Y + look_offset`

Note: In Sonic 2, look up shows more above (camera moves up = lower y), and look down shows more below. The signs:
- Up held → look_offset goes negative (camera y decreases, showing more above)
- Down held → look_offset goes positive (camera y increases, showing more below)

The ticket says "pressing up shifts focal down 104px" — this means the focal point on screen moves down, which makes the camera show more above. A focal point moving down from 96px toward 200px means the camera viewport shifts upward. This is achieved by `look_offset = -104` (camera.y decreases by 104).

Wait, re-reading: "pressing up shifts focal down 104px at 2px/step." The focal point is where the player sits on screen. Shifting the focal down means the player appears lower on screen, revealing more of the world above. So `effective_focal = 96 + 104 = 200` when looking up, and `effective_focal = 96 - 88 = 8` when looking down.

Equivalently: `look_offset` ranges from -88 (look down) to +104 (look up), where positive means the focal moves down on screen (player lower = see more above).

## Level Boundary Clamping

After computing the target camera position:
```python
camera.x = clamp(camera.x, 0, level_width - SCREEN_WIDTH)
camera.y = clamp(camera.y, 0, level_height - SCREEN_HEIGHT)
```

If the level is smaller than the screen in either dimension, clamp to 0.

## Pyxel Integration

In `main.py:draw()`:
1. Call `pyxel.camera(int(camera.x), int(camera.y))` before drawing world objects
2. Draw tiles, player, rings (all in world coordinates — no manual offset needed)
3. Call `pyxel.camera()` (reset to 0,0) before drawing HUD text

This replaces the current `cam_x` manual subtraction.

## InputState Change

Add `up_held: bool = False` to InputState. Map to `pyxel.btn(pyxel.KEY_UP)` in `_read_input()`.

This is a minimal, backward-compatible change. Existing code doesn't reference `up_held` so no breakage.

## Constants to Add

All camera constants go in `constants.py`:
```python
# Camera horizontal (§spec)
CAMERA_LEFT_BORDER = 144
CAMERA_RIGHT_BORDER = 160
CAMERA_H_SCROLL_CAP = 16

# Camera vertical (§spec)
CAMERA_FOCAL_Y = 96
CAMERA_AIR_BORDER = 32
CAMERA_V_SCROLL_GROUND_SLOW = 6
CAMERA_V_SCROLL_GROUND_FAST = 16
CAMERA_V_SCROLL_AIR = 16
CAMERA_GROUND_SPEED_THRESHOLD = 8.0

# Camera look (§spec)
CAMERA_LOOK_UP_MAX = 104
CAMERA_LOOK_DOWN_MAX = 88
CAMERA_LOOK_SPEED = 2
```

## Testing Strategy

Camera is pure math — fully testable without Pyxel:
1. **Horizontal tracking**: player within borders → no scroll; player outside → scroll capped at 16
2. **Vertical ground mode**: scroll toward focal with speed-dependent cap
3. **Vertical air mode**: tolerance zone, scroll when outside borders
4. **Look up/down**: offset accumulation, release return, clamping
5. **Level boundary clamping**: camera doesn't go negative or past level edge
6. **Edge cases**: player at level start, player at level end, very small levels

## Decision Summary

- **Architecture**: `Camera` dataclass + `camera_update()` function in `camera.py`
- **Integration**: `pyxel.camera()` replaces manual cam_x subtraction
- **InputState**: Add `up_held` field
- **Constants**: 12 new constants in `constants.py`
- **No player.py changes** — camera only reads player state

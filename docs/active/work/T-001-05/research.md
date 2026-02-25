# Research — T-001-05: Camera System

## Ticket Requirements

Implement Sonic 2 camera with horizontal borders, vertical focal point, speed-dependent scroll rates, look up/down, and level boundary clamping. Must integrate with `pyxel.camera()` and the T-001-04 player demo.

## Specification Constants (from ticket AC)

| Parameter | Value |
|-----------|-------|
| Left horizontal border | 144px from left screen edge |
| Right horizontal border | 160px from left screen edge |
| Horizontal scroll cap | 16px/frame |
| Vertical focal point | 96px from top |
| Airborne vertical borders | focal ± 32px (64px to 128px) |
| Airborne vertical scroll cap | 16px/frame |
| Ground vertical scroll (slow) | 6px/frame when ground_speed < 8 |
| Ground vertical scroll (fast) | 16px/frame when ground_speed >= 8 |
| Look up shift | -104px from focal at 2px/step |
| Look down shift | +88px from focal at 2px/step |
| Look release return | 2px/step back to default |

## Existing Codebase

### Screen dimensions (`constants.py`)

- `SCREEN_WIDTH = 256`, `SCREEN_HEIGHT = 224`, `FPS = 60`
- These define the viewport size. The camera positions the viewport within world space.

### Current camera in `main.py`

Lines 105–106, 117–120: The App currently has a simple smooth-follow camera:
```python
self.cam_x = 0.0
...
target_cam = self.player.physics.x - SCREEN_WIDTH // 2
self.cam_x += (target_cam - self.cam_x) * 0.1
if self.cam_x < 0:
    self.cam_x = 0
```

This is a placeholder lerp-based horizontal-only camera. No vertical scrolling. No borders. No speed dependency. It will be fully replaced.

### How `cam_x` is used in drawing (`main.py:draw`)

- Tile rendering: `screen_x = tx * TILE_SIZE - cam_x` (line 131)
- Player rendering: `draw_x = int(px) - cam_x` (line 145)
- Scattered ring rendering: `rx = int(ring.x) - cam_x` (line 153)
- No `cam_y` offset exists — all y coordinates are world coordinates.

**Key insight:** The draw method manually subtracts `cam_x` from every x coordinate. Pyxel provides `pyxel.camera(x, y)` which sets a global viewport offset, eliminating the need for manual subtraction. The ticket AC requires using `pyxel.camera()`.

### Player state available (`player.py`, `physics.py`)

The camera needs to read from the player:
- `player.physics.x`, `player.physics.y` — player center position in world pixels
- `player.physics.ground_speed` — for speed-dependent vertical scroll rate
- `player.physics.on_ground` — for ground vs airborne scroll behavior
- `player.state` — might need for look-up/look-down detection (but InputState is better)

### InputState (`physics.py`)

```python
@dataclass
class InputState:
    left: bool = False
    right: bool = False
    jump_pressed: bool = False
    jump_held: bool = False
    down_held: bool = False
```

**Missing:** No `up_held` field. Look-up requires detecting up arrow press. This must be added to InputState (or read directly from Pyxel in the camera — but the InputState pattern is better for testability).

### Demo level dimensions (`main.py:_build_demo_level`)

- Flat ground at tile y=12 (pixel 192..208) from tile x=0 to x=49
- Slope tiles at y=11, x=10–13
- Total level: roughly 50 tiles wide × 13 tiles tall = 800px × 208px
- Level is slightly wider than 3 screens (256×3=768)
- Level height is less than one screen (208 < 224), meaning vertical scrolling won't exercise much in the current demo, but the camera still needs to handle it correctly for future levels.

### Module patterns

All modules use:
- Dataclasses for state (`PhysicsState`, `Player`, `InputState`, `Tile`)
- Module-level functions operating on state objects (no class methods)
- Type aliases (e.g., `TileLookup = Callable[...]`)
- Constants imported from `constants.py`

The camera should follow this pattern: a `CameraState` dataclass + `camera_update()` function.

### Pyxel `camera()` API

`pyxel.camera(x, y)` sets the drawing offset. All subsequent `pyxel.rect()`, `pyxel.text()`, etc. calls are offset by (-x, -y). To draw the HUD at fixed screen positions, call `pyxel.camera()` (reset to 0,0) before HUD drawing.

### Level boundary information

The camera must not scroll past level edges. Currently there's no explicit "level width/height" value — the demo level is implicitly defined by which tiles exist. The camera will need level dimensions passed in (or computed from tile data).

## Dependencies and Integration Points

1. **`constants.py`** — needs new camera constants (borders, scroll speeds, etc.)
2. **`physics.py`** — needs `up_held` added to `InputState`
3. **`main.py`** — camera replaces the current cam_x system, draw method switches to `pyxel.camera()`, input reading adds up arrow
4. **`player.py`** — no changes needed (camera reads player state, doesn't modify it)
5. **`terrain.py`** — no changes needed

## Constraints and Assumptions

- **No level module yet.** Level dimensions must be passed to the camera as parameters for now. Future levels (T-002+) will provide this from level data.
- **Look up/down** requires detecting when the player presses up while standing still. The spec says "pressing up shifts focal down 104px" — this means the camera shifts to show more of what's above the player (lower y in screen coords = higher in world). Same logic inverted for down.
- **Sonic 2 camera specifics:** The horizontal border system creates a "dead zone" between 144px and 160px from the left edge. When the player is within this zone, the camera doesn't scroll horizontally. When outside, it scrolls to bring the player back within the border, capped at 16px/frame.
- **Vertical behavior differs between ground and air.** On ground, the camera tries to snap the player to the focal point (96px from top) with speed-dependent scroll rate. In air, the camera has wider tolerance (±32px) and scrolls at 16px/frame when outside those borders.
- **`pyxel.camera()` vs manual offset:** Using `pyxel.camera()` simplifies rendering but requires a `pyxel.camera()` reset before drawing HUD elements.
- **Frame order:** Camera update should happen after player update (needs final player position for the frame).

## Open Questions

1. Should look up/down only activate when standing still, or also while running? Sonic 2 only allows it when standing. The current InputState tracks `down_held` but not `up_held`. Need to add `up_held`.
2. The demo level is very small. The camera's level bounds clamping might need a reasonable default if no level dimensions are provided.

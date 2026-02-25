"""speednik/camera.py — Sonic 2 camera with borders & look-ahead.

Implements horizontal border tracking, vertical focal point with
speed-dependent scroll rates, look up/down, and level boundary clamping.
"""

from __future__ import annotations

from dataclasses import dataclass

from speednik.constants import (
    CAMERA_AIR_BORDER,
    CAMERA_FOCAL_Y,
    CAMERA_GROUND_SPEED_THRESHOLD,
    CAMERA_H_SCROLL_CAP,
    CAMERA_LEFT_BORDER,
    CAMERA_LOOK_DOWN_MAX,
    CAMERA_LOOK_SPEED,
    CAMERA_LOOK_UP_MAX,
    CAMERA_RIGHT_BORDER,
    CAMERA_V_SCROLL_AIR,
    CAMERA_V_SCROLL_GROUND_FAST,
    CAMERA_V_SCROLL_GROUND_SLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from speednik.physics import InputState
from speednik.player import Player


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class Camera:
    """Camera viewport state."""
    x: float = 0.0
    y: float = 0.0
    look_offset: float = 0.0
    level_width: int = 0
    level_height: int = 0


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_camera(
    level_width: int,
    level_height: int,
    start_x: float = 0.0,
    start_y: float = 0.0,
) -> Camera:
    """Create a camera centered on the given start position, clamped to bounds."""
    cam = Camera(
        x=start_x - CAMERA_LEFT_BORDER,
        y=start_y - CAMERA_FOCAL_Y,
        level_width=level_width,
        level_height=level_height,
    )
    _clamp_to_bounds(cam)
    return cam


# ---------------------------------------------------------------------------
# Main update
# ---------------------------------------------------------------------------

def camera_update(camera: Camera, player: Player, inp: InputState) -> None:
    """Update camera position based on player state and input."""
    p = player.physics
    _update_horizontal(camera, p.x)
    _update_look_offset(camera, inp, p.on_ground, p.ground_speed)
    _update_vertical(camera, p.y, p.on_ground, p.ground_speed)
    _clamp_to_bounds(camera)


# ---------------------------------------------------------------------------
# Horizontal tracking
# ---------------------------------------------------------------------------

def _update_horizontal(camera: Camera, player_x: float) -> None:
    """Border-based horizontal scrolling."""
    screen_x = player_x - camera.x

    if screen_x < CAMERA_LEFT_BORDER:
        delta = screen_x - CAMERA_LEFT_BORDER  # negative
        camera.x += max(delta, -CAMERA_H_SCROLL_CAP)
    elif screen_x > CAMERA_RIGHT_BORDER:
        delta = screen_x - CAMERA_RIGHT_BORDER  # positive
        camera.x += min(delta, CAMERA_H_SCROLL_CAP)


# ---------------------------------------------------------------------------
# Look up/down
# ---------------------------------------------------------------------------

def _update_look_offset(
    camera: Camera,
    inp: InputState,
    on_ground: bool,
    ground_speed: float,
) -> None:
    """Update look offset for look up/down input."""
    if on_ground and ground_speed == 0.0:
        if inp.up_held:
            # Look up: shift focal down on screen → show more above
            target = CAMERA_LOOK_UP_MAX
        elif inp.down_held:
            # Look down: shift focal up on screen → show more below
            target = -CAMERA_LOOK_DOWN_MAX
        else:
            target = 0.0
    else:
        target = 0.0

    if camera.look_offset < target:
        camera.look_offset = min(camera.look_offset + CAMERA_LOOK_SPEED, target)
    elif camera.look_offset > target:
        camera.look_offset = max(camera.look_offset - CAMERA_LOOK_SPEED, target)


# ---------------------------------------------------------------------------
# Vertical tracking
# ---------------------------------------------------------------------------

def _update_vertical(
    camera: Camera,
    player_y: float,
    on_ground: bool,
    ground_speed: float,
) -> None:
    """Speed-dependent vertical scrolling with air border tolerance."""
    if on_ground:
        target_y = player_y - CAMERA_FOCAL_Y + camera.look_offset
        delta = target_y - camera.y
        if abs(ground_speed) >= CAMERA_GROUND_SPEED_THRESHOLD:
            cap = CAMERA_V_SCROLL_GROUND_FAST
        else:
            cap = CAMERA_V_SCROLL_GROUND_SLOW
        if delta > 0:
            camera.y += min(delta, cap)
        elif delta < 0:
            camera.y += max(delta, -cap)
    else:
        # Airborne: border-based tolerance
        screen_y = player_y - camera.y
        upper = CAMERA_FOCAL_Y - CAMERA_AIR_BORDER
        lower = CAMERA_FOCAL_Y + CAMERA_AIR_BORDER

        if screen_y < upper:
            delta = screen_y - upper  # negative
            camera.y += max(delta, -CAMERA_V_SCROLL_AIR)
        elif screen_y > lower:
            delta = screen_y - lower  # positive
            camera.y += min(delta, CAMERA_V_SCROLL_AIR)


# ---------------------------------------------------------------------------
# Boundary clamping
# ---------------------------------------------------------------------------

def _clamp_to_bounds(camera: Camera) -> None:
    """Clamp camera position to level boundaries."""
    max_x = max(0, camera.level_width - SCREEN_WIDTH)
    max_y = max(0, camera.level_height - SCREEN_HEIGHT)
    camera.x = max(0.0, min(camera.x, float(max_x)))
    camera.y = max(0.0, min(camera.y, float(max_y)))

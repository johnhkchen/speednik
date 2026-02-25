"""Tests for speednik/camera.py — Sonic 2 camera system."""

from __future__ import annotations

import pytest

from speednik.camera import Camera, camera_update, create_camera
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
from speednik.player import Player, PlayerState, create_player


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_player(
    x: float = 400.0,
    y: float = 300.0,
    on_ground: bool = True,
    ground_speed: float = 0.0,
) -> Player:
    """Create a player with specified physics state for camera testing."""
    p = create_player(x, y)
    p.physics.on_ground = on_ground
    p.physics.ground_speed = ground_speed
    return p


def make_camera(
    player_x: float = 400.0,
    player_y: float = 300.0,
    level_width: int = 4800,
    level_height: int = 720,
) -> Camera:
    """Create a camera centered on a position in a large level."""
    return create_camera(level_width, level_height, player_x, player_y)


# ---------------------------------------------------------------------------
# TestCreateCamera
# ---------------------------------------------------------------------------

class TestCreateCamera:
    def test_initial_position(self):
        """Camera initializes with player at left border position."""
        cam = create_camera(4800, 720, 400.0, 300.0)
        # Player screen_x should be at CAMERA_LEFT_BORDER
        screen_x = 400.0 - cam.x
        assert screen_x == pytest.approx(CAMERA_LEFT_BORDER)
        # Player screen_y should be at CAMERA_FOCAL_Y
        screen_y = 300.0 - cam.y
        assert screen_y == pytest.approx(CAMERA_FOCAL_Y)

    def test_initial_bounds_stored(self):
        cam = create_camera(4800, 720, 400.0, 300.0)
        assert cam.level_width == 4800
        assert cam.level_height == 720

    def test_initial_clamp_near_origin(self):
        """Camera at level start clamps to (0, 0)."""
        cam = create_camera(4800, 720, 10.0, 10.0)
        assert cam.x >= 0.0
        assert cam.y >= 0.0


# ---------------------------------------------------------------------------
# TestHorizontalTracking
# ---------------------------------------------------------------------------

class TestHorizontalTracking:
    def test_player_in_dead_zone_no_scroll(self):
        """Player between left and right borders — camera doesn't move."""
        cam = make_camera(400.0, 300.0)
        # Place player exactly at midpoint of dead zone
        mid = cam.x + (CAMERA_LEFT_BORDER + CAMERA_RIGHT_BORDER) / 2
        player = make_player(x=mid, y=300.0)
        inp = InputState()
        old_x = cam.x

        camera_update(cam, player, inp)

        assert cam.x == pytest.approx(old_x)

    def test_player_right_of_border_scrolls_right(self):
        """Player past right border — camera scrolls right."""
        cam = make_camera(400.0, 300.0)
        # Move player 10px past right border
        player = make_player(x=cam.x + CAMERA_RIGHT_BORDER + 10, y=300.0)
        inp = InputState()
        old_x = cam.x

        camera_update(cam, player, inp)

        assert cam.x > old_x
        assert cam.x == pytest.approx(old_x + 10)  # delta 10 < cap 16

    def test_player_left_of_border_scrolls_left(self):
        """Player past left border — camera scrolls left."""
        cam = make_camera(400.0, 300.0)
        player = make_player(x=cam.x + CAMERA_LEFT_BORDER - 8, y=300.0)
        inp = InputState()
        old_x = cam.x

        camera_update(cam, player, inp)

        assert cam.x < old_x
        assert cam.x == pytest.approx(old_x - 8)  # delta 8 < cap 16

    def test_horizontal_scroll_capped(self):
        """Large delta clamped to 16px/frame."""
        cam = make_camera(400.0, 300.0)
        # Move player 50px past right border
        player = make_player(x=cam.x + CAMERA_RIGHT_BORDER + 50, y=300.0)
        inp = InputState()
        old_x = cam.x

        camera_update(cam, player, inp)

        assert cam.x == pytest.approx(old_x + CAMERA_H_SCROLL_CAP)

    def test_multiple_frames_catch_up(self):
        """Camera catches up to player over multiple frames."""
        cam = make_camera(400.0, 300.0)
        player = make_player(x=cam.x + CAMERA_RIGHT_BORDER + 50, y=300.0)
        inp = InputState()

        for _ in range(10):
            camera_update(cam, player, inp)

        # After enough frames, player should be within borders
        screen_x = player.physics.x - cam.x
        assert CAMERA_LEFT_BORDER <= screen_x <= CAMERA_RIGHT_BORDER


# ---------------------------------------------------------------------------
# TestVerticalGround
# ---------------------------------------------------------------------------

class TestVerticalGround:
    def test_ground_slow_scroll(self):
        """Slow ground speed (< 8) → 6px/frame vertical scroll cap."""
        cam = make_camera(400.0, 300.0)
        # Move player 20px below focal
        player = make_player(x=400.0, y=cam.y + CAMERA_FOCAL_Y + 20, ground_speed=3.0)
        inp = InputState()
        old_y = cam.y

        camera_update(cam, player, inp)

        delta = cam.y - old_y
        assert delta == pytest.approx(CAMERA_V_SCROLL_GROUND_SLOW)

    def test_ground_fast_scroll(self):
        """Fast ground speed (>= 8) → 16px/frame vertical scroll cap."""
        cam = make_camera(400.0, 300.0)
        player = make_player(x=400.0, y=cam.y + CAMERA_FOCAL_Y + 50, ground_speed=10.0)
        inp = InputState()
        old_y = cam.y

        camera_update(cam, player, inp)

        delta = cam.y - old_y
        assert delta == pytest.approx(CAMERA_V_SCROLL_GROUND_FAST)

    def test_ground_scroll_to_focal(self):
        """Camera settles with player at focal Y over multiple frames."""
        cam = make_camera(400.0, 300.0)
        player = make_player(x=400.0, y=cam.y + CAMERA_FOCAL_Y + 50, ground_speed=10.0)
        inp = InputState()

        for _ in range(50):
            camera_update(cam, player, inp)

        screen_y = player.physics.y - cam.y
        assert screen_y == pytest.approx(CAMERA_FOCAL_Y, abs=1.0)


# ---------------------------------------------------------------------------
# TestVerticalAir
# ---------------------------------------------------------------------------

class TestVerticalAir:
    def test_airborne_within_borders_no_scroll(self):
        """Player within ±32px of focal — no vertical scroll."""
        cam = make_camera(400.0, 300.0)
        # Player at exactly the focal point
        player = make_player(x=400.0, y=cam.y + CAMERA_FOCAL_Y, on_ground=False)
        inp = InputState()
        old_y = cam.y

        camera_update(cam, player, inp)

        assert cam.y == pytest.approx(old_y)

    def test_airborne_outside_lower_border_scrolls(self):
        """Player below lower air border — camera scrolls down."""
        cam = make_camera(400.0, 300.0)
        lower_border = CAMERA_FOCAL_Y + CAMERA_AIR_BORDER
        player = make_player(x=400.0, y=cam.y + lower_border + 10, on_ground=False)
        inp = InputState()
        old_y = cam.y

        camera_update(cam, player, inp)

        assert cam.y > old_y
        assert cam.y == pytest.approx(old_y + 10)  # 10 < cap 16

    def test_airborne_scroll_capped(self):
        """Large airborne delta clamped to 16px/frame."""
        cam = make_camera(400.0, 300.0)
        lower_border = CAMERA_FOCAL_Y + CAMERA_AIR_BORDER
        player = make_player(x=400.0, y=cam.y + lower_border + 50, on_ground=False)
        inp = InputState()
        old_y = cam.y

        camera_update(cam, player, inp)

        assert cam.y == pytest.approx(old_y + CAMERA_V_SCROLL_AIR)


# ---------------------------------------------------------------------------
# TestLookUpDown
# ---------------------------------------------------------------------------

class TestLookUpDown:
    def test_look_up_shifts_offset(self):
        """Holding up while standing increases look_offset toward max."""
        cam = make_camera(400.0, 300.0)
        player = make_player(x=400.0, y=cam.y + CAMERA_FOCAL_Y, ground_speed=0.0)
        inp = InputState(up_held=True)

        camera_update(cam, player, inp)

        assert cam.look_offset == pytest.approx(CAMERA_LOOK_SPEED)

    def test_look_down_shifts_offset(self):
        """Holding down while standing decreases look_offset toward -max."""
        cam = make_camera(400.0, 300.0)
        player = make_player(x=400.0, y=cam.y + CAMERA_FOCAL_Y, ground_speed=0.0)
        inp = InputState(down_held=True)

        camera_update(cam, player, inp)

        assert cam.look_offset == pytest.approx(-CAMERA_LOOK_SPEED)

    def test_look_release_returns(self):
        """Releasing look input returns offset toward 0."""
        cam = make_camera(400.0, 300.0)
        cam.look_offset = 20.0
        player = make_player(x=400.0, y=cam.y + CAMERA_FOCAL_Y, ground_speed=0.0)
        inp = InputState()  # no up or down

        camera_update(cam, player, inp)

        assert cam.look_offset == pytest.approx(20.0 - CAMERA_LOOK_SPEED)

    def test_look_only_when_standing_still(self):
        """Moving player → look offset returns to 0, not accumulated."""
        cam = make_camera(400.0, 300.0)
        cam.look_offset = 0.0
        player = make_player(x=400.0, y=cam.y + CAMERA_FOCAL_Y, ground_speed=3.0)
        inp = InputState(up_held=True)

        camera_update(cam, player, inp)

        # Not standing still, so offset should not increase
        assert cam.look_offset == pytest.approx(0.0)

    def test_look_up_max_clamp(self):
        """Look offset clamped at CAMERA_LOOK_UP_MAX."""
        cam = make_camera(400.0, 300.0)
        cam.look_offset = float(CAMERA_LOOK_UP_MAX)
        player = make_player(x=400.0, y=cam.y + CAMERA_FOCAL_Y, ground_speed=0.0)
        inp = InputState(up_held=True)

        camera_update(cam, player, inp)

        assert cam.look_offset == pytest.approx(CAMERA_LOOK_UP_MAX)

    def test_look_down_max_clamp(self):
        """Look offset clamped at -CAMERA_LOOK_DOWN_MAX."""
        cam = make_camera(400.0, 300.0)
        cam.look_offset = float(-CAMERA_LOOK_DOWN_MAX)
        player = make_player(x=400.0, y=cam.y + CAMERA_FOCAL_Y, ground_speed=0.0)
        inp = InputState(down_held=True)

        camera_update(cam, player, inp)

        assert cam.look_offset == pytest.approx(-CAMERA_LOOK_DOWN_MAX)


# ---------------------------------------------------------------------------
# TestBoundaryClamping
# ---------------------------------------------------------------------------

class TestBoundaryClamping:
    def test_left_boundary(self):
        """Camera x never goes negative."""
        cam = create_camera(4800, 720, 10.0, 300.0)
        assert cam.x >= 0.0

        # Push camera left with player near origin
        player = make_player(x=5.0, y=300.0)
        inp = InputState()
        camera_update(cam, player, inp)
        assert cam.x >= 0.0

    def test_right_boundary(self):
        """Camera x does not exceed level_width - SCREEN_WIDTH."""
        max_x = 4800 - SCREEN_WIDTH
        cam = create_camera(4800, 720, 4790.0, 300.0)
        assert cam.x <= max_x

    def test_top_boundary(self):
        """Camera y never goes negative."""
        cam = create_camera(4800, 720, 400.0, 10.0)
        assert cam.y >= 0.0

    def test_bottom_boundary(self):
        """Camera y does not exceed level_height - SCREEN_HEIGHT."""
        max_y = 720 - SCREEN_HEIGHT
        cam = create_camera(4800, 720, 400.0, 710.0)
        assert cam.y <= max_y

    def test_small_level(self):
        """Level smaller than screen → camera stays at 0."""
        cam = create_camera(200, 200, 100.0, 100.0)
        assert cam.x == 0.0
        assert cam.y == 0.0

        player = make_player(x=150.0, y=150.0)
        inp = InputState()
        camera_update(cam, player, inp)
        assert cam.x == 0.0
        assert cam.y == 0.0

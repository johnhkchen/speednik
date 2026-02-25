"""Tests for speednik/debug.py and debug HUD overlay (T-009-01)."""

from __future__ import annotations

import importlib
import os
from unittest.mock import patch

import pytest

from speednik.physics import PhysicsState
from speednik.player import Player, PlayerState, create_player


# ---------------------------------------------------------------------------
# Debug flag
# ---------------------------------------------------------------------------

class TestDebugFlag:
    def test_debug_false_by_default(self):
        """DEBUG is False when SPEEDNIK_DEBUG is not set."""
        with patch.dict(os.environ, {}, clear=True):
            import speednik.debug
            importlib.reload(speednik.debug)
            assert speednik.debug.DEBUG is False

    def test_debug_true_when_set(self):
        """DEBUG is True when SPEEDNIK_DEBUG=1."""
        with patch.dict(os.environ, {"SPEEDNIK_DEBUG": "1"}):
            import speednik.debug
            importlib.reload(speednik.debug)
            assert speednik.debug.DEBUG is True

    def test_debug_false_when_zero(self):
        """DEBUG is False when SPEEDNIK_DEBUG=0."""
        with patch.dict(os.environ, {"SPEEDNIK_DEBUG": "0"}):
            import speednik.debug
            importlib.reload(speednik.debug)
            assert speednik.debug.DEBUG is False

    def test_debug_false_when_empty(self):
        """DEBUG is False when SPEEDNIK_DEBUG is empty string."""
        with patch.dict(os.environ, {"SPEEDNIK_DEBUG": ""}):
            import speednik.debug
            importlib.reload(speednik.debug)
            assert speednik.debug.DEBUG is False


# ---------------------------------------------------------------------------
# Debug HUD rendering
# ---------------------------------------------------------------------------

class TestDebugHUD:
    def _make_player(self, x=100.0, y=200.0, gs=3.5, angle=32,
                     on_ground=True, state=PlayerState.RUNNING) -> Player:
        player = create_player(x, y)
        player.physics.ground_speed = gs
        player.physics.angle = angle
        player.physics.on_ground = on_ground
        player.state = state
        return player

    @patch("speednik.renderer.pyxel")
    def test_draws_three_lines(self, mock_pyxel):
        from speednik.renderer import draw_debug_hud
        player = self._make_player()
        draw_debug_hud(player, frame_counter=1234)
        assert mock_pyxel.text.call_count == 3

    @patch("speednik.renderer.pyxel")
    def test_shows_frame_counter(self, mock_pyxel):
        from speednik.renderer import draw_debug_hud
        player = self._make_player()
        draw_debug_hud(player, frame_counter=5678)
        calls = [str(c) for c in mock_pyxel.text.call_args_list]
        assert any("F:5678" in c for c in calls)

    @patch("speednik.renderer.pyxel")
    def test_shows_position(self, mock_pyxel):
        from speednik.renderer import draw_debug_hud
        player = self._make_player(x=3456.2, y=512.0)
        draw_debug_hud(player, frame_counter=0)
        calls = [str(c) for c in mock_pyxel.text.call_args_list]
        assert any("X:3456.2" in c for c in calls)
        assert any("Y:512.0" in c for c in calls)

    @patch("speednik.renderer.pyxel")
    def test_shows_ground_speed(self, mock_pyxel):
        from speednik.renderer import draw_debug_hud
        player = self._make_player(gs=6.0)
        draw_debug_hud(player, frame_counter=0)
        calls = [str(c) for c in mock_pyxel.text.call_args_list]
        assert any("GS:6.00" in c for c in calls)

    @patch("speednik.renderer.pyxel")
    def test_shows_angle_and_quadrant(self, mock_pyxel):
        from speednik.renderer import draw_debug_hud
        player = self._make_player(angle=128)
        draw_debug_hud(player, frame_counter=0)
        calls = [str(c) for c in mock_pyxel.text.call_args_list]
        assert any("A:128" in c for c in calls)
        assert any("Q:2" in c for c in calls)  # 128 // 64 = 2

    @patch("speednik.renderer.pyxel")
    def test_shows_state(self, mock_pyxel):
        from speednik.renderer import draw_debug_hud
        player = self._make_player(state=PlayerState.ROLLING)
        draw_debug_hud(player, frame_counter=0)
        calls = [str(c) for c in mock_pyxel.text.call_args_list]
        assert any("STATE:rolling" in c for c in calls)

    @patch("speednik.renderer.pyxel")
    def test_shows_ground_flag_yes(self, mock_pyxel):
        from speednik.renderer import draw_debug_hud
        player = self._make_player(on_ground=True)
        draw_debug_hud(player, frame_counter=0)
        calls = [str(c) for c in mock_pyxel.text.call_args_list]
        assert any("GND:Y" in c for c in calls)

    @patch("speednik.renderer.pyxel")
    def test_shows_ground_flag_no(self, mock_pyxel):
        from speednik.renderer import draw_debug_hud
        player = self._make_player(on_ground=False)
        draw_debug_hud(player, frame_counter=0)
        calls = [str(c) for c in mock_pyxel.text.call_args_list]
        assert any("GND:N" in c for c in calls)

    @patch("speednik.renderer.pyxel")
    def test_positioned_in_top_right(self, mock_pyxel):
        from speednik.renderer import draw_debug_hud
        player = self._make_player()
        draw_debug_hud(player, frame_counter=0)
        # All text calls should have x >= 136 (right half of 256px screen)
        for call in mock_pyxel.text.call_args_list:
            x = call[0][0]
            assert x >= 136, f"Debug HUD text at x={x}, expected >= 136"

    @patch("speednik.renderer.pyxel")
    def test_positioned_below_main_hud(self, mock_pyxel):
        from speednik.renderer import draw_debug_hud
        player = self._make_player()
        draw_debug_hud(player, frame_counter=0)
        # All text calls should have y >= 14 (below main HUD at y=4)
        for call in mock_pyxel.text.call_args_list:
            y = call[0][1]
            assert y >= 14, f"Debug HUD text at y={y}, expected >= 14"

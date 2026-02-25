"""Tests for speednik/renderer.py — palette, dispatch, culling, particles, HUD."""

from __future__ import annotations

import math
from unittest.mock import MagicMock, call, patch

import pytest

from speednik.player import Player, PlayerState, ScatteredRing, create_player
from speednik.physics import PhysicsState
from speednik.terrain import FULL, TILE_SIZE, Tile


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

class TestPalette:
    def test_base_palette_has_required_slots(self):
        from speednik.renderer import _BASE_PALETTE
        # Fixed slots: 0, 4–12
        for slot in (0, 4, 5, 6, 7, 8, 9, 10, 11, 12):
            assert slot in _BASE_PALETTE, f"Missing palette slot {slot}"

    def test_stage_palettes_have_terrain_slots(self):
        from speednik.renderer import STAGE_PALETTES
        for name, pal in STAGE_PALETTES.items():
            for slot in (1, 2, 3, 13, 14, 15):
                assert slot in pal, f"Stage {name} missing slot {slot}"

    def test_all_stages_present(self):
        from speednik.renderer import STAGE_PALETTES
        assert "hillside" in STAGE_PALETTES
        assert "pipeworks" in STAGE_PALETTES
        assert "skybridge" in STAGE_PALETTES

    def test_palette_values_are_ints(self):
        from speednik.renderer import _BASE_PALETTE, STAGE_PALETTES
        for slot, val in _BASE_PALETTE.items():
            assert isinstance(val, int), f"Slot {slot} value is not int"
        for name, pal in STAGE_PALETTES.items():
            for slot, val in pal.items():
                assert isinstance(val, int), f"{name} slot {slot} not int"


# ---------------------------------------------------------------------------
# Player draw dispatch
# ---------------------------------------------------------------------------

class TestPlayerDrawDispatch:
    def _make_player(self, state: PlayerState, anim: str, **kwargs) -> Player:
        p = create_player(100.0, 100.0)
        p.state = state
        p.anim_name = anim
        for k, v in kwargs.items():
            setattr(p, k, v)
        return p

    @patch("speednik.renderer.pyxel")
    def test_idle_draws_ellipse(self, mock_pyxel):
        from speednik.renderer import draw_player
        player = self._make_player(PlayerState.STANDING, "idle")
        draw_player(player, frame_count=0)
        # Should call elli for body
        assert mock_pyxel.elli.called

    @patch("speednik.renderer.pyxel")
    def test_running_draws_body_and_legs(self, mock_pyxel):
        from speednik.renderer import draw_player
        player = self._make_player(PlayerState.RUNNING, "running", anim_frame=2)
        draw_player(player, frame_count=0)
        # Should call elli (body) and line (limbs)
        assert mock_pyxel.elli.called
        assert mock_pyxel.line.called

    @patch("speednik.renderer.pyxel")
    def test_rolling_draws_circle(self, mock_pyxel):
        from speednik.renderer import draw_player
        player = self._make_player(PlayerState.JUMPING, "rolling")
        draw_player(player, frame_count=10)
        # Should call circ for ball
        assert mock_pyxel.circ.called

    @patch("speednik.renderer.pyxel")
    def test_invulnerable_flicker_skips_draw(self, mock_pyxel):
        from speednik.renderer import draw_player
        player = self._make_player(PlayerState.STANDING, "idle",
                                    invulnerability_timer=60)
        # frame_count % 4 < 2 → skip
        draw_player(player, frame_count=0)
        assert not mock_pyxel.elli.called

    @patch("speednik.renderer.pyxel")
    def test_invulnerable_visible_frame(self, mock_pyxel):
        from speednik.renderer import draw_player
        player = self._make_player(PlayerState.STANDING, "idle",
                                    invulnerability_timer=60)
        # frame_count=2 → 2 % 4 = 2, not < 2 → draw
        draw_player(player, frame_count=2)
        assert mock_pyxel.elli.called

    @patch("speednik.renderer.pyxel")
    def test_spindash_draws_ball_and_dust(self, mock_pyxel):
        from speednik.renderer import draw_player
        player = self._make_player(PlayerState.SPINDASH, "spindash")
        draw_player(player, frame_count=5)
        # Should draw circle (ball) and pset (dust)
        assert mock_pyxel.circ.called
        assert mock_pyxel.pset.called

    @patch("speednik.renderer.pyxel")
    def test_hurt_draws_body(self, mock_pyxel):
        from speednik.renderer import draw_player
        player = self._make_player(PlayerState.HURT, "hurt")
        draw_player(player, frame_count=2)
        assert mock_pyxel.elli.called


# ---------------------------------------------------------------------------
# Terrain culling
# ---------------------------------------------------------------------------

class TestTerrainCulling:
    def _make_tiles(self):
        """Create a grid of tiles for testing culling."""
        tiles = {}
        for tx in range(10):
            tiles[(tx, 5)] = Tile(
                height_array=[TILE_SIZE] * TILE_SIZE,
                angle=0,
                solidity=FULL,
            )
        return tiles

    @patch("speednik.renderer.pyxel")
    def test_tiles_outside_viewport_not_drawn(self, mock_pyxel):
        from speednik.renderer import draw_terrain
        tiles = self._make_tiles()
        # Camera at (200, 0) — tiles 0–9 are at x=0..160, camera sees x=200..456
        # Only tiles at x >= 200 - 16 = 184 should be drawn (tiles 12+)
        # None of our tiles (0–9, x=0..160) should be drawn
        draw_terrain(tiles, 300, 0)
        assert not mock_pyxel.line.called
        assert not mock_pyxel.pset.called

    @patch("speednik.renderer.pyxel")
    def test_visible_tiles_are_drawn(self, mock_pyxel):
        from speednik.renderer import draw_terrain
        tiles = self._make_tiles()
        # Camera at (0, 64) — all tiles at y=80 should be visible
        draw_terrain(tiles, 0, 64)
        assert mock_pyxel.line.called


# ---------------------------------------------------------------------------
# Particles
# ---------------------------------------------------------------------------

class TestParticles:
    def setup_method(self):
        """Clear particle list before each test."""
        from speednik import renderer
        renderer._particles.clear()

    @patch("speednik.renderer.pyxel")
    def test_spawn_creates_particles(self, mock_pyxel):
        from speednik.renderer import spawn_destroy_particles, _particles
        spawn_destroy_particles(100.0, 100.0)
        assert len(_particles) == 6

    @patch("speednik.renderer.pyxel")
    def test_particles_have_velocity(self, mock_pyxel):
        from speednik.renderer import spawn_destroy_particles, _particles
        spawn_destroy_particles(50.0, 50.0)
        for p in _particles:
            assert p.vx != 0 or p.vy != 0

    @patch("speednik.renderer.pyxel")
    def test_particles_expire_after_lifetime(self, mock_pyxel):
        from speednik.renderer import spawn_destroy_particles, draw_particles, _particles
        spawn_destroy_particles(50.0, 50.0)
        # Tick 15 frames — all should expire
        for i in range(16):
            draw_particles(i)
        assert len(_particles) == 0

    @patch("speednik.renderer.pyxel")
    def test_particles_survive_during_lifetime(self, mock_pyxel):
        from speednik.renderer import spawn_destroy_particles, draw_particles, _particles
        spawn_destroy_particles(50.0, 50.0)
        draw_particles(0)
        # After 1 tick, all 6 should still be alive (life=14)
        assert len(_particles) == 6


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------

class TestHUD:
    @patch("speednik.renderer.pyxel")
    def test_hud_shows_ring_count(self, mock_pyxel):
        from speednik.renderer import draw_hud
        player = create_player(0, 0)
        player.rings = 42
        draw_hud(player, timer_frames=0, frame_count=0)
        # Check that text was called with ring count
        calls = [str(c) for c in mock_pyxel.text.call_args_list]
        ring_text_found = any("42" in c for c in calls)
        assert ring_text_found, f"Ring count 42 not found in text calls: {calls}"

    @patch("speednik.renderer.pyxel")
    def test_hud_ring_flash_at_zero(self, mock_pyxel):
        from speednik.renderer import draw_hud
        player = create_player(0, 0)
        player.rings = 0
        # frame_count=0: 0 % 60 = 0, which is < 30, so flash color 9
        draw_hud(player, timer_frames=0, frame_count=0)
        # pyxel.text(x, y, string, color) — color is 4th positional arg
        ring_call = mock_pyxel.text.call_args_list[0]
        assert ring_call[0][3] == 9  # Color arg is orange flash

    @patch("speednik.renderer.pyxel")
    def test_hud_ring_normal_color_when_nonzero(self, mock_pyxel):
        from speednik.renderer import draw_hud
        player = create_player(0, 0)
        player.rings = 10
        draw_hud(player, timer_frames=0, frame_count=0)
        ring_call = mock_pyxel.text.call_args_list[0]
        assert ring_call[0][3] == 7  # Normal yellow

    @patch("speednik.renderer.pyxel")
    def test_hud_timer_format(self, mock_pyxel):
        from speednik.renderer import draw_hud
        player = create_player(0, 0)
        # 90 seconds = 1 minute 30 seconds
        draw_hud(player, timer_frames=90 * 60, frame_count=0)
        calls = [str(c) for c in mock_pyxel.text.call_args_list]
        timer_found = any("1:30" in c for c in calls)
        assert timer_found, f"Timer 1:30 not found in: {calls}"

    @patch("speednik.renderer.pyxel")
    def test_hud_lives_display(self, mock_pyxel):
        from speednik.renderer import draw_hud
        player = create_player(0, 0)
        player.lives = 5
        draw_hud(player, timer_frames=0, frame_count=0)
        calls = [str(c) for c in mock_pyxel.text.call_args_list]
        lives_found = any("x5" in c for c in calls)
        assert lives_found, f"Lives x5 not found in: {calls}"


# ---------------------------------------------------------------------------
# Entity dispatch
# ---------------------------------------------------------------------------

class TestEntityDispatch:
    @patch("speednik.renderer.pyxel")
    def test_ring_entity_draws(self, mock_pyxel):
        from speednik.renderer import draw_entities
        entities = [{"type": "ring", "x": 100, "y": 50}]
        draw_entities(entities, frame_count=0)
        assert mock_pyxel.circ.called

    @patch("speednik.renderer.pyxel")
    def test_enemy_crab_draws(self, mock_pyxel):
        from speednik.renderer import draw_entities
        entities = [{"type": "enemy_crab", "x": 200, "y": 100}]
        draw_entities(entities, frame_count=0)
        assert mock_pyxel.elli.called

    @patch("speednik.renderer.pyxel")
    def test_enemy_buzzer_draws(self, mock_pyxel):
        from speednik.renderer import draw_entities
        entities = [{"type": "enemy_buzzer", "x": 200, "y": 100}]
        draw_entities(entities, frame_count=0)
        assert mock_pyxel.circ.called
        assert mock_pyxel.tri.called

    @patch("speednik.renderer.pyxel")
    def test_unknown_entity_skipped(self, mock_pyxel):
        from speednik.renderer import draw_entities
        entities = [{"type": "unknown_thing", "x": 200, "y": 100}]
        draw_entities(entities, frame_count=0)
        # No drawing should occur
        assert not mock_pyxel.circ.called
        assert not mock_pyxel.rect.called
        assert not mock_pyxel.elli.called

    @patch("speednik.renderer.pyxel")
    def test_checkpoint_draws(self, mock_pyxel):
        from speednik.renderer import draw_entities
        entities = [{"type": "checkpoint", "x": 300, "y": 200}]
        draw_entities(entities, frame_count=0)
        assert mock_pyxel.line.called

    @patch("speednik.renderer.pyxel")
    def test_goal_draws(self, mock_pyxel):
        from speednik.renderer import draw_entities
        entities = [{"type": "goal", "x": 400, "y": 200}]
        draw_entities(entities, frame_count=0)
        assert mock_pyxel.line.called
        assert mock_pyxel.rect.called

    @patch("speednik.renderer.pyxel")
    def test_multiple_entities(self, mock_pyxel):
        from speednik.renderer import draw_entities
        entities = [
            {"type": "ring", "x": 100, "y": 50},
            {"type": "enemy_crab", "x": 200, "y": 100},
            {"type": "goal", "x": 400, "y": 200},
        ]
        draw_entities(entities, frame_count=0)
        assert mock_pyxel.circ.called
        assert mock_pyxel.elli.called


# ---------------------------------------------------------------------------
# Scattered rings
# ---------------------------------------------------------------------------

class TestScatteredRings:
    @patch("speednik.renderer.pyxel")
    def test_draws_active_rings(self, mock_pyxel):
        from speednik.renderer import draw_scattered_rings
        rings = [
            ScatteredRing(x=50.0, y=60.0, vx=1.0, vy=-2.0, timer=100),
            ScatteredRing(x=80.0, y=70.0, vx=-1.0, vy=-1.0, timer=30),
        ]
        draw_scattered_rings(rings, frame_count=0)
        assert mock_pyxel.circ.call_count == 2

    @patch("speednik.renderer.pyxel")
    def test_fading_rings_use_darker_color(self, mock_pyxel):
        from speednik.renderer import draw_scattered_rings
        rings = [
            ScatteredRing(x=50.0, y=60.0, vx=1.0, vy=-2.0, timer=30),
        ]
        draw_scattered_rings(rings, frame_count=0)
        # Timer < 60 → color 9 (orange/dim)
        circ_call = mock_pyxel.circ.call_args_list[0]
        assert circ_call[0][3] == 9  # 4th positional arg is color

    @patch("speednik.renderer.pyxel")
    def test_bright_rings_use_yellow(self, mock_pyxel):
        from speednik.renderer import draw_scattered_rings
        rings = [
            ScatteredRing(x=50.0, y=60.0, vx=1.0, vy=-2.0, timer=100),
        ]
        draw_scattered_rings(rings, frame_count=0)
        circ_call = mock_pyxel.circ.call_args_list[0]
        assert circ_call[0][3] == 7  # Color 7 = yellow


# ---------------------------------------------------------------------------
# Facing direction
# ---------------------------------------------------------------------------

class TestFacingDirection:
    @patch("speednik.renderer.pyxel")
    def test_idle_facing_right_eye_position(self, mock_pyxel):
        from speednik.renderer import _draw_player_idle
        _draw_player_idle(100, 100, right=True)
        # Eyes should be at cx+1, cx+2 (right-facing)
        pset_calls = mock_pyxel.pset.call_args_list
        eye_xs = [c[0][0] for c in pset_calls if c[0][2] == 11]
        assert 101 in eye_xs  # cx + 1

    @patch("speednik.renderer.pyxel")
    def test_idle_facing_left_eye_position(self, mock_pyxel):
        from speednik.renderer import _draw_player_idle
        _draw_player_idle(100, 100, right=False)
        pset_calls = mock_pyxel.pset.call_args_list
        eye_xs = [c[0][0] for c in pset_calls if c[0][2] == 11]
        assert 99 in eye_xs  # cx - 1

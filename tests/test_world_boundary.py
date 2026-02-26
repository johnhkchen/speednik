"""tests/test_world_boundary.py — Tests for world boundary enforcement in sim_step."""

from __future__ import annotations

import pytest

from speednik.physics import InputState
from speednik.player import PlayerState, create_player
from speednik.simulation import DeathEvent, create_sim_from_lookup, sim_step
from speednik.terrain import TILE_SIZE, Tile, FULL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flat_tile() -> Tile:
    return Tile(height_array=[TILE_SIZE] * TILE_SIZE, angle=0, solidity=FULL)


def _ground_at_row(ground_row: int):
    """Tile lookup with flat ground at ground_row and below."""
    def lookup(tx: int, ty: int) -> Tile | None:
        if ty >= ground_row:
            return _flat_tile()
        return None
    return lookup


def _empty_lookup(tx: int, ty: int) -> Tile | None:
    return None


def _make_sim(level_width: int = 500, level_height: int = 500):
    """Create a small sim for boundary testing."""
    ground_row = level_height // TILE_SIZE
    lookup = _ground_at_row(ground_row)
    start_y = float(ground_row * TILE_SIZE - 20)
    return create_sim_from_lookup(
        lookup, 100.0, start_y,
        level_width=level_width, level_height=level_height,
    )


def _make_pit_sim(level_height: int = 500):
    """Create a sim with no ground below for pit death testing."""
    return create_sim_from_lookup(
        _empty_lookup, 100.0, 100.0,
        level_width=9999, level_height=level_height,
    )


def _inp_left() -> InputState:
    return InputState(left=True)


def _inp_right() -> InputState:
    return InputState(right=True)


def _inp_none() -> InputState:
    return InputState()


# ---------------------------------------------------------------------------
# Left boundary
# ---------------------------------------------------------------------------

class TestLeftBoundary:
    def test_left_clamp_stops_at_zero(self):
        sim = _make_sim()
        p = sim.player.physics
        p.x = 2.0
        p.x_vel = -10.0
        p.ground_speed = -10.0
        p.on_ground = False
        sim_step(sim, _inp_none())
        assert p.x >= 0.0

    def test_left_clamp_zeros_velocity(self):
        sim = _make_sim()
        p = sim.player.physics
        p.x = 2.0
        p.x_vel = -10.0
        p.ground_speed = -10.0
        p.on_ground = False
        sim_step(sim, _inp_none())
        assert p.x_vel >= 0.0
        assert p.ground_speed >= 0.0

    def test_left_boundary_no_death(self):
        sim = _make_sim()
        p = sim.player.physics
        p.x = 2.0
        p.x_vel = -10.0
        p.on_ground = False
        events = sim_step(sim, _inp_none())
        assert sim.player.state != PlayerState.DEAD
        assert not any(isinstance(e, DeathEvent) for e in events)


# ---------------------------------------------------------------------------
# Right boundary
# ---------------------------------------------------------------------------

class TestRightBoundary:
    def test_right_clamp_stops_at_level_width(self):
        sim = _make_sim(level_width=500)
        p = sim.player.physics
        p.x = 498.0
        p.x_vel = 10.0
        p.ground_speed = 10.0
        p.on_ground = False
        sim_step(sim, _inp_none())
        assert p.x <= 500.0

    def test_right_clamp_zeros_velocity(self):
        sim = _make_sim(level_width=500)
        p = sim.player.physics
        p.x = 498.0
        p.x_vel = 10.0
        p.ground_speed = 10.0
        p.on_ground = False
        sim_step(sim, _inp_none())
        assert p.x_vel <= 0.0
        assert p.ground_speed <= 0.0


# ---------------------------------------------------------------------------
# Pit death
# ---------------------------------------------------------------------------

class TestPitDeath:
    def test_pit_death_triggers(self):
        sim = _make_pit_sim(level_height=500)
        p = sim.player.physics
        # Place player just above the pit threshold, with downward velocity
        p.y = 530.0
        p.y_vel = 5.0
        p.on_ground = False
        sim.player.state = PlayerState.JUMPING
        sim_step(sim, _inp_none())
        # After step: y = 530 + 5 + gravity ≈ 535.2 > 500 + 32 = 532
        assert sim.player.state == PlayerState.DEAD

    def test_pit_death_emits_event(self):
        sim = _make_pit_sim(level_height=500)
        p = sim.player.physics
        p.y = 540.0  # Already past threshold
        p.y_vel = 0.0
        p.on_ground = False
        sim.player.state = PlayerState.JUMPING
        events = sim_step(sim, _inp_none())
        assert any(isinstance(e, DeathEvent) for e in events)

    def test_pit_death_increments_counter(self):
        sim = _make_pit_sim(level_height=500)
        p = sim.player.physics
        p.y = 540.0
        p.y_vel = 0.0
        p.on_ground = False
        sim.player.state = PlayerState.JUMPING
        assert sim.deaths == 0
        sim_step(sim, _inp_none())
        assert sim.deaths == 1

    def test_no_death_above_threshold(self):
        sim = _make_pit_sim(level_height=500)
        p = sim.player.physics
        # y=520 < 500+32=532 → no death
        p.y = 520.0
        p.y_vel = 0.0
        p.on_ground = False
        sim.player.state = PlayerState.JUMPING
        events = sim_step(sim, _inp_none())
        assert sim.player.state != PlayerState.DEAD
        assert not any(isinstance(e, DeathEvent) for e in events)

    def test_pit_death_regardless_of_rings(self):
        sim = _make_pit_sim(level_height=500)
        sim.player.rings = 10
        p = sim.player.physics
        p.y = 540.0
        p.y_vel = 0.0
        p.on_ground = False
        sim.player.state = PlayerState.JUMPING
        events = sim_step(sim, _inp_none())
        assert sim.player.state == PlayerState.DEAD
        assert any(isinstance(e, DeathEvent) for e in events)

    def test_pit_death_only_fires_once(self):
        """If already DEAD, pit check shouldn't fire again."""
        sim = _make_pit_sim(level_height=500)
        p = sim.player.physics
        p.y = 540.0
        p.on_ground = False
        sim.player.state = PlayerState.DEAD
        # player_update is a no-op for DEAD. Boundary check sees DEAD → skips.
        events = sim_step(sim, _inp_none())
        assert sim.deaths == 0  # Was already dead, no new increment

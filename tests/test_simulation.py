"""Tests for speednik/simulation.py — SimState, create_sim, event types."""

from __future__ import annotations

import inspect
from pathlib import Path

from speednik.simulation import (
    CheckpointEvent,
    DamageEvent,
    DeathEvent,
    GoalReachedEvent,
    RingCollectedEvent,
    SimState,
    SpringEvent,
    create_sim,
)


# ---------------------------------------------------------------------------
# create_sim — hillside
# ---------------------------------------------------------------------------

def test_create_sim_hillside():
    sim = create_sim("hillside")

    # Player exists at stage start
    assert sim.player is not None
    assert sim.player.physics.x > 0
    assert sim.player.physics.y > 0

    # Tile lookup is callable
    assert callable(sim.tile_lookup)

    # Entity lists populated
    assert len(sim.rings) > 0
    assert len(sim.springs) > 0
    assert len(sim.enemies) > 0
    assert len(sim.checkpoints) > 0

    # Goal position matches known hillside goal
    assert sim.goal_x == 4758.0
    assert sim.goal_y == 642.0

    # Level dimensions
    assert sim.level_width > 0
    assert sim.level_height > 0

    # Defaults
    assert sim.frame == 0
    assert sim.max_x_reached == 0.0
    assert sim.rings_collected == 0
    assert sim.deaths == 0
    assert sim.goal_reached is False
    assert sim.player_dead is False


# ---------------------------------------------------------------------------
# create_sim — pipeworks
# ---------------------------------------------------------------------------

def test_create_sim_pipeworks():
    sim = create_sim("pipeworks")

    assert sim.player is not None
    assert len(sim.rings) > 0
    assert len(sim.pipes) > 0
    assert len(sim.liquid_zones) > 0
    assert sim.goal_x == 5558.0
    assert sim.goal_y == 782.0


# ---------------------------------------------------------------------------
# create_sim — skybridge
# ---------------------------------------------------------------------------

def test_create_sim_skybridge():
    sim = create_sim("skybridge")

    assert sim.player is not None
    assert sim.goal_x == 5158.0
    assert sim.goal_y == 482.0


# ---------------------------------------------------------------------------
# Boss injection
# ---------------------------------------------------------------------------

def test_skybridge_boss_injection():
    sim = create_sim("skybridge")
    boss_enemies = [e for e in sim.enemies if e.enemy_type == "enemy_egg_piston"]
    assert len(boss_enemies) == 1
    boss = boss_enemies[0]
    assert boss.boss_state == "idle"
    assert boss.boss_hp > 0


def test_hillside_no_boss():
    sim = create_sim("hillside")
    boss_enemies = [e for e in sim.enemies if e.enemy_type == "enemy_egg_piston"]
    assert len(boss_enemies) == 0


def test_pipeworks_no_boss():
    sim = create_sim("pipeworks")
    boss_enemies = [e for e in sim.enemies if e.enemy_type == "enemy_egg_piston"]
    assert len(boss_enemies) == 0


# ---------------------------------------------------------------------------
# Entity lists populated
# ---------------------------------------------------------------------------

def test_hillside_entity_lists():
    sim = create_sim("hillside")
    assert len(sim.rings) > 0, "hillside should have rings"
    assert len(sim.springs) > 0, "hillside should have springs"
    assert len(sim.checkpoints) > 0, "hillside should have checkpoints"
    assert len(sim.enemies) > 0, "hillside should have enemies"


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

def test_event_types_instantiable():
    events = [
        RingCollectedEvent(),
        DamageEvent(),
        DeathEvent(),
        SpringEvent(),
        GoalReachedEvent(),
        CheckpointEvent(),
    ]
    assert len(events) == 6
    assert isinstance(events[0], RingCollectedEvent)
    assert isinstance(events[1], DamageEvent)
    assert isinstance(events[2], DeathEvent)
    assert isinstance(events[3], SpringEvent)
    assert isinstance(events[4], GoalReachedEvent)
    assert isinstance(events[5], CheckpointEvent)


# ---------------------------------------------------------------------------
# No Pyxel import
# ---------------------------------------------------------------------------

def test_no_pyxel_import():
    source_path = Path(inspect.getfile(SimState))
    source = source_path.read_text()
    assert "import pyxel" not in source
    assert "from pyxel" not in source


# ---------------------------------------------------------------------------
# SimState defaults
# ---------------------------------------------------------------------------

def test_sim_state_defaults():
    """Verify that create_sim produces correct default metric values."""
    sim = create_sim("hillside")
    assert sim.frame == 0
    assert sim.max_x_reached == 0.0
    assert sim.rings_collected == 0
    assert sim.deaths == 0
    assert sim.goal_reached is False
    assert sim.player_dead is False

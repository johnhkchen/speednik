"""speednik/simulation.py — Headless game simulation (Layer 2).

Provides SimState (complete headless game state) and create_sim() factory
for loading a real stage into a simulation-ready state. No Pyxel imports.
"""

from __future__ import annotations

from dataclasses import dataclass

from speednik.constants import BOSS_SPAWN_X, BOSS_SPAWN_Y
from speednik.enemies import Enemy, EnemyEvent, check_enemy_collision, load_enemies, update_enemies
from speednik.level import load_stage
from speednik.objects import (
    Checkpoint,
    CheckpointEvent as ObjCheckpointEvent,
    GoalEvent as ObjGoalEvent,
    LaunchPipe,
    LiquidEvent as ObjLiquidEvent,
    LiquidZone,
    Ring,
    RingEvent as ObjRingEvent,
    Spring,
    SpringEvent as ObjSpringEvent,
    check_checkpoint_collision,
    check_goal_collision,
    check_ring_collection,
    check_spring_collision,
    load_checkpoints,
    load_liquid_zones,
    load_pipes,
    load_rings,
    load_springs,
    update_pipe_travel,
    update_spring_cooldowns,
    update_liquid_zones,
)
from speednik.physics import InputState
from speednik.player import Player, PlayerState, create_player, player_update
from speednik.terrain import TileLookup


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

@dataclass
class RingCollectedEvent:
    pass


@dataclass
class DamageEvent:
    pass


@dataclass
class DeathEvent:
    pass


@dataclass
class SpringEvent:
    pass


@dataclass
class GoalReachedEvent:
    pass


@dataclass
class CheckpointEvent:
    pass


Event = (
    RingCollectedEvent
    | DamageEvent
    | DeathEvent
    | SpringEvent
    | GoalReachedEvent
    | CheckpointEvent
)


# ---------------------------------------------------------------------------
# SimState
# ---------------------------------------------------------------------------

@dataclass
class SimState:
    """Complete headless game state — everything main.py:App tracks
    for gameplay, minus rendering/audio state."""

    player: Player
    tile_lookup: TileLookup
    rings: list[Ring]
    springs: list[Spring]
    checkpoints: list[Checkpoint]
    pipes: list[LaunchPipe]
    liquid_zones: list[LiquidZone]
    enemies: list[Enemy]
    goal_x: float
    goal_y: float
    level_width: int
    level_height: int
    frame: int = 0
    max_x_reached: float = 0.0
    rings_collected: int = 0
    deaths: int = 0
    goal_reached: bool = False
    player_dead: bool = False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_sim(stage_name: str) -> SimState:
    """Load a stage and initialize all game state. No Pyxel.

    Args:
        stage_name: One of "hillside", "pipeworks", "skybridge".

    Returns:
        Fully populated SimState ready for sim_step.
    """
    stage = load_stage(stage_name)

    # Player
    sx, sy = stage.player_start
    player = create_player(float(sx), float(sy))

    # Entities
    rings = load_rings(stage.entities)
    springs = load_springs(stage.entities)
    checkpoints = load_checkpoints(stage.entities)
    pipes = load_pipes(stage.entities)
    liquid_zones = load_liquid_zones(stage.entities)
    enemies = load_enemies(stage.entities)

    # Goal position
    goal_x = 0.0
    goal_y = 0.0
    for e in stage.entities:
        if e.get("type") == "goal":
            goal_x = float(e["x"])
            goal_y = float(e["y"])
            break

    # Stage 3 (skybridge): inject boss
    if stage_name == "skybridge":
        boss_entities = [
            {"type": "enemy_egg_piston", "x": BOSS_SPAWN_X, "y": BOSS_SPAWN_Y}
        ]
        enemies.extend(load_enemies(boss_entities))

    return SimState(
        player=player,
        tile_lookup=stage.tile_lookup,
        rings=rings,
        springs=springs,
        checkpoints=checkpoints,
        pipes=pipes,
        liquid_zones=liquid_zones,
        enemies=enemies,
        goal_x=goal_x,
        goal_y=goal_y,
        level_width=stage.level_width,
        level_height=stage.level_height,
    )

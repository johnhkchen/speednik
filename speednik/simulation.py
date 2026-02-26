"""speednik/simulation.py — Headless game simulation (Layer 2).

Provides SimState (complete headless game state) and create_sim() factory
for loading a real stage into a simulation-ready state. No Pyxel imports.
"""

from __future__ import annotations

from dataclasses import dataclass

from speednik.constants import BOSS_SPAWN_X, BOSS_SPAWN_Y, PIT_DEATH_MARGIN
from speednik.enemies import (
    Enemy,
    EnemyEvent,
    check_enemy_collision,
    load_enemies,
    update_enemies,
)
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


def create_sim_from_lookup(
    tile_lookup: TileLookup,
    start_x: float,
    start_y: float,
    *,
    level_width: int = 99999,
    level_height: int = 99999,
) -> SimState:
    """Create a minimal SimState from a tile lookup (for synthetic tests).

    No entities, rings, springs, etc. — just the player and tile data.
    """
    player = create_player(start_x, start_y)
    return SimState(
        player=player,
        tile_lookup=tile_lookup,
        rings=[],
        springs=[],
        checkpoints=[],
        pipes=[],
        liquid_zones=[],
        enemies=[],
        goal_x=99999.0,
        goal_y=0.0,
        level_width=level_width,
        level_height=level_height,
    )


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------

def sim_step(sim: SimState, inp: InputState) -> list[Event]:
    """Advance the simulation by one frame.

    Returns a list of events that occurred during this frame.
    """
    events: list[Event] = []

    if sim.player_dead:
        return events

    # Player update (physics + state machine)
    player_update(sim.player, inp, sim.tile_lookup)

    p = sim.player.physics

    # --- World boundary enforcement ---
    # Left boundary: clamp to x=0
    if p.x < 0:
        p.x = 0.0
        if p.x_vel < 0:
            p.x_vel = 0.0
        if p.ground_speed < 0:
            p.ground_speed = 0.0

    # Right boundary: clamp to level_width
    if p.x > sim.level_width:
        p.x = float(sim.level_width)
        if p.x_vel > 0:
            p.x_vel = 0.0
        if p.ground_speed > 0:
            p.ground_speed = 0.0

    # Pit death: kill player below level_height + margin
    if p.y > sim.level_height + PIT_DEATH_MARGIN:
        if sim.player.state != PlayerState.DEAD:
            sim.player.state = PlayerState.DEAD
            sim.player.physics.on_ground = False
            sim.deaths += 1
            events.append(DeathEvent())

    # Track progress
    sim.max_x_reached = max(sim.max_x_reached, p.x)

    # Ring collection
    for ring_evt in check_ring_collection(sim.player, sim.rings):
        if isinstance(ring_evt, ObjRingEvent):
            sim.rings_collected += 1
            events.append(RingCollectedEvent())

    # Spring collision
    for spring_evt in check_spring_collision(sim.player, sim.springs):
        if isinstance(spring_evt, ObjSpringEvent):
            events.append(SpringEvent())

    # Checkpoint collision
    for cp_evt in check_checkpoint_collision(sim.player, sim.checkpoints):
        if isinstance(cp_evt, ObjCheckpointEvent):
            events.append(CheckpointEvent())

    # Pipe travel
    update_pipe_travel(sim.player, sim.pipes)

    # Liquid zones
    liq_events = update_liquid_zones(sim.player, sim.liquid_zones)
    for liq_evt in liq_events:
        if isinstance(liq_evt, ObjLiquidEvent):
            pass  # Liquid events don't map to sim events yet

    # Spring cooldowns
    update_spring_cooldowns(sim.springs)

    # Enemy updates
    update_enemies(sim.enemies)
    enemy_events = check_enemy_collision(sim.player, sim.enemies)
    for enemy_evt in enemy_events:
        if enemy_evt == EnemyEvent.PLAYER_DAMAGED:
            events.append(DamageEvent())

    # Goal check
    goal_evt = check_goal_collision(sim.player, sim.goal_x, sim.goal_y)
    if isinstance(goal_evt, ObjGoalEvent):
        sim.goal_reached = True
        events.append(GoalReachedEvent())

    sim.frame += 1
    return events

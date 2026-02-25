"""speednik/objects.py — Game objects: rings, springs, checkpoints, etc.

Handles world-placed entity logic. Pyxel-free for testability — returns
events that the main loop maps to SFX calls and visual effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from speednik.constants import (
    CHECKPOINT_ACTIVATION_RADIUS,
    EXTRA_LIFE_THRESHOLD,
    LIQUID_RISE_SPEED,
    PIPE_ENTRY_HITBOX_H,
    PIPE_ENTRY_HITBOX_W,
    RING_COLLECTION_RADIUS,
    SPRING_COOLDOWN_FRAMES,
    SPRING_HITBOX_H,
    SPRING_HITBOX_W,
    SPRING_RIGHT_VELOCITY,
    SPRING_UP_VELOCITY,
)
from speednik.player import Player, PlayerState, damage_player, get_player_rect


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class RingEvent(Enum):
    COLLECTED = "collected"
    EXTRA_LIFE = "extra_life"


class SpringEvent(Enum):
    LAUNCHED = "launched"


class CheckpointEvent(Enum):
    ACTIVATED = "activated"


class PipeEvent(Enum):
    ENTERED = "entered"
    EXITED = "exited"


class LiquidEvent(Enum):
    STARTED_RISING = "started_rising"
    DAMAGE = "damage"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def aabb_overlap(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, by: float, bw: float, bh: float,
) -> bool:
    """Return True if two axis-aligned bounding boxes overlap."""
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


# ---------------------------------------------------------------------------
# Ring entity
# ---------------------------------------------------------------------------

@dataclass
class Ring:
    """A ring placed in the world by the level designer."""
    x: float
    y: float
    collected: bool = False


# ---------------------------------------------------------------------------
# Spring entity
# ---------------------------------------------------------------------------

@dataclass
class Spring:
    """A directional spring that launches the player."""
    x: float
    y: float
    direction: str  # "up" or "right"
    cooldown: int = 0


# ---------------------------------------------------------------------------
# Checkpoint entity
# ---------------------------------------------------------------------------

@dataclass
class Checkpoint:
    """A checkpoint post that saves the player's respawn point."""
    x: float
    y: float
    activated: bool = False


# ---------------------------------------------------------------------------
# Launch pipe entity
# ---------------------------------------------------------------------------

@dataclass
class LaunchPipe:
    """A pipe that launches the player along a fixed trajectory."""
    x: float
    y: float
    exit_x: float
    exit_y: float
    vel_x: float
    vel_y: float


# ---------------------------------------------------------------------------
# Liquid zone entity
# ---------------------------------------------------------------------------

@dataclass
class LiquidZone:
    """A zone where liquid rises from the floor toward a ceiling."""
    trigger_x: float
    exit_x: float
    floor_y: float
    ceiling_y: float
    current_y: float = 0.0  # set to floor_y on load
    active: bool = False


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_rings(entities: list[dict]) -> list[Ring]:
    """Extract ring entities from a stage entity list."""
    return [
        Ring(x=float(e["x"]), y=float(e["y"]))
        for e in entities
        if e.get("type") == "ring"
    ]


def load_springs(entities: list[dict]) -> list[Spring]:
    """Extract spring entities from a stage entity list."""
    springs: list[Spring] = []
    for e in entities:
        etype = e.get("type", "")
        if etype == "spring_up":
            springs.append(Spring(x=float(e["x"]), y=float(e["y"]), direction="up"))
        elif etype == "spring_right":
            springs.append(Spring(x=float(e["x"]), y=float(e["y"]), direction="right"))
    return springs


def load_checkpoints(entities: list[dict]) -> list[Checkpoint]:
    """Extract checkpoint entities from a stage entity list."""
    return [
        Checkpoint(x=float(e["x"]), y=float(e["y"]))
        for e in entities
        if e.get("type") == "checkpoint"
    ]


def load_pipes(entities: list[dict]) -> list[LaunchPipe]:
    """Extract launch pipe entities from a stage entity list."""
    return [
        LaunchPipe(
            x=float(e["x"]),
            y=float(e["y"]),
            exit_x=float(e["exit_x"]),
            exit_y=float(e["exit_y"]),
            vel_x=float(e["vel_x"]),
            vel_y=float(e["vel_y"]),
        )
        for e in entities
        if e.get("type") in ("pipe_h", "pipe_v")
    ]


def load_liquid_zones(entities: list[dict]) -> list[LiquidZone]:
    """Extract liquid zone trigger entities from a stage entity list."""
    return [
        LiquidZone(
            trigger_x=float(e["x"]),
            exit_x=float(e["exit_x"]),
            floor_y=float(e["floor_y"]),
            ceiling_y=float(e["ceiling_y"]),
            current_y=float(e["floor_y"]),
        )
        for e in entities
        if e.get("type") == "liquid_trigger"
    ]


# ---------------------------------------------------------------------------
# Ring collection
# ---------------------------------------------------------------------------

def check_ring_collection(
    player: Player,
    rings: list[Ring],
) -> list[RingEvent]:
    """Check if the player collects any world rings.

    Returns a list of events for the caller to map to SFX/visuals.
    """
    if player.state in (PlayerState.DEAD, PlayerState.HURT):
        return []

    events: list[RingEvent] = []
    px, py = player.physics.x, player.physics.y
    radius_sq = RING_COLLECTION_RADIUS * RING_COLLECTION_RADIUS

    for ring in rings:
        if ring.collected:
            continue
        dx = ring.x - px
        dy = ring.y - py
        if dx * dx + dy * dy < radius_sq:
            ring.collected = True
            old_rings = player.rings
            player.rings += 1
            events.append(RingEvent.COLLECTED)
            # Check extra life threshold crossing
            if old_rings // EXTRA_LIFE_THRESHOLD < player.rings // EXTRA_LIFE_THRESHOLD:
                player.lives += 1
                events.append(RingEvent.EXTRA_LIFE)

    return events


# ---------------------------------------------------------------------------
# Spring collision
# ---------------------------------------------------------------------------

def check_spring_collision(
    player: Player,
    springs: list[Spring],
) -> list[SpringEvent]:
    """Check if the player hits any springs. Override velocity on contact."""
    if player.state in (PlayerState.DEAD, PlayerState.HURT):
        return []

    events: list[SpringEvent] = []
    px, py, pw, ph = get_player_rect(player)
    phys = player.physics

    for spring in springs:
        if spring.cooldown > 0:
            continue

        # Spring hitbox centered on spring position
        sx = spring.x - SPRING_HITBOX_W / 2
        sy = spring.y - SPRING_HITBOX_H / 2

        if not aabb_overlap(px, py, pw, ph, sx, sy, SPRING_HITBOX_W, SPRING_HITBOX_H):
            continue

        if spring.direction == "up":
            phys.y_vel = SPRING_UP_VELOCITY
            phys.x_vel = phys.ground_speed  # preserve horizontal momentum
            phys.on_ground = False
            phys.ground_speed = 0.0
            phys.angle = 0
            phys.is_rolling = False
            player.state = PlayerState.JUMPING
        elif spring.direction == "right":
            phys.x_vel = SPRING_RIGHT_VELOCITY
            phys.on_ground = False
            phys.y_vel = 0.0
            phys.ground_speed = 0.0
            phys.angle = 0
            phys.is_rolling = False
            player.state = PlayerState.JUMPING

        spring.cooldown = SPRING_COOLDOWN_FRAMES
        events.append(SpringEvent.LAUNCHED)

    return events


def update_spring_cooldowns(springs: list[Spring]) -> None:
    """Decrement spring cooldown timers each frame."""
    for spring in springs:
        if spring.cooldown > 0:
            spring.cooldown -= 1


# ---------------------------------------------------------------------------
# Checkpoint collision
# ---------------------------------------------------------------------------

def check_checkpoint_collision(
    player: Player,
    checkpoints: list[Checkpoint],
) -> list[CheckpointEvent]:
    """Check if the player activates any checkpoints."""
    if player.state in (PlayerState.DEAD, PlayerState.HURT):
        return []

    events: list[CheckpointEvent] = []
    px, py = player.physics.x, player.physics.y
    radius_sq = CHECKPOINT_ACTIVATION_RADIUS * CHECKPOINT_ACTIVATION_RADIUS

    for cp in checkpoints:
        if cp.activated:
            continue
        dx = cp.x - px
        dy = cp.y - py
        if dx * dx + dy * dy < radius_sq:
            cp.activated = True
            player.respawn_x = cp.x
            player.respawn_y = cp.y
            player.respawn_rings = player.rings
            events.append(CheckpointEvent.ACTIVATED)

    return events


# ---------------------------------------------------------------------------
# Launch pipe travel
# ---------------------------------------------------------------------------

def update_pipe_travel(
    player: Player,
    pipes: list[LaunchPipe],
) -> list[PipeEvent]:
    """Handle pipe entry, travel, and exit."""
    events: list[PipeEvent] = []
    phys = player.physics

    if player.in_pipe:
        # Currently traveling — move player along pipe velocity
        phys.x += phys.x_vel
        phys.y += phys.y_vel

        # Check if player has reached/passed the exit of the active pipe
        for pipe in pipes:
            # Find the pipe we're traveling in (closest to our trajectory)
            if phys.x_vel > 0 and phys.x >= pipe.exit_x and pipe.vel_x > 0:
                _exit_pipe(player, pipe)
                events.append(PipeEvent.EXITED)
                return events
            if phys.x_vel < 0 and phys.x <= pipe.exit_x and pipe.vel_x < 0:
                _exit_pipe(player, pipe)
                events.append(PipeEvent.EXITED)
                return events
            if phys.y_vel < 0 and phys.y <= pipe.exit_y and pipe.vel_y < 0:
                _exit_pipe(player, pipe)
                events.append(PipeEvent.EXITED)
                return events
            if phys.y_vel > 0 and phys.y >= pipe.exit_y and pipe.vel_y > 0:
                _exit_pipe(player, pipe)
                events.append(PipeEvent.EXITED)
                return events

        return events

    # Not in pipe — check for entry
    if player.state in (PlayerState.DEAD, PlayerState.HURT):
        return events

    px, py, pw, ph = get_player_rect(player)

    for pipe in pipes:
        # Entry hitbox centered on pipe position
        ex = pipe.x - PIPE_ENTRY_HITBOX_W / 2
        ey = pipe.y - PIPE_ENTRY_HITBOX_H / 2

        if not aabb_overlap(px, py, pw, ph, ex, ey, PIPE_ENTRY_HITBOX_W, PIPE_ENTRY_HITBOX_H):
            continue

        # Enter pipe
        player.in_pipe = True
        phys.x_vel = pipe.vel_x
        phys.y_vel = pipe.vel_y
        phys.ground_speed = 0.0
        phys.on_ground = False
        phys.angle = 0
        phys.is_rolling = False
        player.state = PlayerState.JUMPING
        player.invulnerability_timer = 9999  # invulnerable during travel
        events.append(PipeEvent.ENTERED)
        return events

    return events


def _exit_pipe(player: Player, pipe: LaunchPipe) -> None:
    """Place player at pipe exit and resume normal physics."""
    player.physics.x = pipe.exit_x
    player.physics.y = pipe.exit_y
    player.in_pipe = False
    player.invulnerability_timer = 0
    # Keep the pipe velocity so player continues moving after exit


# ---------------------------------------------------------------------------
# Liquid zone update
# ---------------------------------------------------------------------------

def update_liquid_zones(
    player: Player,
    zones: list[LiquidZone],
) -> list[LiquidEvent]:
    """Update liquid zones: trigger activation, rise, and damage."""
    events: list[LiquidEvent] = []
    px = player.physics.x

    for zone in zones:
        was_active = zone.active

        # Activation: player inside zone x-range
        if px > zone.trigger_x and px < zone.exit_x:
            zone.active = True
        else:
            zone.active = False

        if zone.active and not was_active:
            events.append(LiquidEvent.STARTED_RISING)

        # Rise while active
        if zone.active and zone.current_y > zone.ceiling_y:
            zone.current_y -= LIQUID_RISE_SPEED
            if zone.current_y < zone.ceiling_y:
                zone.current_y = zone.ceiling_y

        # Damage check: player below liquid surface
        if zone.active and player.state not in (PlayerState.DEAD, PlayerState.HURT):
            _, py_rect, _, ph_rect = get_player_rect(player)
            player_bottom = py_rect + ph_rect
            if player_bottom > zone.current_y:
                damage_player(player)
                events.append(LiquidEvent.DAMAGE)

    return events

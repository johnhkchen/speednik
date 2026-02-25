"""speednik/player.py — Player state, input handling, animation tracking.

Orchestrates physics.py (steps 1–4) and terrain.py (steps 5–7) per the
frame update order in specification §2.5. Manages player state machine,
damage/ring system, and animation state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from speednik.constants import (
    HURT_KNOCKBACK_X,
    HURT_KNOCKBACK_Y,
    INVULNERABILITY_DURATION,
    MAX_SCATTER_RINGS,
    MIN_ROLL_SPEED,
    ROLLING_HEIGHT_RADIUS,
    ROLLING_WIDTH_RADIUS,
    SCATTER_RING_LIFETIME,
    STANDING_HEIGHT_RADIUS,
    STANDING_WIDTH_RADIUS,
    GRAVITY,
)
from speednik.physics import (
    InputState,
    PhysicsState,
    apply_gravity,
    apply_input,
    apply_jump,
    apply_movement,
    apply_slope_factor,
    apply_spindash_charge,
    apply_spindash_decay,
    apply_spindash_release,
    apply_variable_jump,
    update_slip_timer,
)
from speednik.terrain import TileLookup, resolve_collision


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PlayerState(Enum):
    STANDING = "standing"
    RUNNING = "running"
    JUMPING = "jumping"
    ROLLING = "rolling"
    SPINDASH = "spindash"
    HURT = "hurt"
    DEAD = "dead"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ScatteredRing:
    """A ring scattered from damage, with simple physics."""
    x: float
    y: float
    vx: float
    vy: float
    timer: int = SCATTER_RING_LIFETIME


@dataclass
class Player:
    """All player state: physics + game logic + animation."""
    physics: PhysicsState = field(default_factory=PhysicsState)
    state: PlayerState = PlayerState.STANDING
    rings: int = 0
    lives: int = 3
    invulnerability_timer: int = 0
    anim_frame: int = 0
    anim_timer: int = 0
    anim_name: str = "idle"
    scattered_rings: list[ScatteredRing] = field(default_factory=list)
    # Track previous jump_held for release detection
    _prev_jump_held: bool = False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_player(x: float, y: float) -> Player:
    """Create a player at the given pixel position."""
    physics = PhysicsState(x=x, y=y, on_ground=True)
    return Player(physics=physics)


# ---------------------------------------------------------------------------
# Main update
# ---------------------------------------------------------------------------

def player_update(player: Player, inp: InputState, tile_lookup: TileLookup) -> None:
    """Full frame update: input → state machine → physics → collision → sync."""
    if player.state == PlayerState.DEAD:
        return

    # Pre-physics state machine (jump, roll, spindash transitions)
    _pre_physics(player, inp)

    # Physics steps 1–4
    if player.state != PlayerState.HURT:
        apply_input(player.physics, inp)
    apply_slope_factor(player.physics)
    apply_gravity(player.physics)
    apply_movement(player.physics)

    # Collision steps 5–7
    resolve_collision(player.physics, tile_lookup)

    # Slip timer
    update_slip_timer(player.physics)

    # Post-physics state sync
    _post_physics(player)

    # Subsystems
    _update_invulnerability(player)
    _update_scattered_rings(player)
    _check_ring_collection(player)
    _update_animation(player)

    # Track jump held for next frame's release detection
    player._prev_jump_held = inp.jump_held


# ---------------------------------------------------------------------------
# Pre-physics state machine
# ---------------------------------------------------------------------------

def _pre_physics(player: Player, inp: InputState) -> None:
    """Handle state transitions before physics runs."""
    p = player.physics

    if player.state == PlayerState.HURT:
        return

    # Variable jump height: cap upward velocity when jump released mid-air
    if player.state == PlayerState.JUMPING:
        if player._prev_jump_held and not inp.jump_held:
            apply_variable_jump(p)
        return  # No other transitions from JUMPING before physics

    # --- Spindash state ---
    if player.state == PlayerState.SPINDASH:
        if not inp.down_held:
            # Release spindash
            apply_spindash_release(p)
            player.state = PlayerState.ROLLING
            return
        if inp.jump_pressed:
            # Charge spindash
            apply_spindash_charge(p)
            return
        # Decay while holding
        apply_spindash_decay(p)
        return

    # --- Ground states: STANDING, RUNNING, ROLLING ---
    if not p.on_ground:
        return  # Will be handled in post_physics

    # Jump from any ground state
    if inp.jump_pressed and player.state in (
        PlayerState.STANDING, PlayerState.RUNNING, PlayerState.ROLLING
    ):
        apply_jump(p)
        player.state = PlayerState.JUMPING
        return

    # Enter spindash: down held while standing/nearly still
    if player.state in (PlayerState.STANDING, PlayerState.RUNNING):
        if inp.down_held and abs(p.ground_speed) < MIN_ROLL_SPEED:
            p.is_charging_spindash = True
            p.ground_speed = 0.0
            player.state = PlayerState.SPINDASH
            return

    # Enter roll: down pressed while moving fast enough
    if player.state in (PlayerState.STANDING, PlayerState.RUNNING):
        if inp.down_held and abs(p.ground_speed) >= MIN_ROLL_SPEED:
            p.is_rolling = True
            player.state = PlayerState.ROLLING
            return


# ---------------------------------------------------------------------------
# Post-physics state sync
# ---------------------------------------------------------------------------

def _post_physics(player: Player) -> None:
    """Sync state machine with physics results after collision resolution."""
    p = player.physics

    # Landing: JUMPING + on_ground → ground state
    if player.state == PlayerState.JUMPING and p.on_ground:
        if p.is_rolling:
            player.state = PlayerState.ROLLING
        elif abs(p.ground_speed) > 0:
            player.state = PlayerState.RUNNING
        else:
            player.state = PlayerState.STANDING
        return

    # Fell off edge: ground state + not on_ground → JUMPING
    if player.state in (PlayerState.STANDING, PlayerState.RUNNING,
                        PlayerState.ROLLING) and not p.on_ground:
        player.state = PlayerState.JUMPING
        return

    # Unroll detection: physics set is_rolling = False (speed below threshold)
    if player.state == PlayerState.ROLLING and not p.is_rolling:
        player.state = PlayerState.STANDING
        return

    # HURT landing: on ground + invulnerability expired
    if player.state == PlayerState.HURT and p.on_ground and player.invulnerability_timer <= 0:
        player.state = PlayerState.STANDING
        return

    # Ground movement state sync
    if player.state == PlayerState.STANDING and abs(p.ground_speed) > 0 and p.on_ground:
        player.state = PlayerState.RUNNING
    elif player.state == PlayerState.RUNNING and abs(p.ground_speed) == 0 and p.on_ground:
        player.state = PlayerState.STANDING


# ---------------------------------------------------------------------------
# Damage
# ---------------------------------------------------------------------------

def damage_player(player: Player) -> None:
    """Apply damage to the player. Called by external collision checks."""
    if player.invulnerability_timer > 0:
        return
    if player.state == PlayerState.DEAD:
        return

    if player.rings > 0:
        _scatter_rings(player)
        player.rings = 0
        player.invulnerability_timer = INVULNERABILITY_DURATION
        player.state = PlayerState.HURT
        # Knockback
        p = player.physics
        p.y_vel = HURT_KNOCKBACK_Y
        p.x_vel = -HURT_KNOCKBACK_X if p.facing_right else HURT_KNOCKBACK_X
        p.ground_speed = 0.0
        p.on_ground = False
        p.is_rolling = False
        p.is_charging_spindash = False
    else:
        player.state = PlayerState.DEAD
        player.physics.y_vel = HURT_KNOCKBACK_Y
        player.physics.on_ground = False


def _scatter_rings(player: Player) -> None:
    """Create scattered ring objects in a fan pattern."""
    count = min(player.rings, MAX_SCATTER_RINGS)
    rings = []
    for i in range(count):
        # Fan pattern: alternate sides, varying angles
        angle = math.pi / 2 + (i + 1) * math.pi / (count + 1)
        if i % 2 == 1:
            angle = math.pi - angle  # Mirror
        speed = 3.0 + (i % 4) * 0.5
        rings.append(ScatteredRing(
            x=player.physics.x,
            y=player.physics.y,
            vx=speed * math.cos(angle),
            vy=-abs(speed * math.sin(angle)),
        ))
    player.scattered_rings.extend(rings)


def _update_scattered_rings(player: Player) -> None:
    """Update scattered ring physics and remove expired ones."""
    alive = []
    for ring in player.scattered_rings:
        ring.vy += GRAVITY
        ring.x += ring.vx
        ring.y += ring.vy
        ring.timer -= 1
        if ring.timer > 0:
            alive.append(ring)
    player.scattered_rings = alive


def _check_ring_collection(player: Player) -> None:
    """Check if player is close enough to collect scattered rings."""
    if player.state == PlayerState.DEAD:
        return
    px, py = player.physics.x, player.physics.y
    still_alive = []
    for ring in player.scattered_rings:
        dx = ring.x - px
        dy = ring.y - py
        if dx * dx + dy * dy < 16 * 16:  # 16px collection radius
            player.rings += 1
        else:
            still_alive.append(ring)
    player.scattered_rings = still_alive


# ---------------------------------------------------------------------------
# Invulnerability
# ---------------------------------------------------------------------------

def _update_invulnerability(player: Player) -> None:
    """Decrement invulnerability timer."""
    if player.invulnerability_timer > 0:
        player.invulnerability_timer -= 1


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

# Animation speeds: frames between frame index advances
_ANIM_SPEED_IDLE = 0  # Static
_ANIM_SPEED_RUNNING_BASE = 8  # At low speed
_ANIM_SPEED_RUNNING_MIN = 2  # At top speed
_ANIM_FRAMES_RUNNING = 4


def _update_animation(player: Player) -> None:
    """Update animation name, timer, and frame index based on state."""
    # Set animation name from state
    state_to_anim = {
        PlayerState.STANDING: "idle",
        PlayerState.RUNNING: "running",
        PlayerState.JUMPING: "rolling",
        PlayerState.ROLLING: "rolling",
        PlayerState.SPINDASH: "spindash",
        PlayerState.HURT: "hurt",
        PlayerState.DEAD: "dead",
    }
    new_anim = state_to_anim.get(player.state, "idle")

    if new_anim != player.anim_name:
        player.anim_name = new_anim
        player.anim_frame = 0
        player.anim_timer = 0
        return

    # Advance running animation
    if player.anim_name == "running":
        speed = abs(player.physics.ground_speed)
        if speed > 0:
            # Faster movement = faster animation
            anim_speed = max(
                _ANIM_SPEED_RUNNING_MIN,
                int(_ANIM_SPEED_RUNNING_BASE - speed),
            )
            player.anim_timer += 1
            if player.anim_timer >= anim_speed:
                player.anim_timer = 0
                player.anim_frame = (player.anim_frame + 1) % _ANIM_FRAMES_RUNNING


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def get_player_rect(player: Player) -> tuple[float, float, int, int]:
    """Return (x, y, width, height) for rendering the player hitbox."""
    p = player.physics
    if p.is_rolling or not p.on_ground:
        w = ROLLING_WIDTH_RADIUS * 2
        h = ROLLING_HEIGHT_RADIUS * 2
    else:
        w = STANDING_WIDTH_RADIUS * 2
        h = STANDING_HEIGHT_RADIUS * 2
    # x, y is the center; return top-left corner
    return (p.x - w // 2, p.y - h // 2, w, h)

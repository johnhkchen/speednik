"""speednik/physics.py — Sonic 2 ground/air/slope physics engine.

Implements the mathematical model of movement per specification §2.1–2.4.
Does not include collision detection (that's T-001-03).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from speednik.constants import (
    ACCELERATION,
    AIR_ACCELERATION,
    ANGLE_STEPS,
    DECELERATION,
    FRICTION,
    GRAVITY,
    JUMP_FORCE,
    JUMP_RELEASE_CAP,
    MAX_X_SPEED,
    MIN_ROLL_SPEED,
    ROLLING_DECELERATION,
    ROLLING_FRICTION,
    SLIP_ANGLE_THRESHOLD,
    SLIP_DURATION,
    SLIP_SPEED_THRESHOLD,
    SLOPE_FACTOR_ROLL_DOWN,
    SLOPE_FACTOR_ROLL_UP,
    SLOPE_FACTOR_RUNNING,
    SPINDASH_BASE_SPEED,
    SPINDASH_CHARGE_INCREMENT,
    SPINDASH_DECAY_DIVISOR,
    SPINDASH_MAX_CHARGE,
    TOP_SPEED,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def byte_angle_to_rad(angle: int) -> float:
    """Convert a byte angle (0–255) to radians."""
    return angle * (2.0 * math.pi / ANGLE_STEPS)


def sign(x: float) -> float:
    """Return -1.0, 0.0, or 1.0."""
    if x > 0:
        return 1.0
    elif x < 0:
        return -1.0
    return 0.0


def _byte_angle_to_degrees(angle: int) -> float:
    """Convert byte angle to degrees (for range comparisons)."""
    return angle * 360.0 / ANGLE_STEPS


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class InputState:
    """Input flags decoupled from Pyxel for testability."""
    left: bool = False
    right: bool = False
    jump_pressed: bool = False
    jump_held: bool = False
    down_held: bool = False
    up_held: bool = False


@dataclass
class PhysicsState:
    """All physics-relevant mutable state for one entity."""
    x: float = 0.0
    y: float = 0.0
    x_vel: float = 0.0
    y_vel: float = 0.0
    ground_speed: float = 0.0
    angle: int = 0          # byte angle 0–255, 0 = flat ground
    on_ground: bool = True
    is_rolling: bool = False
    facing_right: bool = True
    spinrev: float = 0.0
    is_charging_spindash: bool = False
    slip_timer: int = 0
    adhesion_miss_count: int = 0  # consecutive frames of found=False adhesion


# ---------------------------------------------------------------------------
# Step 1: Input handling
# ---------------------------------------------------------------------------

def apply_input(state: PhysicsState, inp: InputState) -> None:
    """Apply acceleration, deceleration, and friction based on state and input.

    Ground standing: accelerate/decelerate/friction with TOP_SPEED enforcement.
    Ground rolling: no acceleration, rolling friction/decel, unroll below min speed.
    Airborne: air acceleration, no speed cap from accel.
    """
    if state.on_ground:
        if state.is_rolling:
            _apply_rolling_input(state, inp)
        else:
            _apply_ground_input(state, inp)
    else:
        _apply_air_input(state, inp)

    # Hard clamp
    if state.on_ground:
        state.ground_speed = max(-MAX_X_SPEED, min(MAX_X_SPEED, state.ground_speed))
    else:
        state.x_vel = max(-MAX_X_SPEED, min(MAX_X_SPEED, state.x_vel))


def _apply_ground_input(state: PhysicsState, inp: InputState) -> None:
    """Ground movement when standing (not rolling)."""
    if state.slip_timer > 0:
        # Slipping — ignore directional input, still apply friction
        if state.ground_speed > 0:
            state.ground_speed -= FRICTION
            if state.ground_speed < 0:
                state.ground_speed = 0.0
        elif state.ground_speed < 0:
            state.ground_speed += FRICTION
            if state.ground_speed > 0:
                state.ground_speed = 0.0
        return

    if inp.left:
        if state.ground_speed > 0:
            # Pressing against movement — decelerate
            state.ground_speed -= DECELERATION
            if state.ground_speed < 0:
                state.ground_speed = -DECELERATION  # Overshoot: start moving left
        elif abs(state.ground_speed) < TOP_SPEED:
            # Accelerate left (only below top speed)
            state.ground_speed -= ACCELERATION
        state.facing_right = False
    elif inp.right:
        if state.ground_speed < 0:
            # Pressing against movement — decelerate
            state.ground_speed += DECELERATION
            if state.ground_speed > 0:
                state.ground_speed = DECELERATION  # Overshoot: start moving right
        elif abs(state.ground_speed) < TOP_SPEED:
            # Accelerate right (only below top speed)
            state.ground_speed += ACCELERATION
        state.facing_right = True
    else:
        # No input — apply friction
        if state.ground_speed > 0:
            state.ground_speed -= FRICTION
            if state.ground_speed < 0:
                state.ground_speed = 0.0
        elif state.ground_speed < 0:
            state.ground_speed += FRICTION
            if state.ground_speed > 0:
                state.ground_speed = 0.0


def _apply_rolling_input(state: PhysicsState, inp: InputState) -> None:
    """Ground movement when rolling: no acceleration, rolling friction/decel."""
    # Rolling deceleration when pressing opposite direction
    if inp.left and state.ground_speed > 0:
        state.ground_speed -= ROLLING_DECELERATION
    elif inp.right and state.ground_speed < 0:
        state.ground_speed += ROLLING_DECELERATION

    # Always apply rolling friction
    if state.ground_speed > 0:
        state.ground_speed -= ROLLING_FRICTION
        if state.ground_speed < 0:
            state.ground_speed = 0.0
    elif state.ground_speed < 0:
        state.ground_speed += ROLLING_FRICTION
        if state.ground_speed > 0:
            state.ground_speed = 0.0

    # Unroll below minimum speed
    if abs(state.ground_speed) < MIN_ROLL_SPEED:
        state.is_rolling = False


def _apply_air_input(state: PhysicsState, inp: InputState) -> None:
    """Air movement: air acceleration in pressed direction."""
    if inp.left:
        state.x_vel -= AIR_ACCELERATION
        state.facing_right = False
    elif inp.right:
        state.x_vel += AIR_ACCELERATION
        state.facing_right = True


# ---------------------------------------------------------------------------
# Step 1 (continued): Jump
# ---------------------------------------------------------------------------

def apply_jump(state: PhysicsState) -> None:
    """Initiate a jump with angle-aware launch. Call only when on_ground."""
    angle_rad = byte_angle_to_rad(state.angle)
    state.x_vel = state.ground_speed * math.cos(angle_rad) - JUMP_FORCE * math.sin(angle_rad)
    state.y_vel = state.ground_speed * -math.sin(angle_rad) - JUMP_FORCE * math.cos(angle_rad)
    state.on_ground = False
    state.angle = 0
    state.ground_speed = 0.0


def apply_variable_jump(state: PhysicsState) -> None:
    """Cap upward velocity on jump release. Call when jump button released."""
    if state.y_vel < JUMP_RELEASE_CAP:
        state.y_vel = JUMP_RELEASE_CAP


# ---------------------------------------------------------------------------
# Step 2: Slope factor
# ---------------------------------------------------------------------------

def apply_slope_factor(state: PhysicsState) -> None:
    """Apply slope factor to ground_speed. Only call when on_ground."""
    if not state.on_ground:
        return

    angle_rad = byte_angle_to_rad(state.angle)
    sin_a = math.sin(angle_rad)

    if not state.is_rolling:
        factor = SLOPE_FACTOR_RUNNING
    else:
        # Rolling: uphill uses weaker factor, downhill uses stronger factor
        # Uphill = slope decelerates the player (sin_a and ground_speed same sign effect)
        # If ground_speed > 0 and sin_a > 0, player is going right up a slope → uphill
        # If ground_speed < 0 and sin_a < 0, player is going left up a slope → uphill
        going_uphill = sign(state.ground_speed) == sign(sin_a) if state.ground_speed != 0 else False
        if going_uphill:
            factor = SLOPE_FACTOR_ROLL_UP
        else:
            factor = SLOPE_FACTOR_ROLL_DOWN

    state.ground_speed -= factor * sin_a


# ---------------------------------------------------------------------------
# Step 3: Gravity
# ---------------------------------------------------------------------------

def apply_gravity(state: PhysicsState) -> None:
    """Apply gravity when airborne."""
    if state.on_ground:
        return
    state.y_vel += GRAVITY


# ---------------------------------------------------------------------------
# Step 4: Movement
# ---------------------------------------------------------------------------

def apply_movement(state: PhysicsState) -> None:
    """Decompose ground_speed to velocity components and update position."""
    if state.on_ground:
        angle_rad = byte_angle_to_rad(state.angle)
        state.x_vel = state.ground_speed * math.cos(angle_rad)
        state.y_vel = state.ground_speed * -math.sin(angle_rad)

    state.x += state.x_vel
    state.y += state.y_vel


# ---------------------------------------------------------------------------
# Spindash
# ---------------------------------------------------------------------------

def apply_spindash_charge(state: PhysicsState) -> None:
    """Add charge increment to spinrev (call on each jump press during spindash)."""
    state.spinrev = min(state.spinrev + SPINDASH_CHARGE_INCREMENT, SPINDASH_MAX_CHARGE)


def apply_spindash_decay(state: PhysicsState) -> None:
    """Apply per-frame decay to spinrev while holding spindash charge."""
    state.spinrev -= state.spinrev / SPINDASH_DECAY_DIVISOR


def apply_spindash_release(state: PhysicsState) -> None:
    """Release spindash: convert charge to ground_speed."""
    speed = SPINDASH_BASE_SPEED + math.floor(state.spinrev / 2)
    state.ground_speed = speed if state.facing_right else -speed
    state.spinrev = 0.0
    state.is_charging_spindash = False
    state.is_rolling = True


# ---------------------------------------------------------------------------
# Landing
# ---------------------------------------------------------------------------

def calculate_landing_speed(state: PhysicsState) -> None:
    """Recalculate ground_speed from x/y velocity based on landing angle.

    Angle ranges (in degrees):
    - Flat (339°–23°): ground_speed = x_vel
    - Slope (316°–338° or 24°–45°): use whichever is larger of x_vel or y-based calc
    - Steep (46°–315°): use whichever is larger of x_vel or y-based calc (no 0.5 factor)
    """
    deg = _byte_angle_to_degrees(state.angle)
    angle_rad = byte_angle_to_rad(state.angle)
    sin_a = math.sin(angle_rad)

    # Flat range: 339°–360° or 0°–23°
    if deg >= 339.0 or deg <= 23.0:
        state.ground_speed = state.x_vel
        return

    # Slope range: 24°–45° or 316°–338°
    if (24.0 <= deg <= 45.0) or (316.0 <= deg <= 338.0):
        y_based = state.y_vel * 0.5 * -sign(sin_a)
        if abs(y_based) > abs(state.x_vel):
            state.ground_speed = y_based
        else:
            state.ground_speed = state.x_vel
        return

    # Steep range: 46°–315°
    y_based = state.y_vel * -sign(sin_a)
    if abs(y_based) > abs(state.x_vel):
        state.ground_speed = y_based
    else:
        state.ground_speed = state.x_vel


# ---------------------------------------------------------------------------
# Slip detection
# ---------------------------------------------------------------------------

def check_slip(state: PhysicsState) -> bool:
    """Check if the player should enter slip state."""
    if not state.on_ground:
        return False
    deg = _byte_angle_to_degrees(state.angle)
    on_steep_slope = 46.0 <= deg <= 315.0
    return abs(state.ground_speed) < SLIP_SPEED_THRESHOLD and on_steep_slope


def update_slip_timer(state: PhysicsState) -> None:
    """Update slip timer: activate if conditions met, decrement if active."""
    if check_slip(state):
        state.slip_timer = SLIP_DURATION
    elif state.slip_timer > 0:
        state.slip_timer -= 1

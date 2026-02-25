"""Unit tests for speednik.physics — Sonic 2 physics engine."""

import math

import pytest

from speednik.constants import (
    ACCELERATION,
    DECELERATION,
    FRICTION,
    GRAVITY,
    JUMP_FORCE,
    JUMP_RELEASE_CAP,
    MIN_ROLL_SPEED,
    ROLLING_DECELERATION,
    ROLLING_FRICTION,
    SLOPE_FACTOR_RUNNING,
    SPINDASH_BASE_SPEED,
    SPINDASH_CHARGE_INCREMENT,
    SPINDASH_DECAY_DIVISOR,
    SPINDASH_MAX_CHARGE,
    TOP_SPEED,
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
    byte_angle_to_rad,
    calculate_landing_speed,
    check_slip,
    sign,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def degrees_to_byte(deg: float) -> int:
    """Convert degrees to byte angle (0–255)."""
    return round(deg * 256 / 360) % 256


# ---------------------------------------------------------------------------
# Acceleration to top speed
# ---------------------------------------------------------------------------

class TestAcceleration:
    def test_acceleration_to_top_speed(self):
        """Pressing right from standstill should reach TOP_SPEED and not exceed it."""
        state = PhysicsState(on_ground=True)
        inp = InputState(right=True)

        # Run enough frames to reach top speed
        frames_needed = int(TOP_SPEED / ACCELERATION) + 10
        for _ in range(frames_needed):
            apply_input(state, inp)

        assert state.ground_speed == pytest.approx(TOP_SPEED, abs=ACCELERATION)

    def test_acceleration_not_applied_above_top_speed(self):
        """If ground_speed is already at TOP_SPEED, acceleration should not increase it."""
        state = PhysicsState(on_ground=True, ground_speed=TOP_SPEED)
        inp = InputState(right=True)

        apply_input(state, inp)

        assert state.ground_speed == pytest.approx(TOP_SPEED)

    def test_momentum_can_exceed_top_speed(self):
        """Speed set above TOP_SPEED (e.g. from slopes) is preserved."""
        state = PhysicsState(on_ground=True, ground_speed=10.0)
        inp = InputState(right=True)

        apply_input(state, inp)

        # Should not accelerate further, but should not clamp down either
        assert state.ground_speed == pytest.approx(10.0)

    def test_deceleration(self):
        """Pressing opposite direction applies deceleration."""
        state = PhysicsState(on_ground=True, ground_speed=3.0)
        inp = InputState(left=True)

        apply_input(state, inp)

        assert state.ground_speed == pytest.approx(3.0 - DECELERATION)

    def test_friction_when_no_input(self):
        """No directional input applies friction."""
        state = PhysicsState(on_ground=True, ground_speed=1.0)
        inp = InputState()

        apply_input(state, inp)

        assert state.ground_speed == pytest.approx(1.0 - FRICTION)


# ---------------------------------------------------------------------------
# Spindash
# ---------------------------------------------------------------------------

class TestSpindash:
    def test_charge_increment(self):
        """Each charge press adds SPINDASH_CHARGE_INCREMENT."""
        state = PhysicsState()

        apply_spindash_charge(state)
        assert state.spinrev == pytest.approx(SPINDASH_CHARGE_INCREMENT)

        apply_spindash_charge(state)
        assert state.spinrev == pytest.approx(2 * SPINDASH_CHARGE_INCREMENT)

    def test_charge_max_cap(self):
        """Spinrev cannot exceed SPINDASH_MAX_CHARGE."""
        state = PhysicsState()

        for _ in range(10):
            apply_spindash_charge(state)

        assert state.spinrev == pytest.approx(SPINDASH_MAX_CHARGE)

    def test_decay_formula(self):
        """Decay follows spinrev -= spinrev / SPINDASH_DECAY_DIVISOR."""
        state = PhysicsState(spinrev=8.0)

        apply_spindash_decay(state)
        expected = 8.0 - 8.0 / SPINDASH_DECAY_DIVISOR
        assert state.spinrev == pytest.approx(expected)

        # Another frame
        prev = state.spinrev
        apply_spindash_decay(state)
        assert state.spinrev == pytest.approx(prev - prev / SPINDASH_DECAY_DIVISOR)

    def test_release_speed(self):
        """Release sets ground_speed = SPINDASH_BASE_SPEED + floor(spinrev / 2)."""
        state = PhysicsState(spinrev=6.0, facing_right=True, is_charging_spindash=True)

        apply_spindash_release(state)

        expected = SPINDASH_BASE_SPEED + math.floor(6.0 / 2)
        assert state.ground_speed == pytest.approx(expected)
        assert state.spinrev == 0.0
        assert not state.is_charging_spindash
        assert state.is_rolling

    def test_release_speed_facing_left(self):
        """Release facing left produces negative ground_speed."""
        state = PhysicsState(spinrev=4.0, facing_right=False, is_charging_spindash=True)

        apply_spindash_release(state)

        expected = -(SPINDASH_BASE_SPEED + math.floor(4.0 / 2))
        assert state.ground_speed == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Variable jump height
# ---------------------------------------------------------------------------

class TestVariableJump:
    def test_cap_while_rising(self):
        """When y_vel < JUMP_RELEASE_CAP and jump released, cap to -4.0."""
        state = PhysicsState(y_vel=-6.5, on_ground=False)

        apply_variable_jump(state)

        assert state.y_vel == pytest.approx(JUMP_RELEASE_CAP)

    def test_no_cap_when_rising_slowly(self):
        """When y_vel is between JUMP_RELEASE_CAP and 0, no change."""
        state = PhysicsState(y_vel=-2.0, on_ground=False)

        apply_variable_jump(state)

        assert state.y_vel == pytest.approx(-2.0)

    def test_no_cap_when_falling(self):
        """When y_vel >= 0 (falling), do nothing."""
        state = PhysicsState(y_vel=1.0, on_ground=False)

        apply_variable_jump(state)

        assert state.y_vel == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Slope factor on 45° slope
# ---------------------------------------------------------------------------

class TestSlopeFactor:
    def test_slope_factor_45_degrees(self):
        """On a 45° slope, ground_speed changes by -SLOPE_FACTOR_RUNNING * sin(45°)."""
        byte_45 = degrees_to_byte(45.0)
        state = PhysicsState(on_ground=True, ground_speed=3.0, angle=byte_45)

        apply_slope_factor(state)

        angle_rad = byte_angle_to_rad(byte_45)
        expected = 3.0 - SLOPE_FACTOR_RUNNING * math.sin(angle_rad)
        assert state.ground_speed == pytest.approx(expected)

    def test_slope_factor_flat(self):
        """On flat ground (angle=0), slope factor has no effect."""
        state = PhysicsState(on_ground=True, ground_speed=3.0, angle=0)

        apply_slope_factor(state)

        assert state.ground_speed == pytest.approx(3.0)

    def test_slope_factor_not_applied_in_air(self):
        """Slope factor is not applied when airborne."""
        state = PhysicsState(on_ground=False, ground_speed=3.0, angle=degrees_to_byte(45.0))

        apply_slope_factor(state)

        assert state.ground_speed == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# Landing speed recalculation
# ---------------------------------------------------------------------------

class TestLandingSpeed:
    def test_landing_flat(self):
        """On flat ground (angle ~0°), ground_speed = x_vel."""
        state = PhysicsState(
            x_vel=5.0, y_vel=3.0,
            angle=0,  # 0° = flat
        )

        calculate_landing_speed(state)

        assert state.ground_speed == pytest.approx(5.0)

    def test_landing_slope(self):
        """On a 30° slope, use y-based formula with 0.5 factor if |y_based| > |x_vel|."""
        byte_30 = degrees_to_byte(30.0)
        angle_rad = byte_angle_to_rad(byte_30)
        sin_a = math.sin(angle_rad)

        # Use high y_vel to ensure y-based wins
        state = PhysicsState(
            x_vel=1.0, y_vel=8.0,
            angle=byte_30,
        )

        calculate_landing_speed(state)

        y_based = 8.0 * 0.5 * -sign(sin_a)
        assert state.ground_speed == pytest.approx(y_based)

    def test_landing_slope_x_wins(self):
        """On a slope, if |x_vel| > |y_based|, use x_vel."""
        byte_30 = degrees_to_byte(30.0)
        state = PhysicsState(
            x_vel=10.0, y_vel=1.0,
            angle=byte_30,
        )

        calculate_landing_speed(state)

        assert state.ground_speed == pytest.approx(10.0)

    def test_landing_steep(self):
        """On a steep angle (e.g. 90°), use y-based formula without 0.5 factor."""
        byte_90 = degrees_to_byte(90.0)
        angle_rad = byte_angle_to_rad(byte_90)
        sin_a = math.sin(angle_rad)

        state = PhysicsState(
            x_vel=1.0, y_vel=8.0,
            angle=byte_90,
        )

        calculate_landing_speed(state)

        y_based = 8.0 * -sign(sin_a)
        assert state.ground_speed == pytest.approx(y_based)


# ---------------------------------------------------------------------------
# Rolling
# ---------------------------------------------------------------------------

class TestRolling:
    def test_rolling_no_acceleration(self):
        """While rolling, pressing a direction does not accelerate."""
        state = PhysicsState(on_ground=True, is_rolling=True, ground_speed=3.0)
        inp = InputState(right=True)

        apply_input(state, inp)

        # Should have friction applied but no acceleration
        assert state.ground_speed < 3.0
        # Should be exactly: 3.0 - ROLLING_FRICTION (no accel)
        assert state.ground_speed == pytest.approx(3.0 - ROLLING_FRICTION)

    def test_rolling_friction(self):
        """Rolling friction is applied every frame."""
        state = PhysicsState(on_ground=True, is_rolling=True, ground_speed=3.0)
        inp = InputState()

        apply_input(state, inp)

        assert state.ground_speed == pytest.approx(3.0 - ROLLING_FRICTION)

    def test_rolling_deceleration(self):
        """Pressing opposite direction while rolling applies rolling deceleration."""
        state = PhysicsState(on_ground=True, is_rolling=True, ground_speed=3.0)
        inp = InputState(left=True)

        apply_input(state, inp)

        # Both rolling decel and rolling friction applied
        expected = 3.0 - ROLLING_DECELERATION - ROLLING_FRICTION
        assert state.ground_speed == pytest.approx(expected)

    def test_unroll_below_min_speed(self):
        """Rolling stops when ground_speed drops below MIN_ROLL_SPEED."""
        state = PhysicsState(on_ground=True, is_rolling=True, ground_speed=0.3)
        inp = InputState()

        apply_input(state, inp)

        assert not state.is_rolling


# ---------------------------------------------------------------------------
# Gravity
# ---------------------------------------------------------------------------

class TestGravity:
    def test_gravity_applied_in_air(self):
        """Gravity increases y_vel when airborne."""
        state = PhysicsState(on_ground=False, y_vel=0.0)

        apply_gravity(state)

        assert state.y_vel == pytest.approx(GRAVITY)

    def test_gravity_not_applied_on_ground(self):
        """Gravity is not applied when on ground."""
        state = PhysicsState(on_ground=True, y_vel=0.0)

        apply_gravity(state)

        assert state.y_vel == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Jump
# ---------------------------------------------------------------------------

class TestJump:
    def test_jump_from_flat_ground(self):
        """Jumping from flat ground (angle=0) gives pure upward velocity."""
        state = PhysicsState(on_ground=True, ground_speed=3.0, angle=0)

        apply_jump(state)

        assert state.x_vel == pytest.approx(3.0)  # cos(0) = 1
        assert state.y_vel == pytest.approx(-JUMP_FORCE)  # -cos(0) * JUMP_FORCE
        assert not state.on_ground

    def test_jump_from_slope(self):
        """Jumping from a slope adjusts velocity by angle."""
        byte_45 = degrees_to_byte(45.0)
        angle_rad = byte_angle_to_rad(byte_45)
        gs = 3.0
        state = PhysicsState(on_ground=True, ground_speed=gs, angle=byte_45)

        apply_jump(state)

        expected_x = gs * math.cos(angle_rad) - JUMP_FORCE * math.sin(angle_rad)
        expected_y = gs * -math.sin(angle_rad) - JUMP_FORCE * math.cos(angle_rad)
        assert state.x_vel == pytest.approx(expected_x)
        assert state.y_vel == pytest.approx(expected_y)
        assert not state.on_ground
        assert state.angle == 0


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------

class TestMovement:
    def test_ground_movement_flat(self):
        """On flat ground, x_vel = ground_speed, y_vel = 0."""
        state = PhysicsState(on_ground=True, ground_speed=5.0, angle=0, x=10.0, y=20.0)

        apply_movement(state)

        assert state.x_vel == pytest.approx(5.0)
        assert state.y_vel == pytest.approx(0.0)
        assert state.x == pytest.approx(15.0)
        assert state.y == pytest.approx(20.0)

    def test_air_movement(self):
        """In air, x/y vel are used directly (no decomposition)."""
        state = PhysicsState(on_ground=False, x_vel=3.0, y_vel=2.0, x=0.0, y=0.0)

        apply_movement(state)

        assert state.x == pytest.approx(3.0)
        assert state.y == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Slip detection
# ---------------------------------------------------------------------------

class TestSlip:
    def test_slip_on_steep_slope(self):
        """Slip triggers when slow on steep slope."""
        byte_90 = degrees_to_byte(90.0)
        state = PhysicsState(on_ground=True, ground_speed=1.0, angle=byte_90)

        assert check_slip(state)

    def test_no_slip_on_flat(self):
        """No slip on flat ground regardless of speed."""
        state = PhysicsState(on_ground=True, ground_speed=0.5, angle=0)

        assert not check_slip(state)

    def test_no_slip_when_fast(self):
        """No slip even on steep slope if moving fast enough."""
        byte_90 = degrees_to_byte(90.0)
        state = PhysicsState(on_ground=True, ground_speed=5.0, angle=byte_90)

        assert not check_slip(state)


# ---------------------------------------------------------------------------
# Byte angle conversion
# ---------------------------------------------------------------------------

class TestAngleConversion:
    def test_zero(self):
        assert byte_angle_to_rad(0) == pytest.approx(0.0)

    def test_quarter(self):
        assert byte_angle_to_rad(64) == pytest.approx(math.pi / 2)

    def test_half(self):
        assert byte_angle_to_rad(128) == pytest.approx(math.pi)

    def test_full(self):
        assert byte_angle_to_rad(256) == pytest.approx(2 * math.pi)

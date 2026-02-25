"""Tests for speednik/player.py — player state machine and integration."""

from __future__ import annotations

import pytest

from speednik.constants import (
    GRAVITY,
    HURT_KNOCKBACK_X,
    HURT_KNOCKBACK_Y,
    INVULNERABILITY_DURATION,
    MIN_ROLL_SPEED,
    SCATTER_RING_LIFETIME,
    SPINDASH_BASE_SPEED,
    STANDING_HEIGHT_RADIUS,
    STANDING_WIDTH_RADIUS,
    ROLLING_HEIGHT_RADIUS,
    ROLLING_WIDTH_RADIUS,
)
from speednik.physics import InputState, PhysicsState
from speednik.player import (
    Player,
    PlayerState,
    ScatteredRing,
    create_player,
    damage_player,
    get_player_rect,
    player_update,
)
from speednik.terrain import FULL, TILE_SIZE, Tile, TileLookup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def flat_tile(angle: int = 0, solidity: int = FULL) -> Tile:
    """A completely flat full tile."""
    return Tile(height_array=[TILE_SIZE] * TILE_SIZE, angle=angle, solidity=solidity)


def make_tile_lookup(tiles: dict[tuple[int, int], Tile]) -> TileLookup:
    """Create a TileLookup from a dict."""
    def lookup(tx: int, ty: int) -> Tile | None:
        return tiles.get((tx, ty))
    return lookup


def flat_ground_lookup() -> TileLookup:
    """A wide flat ground at tile_y=12 (pixel y=192)."""
    tiles = {}
    for tx in range(30):
        tiles[(tx, 12)] = flat_tile()
    return make_tile_lookup(tiles)


def empty_lookup() -> TileLookup:
    """No tiles at all — player is in the void."""
    return make_tile_lookup({})


# ---------------------------------------------------------------------------
# TestCreatePlayer
# ---------------------------------------------------------------------------

class TestCreatePlayer:
    def test_initial_position(self):
        p = create_player(64.0, 172.0)
        assert p.physics.x == pytest.approx(64.0)
        assert p.physics.y == pytest.approx(172.0)

    def test_initial_state(self):
        p = create_player(0.0, 0.0)
        assert p.state == PlayerState.STANDING
        assert p.rings == 0
        assert p.lives == 3
        assert p.physics.on_ground is True


# ---------------------------------------------------------------------------
# TestStateTransitions
# ---------------------------------------------------------------------------

class TestStateTransitions:
    def test_standing_to_running(self):
        """Moving on ground transitions to RUNNING."""
        p = create_player(64.0, 172.0)
        lookup = flat_ground_lookup()
        inp = InputState(right=True, jump_held=False)

        # Run a few frames to build speed
        for _ in range(5):
            player_update(p, inp, lookup)

        assert p.state == PlayerState.RUNNING
        assert p.physics.ground_speed > 0

    def test_running_to_standing(self):
        """Friction brings player to a stop → STANDING."""
        p = create_player(64.0, 172.0)
        p.physics.ground_speed = 0.1
        p.state = PlayerState.RUNNING
        lookup = flat_ground_lookup()
        inp = InputState()  # No input → friction

        for _ in range(20):
            player_update(p, inp, lookup)

        assert p.state == PlayerState.STANDING
        assert p.physics.ground_speed == pytest.approx(0.0)

    def test_standing_to_jumping(self):
        """Jump from standing."""
        p = create_player(64.0, 172.0)
        lookup = flat_ground_lookup()
        inp = InputState(jump_pressed=True, jump_held=True)

        player_update(p, inp, lookup)

        assert p.state == PlayerState.JUMPING
        assert p.physics.on_ground is False

    def test_running_to_jumping(self):
        """Jump while running."""
        p = create_player(64.0, 172.0)
        p.physics.ground_speed = 3.0
        p.state = PlayerState.RUNNING
        lookup = flat_ground_lookup()
        inp = InputState(right=True, jump_pressed=True, jump_held=True)

        player_update(p, inp, lookup)

        assert p.state == PlayerState.JUMPING

    def test_standing_to_rolling(self):
        """Press down while moving → ROLLING."""
        p = create_player(64.0, 172.0)
        p.physics.ground_speed = 2.0
        p.state = PlayerState.RUNNING
        lookup = flat_ground_lookup()
        inp = InputState(down_held=True)

        player_update(p, inp, lookup)

        assert p.state == PlayerState.ROLLING
        assert p.physics.is_rolling is True

    def test_rolling_to_standing_on_slow(self):
        """Rolling stops when speed drops below threshold."""
        p = create_player(64.0, 172.0)
        p.physics.ground_speed = 0.3
        p.physics.is_rolling = True
        p.state = PlayerState.ROLLING
        lookup = flat_ground_lookup()
        inp = InputState()

        player_update(p, inp, lookup)

        # Physics will unroll, post-physics syncs state
        assert p.state == PlayerState.STANDING
        assert p.physics.is_rolling is False

    def test_jump_landing_returns_to_standing(self):
        """After jumping, landing brings player back to STANDING."""
        p = create_player(64.0, 172.0)
        lookup = flat_ground_lookup()

        # Jump
        inp_jump = InputState(jump_pressed=True, jump_held=True)
        player_update(p, inp_jump, lookup)
        assert p.state == PlayerState.JUMPING

        # Let player fall back down
        inp_none = InputState()
        for _ in range(100):
            player_update(p, inp_none, lookup)
            if p.state != PlayerState.JUMPING:
                break

        assert p.state in (PlayerState.STANDING, PlayerState.RUNNING)
        assert p.physics.on_ground is True

    def test_walk_off_edge(self):
        """Walking off edge transitions to JUMPING."""
        p = create_player(64.0, 172.0)
        p.physics.ground_speed = 6.0
        p.state = PlayerState.RUNNING
        # Only 2 tiles of ground — player will walk off
        tiles = {(4, 12): flat_tile(), (5, 12): flat_tile()}
        lookup = make_tile_lookup(tiles)
        inp = InputState(right=True)

        for _ in range(30):
            player_update(p, inp, lookup)
            if p.state == PlayerState.JUMPING:
                break

        assert p.state == PlayerState.JUMPING


# ---------------------------------------------------------------------------
# TestSpindashFlow
# ---------------------------------------------------------------------------

class TestSpindashFlow:
    def test_enter_spindash(self):
        """Press down while standing still enters SPINDASH."""
        p = create_player(64.0, 172.0)
        lookup = flat_ground_lookup()
        inp = InputState(down_held=True)

        player_update(p, inp, lookup)

        assert p.state == PlayerState.SPINDASH

    def test_spindash_charge(self):
        """Pressing jump during spindash increases spinrev."""
        p = create_player(64.0, 172.0)
        p.state = PlayerState.SPINDASH
        p.physics.is_charging_spindash = True
        lookup = flat_ground_lookup()
        inp = InputState(down_held=True, jump_pressed=True, jump_held=True)

        player_update(p, inp, lookup)

        assert p.physics.spinrev > 0

    def test_spindash_release(self):
        """Releasing down during spindash launches into ROLLING."""
        p = create_player(64.0, 172.0)
        p.state = PlayerState.SPINDASH
        p.physics.is_charging_spindash = True
        p.physics.spinrev = 4.0
        lookup = flat_ground_lookup()
        inp = InputState(down_held=False)  # Release down

        player_update(p, inp, lookup)

        assert p.state == PlayerState.ROLLING
        assert abs(p.physics.ground_speed) >= SPINDASH_BASE_SPEED

    def test_spindash_decay(self):
        """Spinrev decays each frame while holding spindash."""
        p = create_player(64.0, 172.0)
        p.state = PlayerState.SPINDASH
        p.physics.is_charging_spindash = True
        p.physics.spinrev = 8.0
        lookup = flat_ground_lookup()
        inp = InputState(down_held=True)  # Hold, no jump

        player_update(p, inp, lookup)

        assert p.physics.spinrev < 8.0


# ---------------------------------------------------------------------------
# TestJumpFlow
# ---------------------------------------------------------------------------

class TestJumpFlow:
    def test_jump_initiates(self):
        """Jump sets y_vel negative and clears on_ground."""
        p = create_player(64.0, 172.0)
        lookup = flat_ground_lookup()
        inp = InputState(jump_pressed=True, jump_held=True)

        player_update(p, inp, lookup)

        assert p.physics.y_vel < 0
        assert p.physics.on_ground is False
        assert p.state == PlayerState.JUMPING

    def test_variable_jump_height(self):
        """Releasing jump caps upward velocity."""
        p = create_player(64.0, 172.0)
        lookup = flat_ground_lookup()

        # Jump
        inp_jump = InputState(jump_pressed=True, jump_held=True)
        player_update(p, inp_jump, lookup)
        assert p.state == PlayerState.JUMPING

        # Release immediately
        inp_release = InputState(jump_held=False)
        player_update(p, inp_release, lookup)

        # y_vel should be capped (less negative than full jump)
        assert p.physics.y_vel >= -4.0

    def test_jump_from_rolling(self):
        """Can jump while rolling."""
        p = create_player(64.0, 172.0)
        p.physics.ground_speed = 3.0
        p.physics.is_rolling = True
        p.state = PlayerState.ROLLING
        lookup = flat_ground_lookup()
        inp = InputState(jump_pressed=True, jump_held=True)

        player_update(p, inp, lookup)

        assert p.state == PlayerState.JUMPING

    def test_cannot_jump_while_hurt(self):
        """Cannot jump in HURT state."""
        p = create_player(64.0, 172.0)
        p.state = PlayerState.HURT
        p.physics.on_ground = False
        p.invulnerability_timer = 60
        lookup = flat_ground_lookup()
        inp = InputState(jump_pressed=True, jump_held=True)

        player_update(p, inp, lookup)

        # Should still be hurt, not jumping
        assert p.state == PlayerState.HURT


# ---------------------------------------------------------------------------
# TestRollFlow
# ---------------------------------------------------------------------------

class TestRollFlow:
    def test_roll_requires_speed(self):
        """Cannot roll when speed is below threshold."""
        p = create_player(64.0, 172.0)
        p.physics.ground_speed = 0.1  # Below MIN_ROLL_SPEED
        lookup = flat_ground_lookup()
        inp = InputState(down_held=True)

        player_update(p, inp, lookup)

        # Should enter spindash instead (standing + slow + down)
        assert p.state == PlayerState.SPINDASH

    def test_roll_at_speed(self):
        """Can roll when speed meets threshold."""
        p = create_player(64.0, 172.0)
        p.physics.ground_speed = 3.0
        p.state = PlayerState.RUNNING
        lookup = flat_ground_lookup()
        inp = InputState(down_held=True)

        player_update(p, inp, lookup)

        assert p.state == PlayerState.ROLLING

    def test_roll_unroll_on_slow(self):
        """Rolling stops when speed drops."""
        p = create_player(64.0, 172.0)
        p.physics.ground_speed = 0.3
        p.physics.is_rolling = True
        p.state = PlayerState.ROLLING
        lookup = flat_ground_lookup()
        inp = InputState()

        player_update(p, inp, lookup)

        assert p.state == PlayerState.STANDING


# ---------------------------------------------------------------------------
# TestDamage
# ---------------------------------------------------------------------------

class TestDamage:
    def test_damage_with_rings_scatters(self):
        """Damage with rings > 0 scatters rings and enters HURT."""
        p = create_player(64.0, 172.0)
        p.rings = 10

        damage_player(p)

        assert p.state == PlayerState.HURT
        assert p.rings == 0
        assert p.invulnerability_timer == INVULNERABILITY_DURATION
        assert len(p.scattered_rings) == 10
        assert p.physics.on_ground is False

    def test_damage_without_rings_kills(self):
        """Damage with rings == 0 kills player."""
        p = create_player(64.0, 172.0)
        p.rings = 0

        damage_player(p)

        assert p.state == PlayerState.DEAD

    def test_invulnerability_prevents_damage(self):
        """Cannot take damage during invulnerability."""
        p = create_player(64.0, 172.0)
        p.rings = 5
        p.invulnerability_timer = 60

        damage_player(p)

        assert p.rings == 5  # Unchanged

    def test_scattered_rings_expire(self):
        """Scattered rings disappear after timeout."""
        p = create_player(64.0, 172.0)
        p.scattered_rings = [ScatteredRing(x=100, y=100, vx=1, vy=-2, timer=2)]
        lookup = flat_ground_lookup()
        inp = InputState()

        player_update(p, inp, lookup)
        assert len(p.scattered_rings) == 1  # timer=1 after update

        player_update(p, inp, lookup)
        assert len(p.scattered_rings) == 0  # timer=0 → removed

    def test_dead_state_stops_updates(self):
        """Dead player doesn't process inputs."""
        p = create_player(64.0, 172.0)
        p.state = PlayerState.DEAD
        old_x = p.physics.x
        lookup = flat_ground_lookup()
        inp = InputState(right=True)

        player_update(p, inp, lookup)

        assert p.physics.x == pytest.approx(old_x)

    def test_max_scatter_cap(self):
        """Ring scatter is capped at MAX_SCATTER_RINGS."""
        p = create_player(64.0, 172.0)
        p.rings = 100

        damage_player(p)

        assert len(p.scattered_rings) == 32


# ---------------------------------------------------------------------------
# TestAnimationState
# ---------------------------------------------------------------------------

class TestAnimationState:
    def test_idle_animation(self):
        """Standing player has idle animation."""
        p = create_player(64.0, 172.0)
        lookup = flat_ground_lookup()
        inp = InputState()

        player_update(p, inp, lookup)

        assert p.anim_name == "idle"

    def test_running_animation(self):
        """Running player has running animation."""
        p = create_player(64.0, 172.0)
        p.physics.ground_speed = 3.0
        p.state = PlayerState.RUNNING
        lookup = flat_ground_lookup()
        inp = InputState(right=True)

        player_update(p, inp, lookup)

        assert p.anim_name == "running"

    def test_animation_resets_on_state_change(self):
        """Animation frame resets when anim_name changes."""
        p = create_player(64.0, 172.0)
        p.anim_frame = 3
        p.anim_name = "running"
        p.state = PlayerState.STANDING
        lookup = flat_ground_lookup()
        inp = InputState()

        player_update(p, inp, lookup)

        assert p.anim_frame == 0


# ---------------------------------------------------------------------------
# TestGetPlayerRect
# ---------------------------------------------------------------------------

class TestGetPlayerRect:
    def test_standing_rect(self):
        p = create_player(100.0, 100.0)
        x, y, w, h = get_player_rect(p)
        assert w == STANDING_WIDTH_RADIUS * 2
        assert h == STANDING_HEIGHT_RADIUS * 2

    def test_rolling_rect(self):
        p = create_player(100.0, 100.0)
        p.physics.is_rolling = True
        x, y, w, h = get_player_rect(p)
        assert w == ROLLING_WIDTH_RADIUS * 2
        assert h == ROLLING_HEIGHT_RADIUS * 2

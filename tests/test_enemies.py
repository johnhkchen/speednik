"""Tests for speednik/enemies.py — enemy loading, behavior, and collision."""

from __future__ import annotations

from speednik.constants import (
    CHOPPER_JUMP_INTERVAL,
    CHOPPER_JUMP_VELOCITY,
    CRAB_PATROL_RANGE,
    CRAB_PATROL_SPEED,
    ENEMY_BOUNCE_VELOCITY,
    GRAVITY,
    SPINDASH_KILL_THRESHOLD,
)
from speednik.enemies import (
    Enemy,
    EnemyEvent,
    check_enemy_collision,
    load_enemies,
    update_enemies,
)
from speednik.player import PlayerState, create_player


# ---------------------------------------------------------------------------
# TestLoadEnemies
# ---------------------------------------------------------------------------

class TestLoadEnemies:
    def test_loads_enemy_entities(self):
        entities = [
            {"type": "enemy_crab", "x": 100, "y": 200},
            {"type": "enemy_buzzer", "x": 300, "y": 150},
        ]
        enemies = load_enemies(entities)
        assert len(enemies) == 2
        assert enemies[0].enemy_type == "enemy_crab"
        assert enemies[0].x == 100.0
        assert enemies[0].y == 200.0
        assert enemies[1].enemy_type == "enemy_buzzer"

    def test_ignores_non_enemy_entities(self):
        entities = [
            {"type": "ring", "x": 100, "y": 200},
            {"type": "enemy_crab", "x": 300, "y": 400},
            {"type": "player_start", "x": 50, "y": 100},
        ]
        enemies = load_enemies(entities)
        assert len(enemies) == 1
        assert enemies[0].enemy_type == "enemy_crab"

    def test_empty_entities(self):
        enemies = load_enemies([])
        assert enemies == []

    def test_sets_origin_and_base_y(self):
        entities = [{"type": "enemy_crab", "x": 200, "y": 300}]
        enemies = load_enemies(entities)
        assert enemies[0].origin_x == 200.0
        assert enemies[0].base_y == 300.0

    def test_guardian_loads_shielded(self):
        entities = [{"type": "enemy_guardian", "x": 100, "y": 200}]
        enemies = load_enemies(entities)
        assert enemies[0].shielded is True

    def test_non_guardian_not_shielded(self):
        entities = [{"type": "enemy_crab", "x": 100, "y": 200}]
        enemies = load_enemies(entities)
        assert enemies[0].shielded is False

    def test_chopper_gets_jump_timer(self):
        entities = [{"type": "enemy_chopper", "x": 100, "y": 200}]
        enemies = load_enemies(entities)
        assert enemies[0].jump_timer == CHOPPER_JUMP_INTERVAL


# ---------------------------------------------------------------------------
# TestCrabPatrol
# ---------------------------------------------------------------------------

class TestCrabPatrol:
    def test_crab_moves_right(self):
        enemy = Enemy(x=100.0, y=200.0, enemy_type="enemy_crab", origin_x=100.0)
        update_enemies([enemy])
        assert enemy.x == 100.0 + CRAB_PATROL_SPEED

    def test_crab_moves_left(self):
        enemy = Enemy(x=100.0, y=200.0, enemy_type="enemy_crab",
                      origin_x=100.0, patrol_dir=-1)
        update_enemies([enemy])
        assert enemy.x == 100.0 - CRAB_PATROL_SPEED

    def test_crab_reverses_at_right_edge(self):
        enemy = Enemy(x=100.0 + CRAB_PATROL_RANGE - 0.1, y=200.0,
                      enemy_type="enemy_crab", origin_x=100.0, patrol_dir=1)
        update_enemies([enemy])
        assert enemy.patrol_dir == -1
        assert enemy.x == 100.0 + CRAB_PATROL_RANGE

    def test_crab_reverses_at_left_edge(self):
        enemy = Enemy(x=100.0 - CRAB_PATROL_RANGE + 0.1, y=200.0,
                      enemy_type="enemy_crab", origin_x=100.0, patrol_dir=-1)
        update_enemies([enemy])
        assert enemy.patrol_dir == 1
        assert enemy.x == 100.0 - CRAB_PATROL_RANGE

    def test_crab_full_patrol_cycle(self):
        """Crab patrols from origin to +range, back to -range, and returns."""
        enemy = Enemy(x=100.0, y=200.0, enemy_type="enemy_crab", origin_x=100.0)
        positions = [enemy.x]
        for _ in range(300):
            update_enemies([enemy])
            positions.append(enemy.x)
        # Should stay within patrol range
        assert all(100.0 - CRAB_PATROL_RANGE <= p <= 100.0 + CRAB_PATROL_RANGE
                   for p in positions)

    def test_dead_crab_does_not_move(self):
        enemy = Enemy(x=100.0, y=200.0, enemy_type="enemy_crab",
                      origin_x=100.0, alive=False)
        update_enemies([enemy])
        assert enemy.x == 100.0


# ---------------------------------------------------------------------------
# TestChopperJump
# ---------------------------------------------------------------------------

class TestChopperJump:
    def test_chopper_jumps_after_interval(self):
        enemy = Enemy(x=100.0, y=200.0, enemy_type="enemy_chopper",
                      base_y=200.0, jump_timer=1)
        update_enemies([enemy])
        assert enemy.y_vel == CHOPPER_JUMP_VELOCITY
        assert enemy.jump_timer == CHOPPER_JUMP_INTERVAL

    def test_chopper_waiting(self):
        """Chopper stays at base_y while timer counts down."""
        enemy = Enemy(x=100.0, y=200.0, enemy_type="enemy_chopper",
                      base_y=200.0, jump_timer=10)
        update_enemies([enemy])
        assert enemy.y == 200.0
        assert enemy.jump_timer == 9

    def test_chopper_rises_after_jump(self):
        enemy = Enemy(x=100.0, y=200.0, enemy_type="enemy_chopper",
                      base_y=200.0, y_vel=CHOPPER_JUMP_VELOCITY)
        # Simulate being in air (above base)
        enemy.y = 195.0
        update_enemies([enemy])
        # Should have moved up and had gravity applied
        expected_vel = CHOPPER_JUMP_VELOCITY + GRAVITY
        assert enemy.y_vel == expected_vel
        assert enemy.y < 200.0  # Still above base

    def test_chopper_returns_to_base(self):
        """Chopper resets to base_y when falling back down."""
        enemy = Enemy(x=100.0, y=200.0, enemy_type="enemy_chopper",
                      base_y=200.0, y_vel=1.0, jump_timer=50)  # falling, timer still counting
        update_enemies([enemy])
        # y >= base_y and y_vel >= 0 → reset to waiting state
        assert enemy.y == 200.0
        assert enemy.y_vel == 0.0
        assert enemy.jump_timer == 49  # decremented after reset


# ---------------------------------------------------------------------------
# TestBounceKill
# ---------------------------------------------------------------------------

class TestBounceKill:
    def test_bounce_on_enemy_from_above(self):
        """Player above enemy with downward velocity destroys enemy."""
        p = create_player(100.0, 90.0)
        p.physics.y_vel = 2.0  # descending
        p.physics.on_ground = False
        p.state = PlayerState.JUMPING
        enemy = Enemy(x=100.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=100.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert enemy.alive is False
        assert EnemyEvent.BOUNCE in events
        assert EnemyEvent.DESTROYED in events

    def test_bounce_sets_player_y_vel(self):
        """Bounce sets player y_vel to ENEMY_BOUNCE_VELOCITY."""
        p = create_player(100.0, 90.0)
        p.physics.y_vel = 2.0
        p.physics.on_ground = False
        p.state = PlayerState.JUMPING
        enemy = Enemy(x=100.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=100.0, alive=True)

        check_enemy_collision(p, [enemy])

        assert p.physics.y_vel == ENEMY_BOUNCE_VELOCITY

    def test_rolling_above_bounces(self):
        """Rolling player above enemy also triggers bounce."""
        p = create_player(100.0, 90.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = 3.0  # below spindash threshold
        p.physics.y_vel = 2.0
        p.physics.on_ground = False
        p.state = PlayerState.JUMPING
        enemy = Enemy(x=100.0, y=100.0, enemy_type="enemy_buzzer",
                      origin_x=100.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert enemy.alive is False
        assert EnemyEvent.BOUNCE in events

    def test_dead_enemy_ignored(self):
        """Dead enemies are skipped in collision."""
        p = create_player(100.0, 90.0)
        p.physics.y_vel = 2.0
        p.physics.on_ground = False
        p.state = PlayerState.JUMPING
        enemy = Enemy(x=100.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=100.0, alive=False)

        events = check_enemy_collision(p, [enemy])

        assert events == []


# ---------------------------------------------------------------------------
# TestSpindashKill
# ---------------------------------------------------------------------------

class TestSpindashKill:
    def test_spindash_through_enemy(self):
        """Rolling with ground_speed >= threshold destroys enemy."""
        p = create_player(100.0, 100.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        enemy = Enemy(x=108.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=108.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert enemy.alive is False
        assert EnemyEvent.DESTROYED in events

    def test_spindash_no_bounce(self):
        """Spindash kill does not set bounce velocity."""
        p = create_player(100.0, 100.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        original_y_vel = p.physics.y_vel
        enemy = Enemy(x=108.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=108.0, alive=True)

        check_enemy_collision(p, [enemy])

        assert p.physics.y_vel == original_y_vel
        assert EnemyEvent.BOUNCE not in check_enemy_collision(p, [])

    def test_spindash_negative_speed(self):
        """Spindash kill works with negative ground_speed (going left)."""
        p = create_player(100.0, 100.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = -SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        enemy = Enemy(x=92.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=92.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert enemy.alive is False
        assert EnemyEvent.DESTROYED in events

    def test_rolling_below_threshold_from_side_damages(self):
        """Rolling at speed below threshold from the side damages player."""
        p = create_player(100.0, 100.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD - 1
        p.state = PlayerState.ROLLING
        p.rings = 5
        enemy = Enemy(x=108.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=108.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert enemy.alive is True
        assert EnemyEvent.PLAYER_DAMAGED in events


# ---------------------------------------------------------------------------
# TestSideDamage
# ---------------------------------------------------------------------------

class TestSideDamage:
    def test_side_contact_damages_player(self):
        """Player walking into enemy from the side takes damage."""
        p = create_player(100.0, 100.0)
        p.rings = 10
        p.state = PlayerState.RUNNING
        enemy = Enemy(x=108.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=108.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert EnemyEvent.PLAYER_DAMAGED in events
        assert p.state == PlayerState.HURT
        assert p.rings == 0

    def test_invulnerable_player_not_damaged(self):
        """Invulnerable player touching enemy is not damaged."""
        p = create_player(100.0, 100.0)
        p.rings = 10
        p.invulnerability_timer = 60
        p.state = PlayerState.RUNNING
        enemy = Enemy(x=108.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=108.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert EnemyEvent.PLAYER_DAMAGED not in events
        assert p.rings == 10

    def test_dead_player_no_collision(self):
        """Dead player does not collide with enemies."""
        p = create_player(100.0, 100.0)
        p.state = PlayerState.DEAD
        enemy = Enemy(x=108.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=108.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert events == []

    def test_hurt_player_no_collision(self):
        """Hurt player (in knockback) does not collide with enemies."""
        p = create_player(100.0, 100.0)
        p.state = PlayerState.HURT
        enemy = Enemy(x=108.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=108.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert events == []

    def test_no_overlap_no_events(self):
        """Player far from enemy produces no events."""
        p = create_player(100.0, 100.0)
        enemy = Enemy(x=300.0, y=300.0, enemy_type="enemy_crab",
                      origin_x=300.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert events == []

    def test_player_zero_rings_dies(self):
        """Player with 0 rings touching enemy dies."""
        p = create_player(100.0, 100.0)
        p.rings = 0
        p.state = PlayerState.RUNNING
        enemy = Enemy(x=108.0, y=100.0, enemy_type="enemy_crab",
                      origin_x=108.0, alive=True)

        events = check_enemy_collision(p, [enemy])

        assert EnemyEvent.PLAYER_DAMAGED in events
        assert p.state == PlayerState.DEAD


# ---------------------------------------------------------------------------
# TestGuardian
# ---------------------------------------------------------------------------

class TestGuardian:
    def test_guardian_blocks_normal_attack(self):
        """Jumping on guardian with shield damages the player."""
        p = create_player(100.0, 86.0)
        p.physics.y_vel = 2.0
        p.physics.on_ground = False
        p.state = PlayerState.JUMPING
        p.rings = 5
        enemy = Enemy(x=100.0, y=100.0, enemy_type="enemy_guardian",
                      origin_x=100.0, shielded=True)

        events = check_enemy_collision(p, [enemy])

        assert enemy.alive is True
        assert EnemyEvent.PLAYER_DAMAGED in events

    def test_guardian_spindash_kills(self):
        """Spindash at threshold speed destroys shielded guardian."""
        p = create_player(100.0, 100.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        enemy = Enemy(x=112.0, y=100.0, enemy_type="enemy_guardian",
                      origin_x=112.0, shielded=True)

        events = check_enemy_collision(p, [enemy])

        assert enemy.alive is False
        assert EnemyEvent.SHIELD_BREAK in events
        assert EnemyEvent.DESTROYED in events

    def test_guardian_shield_break_event(self):
        """Shield break event is returned alongside destroyed."""
        p = create_player(100.0, 100.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        enemy = Enemy(x=112.0, y=100.0, enemy_type="enemy_guardian",
                      origin_x=112.0, shielded=True)

        events = check_enemy_collision(p, [enemy])

        assert events == [EnemyEvent.SHIELD_BREAK, EnemyEvent.DESTROYED]

    def test_guardian_invulnerable_player_not_damaged(self):
        """Invulnerable player touching shielded guardian is not damaged."""
        p = create_player(100.0, 100.0)
        p.invulnerability_timer = 60
        p.state = PlayerState.RUNNING
        enemy = Enemy(x=112.0, y=100.0, enemy_type="enemy_guardian",
                      origin_x=112.0, shielded=True)

        events = check_enemy_collision(p, [enemy])

        assert events == []
        assert p.state == PlayerState.RUNNING

    def test_guardian_below_threshold_damages(self):
        """Rolling below spindash threshold into guardian damages player."""
        p = create_player(100.0, 100.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD - 1
        p.state = PlayerState.ROLLING
        p.rings = 5
        enemy = Enemy(x=112.0, y=100.0, enemy_type="enemy_guardian",
                      origin_x=112.0, shielded=True)

        events = check_enemy_collision(p, [enemy])

        assert enemy.alive is True
        assert EnemyEvent.PLAYER_DAMAGED in events

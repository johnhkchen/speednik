"""Tests for speednik/enemies.py — enemy loading, behavior, and collision."""

from __future__ import annotations

from speednik.constants import (
    BOSS_ASCEND_DURATION,
    BOSS_DESCEND_DURATION,
    BOSS_ESCALATION_HP,
    BOSS_HIT_INVULN,
    BOSS_HP,
    BOSS_IDLE_DURATION,
    BOSS_IDLE_SPEED,
    BOSS_IDLE_SPEED_ESC,
    BOSS_VULNERABLE_DURATION,
    BOSS_VULNERABLE_DURATION_ESC,
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


# ---------------------------------------------------------------------------
# Helper: create an egg piston boss in a specific state
# ---------------------------------------------------------------------------

def _make_boss(
    x: float = 500.0,
    y: float = 500.0,
    state: str = "idle",
    hp: int = BOSS_HP,
    timer: int = 0,
    escalated: bool = False,
) -> Enemy:
    """Create a boss enemy for testing."""
    boss = Enemy(
        x=x,
        y=y,
        enemy_type="enemy_egg_piston",
        origin_x=x,
        boss_state=state,
        boss_hp=hp,
        boss_timer=timer if timer else BOSS_IDLE_DURATION,
        boss_hover_y=y - 80.0,
        boss_ground_y=y,
        boss_target_x=x,
        boss_left_x=x - 128.0,
        boss_right_x=x + 128.0,
        boss_escalated=escalated,
    )
    return boss


# ---------------------------------------------------------------------------
# TestEggPistonLoading
# ---------------------------------------------------------------------------

class TestEggPistonLoading:
    def test_loads_boss_state(self):
        entities = [{"type": "enemy_egg_piston", "x": 500, "y": 500}]
        enemies = load_enemies(entities)
        boss = enemies[0]
        assert boss.boss_state == "idle"
        assert boss.boss_hp == BOSS_HP
        assert boss.boss_timer == BOSS_IDLE_DURATION

    def test_loads_boss_positions(self):
        entities = [{"type": "enemy_egg_piston", "x": 500, "y": 500}]
        enemies = load_enemies(entities)
        boss = enemies[0]
        assert boss.boss_hover_y == 420.0  # 500 - 80
        assert boss.boss_ground_y == 500.0
        assert boss.boss_target_x == 500.0

    def test_loads_boss_arena_bounds(self):
        entities = [{"type": "enemy_egg_piston", "x": 500, "y": 500}]
        enemies = load_enemies(entities)
        boss = enemies[0]
        assert boss.boss_left_x == 372.0  # 500 - 128
        assert boss.boss_right_x == 628.0  # 500 + 128


# ---------------------------------------------------------------------------
# TestEggPistonStateTransitions
# ---------------------------------------------------------------------------

class TestEggPistonStateTransitions:
    def test_idle_to_descend(self):
        """Boss transitions from idle to descend when timer expires."""
        boss = _make_boss(state="idle", timer=1)
        update_enemies([boss])
        assert boss.boss_state == "descend"
        assert boss.boss_timer == BOSS_DESCEND_DURATION

    def test_descend_to_vulnerable(self):
        """Boss transitions from descend to vulnerable when timer expires."""
        boss = _make_boss(state="descend", timer=1)
        update_enemies([boss])
        assert boss.boss_state == "vulnerable"
        assert boss.boss_timer == BOSS_VULNERABLE_DURATION

    def test_descend_to_vulnerable_escalated(self):
        """After escalation, vulnerable duration is shorter."""
        boss = _make_boss(state="descend", timer=1, escalated=True)
        update_enemies([boss])
        assert boss.boss_state == "vulnerable"
        assert boss.boss_timer == BOSS_VULNERABLE_DURATION_ESC

    def test_vulnerable_to_ascend(self):
        """Boss transitions from vulnerable to ascend when timer expires."""
        boss = _make_boss(state="vulnerable", timer=1)
        update_enemies([boss])
        assert boss.boss_state == "ascend"
        assert boss.boss_timer == BOSS_ASCEND_DURATION

    def test_ascend_to_idle(self):
        """Boss transitions from ascend to idle when timer expires."""
        boss = _make_boss(state="ascend", timer=1)
        update_enemies([boss])
        assert boss.boss_state == "idle"
        assert boss.boss_timer == BOSS_IDLE_DURATION

    def test_full_cycle(self):
        """Boss completes a full state cycle."""
        boss = _make_boss(state="idle", timer=1)
        update_enemies([boss])
        assert boss.boss_state == "descend"

        boss.boss_timer = 1
        update_enemies([boss])
        assert boss.boss_state == "vulnerable"

        boss.boss_timer = 1
        update_enemies([boss])
        assert boss.boss_state == "ascend"

        boss.boss_timer = 1
        update_enemies([boss])
        assert boss.boss_state == "idle"

    def test_idle_timer_decrements(self):
        """Timer decrements each frame during idle."""
        boss = _make_boss(state="idle", timer=50)
        update_enemies([boss])
        assert boss.boss_timer == 49

    def test_dead_boss_not_updated(self):
        """Dead boss does not update."""
        boss = _make_boss(state="idle", timer=50)
        boss.alive = False
        update_enemies([boss])
        assert boss.boss_timer == 50


# ---------------------------------------------------------------------------
# TestEggPistonMovement
# ---------------------------------------------------------------------------

class TestEggPistonMovement:
    def test_idle_moves_right(self):
        """Boss moves right during idle."""
        boss = _make_boss(state="idle", timer=50)
        boss.patrol_dir = 1
        old_x = boss.x
        update_enemies([boss])
        assert boss.x == old_x + BOSS_IDLE_SPEED

    def test_idle_moves_left(self):
        """Boss moves left during idle."""
        boss = _make_boss(state="idle", timer=50)
        boss.patrol_dir = -1
        old_x = boss.x
        update_enemies([boss])
        assert boss.x == old_x - BOSS_IDLE_SPEED

    def test_idle_reverses_at_right_edge(self):
        """Boss reverses at right arena boundary."""
        boss = _make_boss(state="idle", timer=50)
        boss.x = boss.boss_right_x - 0.1
        boss.patrol_dir = 1
        update_enemies([boss])
        assert boss.patrol_dir == -1

    def test_idle_reverses_at_left_edge(self):
        """Boss reverses at left arena boundary."""
        boss = _make_boss(state="idle", timer=50)
        boss.x = boss.boss_left_x + 0.1
        boss.patrol_dir = -1
        update_enemies([boss])
        assert boss.patrol_dir == 1

    def test_idle_escalated_speed(self):
        """After escalation, idle speed doubles."""
        boss = _make_boss(state="idle", timer=50, escalated=True)
        boss.patrol_dir = 1
        old_x = boss.x
        update_enemies([boss])
        assert boss.x == old_x + BOSS_IDLE_SPEED_ESC

    def test_idle_hovers_at_hover_y(self):
        """During idle, boss stays at hover y position."""
        boss = _make_boss(state="idle", timer=50)
        update_enemies([boss])
        assert boss.y == boss.boss_hover_y

    def test_descend_moves_to_ground(self):
        """During descend, boss interpolates from hover to ground."""
        boss = _make_boss(state="descend", timer=BOSS_DESCEND_DURATION)
        boss.y = boss.boss_hover_y
        # Run full descent
        for _ in range(BOSS_DESCEND_DURATION):
            update_enemies([boss])
        assert boss.y == boss.boss_ground_y
        assert boss.boss_state == "vulnerable"

    def test_ascend_moves_to_hover(self):
        """During ascend, boss interpolates from ground to hover."""
        boss = _make_boss(state="ascend", timer=BOSS_ASCEND_DURATION)
        boss.y = boss.boss_ground_y
        # Run full ascent
        for _ in range(BOSS_ASCEND_DURATION):
            update_enemies([boss])
        assert boss.y == boss.boss_hover_y
        assert boss.boss_state == "idle"


# ---------------------------------------------------------------------------
# TestEggPistonDamage
# ---------------------------------------------------------------------------

class TestEggPistonDamage:
    def test_spindash_deals_damage_when_vulnerable(self):
        """Spindash at threshold speed damages vulnerable boss."""
        p = create_player(500.0, 500.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        boss = _make_boss(state="vulnerable")

        events = check_enemy_collision(p, [boss])

        assert EnemyEvent.BOSS_HIT in events
        assert boss.boss_hp == BOSS_HP - 1

    def test_spindash_sets_hit_invulnerability(self):
        """Boss becomes temporarily invulnerable after a hit."""
        p = create_player(500.0, 500.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        boss = _make_boss(state="vulnerable")

        check_enemy_collision(p, [boss])

        assert boss.boss_hit_timer == BOSS_HIT_INVULN

    def test_hit_invulnerability_prevents_double_hit(self):
        """Boss cannot be hit again while hit invulnerability is active."""
        p = create_player(500.0, 500.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        boss = _make_boss(state="vulnerable")
        boss.boss_hit_timer = 10  # Already invulnerable

        events = check_enemy_collision(p, [boss])

        # Player bounces off instead of dealing damage
        assert EnemyEvent.BOSS_HIT not in events
        assert boss.boss_hp == BOSS_HP  # No damage

    def test_normal_jump_no_damage(self):
        """Regular jump from above bounces off armor, no damage."""
        p = create_player(500.0, 490.0)
        p.physics.y_vel = 2.0
        p.physics.on_ground = False
        p.state = PlayerState.JUMPING
        boss = _make_boss(state="vulnerable")

        events = check_enemy_collision(p, [boss])

        assert EnemyEvent.BOUNCE in events
        assert EnemyEvent.BOSS_HIT not in events
        assert boss.boss_hp == BOSS_HP
        assert p.physics.y_vel == ENEMY_BOUNCE_VELOCITY

    def test_side_contact_damages_player_when_vulnerable(self):
        """Side contact with vulnerable boss damages player."""
        p = create_player(500.0, 500.0)
        p.state = PlayerState.RUNNING
        p.rings = 5
        boss = _make_boss(state="vulnerable")

        events = check_enemy_collision(p, [boss])

        assert EnemyEvent.PLAYER_DAMAGED in events
        assert p.state == PlayerState.HURT


# ---------------------------------------------------------------------------
# TestEggPistonEscalation
# ---------------------------------------------------------------------------

class TestEggPistonEscalation:
    def test_escalation_at_threshold(self):
        """Escalation triggers when HP drops to BOSS_ESCALATION_HP."""
        p = create_player(500.0, 500.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        boss = _make_boss(state="vulnerable", hp=BOSS_ESCALATION_HP + 1)

        check_enemy_collision(p, [boss])

        assert boss.boss_escalated is True
        assert boss.boss_hp == BOSS_ESCALATION_HP

    def test_no_escalation_above_threshold(self):
        """No escalation when HP is still above threshold."""
        p = create_player(500.0, 500.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        boss = _make_boss(state="vulnerable", hp=BOSS_ESCALATION_HP + 2)

        check_enemy_collision(p, [boss])

        assert boss.boss_escalated is False
        assert boss.boss_hp == BOSS_ESCALATION_HP + 1

    def test_escalation_stays_set(self):
        """Once escalated, boss stays escalated even as HP drops further."""
        p = create_player(500.0, 500.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        boss = _make_boss(state="vulnerable", hp=3, escalated=True)

        check_enemy_collision(p, [boss])

        assert boss.boss_escalated is True
        assert boss.boss_hp == 2


# ---------------------------------------------------------------------------
# TestEggPistonDefeat
# ---------------------------------------------------------------------------

class TestEggPistonDefeat:
    def test_defeat_at_zero_hp(self):
        """Boss dies when HP reaches 0."""
        p = create_player(500.0, 500.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        boss = _make_boss(state="vulnerable", hp=1, escalated=True)

        events = check_enemy_collision(p, [boss])

        assert boss.alive is False
        assert boss.boss_hp == 0
        assert EnemyEvent.BOSS_HIT in events
        assert EnemyEvent.BOSS_DEFEATED in events

    def test_boss_defeated_event_order(self):
        """BOSS_HIT comes before BOSS_DEFEATED in event list."""
        p = create_player(500.0, 500.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        boss = _make_boss(state="vulnerable", hp=1, escalated=True)

        events = check_enemy_collision(p, [boss])

        assert events == [EnemyEvent.BOSS_HIT, EnemyEvent.BOSS_DEFEATED]


# ---------------------------------------------------------------------------
# TestEggPistonNonVulnerableDamage
# ---------------------------------------------------------------------------

class TestEggPistonNonVulnerableDamage:
    def test_idle_contact_damages_player(self):
        """Contact during idle state damages player."""
        p = create_player(500.0, 420.0)  # At hover height
        p.state = PlayerState.RUNNING
        p.rings = 5
        boss = _make_boss(state="idle")
        boss.y = boss.boss_hover_y

        events = check_enemy_collision(p, [boss])

        assert EnemyEvent.PLAYER_DAMAGED in events

    def test_descend_contact_damages_player(self):
        """Contact during descend state damages player (crush)."""
        p = create_player(500.0, 460.0)
        p.state = PlayerState.RUNNING
        p.rings = 5
        boss = _make_boss(state="descend")
        boss.y = 460.0  # Mid-descent

        events = check_enemy_collision(p, [boss])

        assert EnemyEvent.PLAYER_DAMAGED in events

    def test_ascend_contact_damages_player(self):
        """Contact during ascend state damages player (crush from below)."""
        p = create_player(500.0, 490.0)
        p.state = PlayerState.RUNNING
        p.rings = 5
        boss = _make_boss(state="ascend")
        boss.y = 490.0

        events = check_enemy_collision(p, [boss])

        assert EnemyEvent.PLAYER_DAMAGED in events

    def test_invulnerable_player_safe_in_non_vulnerable_state(self):
        """Invulnerable player not damaged by non-vulnerable boss."""
        p = create_player(500.0, 420.0)
        p.invulnerability_timer = 60
        p.state = PlayerState.RUNNING
        boss = _make_boss(state="idle")
        boss.y = boss.boss_hover_y

        events = check_enemy_collision(p, [boss])

        assert events is None or EnemyEvent.PLAYER_DAMAGED not in (events or [])

    def test_spindash_on_idle_boss_still_damages_player(self):
        """Spindash during non-vulnerable state damages player, not boss."""
        p = create_player(500.0, 420.0)
        p.physics.is_rolling = True
        p.physics.ground_speed = SPINDASH_KILL_THRESHOLD
        p.state = PlayerState.ROLLING
        p.rings = 5
        boss = _make_boss(state="idle")
        boss.y = boss.boss_hover_y

        events = check_enemy_collision(p, [boss])

        assert EnemyEvent.PLAYER_DAMAGED in events
        assert boss.boss_hp == BOSS_HP  # No damage to boss

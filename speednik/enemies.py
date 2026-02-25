"""speednik/enemies.py — Enemy types, behaviors, and collision logic.

Handles enemy loading, per-frame behavior updates, and player-enemy collision.
Pyxel-free for testability — returns events that the main loop maps to SFX/visuals.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from speednik.constants import (
    BOSS_ARENA_HALF_W,
    BOSS_ASCEND_DURATION,
    BOSS_DESCEND_DURATION,
    BOSS_ESCALATION_HP,
    BOSS_HIT_INVULN,
    BOSS_HITBOX_H,
    BOSS_HITBOX_W,
    BOSS_HP,
    BOSS_IDLE_DURATION,
    BOSS_IDLE_SPEED,
    BOSS_IDLE_SPEED_ESC,
    BOSS_INDICATOR_LEAD,
    BOSS_VULNERABLE_DURATION,
    BOSS_VULNERABLE_DURATION_ESC,
    BUZZER_HITBOX_H,
    BUZZER_HITBOX_W,
    CHOPPER_HITBOX_H,
    CHOPPER_HITBOX_W,
    CHOPPER_JUMP_INTERVAL,
    CHOPPER_JUMP_VELOCITY,
    CRAB_HITBOX_H,
    CRAB_HITBOX_W,
    CRAB_PATROL_RANGE,
    CRAB_PATROL_SPEED,
    ENEMY_BOUNCE_VELOCITY,
    GRAVITY,
    GUARDIAN_HITBOX_H,
    GUARDIAN_HITBOX_W,
    SPINDASH_KILL_THRESHOLD,
)
from speednik.objects import aabb_overlap
from speednik.player import Player, PlayerState, damage_player, get_player_rect


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class EnemyEvent(Enum):
    DESTROYED = "destroyed"
    BOUNCE = "bounce"
    PLAYER_DAMAGED = "player_damaged"
    SHIELD_BREAK = "shield_break"
    BOSS_HIT = "boss_hit"
    BOSS_DEFEATED = "boss_defeated"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Enemy:
    """An enemy entity in the world."""
    x: float
    y: float
    enemy_type: str
    alive: bool = True
    # Crab patrol
    origin_x: float = 0.0
    patrol_dir: int = 1        # +1 right, -1 left
    # Chopper jump
    jump_timer: int = 0
    base_y: float = 0.0
    y_vel: float = 0.0
    # Guardian
    shielded: bool = False
    # Boss (Egg Piston) state machine
    boss_state: str = ""       # "idle", "descend", "vulnerable", "ascend"
    boss_timer: int = 0
    boss_hp: int = 0
    boss_escalated: bool = False
    boss_target_x: float = 0.0
    boss_hover_y: float = 0.0
    boss_ground_y: float = 0.0
    boss_hit_timer: int = 0    # Boss invulnerability after being hit
    boss_left_x: float = 0.0
    boss_right_x: float = 0.0


# ---------------------------------------------------------------------------
# Hitbox lookup
# ---------------------------------------------------------------------------

_HITBOX_SIZES: dict[str, tuple[int, int]] = {
    "enemy_crab": (CRAB_HITBOX_W, CRAB_HITBOX_H),
    "enemy_buzzer": (BUZZER_HITBOX_W, BUZZER_HITBOX_H),
    "enemy_chopper": (CHOPPER_HITBOX_W, CHOPPER_HITBOX_H),
    "enemy_guardian": (GUARDIAN_HITBOX_W, GUARDIAN_HITBOX_H),
    "enemy_egg_piston": (BOSS_HITBOX_W, BOSS_HITBOX_H),
}


def _get_enemy_rect(enemy: Enemy) -> tuple[float, float, int, int]:
    """Return (x, y, w, h) AABB centered on enemy position."""
    w, h = _HITBOX_SIZES.get(enemy.enemy_type, (16, 16))
    return (enemy.x - w / 2, enemy.y - h / 2, w, h)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_enemies(entities: list[dict]) -> list[Enemy]:
    """Extract enemy entities from a stage entity list."""
    enemies: list[Enemy] = []
    for e in entities:
        etype = e.get("type", "")
        if not etype.startswith("enemy_"):
            continue
        x = float(e["x"])
        y = float(e["y"])
        enemy = Enemy(
            x=x,
            y=y,
            enemy_type=etype,
            origin_x=x,
            base_y=y,
            jump_timer=CHOPPER_JUMP_INTERVAL if etype == "enemy_chopper" else 0,
            shielded=(etype == "enemy_guardian"),
        )
        if etype == "enemy_egg_piston":
            enemy.boss_state = "idle"
            enemy.boss_hp = BOSS_HP
            enemy.boss_timer = BOSS_IDLE_DURATION
            enemy.boss_hover_y = y - 80.0
            enemy.boss_ground_y = y
            enemy.boss_target_x = x
            enemy.boss_left_x = x - BOSS_ARENA_HALF_W
            enemy.boss_right_x = x + BOSS_ARENA_HALF_W
        enemies.append(enemy)
    return enemies


# ---------------------------------------------------------------------------
# Per-frame behavior updates
# ---------------------------------------------------------------------------

def update_enemies(enemies: list[Enemy]) -> None:
    """Update all alive enemies for one frame."""
    for enemy in enemies:
        if not enemy.alive:
            continue
        if enemy.enemy_type == "enemy_crab":
            _update_crab(enemy)
        elif enemy.enemy_type == "enemy_chopper":
            _update_chopper(enemy)
        elif enemy.enemy_type == "enemy_egg_piston":
            _update_egg_piston(enemy)
        # Buzzer and Guardian are stationary — no update needed


def _update_crab(enemy: Enemy) -> None:
    """Patrol back and forth within CRAB_PATROL_RANGE of origin."""
    enemy.x += enemy.patrol_dir * CRAB_PATROL_SPEED
    if enemy.x >= enemy.origin_x + CRAB_PATROL_RANGE:
        enemy.x = enemy.origin_x + CRAB_PATROL_RANGE
        enemy.patrol_dir = -1
    elif enemy.x <= enemy.origin_x - CRAB_PATROL_RANGE:
        enemy.x = enemy.origin_x - CRAB_PATROL_RANGE
        enemy.patrol_dir = 1


def _update_chopper(enemy: Enemy) -> None:
    """Jump vertically on a timer, fall with gravity."""
    if enemy.y >= enemy.base_y and enemy.y_vel >= 0:
        # At or below base — waiting for next jump
        enemy.y = enemy.base_y
        enemy.y_vel = 0.0
        enemy.jump_timer -= 1
        if enemy.jump_timer <= 0:
            enemy.y_vel = CHOPPER_JUMP_VELOCITY
            enemy.jump_timer = CHOPPER_JUMP_INTERVAL
    else:
        # In air — apply gravity
        enemy.y_vel += GRAVITY
        enemy.y += enemy.y_vel


def _update_egg_piston(enemy: Enemy) -> None:
    """Egg Piston boss state machine: IDLE → DESCEND → VULNERABLE → ASCEND."""
    # Decrement boss hit invulnerability
    if enemy.boss_hit_timer > 0:
        enemy.boss_hit_timer -= 1

    state = enemy.boss_state
    if state == "idle":
        _boss_idle(enemy)
    elif state == "descend":
        _boss_descend(enemy)
    elif state == "vulnerable":
        _boss_vulnerable(enemy)
    elif state == "ascend":
        _boss_ascend(enemy)


def _boss_idle(enemy: Enemy) -> None:
    """IDLE: hover at top, slow left/right patrol, pick landing target."""
    speed = BOSS_IDLE_SPEED_ESC if enemy.boss_escalated else BOSS_IDLE_SPEED
    enemy.x += enemy.patrol_dir * speed
    if enemy.x >= enemy.boss_right_x:
        enemy.x = enemy.boss_right_x
        enemy.patrol_dir = -1
    elif enemy.x <= enemy.boss_left_x:
        enemy.x = enemy.boss_left_x
        enemy.patrol_dir = 1
    enemy.y = enemy.boss_hover_y

    # Pick target position when indicator should appear
    if enemy.boss_timer == BOSS_INDICATOR_LEAD:
        enemy.boss_target_x = max(
            enemy.boss_left_x,
            min(enemy.x, enemy.boss_right_x),
        )

    enemy.boss_timer -= 1
    if enemy.boss_timer <= 0:
        enemy.boss_state = "descend"
        enemy.boss_timer = BOSS_DESCEND_DURATION


def _boss_descend(enemy: Enemy) -> None:
    """DESCEND: drop from hover to ground over duration."""
    progress = 1.0 - (enemy.boss_timer / BOSS_DESCEND_DURATION)
    enemy.y = enemy.boss_hover_y + (enemy.boss_ground_y - enemy.boss_hover_y) * progress
    enemy.x = enemy.boss_target_x

    enemy.boss_timer -= 1
    if enemy.boss_timer <= 0:
        enemy.y = enemy.boss_ground_y
        duration = (BOSS_VULNERABLE_DURATION_ESC if enemy.boss_escalated
                    else BOSS_VULNERABLE_DURATION)
        enemy.boss_state = "vulnerable"
        enemy.boss_timer = duration


def _boss_vulnerable(enemy: Enemy) -> None:
    """VULNERABLE: sit on ground, cockpit exposed."""
    enemy.boss_timer -= 1
    if enemy.boss_timer <= 0:
        enemy.boss_state = "ascend"
        enemy.boss_timer = BOSS_ASCEND_DURATION


def _boss_ascend(enemy: Enemy) -> None:
    """ASCEND: rise from ground to hover position."""
    progress = 1.0 - (enemy.boss_timer / BOSS_ASCEND_DURATION)
    enemy.y = enemy.boss_ground_y + (enemy.boss_hover_y - enemy.boss_ground_y) * progress

    enemy.boss_timer -= 1
    if enemy.boss_timer <= 0:
        enemy.y = enemy.boss_hover_y
        enemy.boss_state = "idle"
        enemy.boss_timer = BOSS_IDLE_DURATION


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------

def check_enemy_collision(
    player: Player,
    enemies: list[Enemy],
) -> list[EnemyEvent]:
    """Check player against all alive enemies. Returns events."""
    if player.state in (PlayerState.DEAD, PlayerState.HURT):
        return []

    events: list[EnemyEvent] = []
    for enemy in enemies:
        if not enemy.alive:
            continue
        result = _check_single_enemy(player, enemy)
        if result is not None:
            events.extend(result)
            # Stop checking after first hit this frame
            if any(e in (EnemyEvent.PLAYER_DAMAGED, EnemyEvent.BOUNCE) for e in result):
                break
    return events


def _check_single_enemy(
    player: Player,
    enemy: Enemy,
) -> list[EnemyEvent] | None:
    """Check collision between player and one enemy. Returns events or None."""
    px, py, pw, ph = get_player_rect(player)
    ex, ey, ew, eh = _get_enemy_rect(enemy)

    if not aabb_overlap(px, py, pw, ph, ex, ey, ew, eh):
        return None

    phys = player.physics
    is_rolling = phys.is_rolling
    is_spindash_kill = is_rolling and abs(phys.ground_speed) >= SPINDASH_KILL_THRESHOLD

    # Egg Piston boss handling
    if enemy.enemy_type == "enemy_egg_piston":
        return _check_boss_collision(player, enemy, is_spindash_kill)

    # Guardian special handling
    if enemy.enemy_type == "enemy_guardian" and enemy.shielded:
        if is_spindash_kill:
            enemy.alive = False
            return [EnemyEvent.SHIELD_BREAK, EnemyEvent.DESTROYED]
        # Shield blocks — damage the player on contact
        if player.invulnerability_timer <= 0:
            damage_player(player)
            return [EnemyEvent.PLAYER_DAMAGED]
        return None

    # Spindash kill: rolling + ground_speed >= threshold
    if is_spindash_kill:
        enemy.alive = False
        return [EnemyEvent.DESTROYED]

    # Bounce kill: player center above enemy center AND (rolling or descending)
    player_center_y = phys.y
    enemy_center_y = enemy.y
    if player_center_y < enemy_center_y and (is_rolling or phys.y_vel > 0):
        enemy.alive = False
        phys.y_vel = ENEMY_BOUNCE_VELOCITY
        return [EnemyEvent.BOUNCE, EnemyEvent.DESTROYED]

    # Side/below contact: damage the player
    if player.invulnerability_timer <= 0:
        damage_player(player)
        return [EnemyEvent.PLAYER_DAMAGED]

    return None


def _check_boss_collision(
    player: Player,
    enemy: Enemy,
    is_spindash_kill: bool,
) -> list[EnemyEvent] | None:
    """Boss-specific collision: state-dependent vulnerability."""
    phys = player.physics

    if enemy.boss_state == "vulnerable":
        # Spindash deals damage
        if is_spindash_kill and enemy.boss_hit_timer <= 0:
            enemy.boss_hp -= 1
            enemy.boss_hit_timer = BOSS_HIT_INVULN
            if not enemy.boss_escalated and enemy.boss_hp <= BOSS_ESCALATION_HP:
                enemy.boss_escalated = True
            if enemy.boss_hp <= 0:
                enemy.alive = False
                return [EnemyEvent.BOSS_HIT, EnemyEvent.BOSS_DEFEATED]
            return [EnemyEvent.BOSS_HIT]

        # Jump from above: bounce off armor, no damage to boss
        player_center_y = phys.y
        if player_center_y < enemy.y and (phys.is_rolling or phys.y_vel > 0):
            phys.y_vel = ENEMY_BOUNCE_VELOCITY
            return [EnemyEvent.BOUNCE]

        # Side/below contact: damage the player
        if player.invulnerability_timer <= 0:
            damage_player(player)
            return [EnemyEvent.PLAYER_DAMAGED]
        return None

    # Non-vulnerable states (idle, descend, ascend): contact damages player
    if player.invulnerability_timer <= 0:
        damage_player(player)
        return [EnemyEvent.PLAYER_DAMAGED]
    return None

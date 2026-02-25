# T-003-03 Structure: Enemy Types

## Files modified

### `speednik/constants.py`
Add enemy-specific constants after the existing damage constants block:

```
# Enemy behavior
ENEMY_BOUNCE_VELOCITY = -6.5
CRAB_PATROL_SPEED = 0.5
CRAB_PATROL_RANGE = 32        # ±32px from origin = 64px total range
CHOPPER_JUMP_INTERVAL = 90
CHOPPER_JUMP_VELOCITY = -5.0
SPINDASH_KILL_THRESHOLD = 8.0  # ground_speed needed for spindash kill

# Enemy hitboxes (width, height)
CRAB_HITBOX_W = 16
CRAB_HITBOX_H = 14
BUZZER_HITBOX_W = 12
BUZZER_HITBOX_H = 12
CHOPPER_HITBOX_W = 8
CHOPPER_HITBOX_H = 16
GUARDIAN_HITBOX_W = 24
GUARDIAN_HITBOX_H = 28
```

### `speednik/main.py`
Add enemy integration to game loop:
- Import `load_enemies`, `update_enemies`, `check_enemy_collision`, `EnemyEvent` from enemies
- In `__init__`: `self.enemies = load_enemies(entities)` (when stage loading is wired)
- In `update()`: call `update_enemies(enemies)` then `check_enemy_collision(player, enemies)` after player_update
- In `draw()`: call draw functions for alive enemies via renderer

## Files created

### `speednik/enemies.py`
New module. ~200 lines. Pyxel-free.

**Imports:** constants (enemy hitboxes, speeds, etc.), player (Player, PlayerState, damage_player, get_player_rect), objects (aabb_overlap)

**Public interface:**

```python
class EnemyEvent(Enum):
    DESTROYED = "destroyed"
    BOUNCE = "bounce"
    PLAYER_DAMAGED = "player_damaged"
    SHIELD_BREAK = "shield_break"

@dataclass
class Enemy:
    x: float
    y: float
    enemy_type: str            # "enemy_crab", "enemy_buzzer", "enemy_chopper", "enemy_guardian"
    alive: bool = True
    origin_x: float = 0.0     # patrol origin (crab)
    patrol_dir: int = 1       # +1 right, -1 left (crab)
    jump_timer: int = 0       # countdown to next jump (chopper)
    base_y: float = 0.0       # resting y position (chopper)
    shielded: bool = False    # guardian shield state

def load_enemies(entities: list[dict]) -> list[Enemy]:
    """Filter entities with type starting with 'enemy_', return Enemy list."""

def update_enemies(enemies: list[Enemy]) -> None:
    """Per-frame behavior update: patrol, jump cycle, etc."""

def check_enemy_collision(player: Player, enemies: list[Enemy]) -> list[EnemyEvent]:
    """Check player vs all alive enemies. Returns events. Mutates player and enemies."""
```

**Internal organization:**

1. `_get_enemy_hitbox(enemy) -> (x, y, w, h)` — returns AABB centered on enemy position, sized by type
2. `_update_crab(enemy)` — move by patrol_dir * CRAB_PATROL_SPEED, reverse at ±CRAB_PATROL_RANGE from origin_x
3. `_update_chopper(enemy)` — decrement jump_timer, when 0 apply CHOPPER_JUMP_VELOCITY, apply gravity, reset timer at base_y
4. `_check_single_enemy(player, enemy) -> EnemyEvent | None` — core collision logic:
   - Skip if not alive or player DEAD/HURT
   - AABB overlap check between player rect and enemy hitbox
   - Spindash kill: player rolling + abs(ground_speed) >= threshold → destroy, no bounce
   - Bounce kill: player above enemy center + (rolling or descending) → destroy, set y_vel
   - Guardian shield: if shielded, only spindash kills; other attacks bounce off or damage player
   - Damage: remaining overlaps → damage_player()

### `tests/test_enemies.py`
New test module. ~200 lines.

**Test classes:**

```
TestLoadEnemies
  - test_loads_enemy_entities
  - test_ignores_non_enemy_entities
  - test_enemy_types_preserved
  - test_sets_origin_and_base_y

TestCrabPatrol
  - test_crab_moves_right
  - test_crab_reverses_at_patrol_edge
  - test_crab_patrol_range

TestChopperJump
  - test_chopper_jumps_after_interval
  - test_chopper_falls_with_gravity
  - test_chopper_resets_at_base

TestBounceKill
  - test_bounce_on_crab_from_above
  - test_bounce_sets_player_y_vel
  - test_enemy_destroyed_on_bounce
  - test_bounce_event_returned

TestSpindashKill
  - test_spindash_through_enemy
  - test_spindash_no_bounce
  - test_spindash_below_threshold_damages_player

TestSideDamage
  - test_side_contact_damages_player
  - test_invulnerable_player_not_damaged
  - test_dead_player_no_collision

TestGuardian
  - test_guardian_blocks_normal_attack
  - test_guardian_spindash_kills
  - test_guardian_shield_break_event
```

## Files NOT modified

- `speednik/renderer.py` — Enemy draw functions already exist. `spawn_destroy_particles()` already exists.
- `speednik/physics.py` — No changes needed.
- `speednik/player.py` — No changes needed; `damage_player()` and `get_player_rect()` already public.
- `speednik/objects.py` — `aabb_overlap()` already exported.

## Module dependency graph

```
constants.py ← enemies.py → player.py
                    ↓
               objects.py (aabb_overlap only)

main.py → enemies.py (load, update, collision)
main.py → renderer.py (draw, particles)
main.py → audio.py (SFX)
```

## Interface contracts

1. `load_enemies()` takes the same `list[dict]` entity format as `load_rings()` etc.
2. `update_enemies()` is called once per frame before collision checks.
3. `check_enemy_collision()` returns events; main.py maps events to SFX/particles.
4. Enemy.alive is set to False on destruction; renderer skips dead enemies.
5. Guardian: shielded=True at load for "enemy_guardian" type.

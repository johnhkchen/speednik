# Structure — T-003-04: Egg Piston Boss

## Files Modified

### 1. `speednik/constants.py` — Add boss constants

Append after existing enemy constants block (after line 90):

```
BOSS_HP = 8
BOSS_ESCALATION_HP = 4         # HP at which escalation triggers
BOSS_IDLE_DURATION = 120       # 2.0s
BOSS_DESCEND_DURATION = 60     # 1.0s
BOSS_VULNERABLE_DURATION = 90  # 1.5s
BOSS_VULNERABLE_DURATION_ESC = 60  # 1.0s after escalation
BOSS_ASCEND_DURATION = 60      # 1.0s
BOSS_IDLE_SPEED = 1.0
BOSS_IDLE_SPEED_ESC = 2.0
BOSS_INDICATOR_LEAD = 60       # 1s before descend
BOSS_HITBOX_W = 24
BOSS_HITBOX_H = 32
BOSS_HIT_INVULN = 30           # frames of boss invulnerability after hit
```

### 2. `speednik/enemies.py` — Boss state machine and collision

**Enemy dataclass** — add fields:
```
boss_state: str = ""
boss_timer: int = 0
boss_hp: int = 0
boss_escalated: bool = False
boss_target_x: float = 0.0
boss_hover_y: float = 0.0
boss_ground_y: float = 0.0
boss_hit_timer: int = 0
boss_left_x: float = 0.0
boss_right_x: float = 0.0
```

**EnemyEvent** — add:
```
BOSS_HIT = "boss_hit"
BOSS_DEFEATED = "boss_defeated"
```

**_HITBOX_SIZES** — add:
```
"enemy_egg_piston": (BOSS_HITBOX_W, BOSS_HITBOX_H)
```

**Import** new constants from `constants.py`.

**`load_enemies()`** — add egg_piston initialization:
- Set `boss_state = "idle"`, `boss_hp = BOSS_HP`, `boss_timer = BOSS_IDLE_DURATION`
- Set `boss_hover_y = y - 80` (80px above spawn point), `boss_ground_y = y`
- Set `boss_left_x` and `boss_right_x` from spawn position ± arena half-width (128px)
- Set `boss_target_x = x`

**`update_enemies()`** — add `elif enemy.enemy_type == "enemy_egg_piston"` branch calling `_update_egg_piston(enemy)`.

**New function `_update_egg_piston(enemy)`**:
- Decrement `boss_hit_timer` if > 0
- State dispatch:
  - **idle**: Move left/right (speed depends on `boss_escalated`). At `boss_timer == BOSS_INDICATOR_LEAD`, compute `boss_target_x` (current x clamped to arena bounds). Decrement timer. At 0 → set state="descend", timer=BOSS_DESCEND_DURATION, record start_y for interpolation.
  - **descend**: Interpolate y from `boss_hover_y` to `boss_ground_y` over duration. Decrement timer. At 0 → set state="vulnerable", timer based on escalation.
  - **vulnerable**: No movement. Decrement timer. At 0 → set state="ascend", timer=BOSS_ASCEND_DURATION.
  - **ascend**: Interpolate y from `boss_ground_y` to `boss_hover_y` over duration. Decrement timer. At 0 → set state="idle", timer=BOSS_IDLE_DURATION.

**`_check_single_enemy()`** — add `enemy_egg_piston` branch before regular collision:
- **Non-vulnerable states** (idle, descend, ascend): Contact damages player. No boss damage possible.
- **Vulnerable state**: Spindash → decrement HP, set boss_hit_timer, return [BOSS_HIT]. If HP == 0 → alive=False, return [BOSS_HIT, BOSS_DEFEATED]. Regular jump from above → bounce (ENEMY_BOUNCE_VELOCITY, no HP loss). Side/below → damage player.

### 3. `speednik/main.py` — Boss event wiring

In the enemy event handling block:
- Add `BOSS_HIT` → `play_sfx(SFX_BOSS_HIT)`
- Add `BOSS_DEFEATED` → `play_sfx(SFX_STAGE_CLEAR)` (future: trigger stage clear sequence)

Add boss targeting indicator rendering in the draw method:
- After drawing enemies, check if any enemy is egg_piston with `boss_state` in ("idle", "descend") and `boss_target_x` set and `boss_timer` within indicator lead window → draw vertical marker at `boss_target_x` on the ground.

### 4. `speednik/renderer.py` — Boss indicator drawing

Add `draw_boss_indicator(x: int, ground_y: int, frame_count: int)` function:
- Draws a flashing vertical line or crosshair at the target landing position.
- Called from main.py draw method, not from `_ENTITY_DRAWERS` (since it's not an entity itself).

### 5. `tests/test_enemies.py` — Boss test class

Add new test class `TestEggPiston` with tests for:
- Loading: boss fields initialized correctly
- State transitions: idle → descend → vulnerable → ascend → idle cycle
- Damage: spindash deals damage, other attacks don't
- Escalation: triggers at 4 HP remaining
- Defeat: alive=False + BOSS_DEFEATED event at 0 HP
- Armor bounce: jump from above returns BOUNCE, no HP loss
- Non-vulnerable states: contact damages player
- Ascend crush: player underneath during ascend gets damaged
- Boss hit invulnerability: prevents multiple hits in one spindash pass

## Files NOT Modified

- `speednik/player.py` — No changes needed. Player interaction through existing physics fields.
- `speednik/physics.py` — No changes.
- `speednik/terrain.py` — No changes.
- `speednik/audio.py` — SFX slots 10 and 11 already defined.
- `speednik/stages/skybridge.py` — Entity JSON already has entity placement; if not, that's a separate concern (stage data ticket). Boss logic doesn't depend on stage data.

## Module Boundaries

- `enemies.py` owns all boss state and logic
- `constants.py` owns all numeric tuning values
- `main.py` owns event→SFX mapping and indicator draw call
- `renderer.py` owns visual representation (indicator helper)
- `tests/test_enemies.py` owns all boss tests

## Change Ordering

1. Constants first (no dependencies)
2. Enemy dataclass fields + events (depends on constants)
3. Enemy loading (depends on dataclass)
4. Boss update logic (depends on loading)
5. Boss collision logic (depends on update for state awareness)
6. Tests (depends on all enemy changes)
7. Renderer indicator (depends on boss state understanding)
8. Main.py integration (depends on events + renderer)

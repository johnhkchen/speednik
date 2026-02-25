# Research — T-003-04: Egg Piston Boss

## Ticket Summary

Implement the Stage 3 boss — Egg Piston. A state-machine boss with 4 states (IDLE, DESCEND, VULNERABLE, ASCEND), 8 HP, escalation at 4 hits, and spindash-only damage.

## Codebase Map

### Enemy System (`speednik/enemies.py`)

The current enemy system uses a single `Enemy` dataclass with type-specific fields. All enemies share the same struct:

```python
@dataclass
class Enemy:
    x, y: float
    enemy_type: str
    alive: bool = True
    origin_x: float = 0.0
    patrol_dir: int = 1
    jump_timer: int = 0
    base_y: float = 0.0
    y_vel: float = 0.0
    shielded: bool = False
```

**Behavior dispatch** is in `update_enemies()` — a per-type if/elif chain. Only crab and chopper have update logic. Buzzer and guardian are stationary.

**Collision dispatch** is in `_check_single_enemy()`. Guardian has special-case handling (shield check before normal bounce/destroy logic). All other enemies share the same collision path.

**Events** returned: `DESTROYED`, `BOUNCE`, `PLAYER_DAMAGED`, `SHIELD_BREAK`. Main.py maps these to SFX and particle spawning.

**Hitboxes** are in `_HITBOX_SIZES` dict, keyed by `enemy_type` string. Default fallback is `(16, 16)`.

### Loading Path (`load_enemies()`)

Filters entities by `type.startswith("enemy_")`, constructs `Enemy` instances. Boss would load from stage entity JSON with `type: "enemy_egg_piston"`.

### Player Interaction Points

- `damage_player(player)` in `player.py` — called by enemy collision when player takes a hit
- `get_player_rect(player)` — returns AABB for collision checks
- `player.physics.is_rolling` + `abs(player.physics.ground_speed) >= SPINDASH_KILL_THRESHOLD` — spindash detection
- `player.invulnerability_timer` — prevents damage stacking

### Rendering (`speednik/renderer.py`)

`_draw_enemy_egg_piston()` already exists at line 355. Registered in `_ENTITY_DRAWERS` dict. Draws cockpit dome, armor body, and piston base. Currently draws in a single static pose — no state-aware rendering.

### Audio (`speednik/audio.py`)

- `SFX_BOSS_HIT = 11` — metallic impact (already wired to `EnemyEvent.SHIELD_BREAK` in main.py)
- `SFX_STAGE_CLEAR = 10` — ascending fanfare
- `MUSIC_BOSS = 4` — tense A minor theme (not yet triggered anywhere in main.py)

### Main Loop Integration (`speednik/main.py`)

Enemy update/collision already integrated at lines 218-232. Event mapping:
- `DESTROYED` → `SFX_ENEMY_DESTROY` + particle spawn
- `BOUNCE` → `SFX_ENEMY_BOUNCE`
- `PLAYER_DAMAGED` → `SFX_HURT`
- `SHIELD_BREAK` → `SFX_BOSS_HIT`

No "stage clear" trigger exists yet. No boss-specific event types.

### Constants (`speednik/constants.py`)

Boss-related constants not yet defined. Relevant existing constants:
- `SPINDASH_KILL_THRESHOLD = 8.0`
- `ENEMY_BOUNCE_VELOCITY = -6.5`
- `SPINDASH_BASE_SPEED = 8.0`
- `FPS = 60`

### Stage 3 Data (`speednik/stages/skybridge.py`)

Stage loader exists. Boss arena is section 6 (x=4000-5200). The entity JSON would need an `enemy_egg_piston` entry placed in the arena.

### Test Patterns (`tests/test_enemies.py`)

~48 tests using `create_player()` + manually constructed `Enemy` instances. No Pyxel dependency. Tests verify:
- Loading filters
- Per-frame behavior (patrol, jump cycles)
- Collision outcomes (bounce, spindash kill, side damage, shield handling)
- Event correctness
- Edge cases (dead enemies, invulnerable player, DEAD/HURT state skips)

## Key Constraints

1. **Enemy dataclass is flat** — no nested state machine. Boss state must be added as fields on `Enemy` or as a separate entity type.
2. **Collision in `_check_single_enemy` dispatches by `enemy_type`** — boss needs its own branch similar to guardian.
3. **Renderer already has the boss drawer** — but it's state-unaware. Boss states should influence rendering (e.g., targeting indicator, vulnerable cockpit glow).
4. **No boss-specific events** — need `BOSS_HIT` (SFX 11) and `STAGE_CLEAR` (SFX 10) event types.
5. **Frame-based timers** — all durations specified in seconds must convert to frames at 60fps (e.g., 2.0s = 120 frames).
6. **Boss hitbox must change per state** — VULNERABLE exposes cockpit (different collision response), IDLE/ASCEND are armored.

## Duration Conversions (at 60fps)

| State | Duration | Frames |
|-------|----------|--------|
| IDLE | 2.0s | 120 |
| DESCEND | 1.0s | 60 |
| VULNERABLE | 1.5s (pre-4 hits) | 90 |
| VULNERABLE | 1.0s (post-4 hits) | 60 |
| ASCEND | 1.0s | 60 |
| Targeting indicator lead time | 1.0s | 60 |

## Assumptions

- Boss arena is flat ground (section 6 of skybridge). No slopes or special terrain in the fight.
- "Slow left/right movement" in IDLE means a simple patrol similar to crab, but at boss altitude.
- "Targeting indicator on ground" is a visual-only cue — a vertical line or marker rendered by the renderer.
- "Damages player if underneath" during ASCEND means an AABB check between boss body and player during that state.
- Regular jumps on top "bounce off armor" means the player gets the bounce velocity but no damage to boss — similar to landing on a spring.
- Boss music (track 4) should start when boss is loaded/active and stop on defeat, replaced by stage clear SFX.

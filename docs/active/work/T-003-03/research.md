# T-003-03 Research: Enemy Types

## Codebase Map

### Core modules relevant to enemies

**`speednik/constants.py`** — All physics constants. Enemy-relevant: `GRAVITY` (0.21875), `JUMP_FORCE` (6.5), `SPINDASH_BASE_SPEED` (8.0), `INVULNERABILITY_DURATION` (120), damage constants. No enemy constants exist yet.

**`speednik/physics.py`** — `PhysicsState` dataclass: x, y, x_vel, y_vel, ground_speed, angle, on_ground, is_rolling, facing_right, spinrev, is_charging_spindash, slip_timer. Pure math, no Pyxel dependency.

**`speednik/player.py`** — `Player` dataclass wraps `PhysicsState` + state machine (`PlayerState` enum: STANDING, RUNNING, JUMPING, ROLLING, SPINDASH, HURT, DEAD). Key functions:
- `damage_player(player)` — rings>0 → scatter+HURT+invulnerability; rings==0 → DEAD
- `get_player_rect(player)` → `(x, y, w, h)` AABB for collision
- `create_player(x, y)` — factory

**`speednik/objects.py`** — Pattern to follow. Contains Ring, Spring, Checkpoint, LaunchPipe, LiquidZone. Each has: dataclass, load function (`load_rings`, etc.), collision check returning event enums (`RingEvent`, `SpringEvent`, etc.). Also exports `aabb_overlap()` helper. No enemy code exists here.

**`speednik/renderer.py`** — Enemy draw functions already implemented:
- `_draw_enemy_crab(x, y, frame_count)` — ellipse body, claw animation, legs
- `_draw_enemy_buzzer(x, y, frame_count)` — circle body, wing flap, stinger
- `_draw_enemy_chopper(x, y, frame_count)` — elongated ellipse, mouth animation
- `_draw_enemy_guardian(x, y, frame_count)` — shielded rectangle, flash
- `_ENTITY_DRAWERS` dict maps type strings to draw functions
- `spawn_destroy_particles(x, y)` — 6-particle sparkle burst, 15 frame lifetime
- `draw_entities(entities, frame_count)` — dispatch via type string

**`speednik/audio.py`** — `SFX_ENEMY_DESTROY = 4`, `SFX_ENEMY_BOUNCE = 5`, `SFX_HURT = 8`, `SFX_RING_LOSS = 7`. Play via `play_sfx(slot)`.

**`speednik/main.py`** — Current game loop: `player_update` → `check_ring_collection` → `camera_update`. Draw: terrain → rings → player → scattered rings → particles → HUD. Enemy update/draw not yet integrated.

### Existing patterns

1. **Pyxel-free logic**: All game logic modules (physics, player, objects) have zero Pyxel imports. Rendering and audio coupling live only in main.py.

2. **Event-driven SFX**: Logic functions return event enums; main.py maps events to `play_sfx()` calls. Example: `check_ring_collection()` returns `list[RingEvent]`.

3. **AABB collision**: `objects.py::aabb_overlap()` used for spring/pipe collision. Ring collection uses distance-squared (circular radius).

4. **Entity loading**: Functions like `load_rings(entities: list[dict])` filter by `e.get("type")`, return typed dataclass lists. Entity dicts have `type`, `x`, `y` plus optional extra fields.

5. **Test fixtures**: `test_rings.py` uses `flat_tile()`, `flat_ground_lookup()` helpers. Tests create players via `create_player(x, y)`, check state mutations and returned events.

### Specification requirements (§5.3, §7.1–7.3)

**Base behavior (all enemies):**
- Jump/roll on top → enemy destroyed, player bounces (y_vel = jump-like), SFX slot 4
- Side/below while not rolling → player takes damage
- Spindash through (rolling + ground_speed ≥ 8) → enemy destroyed, no bounce, continues
- Destroyed enemies produce brief particle effect

**Crab:** Walk patrol 64px range, reverse at edges, 2-frame walk animation. Appears stages 1-3.

**Buzzer:** Hover in place, stationary aerial obstacle. Appears stages 1-3.

**Chopper:** Positioned at liquid surface y. Jumps vertically every ~90 frames, reaches fixed height, falls back. Stage 2 only.

**Guardian:** Large shielded, blocks bridge. Cannot be damaged from front. Spindash ≥ 8 breaks shield. Stage 3 only.

### Collision geometry analysis

Player hitboxes from constants:
- Standing: 18×40 (width_radius=9, height_radius=20), center-based
- Rolling: 14×28 (width_radius=7, height_radius=14)

Enemy visual bounding boxes from renderer:
- Crab: ~32×16 (ellipse 16w + claws extend ±13px, legs extend +8 below)
- Buzzer: ~24×20 (circle r=5, wings extend ±12, stinger extends +9 below)
- Chopper: ~8×16 (ellipse 8w × 16h)
- Guardian: ~24×28 (rect 24w × 28h)

### Key constraints

1. `damage_player()` already handles ring scatter, invulnerability, HURT/DEAD transitions — enemy code should call it, not duplicate logic.
2. Bounce physics must set y_vel to enable reaching next platform in Stage 3 rhythm loops. JUMP_FORCE = 6.5 is the baseline.
3. Guardian shield is a unique state: must track `shielded` per-instance.
4. Chopper needs frame-counting behavior (jump timer, current y offset).
5. Crab needs patrol state (origin_x, direction, current_x).

### Dependencies

- T-003-01 (ring/damage system) — completed ✓
- `get_player_rect()` available in player.py
- `aabb_overlap()` available in objects.py
- `spawn_destroy_particles()` available in renderer.py (Pyxel-dependent, call from main.py only)

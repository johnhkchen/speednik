# Research — T-001-04: Player Module

## Scope

The player module ties physics (T-001-02) and terrain collision (T-001-03) together with input handling, a state machine, animation state tracking, hitbox switching, damage/ring mechanics, and a spindash charge system. It also requires a demo mode with a test level.

## Existing Codebase

### physics.py (352 lines)

**Data structures:**
- `InputState`: decoupled input flags (left, right, jump_pressed, jump_held, down_held)
- `PhysicsState`: all mutable physics state (x, y, velocities, ground_speed, angle, on_ground, is_rolling, facing_right, spinrev, is_charging_spindash, slip_timer)

**Public API — frame update steps 1–4:**
1. `apply_input(state, inp)` — ground/air/rolling input with speed clamping
2. `apply_jump(state)` / `apply_variable_jump(state)` — angle-aware jump + release cap
3. `apply_slope_factor(state)` — running/rolling slope physics
4. `apply_gravity(state)` — airborne gravity
5. `apply_movement(state)` — decompose ground_speed, update position

**Spindash:** `apply_spindash_charge`, `apply_spindash_decay`, `apply_spindash_release`
**Landing:** `calculate_landing_speed(state)` — flat/slope/steep recalculation
**Slip:** `check_slip(state)`, `update_slip_timer(state)`

Key: all functions mutate `PhysicsState` in place. No Pyxel dependency — pure math.

### terrain.py (757 lines)

**Data structures:**
- `Tile`: height_array (16 values), angle (byte), solidity flag
- `SensorResult`: found, distance, tile_angle
- `TileLookup = Callable[[int, int], Optional[Tile]]`

**Public API — frame update steps 5–7:**
- `resolve_collision(state, tile_lookup)` — runs floor/ceiling/wall sensors, snaps position, handles landing
- `find_floor`, `find_ceiling`, `find_wall_push` — individual sensor queries
- `get_quadrant(angle)` — quadrant from byte angle

Key: `resolve_collision` already handles landing detection, angle snap, and calls `calculate_landing_speed`. The player module does NOT need to duplicate landing logic.

### constants.py (50 lines)

All physics constants present. Hitbox radii already defined:
- `STANDING_WIDTH_RADIUS = 9`, `STANDING_HEIGHT_RADIUS = 20`
- `ROLLING_WIDTH_RADIUS = 7`, `ROLLING_HEIGHT_RADIUS = 14`

Missing constants that will be needed:
- Invulnerability duration (not in spec — Sonic 2 uses ~120 frames / 2 seconds)
- Ring scatter count cap (spec says "up to 32")
- Ring recollection timeout (spec says "~3 seconds" = 180 frames)

### main.py (19 lines)

Minimal Pyxel app: `pyxel.init(256, 224)`, update/draw stubs, Q to quit. The player module must integrate into this or replace it for demo mode.

### audio.py (688 lines)

Relevant SFX constants: `SFX_JUMP`, `SFX_SPINDASH_CHARGE`, `SFX_SPINDASH_RELEASE`, `SFX_HURT`, `SFX_RING`. Public API: `play_sfx(id)`, `init_audio()`, `update_audio()`.

### Test patterns

- Pure pytest, no fixtures or conftest
- `degrees_to_byte()` helper duplicated across test files
- `make_tile_lookup(dict)` pattern for terrain tests — dict of `(tx, ty) -> Tile`
- Test classes grouped by feature, 2–5 tests each
- 98 tests total, all passing

## Specification Requirements (§2, §3.2, §5.1)

### Player States (from acceptance criteria)
STANDING, RUNNING, ROLLING, JUMPING, SPINDASH, HURT, DEAD

**State transitions:**
- STANDING → RUNNING: ground_speed != 0 and directional input
- STANDING → JUMPING: jump pressed
- STANDING → SPINDASH: down held, then jump pressed to charge
- STANDING/RUNNING → ROLLING: down pressed when |ground_speed| >= 0.5
- ROLLING → STANDING: |ground_speed| < MIN_ROLL_SPEED (already in physics.py)
- ANY_GROUND → JUMPING: jump pressed (except SPINDASH charge, HURT, DEAD)
- JUMPING → STANDING/RUNNING: landing (handled by resolve_collision)
- ANY → HURT: damage taken with rings > 0
- ANY → DEAD: damage taken with rings = 0
- HURT → STANDING: invulnerability expires + on_ground
- SPINDASH → ROLLING: down released (spindash release)

### Frame Update Order (§2.5)
1. Apply input (acceleration, deceleration, jump initiation)
2. Apply slope factor (if on ground)
3. Apply gravity (if airborne)
4. Move player by velocity
5. Run sensors (floor, ceiling, wall)
6. Resolve collision (push out of solids, snap to surfaces)
7. Update angle (from tile data at sensor contact point)

Steps 1–4 are in physics.py. Steps 5–7 are in terrain.py's `resolve_collision`. The player module orchestrates them in sequence.

### Hitbox Management (§3.2)
Standing: width_radius=9, height_radius=20
Rolling/jumping: width_radius=7, height_radius=14

`terrain.py` already selects radii via `_get_radii(state)` based on `is_rolling` and `on_ground`. The player module just needs to set `is_rolling` correctly on state transitions.

### Spindash (§2.4)
- Initiate: press down while standing still, then jump to charge
- Each jump press: +2.0 to spinrev (max 8.0)
- Decay per frame while holding: spinrev -= spinrev / 32.0
- Release (let go of down): ground_speed = 8 + floor(spinrev / 2)

Physics functions exist. Player module manages the state machine around them.

### Damage (§8)
- rings > 0: scatter rings, brief invulnerability
- rings = 0: death
- Scattered rings recollectable for ~3 seconds

### Animation State Tracking (§5.1)
- Frame index, frame timer — does NOT draw
- Standing: ellipse body, limbs, head, eyes (~24px)
- Running: 4-frame limb animation
- Rolling/spindash: single circle with rotating accent (~14px)
- Jumping: rolling sprite used

### Demo Mode
- Test level: flat ground + slope + loop
- Player controllable with keyboard
- Visible as colored rectangle (temporary rendering)

## Integration Points

1. **Input**: Pyxel button state → `InputState` mapping. Pyxel provides `btn()` (held) and `btnp()` (just pressed).
2. **Physics**: All step 1–4 functions take `PhysicsState` and `InputState`. Player owns the state.
3. **Terrain**: `resolve_collision(state, tile_lookup)` handles steps 5–7. Player provides `tile_lookup`.
4. **Audio**: `play_sfx()` for jump, spindash, hurt sounds. Called from player state transitions.
5. **Rendering**: Player exposes state (position, animation frame, dimensions) for renderer. Does not draw itself.

## Constraints and Risks

1. **PhysicsState is shared** — terrain.py already reads `is_rolling`, `on_ground`, `y_vel` from it. Player state machine must keep these consistent with the player's logical state.
2. **resolve_collision handles landing** — it sets `on_ground = True`, snaps angle, calls `calculate_landing_speed`. Player must sync its state machine after collision resolution (e.g., transition JUMPING → STANDING).
3. **Demo level needs tile data** — no level loader exists yet (that's a later ticket). Must hardcode a simple tile layout.
4. **No renderer yet** — demo mode draws with Pyxel primitives directly. Must be minimal and temporary.
5. **Ring scatter physics** — not covered by existing physics. Scattered rings need simple trajectory (fan outward, gravity, bounce once, disappear after timeout). This is a self-contained subsystem within player.py or a small helper.

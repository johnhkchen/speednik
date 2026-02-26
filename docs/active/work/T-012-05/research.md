# Research — T-012-05: Cross-Stage Behavioral Invariants

## Scope

8 universal behavioral invariants that must hold on every stage (hillside, pipeworks, skybridge).
These test game-logic truths, not progression expectations. Failures are always engine bugs.

## Simulation API Surface

### Stage Loading & Stepping
- `create_sim(stage_name)` → `SimState` — loads any of the 3 stages with full entities
- `sim_step(sim, inp)` → `list[Event]` — one-frame advance, returns events
- `InputState(left, right, jump_pressed, jump_held, down_held)` — input for one frame
- Events: `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`, `GoalReachedEvent`, `CheckpointEvent`

### Player State
- `Player.state: PlayerState` — enum: STANDING, RUNNING, JUMPING, ROLLING, SPINDASH, HURT, DEAD
- `Player.rings: int` — current ring count
- `Player.invulnerability_timer: int` — counts down from 120 after damage
- `Player.scattered_rings: list[ScatteredRing]` — rings dropped on damage
- `Player.physics: PhysicsState` — x, y, x_vel, y_vel, ground_speed, angle, on_ground, is_rolling, facing_right, spinrev, is_charging_spindash

### Damage Mechanics (player.py:damage_player)
- `invulnerability_timer > 0` → damage ignored (returns early)
- `rings > 0` → scatter rings, rings=0, invulnerability=120, state=HURT, knockback
- `rings == 0` → state=DEAD, knockback upward, on_ground=False

### Spindash (physics.py)
- Charge: `spinrev = min(spinrev + SPINDASH_CHARGE_INCREMENT, SPINDASH_MAX_CHARGE)` = min(spinrev+2.0, 8.0)
- Decay: `spinrev -= spinrev / SPINDASH_DECAY_DIVISOR` (÷32)
- Release: `ground_speed = SPINDASH_BASE_SPEED + spinrev/2` = 8.0 + spinrev/2
- With 3 charges: spinrev ≈ 5.64, release speed ≈ 10.82 (always ≥ 8.0)

### Death Mechanics (simulation.py:sim_step)
- When `player.state == PlayerState.DEAD`: sets `player_dead=True`, increments `deaths`, returns `[DeathEvent()]`
- Fall death: no explicit check for y > level_height. Player must die from damage or the caller must handle it.
- Boundary clamping: x < 0 → x=0; x > level_width → clamp. No y clamping upward.

### Wall Collision (terrain.py:resolve_collision)
- Wall sensors E/F detect horizontal blocking
- On wall contact: x velocity zeroed, player pushed out
- Player remains on_ground if grounded before contact
- No "stuck" state — collision resolution always ejects

### Slope Adhesion (terrain.py:resolve_collision + physics.py)
- Floor sensors A/B find distance to surface
- Ground snap tolerance: 14.0 pixels (GROUND_SNAP in resolve_collision)
- `on_ground` stays True if surface found within tolerance
- Angle propagated from tile byte-angle to PhysicsState.angle

### Camera System
- Camera is not part of SimState — it's in main.py's rendering layer
- Constants: CAMERA_LEFT_BORDER=144, CAMERA_RIGHT_BORDER=160, SCREEN_WIDTH=256
- Not directly testable via sim_step alone; would need a camera model

## Existing Test Infrastructure

### Patterns from test_entity_interactions.py
- `_place_buzzer(sim, dx)` — inject enemy relative to player
- `_run_frames(sim, inp, n)` — step N frames, collect events
- `_run_until_event(sim, inp, event_type, max_frames)` — step until specific event
- Tests use `create_sim("hillside")` then manipulate entities

### Patterns from test_audit_*.py
- `run_audit(stage, archetype_fn, expectation)` → (findings, result)
- Expectation-driven: min_x_progress, max_deaths, require_goal
- xfail for known bugs with ticket references

### Invariants Module (speednik/invariants.py)
- `check_invariants(sim, snapshots, events_per_frame)` → `list[Violation]`
- Checks: position bounds, solid tile, velocity limits, velocity spikes, ground consistency, quadrant jumps
- These are *physics* invariants, not *behavioral* invariants

## Key Constraints

1. **No Pyxel dependency** — all tests must work headless via simulation.py
2. **Camera not in SimState** — invariant 8 (camera tracking) needs a lightweight camera model or must use constants to infer screen position
3. **Fall death** — no automatic death at y > level_height. The sim just keeps the player falling. Need to check y coordinate directly.
4. **Stage availability** — all 3 stages load via `create_sim()`: hillside, pipeworks, skybridge
5. **Entity injection** — enemies/rings can be appended to sim lists mid-run
6. **INVULNERABILITY_DURATION = 120 frames** — the i-frame window

## Invariant-by-Invariant Feasibility

| # | Invariant | Approach | Notes |
|---|-----------|----------|-------|
| 1 | Damage with rings scatters | Inject buzzer, give rings, run until DamageEvent | Straightforward |
| 2 | Damage without rings kills | Inject buzzer, set rings=0, run until death | Straightforward |
| 3 | Invulnerability after damage | After first DamageEvent, inject second enemy within 120 frames | Check no second DamageEvent |
| 4 | Wall recovery | Find/inject wall, run into it, verify vel=0 and can jump | Need to detect stall and test escape |
| 5 | Slope adhesion | Find gentle slope tile, walk slowly, check on_ground stays True | Stage-dependent geometry |
| 6 | Fall death below level bounds | Teleport below level_height, check DEAD | May need to check y directly since no auto-death |
| 7 | Spindash speed | Execute spindash sequence, check ground_speed ≥ 8.0 | Use scripted inputs |
| 8 | Camera tracking | Compute camera.x from player.x using border constants | Lightweight model possible |

## File Locations

- Target file: `tests/test_audit_invariants.py`
- Bug tickets: `docs/active/tickets/T-012-05-BUG-*.md`
- Simulation: `speednik/simulation.py`
- Player: `speednik/player.py`
- Constants: `speednik/constants.py`
- QA framework: `speednik/qa.py`
- Terrain: `speednik/terrain.py`
- Existing entity tests: `tests/test_entity_interactions.py`

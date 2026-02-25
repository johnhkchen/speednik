# Review — T-001-02: Physics Constants and Core Engine

## Summary of Changes

### Files Modified
- **`pyproject.toml`** — Added `[project.optional-dependencies] dev = ["pytest"]`
- **`uv.lock`** — Updated with pytest and its dependencies (iniconfig, packaging, pluggy, pygments)
- **`speednik/constants.py`** — Populated with all physics constants from spec §2.1–2.4 and §3.2

### Files Created
- **`speednik/physics.py`** (280 lines) — Core physics engine with:
  - `InputState` dataclass (5 bool fields for input decoupling)
  - `PhysicsState` dataclass (12 fields for all physics-relevant state)
  - 3 helper functions (`byte_angle_to_rad`, `sign`, `_byte_angle_to_degrees`)
  - 14 public functions implementing the full Sonic 2 movement model
- **`tests/__init__.py`** — Empty package marker
- **`tests/test_physics.py`** (290 lines) — 37 unit tests across 10 test classes

### Commit
`ee9b571` — "Add physics constants and core engine (T-001-02)"

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `constants.py` with all physics constants | ✓ | All values from spec §2.1–2.4, §3.2: acceleration, deceleration, friction, top speed, gravity, jump force, slope factors, spindash values, sensor radii |
| Ground movement: accel/decel/friction/top speed | ✓ | `apply_input()` with `_apply_ground_input()`: accel not applied above TOP_SPEED, momentum preserved above it |
| Air movement: gravity, air accel, variable jump | ✓ | `apply_gravity()`, `_apply_air_input()`, `apply_variable_jump()`: cap only when y_vel < -4.0 on release |
| Slope factor with correct factor selection | ✓ | `apply_slope_factor()`: running vs roll_up vs roll_down based on direction |
| Velocity decomposition | ✓ | `apply_movement()`: `x_vel = ground_speed * cos(angle)`, `y_vel = ground_speed * -sin(angle)` |
| Spindash: charge/decay/release | ✓ | Three functions: +2/press (max 8), decay spinrev/32, release 8+floor(spinrev/2) |
| Landing speed recalculation | ✓ | `calculate_landing_speed()`: flat (339°–23°), slope (316°–45°), steep; x-first-then-y comparison |
| Slipping | ✓ | `check_slip()` + `update_slip_timer()`: 30 frames when |gs| < 2.5 on > 46° slopes |
| Frame update order steps 1–4 | ✓ | Functions exist for: input → slope factor → gravity → move. Steps 5–7 (sensors/collision/angle) belong to T-001-03 |
| Unit tests for required scenarios | ✓ | 37 tests: accel to top speed, spindash charge/decay/release, variable jump cap, slope 45°, landing flat/slope/steep |
| Rolling: no accel, half friction, decel, unroll | ✓ | `_apply_rolling_input()`: ROLLING_FRICTION, ROLLING_DECELERATION, MIN_ROLL_SPEED unroll |

## Test Coverage

37 tests, all passing in 0.03s:

- **TestAcceleration** (5): top speed, no-accel-above, momentum preservation, deceleration, friction
- **TestSpindash** (5): charge increment, max cap, decay formula, release speed, release facing left
- **TestVariableJump** (3): cap while rising, no cap when slow rise, no cap when falling
- **TestSlopeFactor** (3): 45° slope, flat (no effect), not applied in air
- **TestLandingSpeed** (4): flat, slope (y wins), slope (x wins), steep
- **TestRolling** (4): no acceleration, friction, deceleration, unroll below min
- **TestGravity** (2): applied in air, not applied on ground
- **TestJump** (2): flat ground, slope
- **TestMovement** (2): ground flat, air
- **TestSlip** (3): steep slope trigger, flat no-trigger, fast no-trigger
- **TestAngleConversion** (4): 0°, 90°, 180°, 360°

### Test gaps
- No integration test for full frame update sequence (apply_input → apply_slope → apply_gravity → apply_movement in order). This is a coordination concern that will matter more when T-001-03 adds steps 5–7.
- Spindash decay over many frames (convergence behavior) not tested — formula is verified per-frame.
- Landing speed with negative x_vel / y_vel combinations not exhaustively tested.

## Design Decisions

1. **PhysicsState dataclass + module functions** over a Physics class — avoids OOP overhead, module provides namespacing
2. **Byte angles (0–255) as primary representation** — matches spec and tile format; convert to radians at trig sites
3. **Mutable state** — functions mutate PhysicsState in place; simpler than copy-on-write for imperative frame updates
4. **InputState decouples from Pyxel** — physics is testable without the game engine
5. **Landing recalculation uses x-first-then-y** — check x_vel first, use y-based only if |y_based| > |x_vel|. This matches Sonic 2 behavior where the engine prefers horizontal speed on gentle slopes.

## Open Concerns

1. **Deceleration overshoot:** When decelerating past zero, the implementation sets ground_speed to ±DECELERATION rather than zero. This matches Sonic 2 behavior (the player instantly starts moving in the new direction) but could surprise someone reading the code.
2. **Slope factor uphill/downhill detection:** Uses `sign(ground_speed) == sign(sin(angle))` to detect uphill. This is correct for the standard angle convention but should be verified against actual tile angles when T-001-03 provides them.
3. **Frame update order boundary:** Steps 1–4 are in physics.py; steps 5–7 will be in terrain.py (T-001-03). The caller (player.py, T-001-04) is responsible for invoking them in order. No enforcement mechanism exists — this is by design (the spec says the order is non-negotiable, not that it should be enforced in code).
4. **No max Y speed cap:** The spec defines MAX_X_SPEED (16.0) but doesn't mention a Y speed cap. Currently y_vel is uncapped. If the player falls for too long, y_vel could grow large. This may need a cap if it causes collision issues in T-001-03.

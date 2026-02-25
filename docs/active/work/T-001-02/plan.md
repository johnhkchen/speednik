# Plan — T-001-02: Physics Constants and Core Engine

## Step 1: Add pytest dev dependency

- Modify `pyproject.toml` to add `[project.optional-dependencies] dev = ["pytest"]`
- Run `uv sync` to install
- Verify: `uv run pytest --version`

**Commit:** "Add pytest dev dependency"

## Step 2: Populate constants.py

- Fill `speednik/constants.py` with all constants from spec §2.1–2.4 and §3.2
- Groups: Screen, Ground Movement, Air Movement, Slopes, Spindash, Sensors, Slip, Angle System
- All values as module-level ALL_CAPS float/int
- Verify: `uv run python -c "from speednik.constants import ACCELERATION; print(ACCELERATION)"`

**Commit:** "Populate physics constants from spec"

## Step 3: Create physics.py — data classes and helpers

- Create `speednik/physics.py`
- Define `InputState` dataclass (left, right, jump_pressed, jump_held, down_held)
- Define `PhysicsState` dataclass (x, y, x_vel, y_vel, ground_speed, angle, on_ground, is_rolling, facing_right, spinrev, is_charging_spindash, slip_timer)
- Implement helpers: `byte_angle_to_rad()`, `sign()`
- Verify: `uv run python -c "from speednik.physics import PhysicsState, InputState; print(PhysicsState())"`

**Commit:** "Add PhysicsState/InputState dataclasses and angle helpers"

## Step 4: Implement ground movement functions

- `apply_input()` — acceleration, deceleration, friction for ground (standing + rolling) and air states
- Handle: no accel above top_speed, momentum can exceed it, rolling has no accel, rolling friction/decel, unroll below min speed, air acceleration, MAX_X_SPEED clamp
- Verify: manual smoke test with print statements

**Commit:** "Implement ground and air input handling"

## Step 5: Implement slope, gravity, movement functions

- `apply_slope_factor()` — factor selection (running/roll up/roll down) + formula
- `apply_gravity()` — airborne gravity application
- `apply_movement()` — velocity decomposition from ground_speed + angle, position update
- Verify: manual check of decomposition at 0° and 45°

**Commit:** "Implement slope factor, gravity, and movement"

## Step 6: Implement jump functions

- `apply_jump()` — angle-aware jump launch formula
- `apply_variable_jump()` — cap y_vel on release while rising

**Commit:** "Implement jump and variable jump height"

## Step 7: Implement spindash functions

- `apply_spindash_charge()` — +2 per press, max 8
- `apply_spindash_decay()` — spinrev /= 32 per frame
- `apply_spindash_release()` — ground_speed = 8 + floor(spinrev / 2), direction

**Commit:** "Implement spindash charge, decay, and release"

## Step 8: Implement landing and slip functions

- `calculate_landing_speed()` — flat/slope/steep angle range checks, ground_speed recalculation
- `check_slip()` — speed threshold + angle check
- `update_slip_timer()` — timer management

**Commit:** "Implement landing speed recalculation and slip detection"

## Step 9: Create test infrastructure and write unit tests

- Create `tests/__init__.py`
- Create `tests/test_physics.py` with all required tests:
  1. Acceleration to top speed (ground_speed reaches 6.0, doesn't exceed from accel)
  2. Spindash charge (+2 per press, max 8)
  3. Spindash decay (verify formula)
  4. Spindash release (ground_speed = 8 + floor(spinrev / 2))
  5. Variable jump cap (capped to -4.0 while rising)
  6. Variable jump no-op (unchanged when falling)
  7. Slope factor on 45° slope
  8. Landing speed — flat angle
  9. Landing speed — slope angle
  10. Landing speed — steep angle
  11. Rolling: no acceleration
  12. Rolling: friction is half of standing
  13. Unroll below min speed
- Run: `uv run pytest tests/ -v`
- Fix any failures

**Commit:** "Add unit tests for physics engine"

## Step 10: Final verification

- Run full test suite: `uv run pytest tests/ -v`
- Verify import works: `uv run python -c "from speednik.physics import *; from speednik.constants import *"`
- Check all acceptance criteria against implementation
- Verify frame update order is structurally supported (functions exist for steps 1–4)

**Commit:** (only if fixes needed)

## Testing Strategy

| Test | Function Under Test | Key Assertion |
|------|-------------------|---------------|
| Accel to top speed | apply_input | ground_speed == TOP_SPEED after N frames |
| Spindash charge | apply_spindash_charge | spinrev increments by 2, caps at 8 |
| Spindash decay | apply_spindash_decay | spinrev follows `spinrev - spinrev/32` |
| Spindash release | apply_spindash_release | ground_speed == 8 + floor(spinrev/2) |
| Variable jump cap | apply_variable_jump | y_vel == -4.0 when was < -4.0 |
| Variable jump noop | apply_variable_jump | y_vel unchanged when >= 0 |
| Slope 45° | apply_slope_factor | Δground_speed == -0.125 * sin(45°) |
| Landing flat | calculate_landing_speed | ground_speed == x_vel |
| Landing slope | calculate_landing_speed | ground_speed uses y * 0.5 formula |
| Landing steep | calculate_landing_speed | ground_speed uses y * 1.0 formula |
| Rolling no accel | apply_input | ground_speed unchanged by direction input |
| Rolling friction | apply_input | friction == ROLLING_FRICTION |
| Unroll | apply_input | is_rolling False below MIN_ROLL_SPEED |

All tests use plain pytest assertions with `pytest.approx()` for float comparisons.

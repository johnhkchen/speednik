# Progress — T-001-02: Physics Constants and Core Engine

## Completed

### Step 1: Add pytest dev dependency ✓
- Added `[project.optional-dependencies] dev = ["pytest"]` to pyproject.toml
- `uv sync --extra dev` installed pytest 9.0.2

### Step 2: Populate constants.py ✓
- All constants from spec §2.1–2.4 and §3.2 added
- Groups: Screen, Ground Movement, Air Movement, Slopes, Spindash, Sensors, Slip, Angle System
- Byte angle conversion for slip threshold: 46° → byte angle 33

### Step 3: Create physics.py — data classes and helpers ✓
- `InputState` dataclass: left, right, jump_pressed, jump_held, down_held
- `PhysicsState` dataclass: x, y, x_vel, y_vel, ground_speed, angle, on_ground, is_rolling, facing_right, spinrev, is_charging_spindash, slip_timer
- `byte_angle_to_rad()`, `sign()`, `_byte_angle_to_degrees()` helpers

### Step 4: Implement ground movement ✓
- `apply_input()` dispatches to ground/rolling/air handlers
- Ground: accel (capped at TOP_SPEED), decel, friction, facing update
- Rolling: no accel, rolling friction, rolling decel, unroll below MIN_ROLL_SPEED
- Air: air acceleration in pressed direction
- MAX_X_SPEED hard clamp applied
- Slip timer suppresses directional input when active

### Step 5: Implement slope, gravity, movement ✓
- `apply_slope_factor()`: factor selection (running/roll up/roll down), formula
- `apply_gravity()`: airborne only
- `apply_movement()`: velocity decomposition from ground_speed + angle, position update

### Step 6: Implement jump functions ✓
- `apply_jump()`: angle-aware launch (decomposes ground_speed then applies jump force)
- `apply_variable_jump()`: caps y_vel to -4.0 on release while rising

### Step 7: Implement spindash functions ✓
- `apply_spindash_charge()`: +2 per press, capped at 8.0
- `apply_spindash_decay()`: spinrev -= spinrev / 32.0
- `apply_spindash_release()`: ground_speed = 8 + floor(spinrev/2), direction-aware

### Step 8: Implement landing and slip ✓
- `calculate_landing_speed()`: flat/slope/steep angle ranges with x-first-then-y logic
- `check_slip()`: speed threshold + steep angle detection
- `update_slip_timer()`: activation and decrement

### Step 9: Create tests ✓
- 37 tests across 10 test classes, all passing
- Coverage: acceleration, deceleration, friction, momentum preservation, spindash (charge/decay/release), variable jump (cap/no-cap), slope factor (45°/flat/air), landing speed (flat/slope/steep), rolling (no accel/friction/decel/unroll), gravity, jump, movement, slip detection, angle conversion

### Step 10: Final verification ✓
- All 37 tests pass (`uv run pytest tests/ -v`)
- All imports work cleanly
- No deviations from plan

## Remaining
None — all steps complete.

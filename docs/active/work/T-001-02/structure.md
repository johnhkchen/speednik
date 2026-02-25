# Structure — T-001-02: Physics Constants and Core Engine

## Files Modified

### 1. `speednik/constants.py` (modify — currently empty)

Populate with all physics constants as module-level `ALL_CAPS` floats/ints. Organized by spec section:

```
# Screen
SCREEN_WIDTH, SCREEN_HEIGHT, FPS

# Ground movement (§2.1)
ACCELERATION, DECELERATION, FRICTION, TOP_SPEED
ROLLING_FRICTION, ROLLING_DECELERATION, MIN_ROLL_SPEED, MAX_X_SPEED

# Air movement (§2.2)
GRAVITY, JUMP_FORCE, AIR_ACCELERATION
JUMP_RELEASE_CAP  (= -4.0)

# Slopes (§2.3)
SLOPE_FACTOR_RUNNING, SLOPE_FACTOR_ROLL_UP, SLOPE_FACTOR_ROLL_DOWN

# Spindash (§2.4)
SPINDASH_CHARGE_INCREMENT (= 2.0)
SPINDASH_MAX_CHARGE (= 8.0)
SPINDASH_DECAY_DIVISOR (= 32.0)
SPINDASH_BASE_SPEED (= 8.0)

# Sensors (§3.2)
STANDING_WIDTH_RADIUS, STANDING_HEIGHT_RADIUS
ROLLING_WIDTH_RADIUS, ROLLING_HEIGHT_RADIUS
WALL_SENSOR_EXTENT (= 10)

# Slip
SLIP_SPEED_THRESHOLD (= 2.5)
SLIP_DURATION (= 30)
SLIP_ANGLE_THRESHOLD (= 46 degrees, stored as byte angle)

# Angle system
ANGLE_STEPS (= 256)
```

No imports. No classes. Pure constants.

### 2. `speednik/physics.py` (create — new file)

#### Imports
```python
from __future__ import annotations
import math
from dataclasses import dataclass, field
from speednik.constants import *
```

#### Data Classes

**`InputState`** — Input flags for physics decoupling:
- `left: bool`, `right: bool`
- `jump_pressed: bool`, `jump_held: bool`
- `down_held: bool`

**`PhysicsState`** — All physics-relevant mutable state:
- `x: float`, `y: float` — position
- `x_vel: float`, `y_vel: float` — velocity components
- `ground_speed: float` — scalar speed along surface
- `angle: int` — byte angle (0–255), 0 = flat ground
- `on_ground: bool`
- `is_rolling: bool`
- `facing_right: bool`
- `spinrev: float` — spindash charge
- `is_charging_spindash: bool`
- `slip_timer: int` — frames of slip remaining

#### Helper Functions

**`byte_angle_to_rad(angle: int) -> float`**
Convert byte angle (0–255) to radians: `angle * (2π / 256)`

**`sign(x: float) -> float`**
Return -1, 0, or 1.

#### Core Physics Functions

All take `PhysicsState` (+ `InputState` where needed), mutate in place, return None.

**`apply_input(state, inp)`** — Step 1
- If on ground and not rolling and not slipping:
  - If pressing direction of movement or from standstill: apply ACCELERATION (skip if |ground_speed| >= TOP_SPEED)
  - If pressing against movement: apply DECELERATION
  - If no input: apply FRICTION
- If on ground and rolling:
  - No acceleration from input
  - If pressing against movement: apply ROLLING_DECELERATION
  - Always apply ROLLING_FRICTION
  - If |ground_speed| < MIN_ROLL_SPEED: unroll
- If airborne:
  - Apply AIR_ACCELERATION in pressed direction (no speed cap in air)
- Clamp |ground_speed| and |x_vel| to MAX_X_SPEED
- Update facing_right from input

**`apply_slope_factor(state)`** — Step 2
- Only when on_ground
- Select slope_factor: RUNNING if not rolling; ROLL_UP if rolling and going uphill; ROLL_DOWN if rolling downhill
- `ground_speed -= slope_factor * sin(angle)`

**`apply_gravity(state)`** — Step 3
- Only when airborne
- `y_vel += GRAVITY`

**`apply_movement(state)`** — Step 4
- If on_ground: decompose ground_speed to x/y via angle
  - `x_vel = ground_speed * cos(angle_rad)`
  - `y_vel = ground_speed * -sin(angle_rad)`
- `x += x_vel`
- `y += y_vel`

**`apply_jump(state)`** — Part of Step 1
- Only when on_ground
- Angle-aware launch:
  - `x_vel -= JUMP_FORCE * sin(angle_rad)`
  - `y_vel -= JUMP_FORCE * cos(angle_rad)`
- Set on_ground = False, angle = 0

**`apply_variable_jump(state)`** — Part of Step 1
- On jump release: if `y_vel < 0`, set `y_vel = max(y_vel, JUMP_RELEASE_CAP)`

**`apply_spindash_charge(state)`**
- `spinrev = min(spinrev + SPINDASH_CHARGE_INCREMENT, SPINDASH_MAX_CHARGE)`

**`apply_spindash_decay(state)`**
- `spinrev -= spinrev / SPINDASH_DECAY_DIVISOR`

**`apply_spindash_release(state)`**
- `ground_speed = SPINDASH_BASE_SPEED + math.floor(spinrev / 2)`
- Direction based on facing_right
- Reset spinrev, is_charging_spindash

**`calculate_landing_speed(state)`**
- Convert angle to degree-equivalent for range checks
- Flat (339°–23°): `ground_speed = x_vel`
- Slope (316°–45°, not flat): `ground_speed = y_vel * 0.5 * -sign(sin(angle))`
- Steep: `ground_speed = y_vel * -sign(sin(angle))`
- Use the one with larger absolute value between x-based and y-based calculation (per Sonic 2 behavior: check x first, use y if |y result| > |x result|)

**`check_slip(state) -> bool`**
- Return True if `|ground_speed| < SLIP_SPEED_THRESHOLD` and angle > SLIP_ANGLE_THRESHOLD

**`update_slip_timer(state, inp)`**
- If check_slip: set slip_timer = SLIP_DURATION
- If slip_timer > 0: decrement, ignore input

## Files Created

### 3. `tests/__init__.py` (create — empty)

Package marker for test discovery.

### 4. `tests/test_physics.py` (create — new file)

Test module with pytest. Test cases:

1. `test_acceleration_to_top_speed` — apply_input with right=True for enough frames; verify ground_speed reaches TOP_SPEED and doesn't exceed it
2. `test_deceleration` — moving right, press left, verify deceleration rate
3. `test_friction` — moving, no input, verify friction rate
4. `test_spindash_charge` — multiple charge calls, verify increment and max cap
5. `test_spindash_decay` — charge to max, apply decay frames, verify formula
6. `test_spindash_release` — charge to known value, release, verify ground_speed
7. `test_variable_jump_cap_while_rising` — set y_vel = -6.5, release jump, verify capped to -4.0
8. `test_variable_jump_no_cap_when_falling` — set y_vel = 1.0, release jump, verify unchanged
9. `test_slope_factor_45_degrees` — on 45° slope, verify ground_speed change per frame
10. `test_landing_speed_flat` — land at angle ~0°, verify ground_speed = x_vel
11. `test_landing_speed_slope` — land at angle ~30°, verify y-based formula
12. `test_landing_speed_steep` — land at steep angle, verify y-based formula (no 0.5 factor)
13. `test_rolling_no_acceleration` — rolling + input, verify no acceleration applied
14. `test_rolling_friction` — rolling, no input, verify ROLLING_FRICTION used
15. `test_unroll_below_min_speed` — rolling at low speed, verify is_rolling becomes False

## Files Modified (Config)

### 5. `pyproject.toml` (modify)

Add pytest as dev dependency:
```toml
[project.optional-dependencies]
dev = ["pytest"]
```

## Module Dependency Graph

```
constants.py  <--  physics.py  <--  tests/test_physics.py
                                    (pytest)
```

No circular dependencies. physics.py depends only on constants.py and stdlib (math, dataclasses). Tests depend on physics.py.

## Public Interface Summary

External modules (player.py, main.py) will import:
- `from speednik.physics import PhysicsState, InputState`
- `from speednik.physics import apply_input, apply_slope_factor, apply_gravity, apply_movement`
- `from speednik.physics import apply_jump, apply_variable_jump`
- `from speednik.physics import apply_spindash_charge, apply_spindash_decay, apply_spindash_release`
- `from speednik.physics import calculate_landing_speed, check_slip, update_slip_timer`
- `from speednik.constants import *` (for any constants needed directly)

# Research — T-001-02: Physics Constants and Core Engine

## 1. Codebase State

The project is post-scaffolding (T-001-01 complete). Relevant files:

- **`speednik/constants.py`** — empty stub, exists and ready for population
- **`speednik/main.py`** — minimal Pyxel app (256×224 @ 60fps, Q to quit). Class-based `App` with `update()`/`draw()` loop
- **`speednik/__init__.py`** — empty package marker
- **`speednik/stages/__init__.py`** — empty subpackage marker
- **`pyproject.toml`** — hatchling build, pyxel dependency, Python >=3.10

No physics, player, collision, or test code exists yet. No test infrastructure (pytest not in dependencies).

## 2. Specification Constants (docs/specification.md §2.1–2.4)

### 2.1 Ground Movement
| Constant | Value | Type |
|----------|-------|------|
| Acceleration | 0.046875 | float |
| Deceleration | 0.5 | float |
| Friction | 0.046875 | float (same as accel) |
| Top speed | 6.0 | float |
| Rolling friction | 0.0234375 | float (half of standing) |
| Rolling deceleration | 0.125 | float |
| Min roll speed | 0.5 | float |
| Max X speed | 16.0 | float (hard cap) |

Key rules: Cannot accelerate while rolling. Acceleration not applied above top speed. Momentum from slopes can exceed top speed.

### 2.2 Air Movement
| Constant | Value |
|----------|-------|
| Gravity | 0.21875 |
| Jump force | 6.5 |
| Air acceleration | 0.09375 |

Variable jump: on release while `y_vel < 0`, set `y_vel = max(y_vel, -4.0)`. If `y_vel >= 0`, no-op.

Jump launch (angle-aware):
```
x_speed -= jump_force * sin(ground_angle)
y_speed -= jump_force * cos(ground_angle)
```

### 2.3 Slope Physics
| Constant | Value |
|----------|-------|
| Slope factor (running) | 0.125 |
| Slope factor (rolling uphill) | 0.078125 |
| Slope factor (rolling downhill) | 0.3125 |

Formula: `ground_speed -= slope_factor * sin(angle)`

Velocity decomposition:
```
x_vel = ground_speed * cos(angle)
y_vel = ground_speed * -sin(angle)
```

Slipping: when `|ground_speed| < 2.5` on slopes > 46°, ignore input for 30 frames.
Detachment: angles 46°–315° trigger surface detachment.

Landing recalculation (from air x/y velocity):
- Flat (339°–23°): `ground_speed = x_speed`
- Slope (316°–45°, excluding flat): `ground_speed = y_speed * 0.5 * -sign(sin(angle))`
- Steep (outside slope range): `ground_speed = y_speed * -sign(sin(angle))`

### 2.4 Spindash
- Charge: +2 per press, max 8.0
- Decay while holding: `spinrev -= spinrev / 32.0` per frame
- Release: `ground_speed = 8 + floor(spinrev / 2)`

### 2.5 Frame Update Order
1. Input (acceleration, deceleration, jump initiation)
2. Slope factor (if on ground)
3. Gravity (if airborne)
4. Move player by velocity
5. Sensors
6. Collision resolution
7. Angle update

## 3. Sensor Constants (§3.2)
| State | width_radius | height_radius |
|-------|-------------|--------------|
| Standing | 9 | 20 |
| Rolling/Jumping | 7 | 14 |

Wall sensor horizontal extent: ±10px from center.

## 4. Angle System

Spec uses 0–255 byte angles mapped to 0°–360°. The physics formulas use `sin(angle)` and `cos(angle)`, meaning we need conversion: `radians = byte_angle * (2π / 256)`.

Angle ranges in spec (for landing recalculation, slipping):
- "Flat": 339°–23° → byte angles ~241–16
- "Slope": 316°–45° → byte angles ~224–32 (excluding flat range)
- "Steep": outside slope range
- "Steeper than 46°": byte angle > ~33

## 5. Dependency Boundaries

**This ticket produces:** `constants.py` (populated) and `physics.py` (new file).

**This ticket does NOT produce:** collision detection (T-001-03), player state machine (T-001-04), camera (T-001-05). The physics engine must be callable from future modules without depending on them.

**Downstream consumers:**
- `terrain.py` (T-001-03) will call sensor/collision steps
- `player.py` (T-001-04) will own player state and call physics functions per frame
- The frame update order spans multiple modules — physics.py owns steps 1–4, terrain.py will own 5–7

## 6. Testing Infrastructure

No pytest dependency exists. T-001-02 acceptance criteria require unit tests. We need to:
1. Add pytest as a dev dependency
2. Create test directory structure
3. Write tests for: acceleration to top speed, spindash charge/decay/release, variable jump cap, slope factor on 45° slope, landing speed recalculation

## 7. Pyxel API Constraints

Pyxel runs at 60fps with `update()`/`draw()` callbacks. Physics calculations happen in `update()`. Pyxel uses a coordinate system where Y increases downward. The spec's `y_vel = ground_speed * -sin(angle)` already accounts for this (negative sin for upward movement in screen space).

## 8. Key Risks and Assumptions

1. **Angle representation:** The spec uses degrees in prose but the tile format stores 0–255 byte angles. Physics functions should accept byte angles and convert internally.
2. **Float precision:** Sonic 2 originals used fixed-point (8.8). Python floats (64-bit) have more than enough precision; no fixed-point emulation needed.
3. **Sign conventions:** Screen Y is down-positive. The spec's formulas already handle this with the negative sin in velocity decomposition.
4. **Module boundary:** physics.py must be stateless — functions take current state and return new state. Player state ownership belongs to T-001-04.
5. **Frame update order:** Steps 1–4 are physics.py's domain. Steps 5–7 belong to collision (T-001-03). physics.py should structure its API so the caller can invoke steps in order.

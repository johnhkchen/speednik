# Design — T-001-02: Physics Constants and Core Engine

## 1. Central Decision: Module Architecture

### Option A: Stateless Function Library
`physics.py` exposes pure functions that take current state (position, velocity, angle, flags) and return updated state. No classes, no internal state.

**Pros:** Simple, testable, no coupling to player representation.
**Cons:** Many parameters to pass around; caller must manage state struct.

### Option B: PhysicsState Dataclass + Functions
Define a `PhysicsState` dataclass holding all physics-relevant fields (ground_speed, x_vel, y_vel, angle, on_ground, is_rolling, spinrev, slip_timer). Functions operate on this dataclass.

**Pros:** Clean API — pass one object instead of 10 parameters. Testable (create a state, call function, assert on result). Natural boundary for serialization.
**Cons:** Slight abstraction; player.py will need to map between its state and PhysicsState.

### Option C: Physics Engine Class
A `PhysicsEngine` class with methods for each sub-step. Holds no persistent state — methods take and return state.

**Pros:** Namespace for related functions.
**Cons:** Unnecessary OOP; a module already provides namespacing.

### Decision: Option B — PhysicsState Dataclass + Module Functions

Rationale:
- The dataclass captures exactly the state that physics cares about, documenting the interface between physics and player modules
- Pure functions on the dataclass are trivially testable
- Player module (T-001-04) will own the authoritative state and construct PhysicsState for each frame's physics update
- No class instances to manage; dataclass is a plain data container

## 2. Angle Representation

### Option A: Byte Angles Everywhere (0–255)
Match the spec's tile format. Convert to radians only at sin/cos call sites.

### Option B: Radians Everywhere
Convert byte angles at input boundaries, work in radians internally.

### Option C: Degrees
Human-readable but requires conversion at every trig call.

### Decision: Option A — Byte Angles as Primary, Conversion Helper

Rationale:
- The spec, tile format, and all angle ranges are defined in byte angles (0–255) or their degree equivalents
- A single `byte_angle_to_rad()` helper handles conversion at trig call sites
- Matching the spec's representation makes it easy to verify against documentation
- Landing recalculation angle ranges (339°–23°, etc.) map cleanly to byte angle comparisons

## 3. Constants Organization

### Decision: Flat Module Constants

`constants.py` will define all values as module-level constants with ALL_CAPS naming. Group by section comments matching the spec sections (§2.1 Ground, §2.2 Air, §2.3 Slopes, §2.4 Spindash, §3.2 Sensors, §1 Screen).

No classes, no enums, no dataclass. These are numeric constants used in arithmetic — plain floats and ints are the right representation.

## 4. Physics Function Decomposition

The frame update order (input → slope → gravity → move → sensors → collision → angle) spans two modules. physics.py owns steps 1–4:

| Function | Step | Responsibility |
|----------|------|---------------|
| `apply_input()` | 1 | Acceleration, deceleration, friction based on ground/air/rolling state and input direction |
| `apply_slope_factor()` | 2 | Slope factor selection (running/rolling up/rolling down) and application |
| `apply_gravity()` | 3 | Gravity when airborne |
| `apply_movement()` | 4 | Velocity decomposition + position update |
| `apply_jump()` | 1 | Jump initiation with angle-aware launch |
| `apply_variable_jump()` | 1 | Jump cap on button release |
| `apply_spindash_charge()` | — | Spindash charge increment |
| `apply_spindash_decay()` | — | Per-frame spinrev decay |
| `apply_spindash_release()` | — | Convert spinrev to ground_speed |
| `calculate_landing_speed()` | — | Recalculate ground_speed from x/y vel on landing |
| `check_slip()` | — | Determine if slip state should activate |

Each function takes `PhysicsState` (and input flags where relevant) and returns a new/modified `PhysicsState`.

## 5. Input Representation

Physics functions need to know directional input and button state. Rather than depending on Pyxel directly, accept simple flags:

```python
@dataclass
class InputState:
    left: bool
    right: bool
    jump_pressed: bool   # just pressed this frame
    jump_held: bool      # held down
    down_held: bool      # for spindash/rolling
```

This decouples physics from the input system and makes testing trivial.

## 6. Mutability Decision

### Decision: Mutate in Place

PhysicsState will be a mutable dataclass. Functions modify it in place and return None. This matches the imperative nature of the physics update (apply X, then apply Y) and avoids unnecessary copies.

For testing, create a fresh state per test case. The mutation is contained within a single frame's update sequence.

## 7. Rolling State

Rolling is a ground state with different physics parameters:
- No acceleration from input
- Rolling friction (half of standing)
- Rolling deceleration when pressing opposite direction
- Unroll below min_roll_speed

The `is_rolling` flag on PhysicsState selects the correct constants. This is simpler than separate rolling functions — the logic is identical except for constant selection.

## 8. Testing Strategy

Add pytest as a dev dependency. Test file: `tests/test_physics.py`.

Required tests per acceptance criteria:
1. **Acceleration to top speed:** Start at 0, apply input frames, verify speed reaches 6.0 and doesn't exceed it from acceleration alone
2. **Spindash charge/decay/release:** Verify +2 per press, max 8, decay formula, release speed formula
3. **Variable jump cap:** Verify y_vel capped to -4.0 on release while rising; no-op when falling
4. **Slope factor on 45° slope:** Verify `ground_speed -= 0.125 * sin(45°)` each frame while running
5. **Landing speed recalculation:** Verify flat/slope/steep angle ranges produce correct ground_speed

## 9. What Was Rejected

- **Fixed-point arithmetic:** Unnecessary; Python floats are sufficient and simpler
- **Physics engine class:** Module-level functions provide the same namespacing without OOP ceremony
- **Separate rolling module:** Rolling is a flag that selects different constants, not a fundamentally different system
- **Radian angles:** Would diverge from spec notation and make angle range checks harder to verify
- **Immutable state with copies:** Adds allocation overhead and verbosity for no testing benefit

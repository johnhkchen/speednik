# T-001-03 Research: Tile Collision System

## Codebase Map

### Existing Modules

**speednik/constants.py** (50 lines)
All physics constants already defined, including collision-relevant values:
- `STANDING_WIDTH_RADIUS = 9`, `STANDING_HEIGHT_RADIUS = 20`
- `ROLLING_WIDTH_RADIUS = 7`, `ROLLING_HEIGHT_RADIUS = 14`
- `WALL_SENSOR_EXTENT = 10`
- `ANGLE_STEPS = 256`

These are consumed directly by T-001-03. No new constants needed.

**speednik/physics.py** (352 lines)
Implements spec §2.1–2.4 (steps 1–4 of the frame update order). Key details:
- `PhysicsState` dataclass: x, y, x_vel, y_vel, ground_speed, angle (byte 0–255), on_ground, is_rolling, facing_right, spinrev, is_charging_spindash, slip_timer
- `byte_angle_to_rad(angle)` and `_byte_angle_to_degrees(angle)` — reusable helpers
- `calculate_landing_speed(state)` — recalculates ground_speed from velocity on landing
- `apply_movement(state)` — decomposes ground_speed to x_vel/y_vel and updates position
- Does NOT include collision. Comment on line 5: "Does not include collision detection (that's T-001-03)."

**speednik/main.py** (20 lines) — Minimal Pyxel skeleton. Not relevant yet.

**speednik/audio.py** (18 lines) — Audio stub. Not relevant.

**tests/test_physics.py** (460 lines) — 37 tests covering physics. Pattern to follow: test classes grouped by feature, `degrees_to_byte()` helper for angle conversions.

### Frame Update Order (spec §2.5)

1. Apply input (acceleration, deceleration, jump initiation) — **physics.py ✓**
2. Apply slope factor (if on ground) — **physics.py ✓**
3. Apply gravity (if airborne) — **physics.py ✓**
4. Move player by velocity — **physics.py ✓**
5. Run sensors (floor, ceiling, wall) — **T-001-03**
6. Resolve collision (push out of solids, snap to surfaces) — **T-001-03**
7. Update angle (from tile data at sensor contact point) — **T-001-03**

This ticket owns steps 5–7. The physics engine provides the state after step 4 (position updated by velocity). Collision reads that position, detects intersections with terrain, pushes the player out, and updates angle/on_ground.

### Specification Analysis (§3)

**§3.1 Tile Format:**
- 16×16 block with height_array (16 values, 0–16), angle (0–255), solidity (not_solid/top_only/full/lrb_only)
- Width array = height_array rotated 90° (computed, not stored separately)
- Angle value 255 = "use nearest 90° cardinal direction" — special sentinel
- Top-only tiles: ignore when y_vel < 0, collide only when y_vel >= 0 from above

**§3.2 Sensor Layout:**
- A/B floor sensors at feet, spread by width_radius
- C/D ceiling sensors at head, spread by width_radius
- E/F wall sensors from center, extend ±WALL_SENSOR_EXTENT(10px) horizontally
- Positions depend on is_rolling: width shrinks 9→7, height shrinks 20→14

**§3.3 Floor Sensor Operation:**
- Cast downward, read height_array[sensor_x_within_tile]
- Extension: height=0 → check tile below
- Regression: height=16 → check tile above
- Return distance to surface
- Use shorter of A/B; A wins ties
- Range: 32px max (current tile + one adjacent)

**§3.5 Wall Sensors:**
- Cast horizontally from center, read width_array
- Disabled when moving away from wall
- Uses current width_radius

**§3.6 Ceiling Sensors:**
- Mirror of floor sensors, cast upward

**§3.7 Angle Quadrant Mode Switching:**
Four quadrants rotate the entire sensor rig:
- 0°–45°, 316°–360° → normal (floor=down, ceiling=up, walls=horizontal)
- 46°–134° → right wall mode (floor=right, ceiling=left, walls=vertical)
- 135°–225° → ceiling mode (floor=up, ceiling=down, walls=horizontal)
- 226°–315° → left wall mode (floor=left, ceiling=right, walls=vertical)

### Data Flow Boundaries

**Input to collision system:**
- `PhysicsState` with updated position (after step 4)
- Tile map / level data (tile lookup by world coordinates)

**Output from collision system:**
- Modified `PhysicsState`: x, y (pushed out of solids), angle (snapped to tile), on_ground (landing/leaving ground), possibly x_vel/y_vel (wall/ceiling collision zeroing)

**Level data interface (not yet built):**
The collision system needs to look up tiles by world position. The `level.py` module doesn't exist yet. The collision system must define the tile data structure and the lookup interface, but the actual level loading is a separate ticket. We need a minimal tile map interface that the collision system depends on.

### Patterns Established by T-001-02

- **Dataclass + module functions:** PhysicsState is a mutable dataclass. Functions mutate it in place.
- **Byte angles:** 0–255 primary representation. `byte_angle_to_rad()` for trig.
- **Constants as flat module-level values:** ALL_CAPS, imported by name.
- **Test structure:** Test classes per feature, helper functions at module level.
- **No classes for logic:** Pure functions operating on dataclasses. No OOP dispatch.

### Constraints

1. **No level loader yet.** terrain.py must define tile data structures but cannot depend on level.py. The tile map abstraction must be minimal — likely a protocol or callable for tile lookup.
2. **PhysicsState is the only entity state.** No separate "collision state" — everything lives on PhysicsState or is local to the collision step.
3. **Pyxel not used in collision.** All collision is pure math, fully testable without Pyxel.
4. **Angle 255 sentinel.** Need to handle the "use nearest cardinal direction" case.
5. **Width array is derived.** Not stored on the tile — computed from height_array by rotating 90°.
6. **The spec says "terrain.py"** — the file path is prescribed by the project structure in §1.

### Risks

1. **Quadrant rotation complexity.** The sensor system needs to rotate all six sensors based on angle. This is the most complex part and the most likely source of bugs.
2. **Extension/regression edge cases.** When a sensor extends to an adjacent tile, what if that tile is a different solidity type? What if it's off the map edge?
3. **Landing transition.** Switching from air to ground requires snapping angle, recalculating ground_speed, and activating ground sensors — all in one frame.
4. **Tile boundary determinism.** The A-wins-ties rule must be applied consistently to prevent jitter.
5. **No level data for testing.** Tests need hand-crafted tile maps. This is fine but requires a clean tile lookup abstraction.

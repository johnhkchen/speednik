# T-011-03 Research: Geometric Feature Probes

## Objective

Targeted tests against specific geometric features in real stages. Unlike walkthrough
smoke tests (T-011-01), these probe **individual features** at known coordinates and
assert specific physics outcomes.

## Codebase Mapping

### Simulation Stack

The test will use the full simulation stack: `create_sim()` → `sim_step()` from
`speednik/simulation.py`. Key types:

- **`SimState`** — complete headless game state (player, entities, tile_lookup, metrics)
- **`sim_step(sim, inp) → list[Event]`** — advances one frame, returns events
- **Event types**: `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`,
  `GoalReachedEvent`, `CheckpointEvent`
- **`InputState`** — per-frame input (left, right, jump_pressed, jump_held, down_held)

### Entity Data (from entities.json per stage)

**Hillside (4800×720px, start 64,610):**
- Loop: tiles tx=217–233, ty=23–38 (px ~3472–3744). All 4 quadrants present in angles.
- Spring: spring_up at x=2380, y=612
- Checkpoint: x=1620, y=610
- Goal: x=4758, y=642

**Pipeworks (5600×1024px, start 200,510):**
- Springs: spring_up at x=200/1400/3400, spring_right at x=1172
- Checkpoints: x=2820/4820
- Goal: x=5558, y=782

**Skybridge (5200×896px, start 64,490):**
- Springs: spring_up at x=304/440/592/1200/2016/2832/3808
- Checkpoints: x=780/3980
- Gaps on row 31 (y=496): 2-tile at px 432, 3-tile at px 576, 20-tile at px 832, etc.
- Goal: x=5158, y=482

### Terrain System

- `TILE_SIZE=16`. Coordinates in pixels. Tile lookup: `(tx, ty) → Tile|None`
- `Tile` has `height_array[16]`, `angle` (byte 0-255), `solidity`, `tile_type`
- `tile_type=5` means `SURFACE_LOOP`
- Quadrants: 0=floor (angle 0-32,224-255), 1=right-wall (33-96), 2=ceiling (97-160),
  3=left-wall (161-223). Function: `get_quadrant(angle)`

### Player Physics

- `PhysicsState`: x, y, x_vel, y_vel, ground_speed, angle, on_ground, is_rolling
- Ground level in hillside before loop: row 39 (y=624). Player stands on surface,
  so player y ≈ 610 on flat ground.
- `SPRING_UP_VELOCITY = -10.0` (upward impulse), `SPRING_RIGHT_VELOCITY = 10.0`

### Ramp Transitions in Hillside

Angle transitions (non-loop) occur at many locations. Key ones:
- tx=44 (px=704): flat→angle 12 (gentle uphill)
- tx=75 (px=1200): flat→angle 22 (moderate uphill)
- tx=128 (px=2048): flat→angle 8 (gentle uphill)

### Test Infrastructure

**`tests/harness.py`** provides:
- `run_on_stage(stage_name, strategy, frames) → ScenarioResult`
- `ScenarioResult.snapshots: list[FrameSnapshot]` with per-frame x, y, x_vel, y_vel,
  ground_speed, angle, on_ground, quadrant, state
- `ScenarioResult.quadrants_visited → set[int]`
- Strategy factories: `hold_right()`, `hold_right_jump()`, `spindash_right()`, `scripted()`

**`speednik/scenarios/runner.py`** provides:
- `run_scenario(ScenarioDef) → ScenarioOutcome` with `trajectory: list[FrameRecord]`
- `FrameRecord` includes `events: list[str]` — event class names per frame

The scenario runner uses the full sim stack including springs/checkpoints/etc.
The harness uses only `player_update()` — no entity processing. **For spring/checkpoint
probes we must use the scenario runner, not the harness.**

### Existing Test Patterns

`test_walkthrough.py` uses `run_scenario()` from the scenario module with
`ScenarioDef`, `StartOverride`, success/failure conditions, and outcome caching.

### Coordinate Discovery Strategy

- Loop: tiles at tx=217–233. Entry from left at ~px 3400. Player ground y ≈ 610.
- Spring (hillside): at x=2380, y=612. Place player just left of spring.
- Checkpoint (hillside): at x=1620, y=610. Run player through with hold_right.
- Gaps (skybridge): small gap at px 432 (2 tiles = 32px), medium at px 576 (3 tiles = 48px)
- Ramps: transitions at multiple hillside locations (px 700, 1200, 2048)

## Constraints

- All probes must work against real stage data (not synthetic grids)
- Probe coordinates must be documented in comments for maintainability
- Spring/checkpoint probes require full sim (scenario runner), not harness-only
- Loop probe needs spindash speed to traverse successfully

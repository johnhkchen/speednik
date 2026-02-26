# T-011-03 Design: Geometric Feature Probes

## Approach: Scenario Runner for All Probes

### Option A: Harness-based (player_update only)

Pros: Simple, fast. Cons: No entity processing — springs, checkpoints, rings are
invisible. Only geometry/physics can be tested. Requires duplicating spring/checkpoint
logic or testing only player trajectory.

### Option B: Scenario runner (full sim_step)

Pros: Springs fire `SpringEvent`, checkpoints fire `CheckpointEvent`, full entity
processing. Cons: Slightly heavier, requires `ScenarioDef` setup.

### Option C: Direct `create_sim()` + `sim_step()` loop

Pros: Full entity support without ScenarioDef overhead. Can place player at arbitrary
start positions via `sim.player.physics.x/y`. Cons: Need to manually manage input and
frame loop. But this is simpler than constructing ScenarioDef for each probe.

**Decision: Option C — direct sim loop with manual input.**

Rationale: ScenarioDef adds boilerplate (success/failure conditions, agent resolution)
that doesn't help probe tests. We just need to place the player, feed inputs, and
check outcomes. Direct `create_sim()` + `sim_step()` gives us full entity processing
with minimal overhead. We'll write a thin helper function `run_probe()` that:
1. Creates sim via `create_sim(stage)`
2. Overrides player position
3. Runs N frames with a strategy function
4. Returns trajectory (list of per-frame dicts) and collected events

This is similar to the harness `run_scenario()` but includes entity processing.

## Probe Design

### 1. Loop Traversal (Hillside)

- Place player at x≈3350, y≈610 (before the loop entry)
- Use spindash strategy to build speed (need ~8+ ground_speed to complete loop)
- Run ~400 frames
- Assert: all 4 quadrants (0,1,2,3) visited
- Assert: player exits with positive ground_speed, on_ground
- Assert: final y ≈ entry y (returned to ground level, ±30px tolerance)

### 2. Spring Launch (Hillside)

- Place player at x≈2370, y≈610 (just left of spring at 2380,612)
- Use hold_right strategy to walk into spring
- Assert: SpringEvent in collected events
- Assert: player y decreased by at least |SPRING_UP_VELOCITY| worth of height
- Assert: player lands back on ground within ~120 frames

### 3. Gap Clearing (Skybridge)

- Target the small gap at px≈432 (2 tiles, 32px)
- Place player before gap, use hold_right_jump
- Assert: player x crosses past the gap
- Assert: player y stays above death threshold (level_height)
- Assert: player is not dead

### 4. Ramp Transitions (Hillside)

- Target the flat→uphill transition at px≈700 (angle 0→12)
- Place player at x≈600, run with hold_right for ~200 frames
- Assert: no frame where ground_speed drops to 0 while x_vel was > 1 (no wall slam)
- Assert: angle changes between consecutive frames are ≤ some threshold

### 5. Checkpoint Activation (Hillside)

- Place player at x≈1550, y≈610 (before checkpoint at 1620,610)
- Use hold_right to walk through
- Assert: CheckpointEvent in collected events

## Rejected Approaches

- **Synthetic grids for probes**: The whole point is testing real stage geometry. Synthetic
  grids already tested in test_simulation.py parity tests.
- **ScenarioDef-based probes**: Too much ceremony for targeted tests. Direct sim loop
  is cleaner.
- **Frame-exact assertions**: Too brittle. Use range-based assertions (e.g., "within
  120 frames" not "at frame 47").

## Test Organization

Single file `tests/test_geometry_probes.py` with:
- A `_run_probe()` helper at top
- One test class per feature type
- Each test method documents probe coordinates in comments
- Sim creation cached per stage to avoid redundant loading

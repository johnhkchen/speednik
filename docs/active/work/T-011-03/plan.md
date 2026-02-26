# T-011-03 Plan: Geometric Feature Probes

## Step 1: Write `_run_probe()` helper and ProbeResult

Create `tests/test_geometry_probes.py` with:
- Module docstring with coordinate reference table
- `ProbeResult` dataclass
- `_run_probe()` function using `create_sim()` + `sim_step()`
- Strategy helper functions for spindash, hold_right, hold_right_jump

Verify: import succeeds, `_run_probe("hillside", 64, 610, hold_right, 10)` returns
a ProbeResult with 10 snapshots.

## Step 2: Loop traversal probe

`TestLoopTraversal` class:
- `test_all_quadrants_visited`: spindash from x≈3300, y≈610. Assert {0,1,2,3} ⊆ quadrants.
- `test_exits_with_positive_speed`: Assert final ground_speed > 0 and on_ground.
- `test_returns_to_ground_level`: Assert |final_y - start_y| < 30px.

Coordinates: Loop tiles at px 3472–3744. Entry at x=3300 gives ~170px approach for
spindash buildup. Ground y ≈ 610.

## Step 3: Spring launch probe

`TestSpringLaunch` class:
- `test_spring_event_fires`: place at x≈2350, run right. Assert SpringEvent in events.
- `test_gains_height`: Assert min(y) < start_y - 50 (launched upward significantly).
- `test_lands_on_ground`: Assert player is on_ground within 120 frames of spring event.

Coordinates: Hillside spring_up at x=2380, y=612.

## Step 4: Gap clearing probe

`TestGapClearing` class:
- `test_clears_small_gap`: skybridge, place before 2-tile gap at px 432. hold_right_jump.
  Assert player x crosses past 480 (gap end) without death.
- `test_stays_above_death_threshold`: Assert all y values < level_height during gap.

Coordinates: Skybridge gap at tiles 27-28 (px 432-464). Player start before gap.

## Step 5: Ramp transition probe

`TestRampTransition` class:
- `test_no_velocity_zeroing`: hillside, place at x≈600. Hold right through the
  flat→uphill transition at px 700 (angle 0→12). Assert no frame where ground_speed
  drops to 0 while previous frame had ground_speed > 1.
- `test_smooth_angle_changes`: Assert consecutive angle changes ≤ 20 byte-angles.

Coordinates: Hillside ramp at px 704 (tx=44, angle 0→12).

## Step 6: Checkpoint activation probe

`TestCheckpointActivation` class:
- `test_checkpoint_event_fires`: hillside, place at x≈1550. Hold right. Assert
  CheckpointEvent in collected events.

Coordinates: Hillside checkpoint at x=1620, y=610.

## Step 7: Run full test suite

```
uv run pytest tests/test_geometry_probes.py -x -v
```

Fix any failures. Tune frame counts and tolerances as needed.

## Testing Strategy

- All probes use real stage data via `create_sim()`
- Assertions are range-based, not frame-exact
- Each test class is independent — can run in isolation
- Coordinates documented in comments within each test method
- Run full suite: `uv run pytest tests/test_geometry_probes.py -x`

# Structure — T-012-06: Composable Mechanic Probes

## Files

### Created

**`tests/test_mechanic_probes.py`** — Main test file (~350 lines)

```
Module docstring
Imports
  - pytest
  - speednik.grids (all builders)
  - speednik.simulation (create_sim_from_lookup, sim_step, SimState, SpringEvent, Event)
  - speednik.physics (InputState)
  - speednik.player (PlayerState)
  - speednik.terrain (get_quadrant, TILE_SIZE)
  - speednik.objects (Spring)
  - speednik.constants (SPRING_UP_VELOCITY, GRAVITY, SPINDASH_BASE_SPEED)

Infrastructure (~50 lines)
  - FrameSnap dataclass (duplicated from test_geometry_probes)
  - ProbeResult dataclass with quadrants_visited, min_y, final properties
  - _run_mechanic_probe(tile_lookup, start_x, start_y, strategy, frames,
                        *, springs=None) -> ProbeResult
    - Creates sim via create_sim_from_lookup
    - Optionally injects springs into sim.springs
    - Steps sim, collects snaps + events
    - Returns ProbeResult

Strategy helpers (~30 lines)
  - _hold_right(frame, sim) -> InputState
  - _make_spindash_strategy() -> Callable (same pattern as test_geometry_probes)
  - _make_jump_right_strategy() -> Callable (hold right, jump on landing)

Test classes:

  TestLoopEntry (~50 lines)
    - @pytest.mark.parametrize("radius", [32, 48, 64, 96])
    - test_loop_traverses_all_quadrants(radius)
    - test_loop_exit_positive_speed(radius)
    - test_loop_exit_on_ground(radius)

  TestRampEntry (~40 lines)
    - @pytest.mark.parametrize("end_angle", [10, 20, 30, 40, 50])
    - test_ramp_no_wall_slam(end_angle)
    - test_ramp_player_advances(end_angle)

  TestGapClearable (~40 lines)
    - @pytest.mark.parametrize("gap_tiles", [2, 3, 4, 5])
    - test_gap_clearable_with_jump(gap_tiles)

  TestSpringLaunch (~50 lines)
    - test_spring_event_fires()
    - test_spring_reaches_expected_height()
    - test_spring_lands_on_ground()

  TestSlopeAdhesion (~40 lines)
    - @pytest.mark.parametrize("angle", range(0, 50, 5))
    - test_slope_stays_on_ground(angle)
```

**`docs/active/tickets/T-012-06-BUG-*.md`** — Bug tickets for failing probes (0-N files)

Each bug ticket follows standard frontmatter:
```yaml
---
id: T-012-06-BUG-01
story: S-012
title: <mechanic>-<failure-mode>
type: bug
status: open
priority: high
phase: ready
depends_on: []
---
```

### Modified

None. This ticket only creates new files.

## Module Boundaries

- `tests/test_mechanic_probes.py` depends on:
  - `speednik.grids` (synthetic grid builders)
  - `speednik.simulation` (SimState, sim_step, create_sim_from_lookup, events)
  - `speednik.physics` (InputState)
  - `speednik.terrain` (get_quadrant, TILE_SIZE)
  - `speednik.objects` (Spring dataclass)
  - `speednik.constants` (physics constants)

- No modifications to any production code.
- No shared test infrastructure changes — self-contained in the test file.

## Key Design Decisions

1. **Ground row = 20 for all probes** — far enough down to avoid top-of-world edge effects,
   consistent with ticket examples.

2. **Player start_y = ground_row * TILE_SIZE** — position at top edge of ground tile.
   Collision resolution will snap the player to the surface.

3. **Spindash strategy for loops/ramps** — base speed 8.0 is the canonical "fast enough"
   speed for most mechanics.

4. **Hold-right-jump for gaps** — models "running jump" player. Need ~15 approach tiles
   to reach near TOP_SPEED before the gap edge.

5. **Spring placed at ground level on flat grid** — spring at x=center of grid, y=ground_row*TILE_SIZE.
   Player walks from left edge.

6. **level_width/level_height sized to grid** — prevent out-of-bounds clamping.

# Plan — T-012-06: Composable Mechanic Probes

## Step 1: Scaffold test file with infrastructure

Create `tests/test_mechanic_probes.py` with:
- Module docstring
- All imports
- FrameSnap, ProbeResult dataclasses
- `_run_mechanic_probe()` function
- Strategy helpers: `_hold_right`, `_make_spindash_strategy`, `_make_jump_right_strategy`

**Verify**: File parses without errors (`python -c "import tests.test_mechanic_probes"`)

## Step 2: Implement loop probes

Add `TestLoopEntry` class with parametrized tests across radii [32, 48, 64, 96]:
- `test_loop_traverses_all_quadrants(radius)` — asserts quadrants {0,1,2,3}
- `test_loop_exit_positive_speed(radius)` — post-loop ground_speed > 0
- `test_loop_exit_on_ground(radius)` — post-loop on_ground

Run tests. For failures, add xfail markers and file bug tickets.

**Verify**: `uv run pytest tests/test_mechanic_probes.py::TestLoopEntry -v`

## Step 3: Implement ramp probes

Add `TestRampEntry` class with parametrized tests across end_angles [10, 20, 30, 40, 50]:
- `test_ramp_no_wall_slam(end_angle)` — no single-frame velocity zeroing
- `test_ramp_player_advances(end_angle)` — player reaches ramp end

**Verify**: `uv run pytest tests/test_mechanic_probes.py::TestRampEntry -v`

## Step 4: Implement gap probes

Add `TestGapClearable` class with parametrized tests across gap_tiles [2, 3, 4, 5]:
- `test_gap_clearable_with_jump(gap_tiles)` — player crosses gap, not dead

**Verify**: `uv run pytest tests/test_mechanic_probes.py::TestGapClearable -v`

## Step 5: Implement spring probe

Add `TestSpringLaunch` class:
- `test_spring_event_fires()` — SpringEvent in events
- `test_spring_reaches_expected_height()` — min_y < start_y - expected_height
- `test_spring_lands_on_ground()` — on_ground within 120 frames

**Verify**: `uv run pytest tests/test_mechanic_probes.py::TestSpringLaunch -v`

## Step 6: Implement slope adhesion probes

Add `TestSlopeAdhesion` class with parametrized tests across angles range(0, 50, 5):
- `test_slope_stays_on_ground(angle)` — on_ground throughout slope region

**Verify**: `uv run pytest tests/test_mechanic_probes.py::TestSlopeAdhesion -v`

## Step 7: Full test suite run

Run complete suite: `uv run pytest tests/test_mechanic_probes.py -v`
Ensure all tests pass or are properly xfailed.

## Step 8: File bug tickets for failures

For each xfailed probe, create `docs/active/tickets/T-012-06-BUG-NN.md` with:
- Standard YAML frontmatter
- Description of the mechanic, parameters, and failure mode
- Expected vs actual behavior

## Testing Strategy

- All assertions are in pytest tests — no separate integration tests needed
- Parametrized tests cover the full parameter space specified in the ticket
- xfail markers document known failures without breaking the suite
- Each probe is independent — no test ordering dependencies

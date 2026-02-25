# T-008-03 Plan: Elemental Terrain Tests

## Step 1: Create test file with imports, helpers, and constants

Create `tests/test_elementals.py` with:
- Module docstring
- All imports (pytest, TILE_SIZE, grid builders, harness functions)
- `_deg_to_byte()` helper
- `_diag()` helper for assertion messages
- Module-level constants: GROUND_ROW, LOOP_GROUND_ROW, START_X, FRAMES, etc.

**Verify:** File parses without import errors: `uv run python -c "import tests.test_elementals"`

## Step 2: Ground adhesion tests

Write three tests:
- `test_idle_on_flat` — flat grid, idle 600 frames, all on_ground, Y stable.
- `test_idle_on_slope` — 20° slope, idle 600 frames, all on_ground.
- `test_idle_on_tile_boundary` — flat grid, start at tile boundary, all on_ground.

**Verify:** `uv run pytest tests/test_elementals.py -x -k "idle" -v`

## Step 3: Walkability threshold tests

Write three tests:
- `test_walk_climbs_gentle_ramp` — 20° ramp, hold_right, progresses.
- `test_walk_stalls_on_steep_ramp` — 70° ramp, hold_right, stuck.
- `test_walkability_sweep` — parametrized 0-90° in 5° steps.

The sweep needs empirical calibration. Run once, observe which angles pass/stall,
then set WALKABLE_CEILING and UNWALKABLE_FLOOR appropriately.

**Verify:** `uv run pytest tests/test_elementals.py -x -k "walk" -v`

## Step 4: Speed gate tests

Write two tests:
- `test_spindash_clears_steep_ramp` — spindash_right clears 50° ramp.
- `test_walk_blocked_by_steep_ramp` — hold_right stalls on same ramp.

**Verify:** `uv run pytest tests/test_elementals.py -x -k "spindash or blocked" -v`

## Step 5: Loop traversal tests

Write three tests:
- `test_loop_spindash_traversal` — with ramps, spindash, all 4 quadrants.
- `test_loop_no_ramps_blocked` — no ramps, spindash fails.
- `test_loop_walk_speed_fails` — with ramps, walk speed insufficient.

Loop geometry constants computed from builder parameters.

**Verify:** `uv run pytest tests/test_elementals.py -x -k "loop" -v`

## Step 6: Gap clearing tests

Write parametrized test:
- `test_gap_clearing` — (gap_tiles, strategy_factory, should_clear) combinations.

Four cases: small/medium/large gaps with jump, medium gap with spindash.

**Verify:** `uv run pytest tests/test_elementals.py -x -k "gap" -v`

## Step 7: Full test suite run

Run entire file: `uv run pytest tests/test_elementals.py -x -v`

Fix any failures by adjusting thresholds or grid parameters based on actual
engine behavior. The tests must document real boundaries, not assumed ones.

## Step 8: Calibration pass

If the walkability sweep or gap clearing thresholds don't match expectations:
1. Run with `-s` to see diagnostic output.
2. Adjust WALKABLE_CEILING / UNWALKABLE_FLOOR to match actual engine behavior.
3. Adjust gap sizes if needed (engine may have different jump distance than
   theoretical calculation).
4. Document actual boundary values as comments.

## Testing Strategy

- **Unit tests:** Every test in `test_elementals.py` is self-contained — builds
  its own grid, runs its own scenario, makes its own assertions.
- **Parametrized tests:** walkability sweep and gap clearing use parametrize for
  coverage across a range of values.
- **Diagnostic output:** All assertions include `_diag()` for failure analysis.
- **No integration tests needed:** these ARE the elemental integration tests
  (physics engine on synthetic terrain).
- **Verification command:** `uv run pytest tests/test_elementals.py -x`

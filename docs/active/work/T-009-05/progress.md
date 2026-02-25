# Progress — T-009-05 boundary-escape-detection

## Step 1: Add hold_left strategy — DONE
Added `hold_left()` factory to tests/harness.py after `hold_right()`.

## Step 2: Add draw_level_bounds() to renderer.py — DONE
Added `draw_level_bounds()` function after `draw_terrain()` in renderer.py.
Draws 4 boundary lines in world space using color slot 8 (red). Viewport-culled.

## Step 3: Add TestBoundaryEscape to test_levels.py — DONE
Added class with 3 xfail test methods: test_right_edge_escape,
test_left_edge_escape, test_bottom_edge_escape. Each iterates all 3 stages
with relevant strategies. Error messages include stage/strategy/frame/position.

## Step 4: Add BOUNDARY PATROL to devpark.py — DONE
- Added `_BOUNDARY_STAGES`, `_boundary_stage_index` module state
- Added `_init_boundary_patrol()` creating hold_right + hold_left bots
- Added `_readout_boundary_patrol()` showing stage name, positions, escape status
- Added Z-key cycling and boundary line rendering in `_draw_running()`
- Added `DevParkStage("BOUNDARY PATROL", ...)` to STAGES list
- Reset `_boundary_stage_index` in `init()`

## Step 5: Update test_devpark.py — DONE
- Updated stage count assertion: 6 → 7
- Updated stage names list to include "BOUNDARY PATROL"
- Added 3 tests: creates_two_bots, bots_can_update, cycles_stages
- Imported `_init_boundary_patrol`

## Step 6: Run full test suite — DONE
`uv run pytest tests/ -x -v` → 811 passed, 5 xfailed (3 new + 2 pre-existing)

No deviations from plan.

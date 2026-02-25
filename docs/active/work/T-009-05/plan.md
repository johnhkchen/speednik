# Plan — T-009-05 boundary-escape-detection

## Step 1: Add hold_left strategy to harness.py

**Action**: Add `hold_left()` factory function after `hold_right()` in
tests/harness.py. Mirrors hold_right but returns `InputState(left=True)`.

**Verification**: `uv run pytest tests/ -x --co -q` — confirm no import errors.

## Step 2: Add draw_level_bounds() to renderer.py

**Action**: Add new function `draw_level_bounds(level_width, level_height,
camera_x, camera_y)` in speednik/renderer.py after draw_terrain().

Draws four boundary lines using `pyxel.line()` in world space with color 8
(red). Each line only drawn if within viewport range.

**Verification**: Visual — will test in step 4 via devpark.

## Step 3: Add TestBoundaryEscape class to test_levels.py

**Action**: Append new test class after TestStallDetection. Three test methods:

- `test_right_edge_escape`: for each stage and right-moving strategy, assert
  all snapshot x <= level_width. @xfail(strict=False).
- `test_left_edge_escape`: for each stage + hold_left, assert all snapshot
  x >= 0. @xfail(strict=False).
- `test_bottom_edge_escape`: for each stage + all strategies, assert all
  snapshot y <= level_height + 64. @xfail(strict=False).

Import hold_left from harness.

**Verification**: `uv run pytest tests/test_levels.py -x -v` — xfail tests
should show as xfail (expected failures) not errors.

## Step 4: Add BOUNDARY PATROL stage to devpark.py

**Action**:
1. Add `_boundary_stage_index: int = 0` module state
2. Add `_BOUNDARY_STAGES = ["hillside", "pipeworks", "skybridge"]`
3. Add `_init_boundary_patrol()` — loads current stage, creates hold_right
   + hold_left bots, max_frames=3600
4. Add `_readout_boundary_patrol()` — shows stage name, bot positions,
   escape status
5. Modify `_draw_running()` — call `renderer.draw_level_bounds()` when
   BOUNDARY PATROL is the active stage
6. Modify `_update_running()` — Z key cycles `_boundary_stage_index` for
   BOUNDARY PATROL
7. Add `DevParkStage("BOUNDARY PATROL", ...)` to STAGES list
8. Reset `_boundary_stage_index` in `init()`

**Verification**: `uv run python -m speednik.main` with `SPEEDNIK_DEBUG=1` —
navigate to dev park → BOUNDARY PATROL. Verify:
- Two bots visible (hold_right and hold_left)
- Red boundary lines at level edges
- Z cycles through stages
- HUD shows positions and escape status

## Step 5: Run full test suite

**Action**: `uv run pytest tests/ -x -v`

**Verification**: All existing tests pass. New xfail tests show as expected
failures (xfail) — not errors, not unexpected passes.

## Testing Strategy

| Test | Type | Expected Result |
|------|------|-----------------|
| test_right_edge_escape | xfail | Expected failure — player escapes right |
| test_left_edge_escape | xfail | Expected failure — player escapes left |
| test_bottom_edge_escape | xfail | May pass (terrain may prevent falling) or fail |
| Existing TestHillside | pass | No regression |
| Existing TestPipeworks | pass/xfail | No regression |
| Existing TestSkybridge | pass/xfail | No regression |
| Existing TestStallDetection | pass | No regression |

## Commit Plan

Single commit after all changes verified:
"feat: boundary escape detection tests and devpark visualization (T-009-05)"

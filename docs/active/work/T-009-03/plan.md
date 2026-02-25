# T-009-03 Plan — Dev Park Stages

## Step 1: Grid Builder Return Type Change

**Files**: `tests/grids.py`, `tests/test_elementals.py`, `tests/test_grids.py`

- Change all 5 public builders (`build_flat`, `build_gap`, `build_slope`, `build_ramp`,
  `build_loop`) to return `(tiles_dict, TileLookup)`.
- Update every call site in `test_elementals.py` to destructure: `_, lookup = build_*()`.
- Update every call site in `test_grids.py` similarly.
- Run `uv run pytest tests/test_elementals.py tests/test_grids.py -x` to verify.

## Step 2: DevPark Palette

**Files**: `speednik/renderer.py`

- Add `"devpark"` entry to `STAGE_PALETTES` dict with green-on-black terminal colors.
- Slots: 0→black, 1→dark green, 2→mid green, 3→bright green, 13-15→darker greens.

## Step 3: DevPark Module — State Machine and Menu

**Files**: `speednik/devpark.py`

- Add module-level state variables.
- Add `DevParkStage` dataclass (name, init_fn, readout_fn).
- Add `STAGES` list with 5 stage entries (init/readout functions as stubs initially).
- Add `init()`, `update()`, `draw()` public API.
- Add `_update_menu()` / `_draw_menu()` for sub-menu navigation.
- Add `_update_running()` / `_draw_running()` for active stage.

## Step 4: Stage Init Functions

**Files**: `speednik/devpark.py`

- Implement `_init_ramp_walker()`: `build_ramp(10, 30, 0, 80, 10)` progressively steeper.
  Single `hold_right` bot. Optional second `spindash_right` bot.
- Implement `_init_speed_gate()`: `build_ramp(10, 15, 0, 55, 10)` with steep obstacle.
  Two bots: `hold_right` + `spindash_right` at same start.
- Implement `_init_loop_lab()`: `build_loop(10, 128, 40, ramp_radius=128)`.
  Single `spindash_right` bot. Z cycles between with-ramps and without-ramps variant.
- Implement `_init_gap_jump()`: `build_gap(30, gap, 10, 10)` with progressive gaps.
  Single `hold_right_jump` bot. Start with gap=3, widen on Z press.
- Implement `_init_hillside_bot()`: `load_stage("hillside")`. Single `hold_right` bot.

## Step 5: Stage Readout Functions

**Files**: `speednik/devpark.py`

- `_readout_ramp_walker`: show current tile angle beneath bot, stall position.
- `_readout_speed_gate`: show both bots' X positions, "BLOCKED" / "CLEARED" labels.
- `_readout_loop_lab`: show variant label ("WITH RAMPS" / "NO RAMPS"), quadrants visited.
- `_readout_gap_jump`: show gap width, "CLEARED" / "FELL" status.
- `_readout_hillside_bot`: show X/Y position, angle, ground speed.

## Step 6: Main.py Integration

**Files**: `speednik/main.py`

- Import devpark module functions.
- In `_update_stage_select`: when entering dev_park, call `devpark.init()`.
- Replace `_update_dev_park` body: call `devpark.update()`, check for exit signal.
- Replace `_draw_dev_park` body: call `devpark.draw()`.

## Step 7: Tests

**Files**: `tests/test_devpark.py`

- Test menu state: init sets sub_state to "menu".
- Test stage init functions: each creates correct number of bots with correct labels.
- Test bot update in each stage: bots advance frames without error.
- Test completion: bots finish at max_frames or goal_x.

## Step 8: Full Test Suite Verification

- Run `uv run pytest tests/ -x` to verify all tests pass.
- Fix any regressions from grid builder return type change.

## Testing Strategy

- **Unit tests**: Each stage init function creates bots headlessly (no Pyxel).
- **Integration tests**: Bots can run multiple frames without error on synthetic grids.
- **No visual tests**: Draw path requires Pyxel runtime; tested manually.
- **Regression**: Full suite must pass — especially test_elementals and test_grids.

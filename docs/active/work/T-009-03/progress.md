# T-009-03 Progress — Dev Park Stages

## Completed Steps

### Step 1: Grid Builder Return Type Change
- Changed all 5 public builders in `tests/grids.py` to return
  `tuple[dict[tuple[int,int], Tile], TileLookup]` instead of just `TileLookup`.
- Updated all call sites in `tests/test_elementals.py` (12 calls) and
  `tests/test_grids.py` (15 calls) to destructure `_, lookup = build_*()`.
- Verified: 72 tests pass in affected files.

### Step 2: DevPark Palette
- Added `"devpark"` entry to `STAGE_PALETTES` in `speednik/renderer.py`.
- Colors: black background (0x000000), green terrain shades (0x003300, 0x00AA00,
  0x00FF00), green player (0x00CC00), green UI text (0x00FF00).

### Step 3: DevPark Module — State Machine and Menu
- Rewrote `speednik/devpark.py` with full module-level state machine.
- Added `DevParkStage` dataclass, `STAGES` list (6 entries: 5 elemental + MULTI-VIEW).
- Implemented `init()`, `update()`, `draw()` public API.
- Menu with UP/DOWN/Z/X navigation, cursor highlight.
- Running state with bot update loop and X-to-exit.

### Step 4: Stage Init Functions
- `_init_ramp_walker()`: build_ramp with 0→60° angle, 2 bots (hold_right + spindash).
- `_init_speed_gate()`: build_ramp with steep obstacle, 2 bots (walk + spindash).
- `_init_loop_lab_with_ramps()`: build_loop with ramp_radius=128, 1 spindash bot.
- `_init_loop_lab_no_ramps()`: build_loop without ramps, 1 spindash bot.
- `_init_gap_jump(gap_index)`: build_gap with progressive widths [3,5,8,12,20], 1 jump bot.
- `_init_hillside_bot()`: load_stage("hillside"), 1 hold_right bot.
- `_init_multi_view_hillside()`: 4 bots on hillside (preserved from previous quad-split).

### Step 5: Stage Readout Functions
- Readouts for each stage: angle readout, walk/spindash comparison, loop variant info,
  gap status, hillside position. Drawn in screen space at bottom of viewport.

### Step 6: Main.py Integration
- Replaced old quad-split dev park methods with delegation to `devpark.init()`,
  `devpark.update()`, `devpark.draw()`.

### Step 7: Tests
- Updated `tests/test_devpark.py`: removed old QUADRANTS-only structure, added
  `TestDevParkStages` with 16 new tests covering all 6 stage init functions.
- Preserved `TestQuadSplit` tests for QUADRANTS geometry.
- Added `TestMultiBotIndependence` tests.

### Step 8: Full Test Suite Verification
- 808 passed, 2 xfailed, 0 errors. All green.

## Deviations from Plan

- **6 stages instead of 5**: The linter/hook preserved the quad-split MULTI-VIEW stage
  from the previous implementation. This is a good addition — it retains the original
  security-camera debug view alongside the 5 new elemental stages.
- **QUADRANTS and draw_quad_split preserved**: Not deleted since they're still used by
  the MULTI-VIEW stage. Tests for QUADRANTS geometry kept as well.

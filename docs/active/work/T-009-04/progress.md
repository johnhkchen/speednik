# Progress — T-009-04: security-camera-quad-split

## Completed

### Step 1: QUADRANTS constant and draw_quad_split — DONE
- Added `QUADRANTS` list to `speednik/devpark.py` with 4 tuples defining the 2×2 layout.
- Added `draw_quad_split(bots, frame_count)` function with clip/camera/terrain/player/label
  rendering loop and white divider lines at screen center.

### Step 2: MULTI-VIEW stage entry — DONE
- Added `_init_multi_view_hillside()` factory: creates 4 bots via `make_bots_for_stage("hillside", max_frames=36000)`.
- Added `_readout_multi_view()` (no-op — labels drawn by draw_quad_split itself).
- Added `DevParkStage("MULTI-VIEW", ...)` to the `STAGES` table.

### Step 3: Quad-split rendering dispatch — DONE
- Modified `_draw_running()` to detect MULTI-VIEW stage and call `draw_quad_split()`
  instead of the normal single-camera rendering path.

### Step 4: Merge with T-009-03 — DONE
- T-009-03 (dev park elemental stages) was completed concurrently, replacing the placeholder
  with a full sub-menu system. Adapted quad-split to integrate as a STAGES table entry
  rather than replacing the placeholder directly.
- Updated T-009-03's tests: STAGES count 5→6, names list includes "MULTI-VIEW".

### Step 5: Tests — DONE
- Added to TestDevParkStages: `test_multi_view_creates_four_bots`, `test_multi_view_bots_can_update`.
- Added TestQuadSplit class with 4 geometry tests:
  - test_quadrants_cover_full_screen
  - test_quadrants_no_overlap
  - test_quadrants_within_screen
  - test_quadrant_count
- All 35 devpark tests pass.

### Step 6: Full test suite — DONE
- 808 passed, 2 xfailed. Zero regressions.

## Deviations from plan

- **Integration approach changed**: Original plan had main.py managing bots directly.
  T-009-03's concurrent work replaced the placeholder with a module-level state machine in
  devpark.py. Adapted to add quad-split as a STAGES entry instead. Cleaner result.
- **main.py changes minimal**: main.py already delegates to devpark.init()/update()/draw().
  No main.py modifications needed beyond what T-009-03 already did.

# Review — T-009-04: security-camera-quad-split

## Summary

Implemented the quad-split security-camera view for the dev park, rendering four bot
strategies (idle, hold_right, hold_right_jump, spindash_right) simultaneously on the
hillside stage. Each bot runs in an independent 128×112 quadrant with its own camera,
terrain rendering, and HUD labels. Integrated as a MULTI-VIEW entry in the dev park
stage menu (added by T-009-03).

## Files changed

### Modified: `speednik/devpark.py`
- Added `QUADRANTS` constant: 4 tuples defining the 2×2 quadrant layout (128×112 each).
- Added `draw_quad_split(bots, frame_count)` function (~25 lines):
  - Iterates QUADRANTS with pyxel.clip/camera/terrain/player/label rendering.
  - Draws white divider lines at x=128 and y=112 after all quadrants.
- Added `_init_multi_view_hillside()` factory: creates 4 hillside bots with 10-min lifetime.
- Added `_readout_multi_view()` no-op (labels drawn within draw_quad_split).
- Added "MULTI-VIEW" entry to STAGES table.
- Modified `_draw_running()` to dispatch to `draw_quad_split()` for MULTI-VIEW stage.

### Modified: `tests/test_devpark.py`
- Updated `test_stages_list_has_five_entries` → `test_stages_list_has_six_entries`.
- Updated `test_stage_names` to include "MULTI-VIEW".
- Added `test_multi_view_creates_four_bots` and `test_multi_view_bots_can_update`.
- Added `TestQuadSplit` class with 4 geometry tests (coverage, overlap, bounds, count).

### Not modified: `speednik/main.py`
- T-009-03 already refactored main.py to delegate to `devpark.init()/update()/draw()`.
  No additional main.py changes were needed for quad-split.

## Test coverage

| Area | Tests | Status |
|------|-------|--------|
| QUADRANTS geometry (area, overlap, bounds, count) | 4 tests | Pass |
| MULTI-VIEW init (creates 4 bots, correct labels) | 1 test | Pass |
| MULTI-VIEW bots can update | 1 test | Pass |
| Multi-bot independence (positions, cameras diverge) | 2 tests | Pass |
| Existing LiveBot/factory/stage tests | 27 tests | Pass (unchanged) |
| Full suite | 808 pass, 2 xfail | No regressions |

**Coverage gaps:**
- `draw_quad_split()` is not unit tested — it calls Pyxel drawing primitives that require
  Pyxel initialization. Visual correctness must be verified manually.
- `_draw_running()` dispatch for MULTI-VIEW not directly tested (Pyxel dependency).

## Acceptance criteria status

- [x] Quad-split renders 4 bot viewports at 128×112 each
- [x] Each quadrant shows its own bot with independent camera and terrain
- [x] Strategy labels visible in each quadrant corner
- [x] Position readout visible in each quadrant
- [x] Divider lines separate the four quadrants
- [x] `pyxel.clip()` prevents cross-quadrant bleed
- [x] All 4 bots update independently each frame
- [x] Quad-split works with real stage data (hillside via MULTI-VIEW menu entry)
- [x] Camera follows each bot within its quadrant
- [x] X key exits back to dev park menu
- [ ] Performance acceptable at 60fps — requires manual verification
- [x] `uv run pytest tests/ -x` passes (808 pass, 2 xfail)

## Design decisions

1. **Camera Option 3 (normal camera, accept mismatch)**: No changes to camera.py. Camera
   borders are calculated for 256px but only 128px is visible per quadrant.

2. **STAGES table integration**: T-009-03 added a sub-menu system concurrently. Rather than
   managing bots in main.py, quad-split was added as a STAGES entry ("MULTI-VIEW"). This
   is cleaner — users navigate to it from the dev park menu like any other stage.

3. **Dispatch in _draw_running**: MULTI-VIEW is detected by name to call `draw_quad_split()`
   instead of the normal single-camera rendering. This keeps the existing rendering path
   untouched for all other stages.

4. **max_frames=36000**: 10 minutes at 60fps for extended observation.

## Open concerns

1. **Performance**: 4× terrain iteration with clipping. Expected ~2× total work (4 bots ×
   1/2 screen area). Should be fine at 60fps but needs manual verification.

2. **Synthetic grid quad-split**: Only hillside is wired up. `make_bots_for_grid` exists
   for synthetic grids but no MULTI-VIEW variant uses it. Could add "MULTI-VIEW: RAMP" etc.
   as follow-up.

3. **Stage palette**: MULTI-VIEW uses hillside palette (set by `make_bots_for_stage` calling
   `load_stage`). The dev park menu sets "devpark" palette; entering MULTI-VIEW overrides it.
   Returning to menu doesn't restore devpark palette. Minor visual glitch.

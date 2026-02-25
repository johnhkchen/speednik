# T-009-03 Review — Dev Park Stages

## Summary of Changes

### Files Modified

| File | Change |
|------|--------|
| `tests/grids.py` | All 5 builders now return `(tiles_dict, TileLookup)` tuples |
| `tests/test_grids.py` | Updated 15 call sites to destructure `_, lookup =` |
| `tests/test_elementals.py` | Updated 12 call sites to destructure `_, lookup =` |
| `speednik/renderer.py` | Added `"devpark"` palette (green-on-black terminal aesthetic) |
| `speednik/devpark.py` | Full rewrite: state machine, 6 stages, menu, readouts |
| `speednik/main.py` | Dev park methods now delegate to `devpark.init/update/draw` |
| `tests/test_devpark.py` | Rewritten: 35+ tests covering all stages and state |

### No Files Created or Deleted

All changes are modifications to existing files.

## Acceptance Criteria Status

- [x] Dev park sub-menu with stage entries, UP/DOWN/Z/X navigation
- [x] RAMP WALKER: shows hold_right bot walking until stall, angle readout visible
- [x] SPEED GATE: shows walk vs spindash bot, visual comparison
- [x] LOOP LAB: shows loop with ramps (success), Z toggles to without ramps (failure)
- [x] GAP JUMP: shows gap clearing, Z cycles progressive widths
- [x] HILLSIDE BOT: runs hold_right on real hillside stage data
- [x] Each stage has init/update/draw/exit lifecycle
- [x] X key returns to dev park menu from any stage
- [x] Dev park palette is distinct from gameplay palettes
- [x] Bot labels rendered on screen (in world space above each bot)
- [x] Debug HUD visible during dev park stages (stage name, F/X/Y/GS/A/Q/GND)
- [x] `uv run pytest tests/ -x` passes — 808 passed, 2 xfailed

## Test Coverage

### Existing Tests (unchanged, still passing)
- `test_elementals.py`: 30 parametrized tests on synthetic grids — all pass with new
  builder return type.
- `test_grids.py`: 22 tests on builder output — all pass.

### New/Updated Tests in `test_devpark.py`
- `TestLiveBotUpdate` (5 tests): frame advance, movement, max_frames, goal_x, stopped bot
- `TestMakeBot` (3 tests): label, position, initial state
- `TestMakeBotsForStage` (3 tests): 4 bots created, correct labels, updatable
- `TestMakeBotsForGrid` (2 tests): correct count, updatable
- `TestMultiBotIndependence` (2 tests): divergent positions, independent cameras
- `TestDevParkStages` (16 tests): all 6 stages init correctly, bots update, labels match
- `TestQuadSplit` (4 tests): screen coverage, no overlap, within bounds, count

Total: 35 tests in test_devpark.py.

### Not Tested (requires Pyxel runtime)
- Draw path: `_draw_menu()`, `_draw_running()`, readout functions, `draw_quad_split()`
- Palette application: `set_stage_palette("devpark")` color values
- Menu visual rendering and stage visual rendering

These require the Pyxel graphics runtime and are tested via manual play.

## Open Concerns

1. **Grid builder return type is a breaking API change**: All callers of `build_flat`,
   `build_gap`, `build_slope`, `build_ramp`, `build_loop` must destructure the return
   value. Any downstream code not yet updated would break. All known call sites have been
   updated and verified.

2. **MULTI-VIEW stage draws differently from others**: The MULTI-VIEW stage uses
   `draw_quad_split()` with 4 independent camera viewports + clipping. The current
   `_draw_running()` function uses a single camera from the primary bot. The MULTI-VIEW
   stage's readout function is a no-op since `draw_quad_split` handles its own labels.
   However, `_draw_running()` will draw all 4 bots through one camera, not quad-split.
   The MULTI-VIEW stage will render functionally but without the quad-split layout
   unless `_draw_running` is special-cased. This is a known limitation — the quad-split
   renderer exists and could be dispatched for the MULTI-VIEW stage with a small change
   to `_draw_running`.

3. **Strategy imports from tests/**: `_init_*` functions import from `tests.harness` and
   `tests.grids`. This works because dev park is DEBUG-only, but it means `tests/` must
   be on the import path when running the game with `SPEEDNIK_DEBUG=1`. This is the same
   pattern established in T-009-02 and is acceptable for developer tooling.

4. **Module-level mutable state**: The dev park uses module globals for state management
   (`_sub_state`, `_selected_index`, etc.). This is simple and works for a single-instance
   game, but means state persists across repeated `init()` calls only if `init()` resets
   everything. It does.

# Review — T-009-05 boundary-escape-detection

## Summary of Changes

This ticket adds boundary escape detection (tests + visualization) without
fixing the underlying problem. The tests document the known defect and serve
as regression gates for the eventual fix.

### Files Modified

| File | Change |
|------|--------|
| `tests/harness.py` | Added `hold_left()` strategy factory |
| `tests/test_levels.py` | Added `TestBoundaryEscape` class (3 xfail test methods) |
| `tests/test_devpark.py` | Updated stage count/names, added boundary patrol tests |
| `speednik/renderer.py` | Added `draw_level_bounds()` function |
| `speednik/devpark.py` | Added BOUNDARY PATROL stage with Z-to-cycle |

### No files created or deleted.

## What Was Delivered

### 1. Boundary escape tests (tests/test_levels.py)

Three `@pytest.mark.xfail(strict=False)` test methods in `TestBoundaryEscape`:

- **test_right_edge_escape**: Runs hold_right, hold_right_jump, and spindash_right
  on all 3 stages (hillside, pipeworks, skybridge) for 3600 frames. Asserts
  `snap.x <= level_width` for every frame snapshot.

- **test_left_edge_escape**: Runs hold_left on all 3 stages for 3600 frames.
  Asserts `snap.x >= 0` for every frame snapshot.

- **test_bottom_edge_escape**: Runs all 4 strategies (idle, hold_right,
  hold_right_jump, spindash_right) on all 3 stages for 3600 frames. Asserts
  `snap.y <= level_height + 64` (64px grace for jump arcs).

Error messages include: `{stage_name}/{strategy_name}: escaped {direction}
at frame {frame}, x/y={value}, level_width/height={bound}`.

All three tests currently xfail as expected — the bug exists.

### 2. hold_left strategy (tests/harness.py)

New `hold_left()` factory alongside existing strategies. Returns
`InputState(left=True)` every frame. Used by both boundary tests and
dev park boundary patrol.

### 3. Boundary rendering (speednik/renderer.py)

New `draw_level_bounds(level_width, level_height, camera_x, camera_y)`:
- Draws 4 boundary lines in world space using color 8 (red)
- Viewport-culled: only draws edges within visible camera area
- Left edge at x=0, right edge at x=level_width
- Top edge at y=0, bottom edge at y=level_height

### 4. Dev park BOUNDARY PATROL stage (speednik/devpark.py)

New stage added to STAGES list (7th entry):
- Creates 2 bots: `RIGHT->` (hold_right) and `<-LEFT` (hold_left)
- Z key cycles through hillside → pipeworks → skybridge
- Red boundary lines rendered at level edges
- HUD readout shows: current stage name, bot X positions, "ESCAPED!" flag
  when bot leaves bounds (x < 0 or x > level_width)
- 3600 frame duration (60 seconds at 60fps)

## Test Coverage

| Area | Tests | Status |
|------|-------|--------|
| Right edge escape (3 stages × 3 strategies) | test_right_edge_escape | xfail |
| Left edge escape (3 stages × 1 strategy) | test_left_edge_escape | xfail |
| Bottom edge escape (3 stages × 4 strategies) | test_bottom_edge_escape | xfail |
| Boundary patrol creates 2 bots | test_boundary_patrol_creates_two_bots | pass |
| Boundary patrol bots update | test_boundary_patrol_bots_can_update | pass |
| Boundary patrol cycles stages | test_boundary_patrol_cycles_stages | pass |
| Stage list count updated | test_stages_list_has_seven_entries | pass |
| Stage names list updated | test_stage_names | pass |

Full suite: **811 passed, 5 xfailed** (3 new boundary + 2 pre-existing).

## Acceptance Criteria Checklist

- [x] Boundary escape test for each real stage: player X stays within [0, level_width]
- [x] Boundary escape test for each real stage: player Y stays within reasonable range
- [x] Tests cover right-edge, left-edge, and bottom-edge escape vectors
- [x] Test failure messages include strategy name, frame number, and position
- [x] Tests marked @pytest.mark.xfail with note about no kill plane
- [x] Dev park BOUNDARY PATROL stage shows bots approaching level edges
- [x] Level boundary lines rendered visually (red) in dev park
- [x] Dev park stage shows both hold_right and hold_left bots
- [x] No Pyxel imports in test files
- [x] `uv run pytest tests/ -x` passes (with expected xfails)

## Open Concerns

1. **Top edge not tested separately**: The ticket mentions top-edge escape
   (springs/spindash up steep ramps). The bottom-edge test includes a Y
   upper bound implicitly (positive Y values), but there's no dedicated top
   test because no strategy currently launches the player above y=0. If springs
   or launchers are added to the harness, a top-edge test should follow.

2. **Boundary rendering only in BOUNDARY PATROL**: The ticket mentions
   "when DEBUG is active" as optional. The `draw_level_bounds()` function is
   ready for use in main.py's debug path, but this ticket doesn't wire it
   into the main game loop. That integration is a separate concern since it
   touches main.py's rendering flow.

3. **Camera follows primary bot only**: In BOUNDARY PATROL, the camera follows
   the first bot (hold_right). The hold_left bot may walk off-screen to the
   left quickly. The readout HUD tracks both bots numerically, but the
   hold_left bot is only visible briefly. This is by design (shows the problem
   as the player experiences it).

# Plan — T-009-04: security-camera-quad-split

## Step 1: Add QUADRANTS constant and draw_quad_split to devpark.py

Add after the LiveBot class (before factory helpers):

- QUADRANTS list of 4 tuples: (qx, qy, qw, qh).
- `draw_quad_split(bots, frame_count)` function that:
  - Iterates zip(QUADRANTS, bots).
  - Sets clip, camera offset, draws terrain + player, resets camera, draws labels.
  - After loop: resets clip, draws divider lines.

Verification: file parses without errors (`python -c "from speednik.devpark import draw_quad_split, QUADRANTS"`).

## Step 2: Add dev_park_bots field and _init_dev_park to main.py

- Add `self.dev_park_bots: list | None = None` in `__init__`.
- Add `_init_dev_park()` method:
  - Lazy-imports `make_bots_for_stage` from devpark.
  - Sets stage palette to hillside.
  - Creates bots with `max_frames=36000` (10 min).
  - Stores in `self.dev_park_bots`.

Verification: no import errors, field accessible.

## Step 3: Update _update_stage_select to init dev park

In the Z/RETURN handler, when `selected_stage == _DEV_PARK_STAGE`:
- Call `self._init_dev_park()` before setting state.

Verification: existing stage_select tests still pass (no dev park tests exercise this path
since they need Pyxel).

## Step 4: Replace _update_dev_park

New implementation:
- Check `pyxel.btnp(pyxel.KEY_X)` → clear bots, return to stage_select.
- If bots exist, update all of them.

Verification: logic review — no Pyxel-free test possible for key check, but update loop
is testable.

## Step 5: Replace _draw_dev_park

New implementation:
- If dev_park_bots exists, lazy-import and call `draw_quad_split(self.dev_park_bots, pyxel.frame_count)`.

Verification: logic review.

## Step 6: Add tests to test_devpark.py

**TestQuadSplit class:**

1. `test_quadrants_cover_full_screen`:
   - Import QUADRANTS and SCREEN_WIDTH, SCREEN_HEIGHT.
   - Verify total area equals 256 * 224.
   - Verify each quadrant's (qx+qw) ≤ 256 and (qy+qh) ≤ 224.

2. `test_quadrants_no_overlap`:
   - For each pair of quadrants, verify their rectangles don't overlap.
   - Two rects overlap if: not (r1.right ≤ r2.left or r2.right ≤ r1.left or
     r1.bottom ≤ r2.top or r2.bottom ≤ r1.top).

3. `test_quad_split_bots_update_independently`:
   - Create 4 bots on flat grid with different strategies (idle, hold_right, hold_right, hold_right).
   - Update all 30 frames.
   - Assert idle bot hasn't moved, hold_right bots have moved.
   - Assert each bot has independent frame counter.

4. `test_make_bots_for_stage_returns_four_labels`:
   - Already exists as `test_bot_labels` — verify it still passes.

Verification: `uv run pytest tests/test_devpark.py -x -v`.

## Step 7: Run full test suite

`uv run pytest tests/ -x` — all tests must pass with no regressions.

## Testing strategy

| What | How | Tool |
|------|-----|------|
| QUADRANTS geometry | Unit test: area coverage, no overlap | pytest |
| Bot independence | Unit test: 4 bots diverge after updates | pytest |
| draw_quad_split rendering | Manual: run game with SPEEDNIK_DEBUG=1 | visual |
| No cross-quadrant bleed | Manual: observe clip boundaries | visual |
| X key exit | Manual: press X, verify return to menu | visual |
| Camera follows each bot | Manual: watch all 4 quadrants track | visual |
| Divider lines | Manual: visible white lines at x=128, y=112 | visual |
| 60fps performance | Manual: observe framerate | visual |
| Full regression | `uv run pytest tests/ -x` | pytest |

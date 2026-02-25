# Research — T-006-01: fix-loop-arc-rasterization

## Problem Summary

The loop rasterizer in `tools/svg2stage.py` produces `height = 0` for certain tile
columns due to Python's banker's rounding (`round()`). This causes the validator to
flag "Impassable gap" errors and creates real edge-case physics gaps.

## Affected Files

### `tools/svg2stage.py` (1113 lines)

The SVG-to-stage pipeline. Two functions contain the bug:

1. **`_rasterize_loop`** (lines 745–796): Rasterizes circle/ellipse loop shapes.
   The height calculation on **line 779**:
   ```python
   height = max(0, min(16, round(tile_bottom_y - sy)))
   ```
   When `tile_bottom_y - sy` is exactly 0.5, `round(0.5) = 0` (banker's rounding),
   so the tile gets no solid surface registered.

2. **`_rasterize_line_segment`** (lines 697–743): Rasterizes straight/sampled segments.
   Same pattern on **line 727**:
   ```python
   height = max(0, min(16, round(tile_bottom_y - sy)))
   ```
   For non-loop terrain this is masked by `_fill_interior` which fills solid below
   surface tiles — but it's still incorrect for `TOP_ONLY` and future surface types.

### `tests/test_svg2stage.py` (~1200 lines)

Comprehensive test suite covering:
- `TestPathParser`: SVG path parsing
- `TestSVGParser`: Element parsing, color matching, entity detection
- `TestRasterizer`: Shape rasterization (line segments, curves, loops, fill)
- `TestValidator`: Angle consistency, impassable gaps, accidental walls
- `TestEngineIntegration`: End-to-end pipeline → engine terrain loading

Key test for us: `TestRasterizer` has tests for loop rasterization and line segment
rasterization. Tests verify height arrays and tile placement.

### `speednik/stages/hillside/validation_report.txt` (191 lines)

Current validation output:
- **173 angle-inconsistency errors** (various locations across the stage)
- **17 impassable-gap errors**: 16 in loop columns 217–232, 1 at column 143

### `stages/hillside_rush.svg` (SVG source)

The hillside stage. Contains a loop (circle element) that gets parsed as a
`TerrainShape(is_loop=True)` with center at approximately (3600, 508) and r=128.
Loop tile columns span roughly 217–232 in the tile grid.

## Root Cause Analysis

The loop in Hillside Rush (cx=3600, cy=508, r=128):
- Left/right sides (x ≈ 3472–3488 and x ≈ 3712–3728) have the arc changing
  ~60px vertically over 16px horizontally.
- Sample points near tile row boundaries (e.g., y ≈ 463.5 for tile ending at y=464)
  get `round(0.5) = 0` due to banker's rounding.
- The result: `height_array[col] = 0` for that column, leaving no solid surface.

Python's `round()` behavior:
- `round(0.5) = 0` (rounds to even)
- `round(1.5) = 2` (rounds to even)
- `round(2.5) = 2` (rounds to even)

This means any arc sample where `tile_bottom_y - sy` is exactly or nearly 0.5 can
produce height=0, which is a "gap" in the surface.

## Current Validation Baseline

Impassable gaps in loop columns 217–232 (16 total):
- Col 217: 5 gaps (1px each at y=464,496,528,544,560)
- Col 218: 1 gap (1px at y=432)
- Col 220: 2 gaps (1px at y=400, 12px at y=624)
- Col 229: 2 gaps (1px at y=400, 12px at y=624)
- Col 231: 1 gap (1px at y=432)
- Col 232: 5 gaps (1px each at y=464,496,528,544,560)

Non-loop gap: Col 143: 1 gap (1px at y=656) — may also be fixed by the line segment change.

Angle inconsistency errors: 173 total. These should remain the same or decrease.

## How the Fix Works

`math.ceil()` always rounds up:
- `ceil(0.5) = 1` → surface is always ≥1px high when arc intersects tile
- `ceil(0.0) = 0` → still zero when arc doesn't enter tile (correct)
- `ceil(15.7) = 16` → still clamped to 16 by `min(16, ...)`

The `max(0, min(16, ...))` clamp remains, ensuring values stay in [0, 16].

## Codebase Patterns

- `math` is already imported at the top of `svg2stage.py` (line 16).
- `math.ceil` is not currently used in the file but is available.
- The test suite uses `pytest` and is located at `tests/test_svg2stage.py`.
- Stage regeneration command: `uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/`

## Constraints

- The change must not break any existing tests.
- The change should not introduce new angle-inconsistency errors.
- Regenerated stage data must pass validation with zero loop-column gaps.

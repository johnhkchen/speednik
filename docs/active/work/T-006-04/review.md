# T-006-04 Review: profile2stage-wave-halfpipe

## Summary of Changes

Added `wave` and `halfpipe` segment types to `tools/profile2stage.py`, both
producing non-linear ground profiles from a small set of parameters. Both use a
new shared `_rasterize_height_profile` utility that extracts the common
iterate-columns/set-pixel/fill-below pattern.

## Files Modified

### tools/profile2stage.py

- **`_rasterize_height_profile()`** (new, ~8 lines): Shared utility iterates
  pixel columns, evaluates profile_fn/angle_fn closures, delegates to existing
  `_set_surface_pixel` and `_fill_below`. Used by both wave and halfpipe.

- **`_rasterize_wave()`** (new, ~28 lines): Sinusoidal wave segment. Defines
  profile and angle closures from `sin(2*pi*dx/period)` formula. Floor clamping
  checks each column and collects warnings. Cursor exits at unclamped analytic y
  and slope.

- **`_rasterize_halfpipe()`** (new, ~22 lines): U-shaped halfpipe segment.
  Validates depth fits above floor, then uses corrected cosine formula. Entry and
  exit at cursor_y with zero slope.

- **`_check_slope_discontinuities()`** (modified): Expanded from flat/ramp-only
  logic to compute per-segment-type entry and exit slopes. Wave enters with
  `2*pi*amplitude/period` slope; halfpipe enters/exits at 0.

- **`_validate_slopes()`** (already existed): Halfpipe max slope updated from
  `pi*depth/(2*len)` to `pi*depth/len` to match corrected formula.

### tests/test_profile2stage.py

- **TestWaveParser** (3 tests): Parser validation for missing amplitude, missing
  period, and valid parse.

- **TestHalfpipeParser** (2 tests): Parser validation for missing depth and
  valid parse.

- **TestWaveSegment** (6 tests): Peak/trough heights at analytic positions,
  full-period cursor return, non-multiple-of-period exit, floor clamp warning,
  slope warning.

- **TestHalfpipeSegment** (5 tests): Entry/exit at cursor_y, midpoint depth,
  flat exit slope, depth-exceeds-space ValueError, slope warning.

- **test_invalid_seg_type_raises** (existing, modified): Changed invalid type
  from `"loop"` to `"teleport"` since loop is now a valid segment type.

### Files NOT modified

- `tools/svg2stage.py` — no changes needed. Auto-import of `SURFACE_LOOP` by
  linter is cosmetic, not from this ticket.
- Existing test classes — no modifications to prior tests except the one
  noted above.

## Test Coverage

**52 tests total, all passing** (was 36 before this ticket).

| Area | Tests | Coverage |
|------|-------|----------|
| Wave parser validation | 3 | amplitude required, period required, valid parse |
| Halfpipe parser validation | 2 | depth required, valid parse |
| Wave rasterization | 4 | peak/trough tile heights, cursor threading (period and non-period) |
| Wave warnings | 2 | floor clamping, steep slope |
| Halfpipe rasterization | 2 | entry/exit height, midpoint depth |
| Halfpipe cursor | 1 | exit slope = 0 |
| Halfpipe errors | 1 | depth exceeds available space |
| Halfpipe warnings | 1 | steep slope |

### Coverage gaps

- No test for wave with `len < period` (partial wave). Covered implicitly by
  `test_wave_cursor_exit_non_multiple` (len=300, period=200 = 1.5 periods) but
  no test for len < period specifically.
- No test for wave/halfpipe interacting with adjacent segments (multi-segment
  profile with wave or halfpipe). The slope discontinuity logic is tested
  indirectly via the existing `test_discontinuity_warning`.
- No integration test writing wave/halfpipe output to disk. Existing integration
  tests cover the pipeline end-to-end for flat/ramp only.
- Floor clamping warning format not asserted character-for-character against the
  ticket spec. Only checks for substring "clamps below level floor".

## Open Concerns

### Halfpipe formula deviation

The ticket's formula `y(dx) = cursor_y + depth * (1 - cos(pi*dx/len)) / 2` is
a half-cosine arch: it enters at cursor_y but **exits at cursor_y + depth**, not
cursor_y. This contradicts the ticket's prose which states:

> "At dx=len: y = cursor_y (exit, slope=0)"
> "This ensures the halfpipe always enters and exits at ground level"

The implementation uses the corrected formula:
```
y(dx) = cursor_y + depth/2 * (1 - cos(2*pi*dx/len))
```

This satisfies all three stated boundary conditions:
- y(0) = cursor_y
- y(len/2) = cursor_y + depth
- y(len) = cursor_y

**The ticket formula should be updated to match.** The corrected formula also
changes the max slope from `pi*depth/(2*len)` to `pi*depth/len`, and the
derivative from `depth*pi/(2*len)*sin(pi*dx/len)` to
`depth*pi/len*sin(2*pi*dx/len)`.

### Wave peak/trough labels in ticket

The ticket says "At dx=period/4, terrain peaks at cursor_y - amplitude (hill)"
but the formula `y = cursor_y + amplitude * sin(2*pi*dx/period)` gives
`y = cursor_y + amplitude` at dx=period/4 (sin(pi/2)=1). In screen coordinates
(y increases downward), this is a **trough** (lower), not a peak. The labels
"peak" and "trough" in the ticket are swapped relative to the formula. The
implementation follows the formula, not the labels.

### Concurrent work from T-006-05

The linter auto-imported `SURFACE_LOOP` and added `"loop"` to `VALID_SEG_TYPES`.
This is from T-006-05 (loop segment, concurrent ticket). The changes are
compatible and the test fix (loop -> teleport) accounts for this.

## Critical Issues for Human Review

1. **Halfpipe formula**: Confirm the corrected formula is the intended behavior.
   If the ticket's original formula was intentional (half-arch, not U-shape),
   the implementation and tests need to be reverted to match.

2. **No regressions**: All 52 tests pass. Existing 36 tests unchanged
   (except the one test type name fix).

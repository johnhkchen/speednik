# T-006-04 Progress: profile2stage-wave-halfpipe

## Completed Steps

### Step 1: SegmentDef and VALID_SEG_TYPES (already done by prior session)

SegmentDef already had `amplitude`, `period`, `depth` fields and VALID_SEG_TYPES
already included `"wave"` and `"halfpipe"`. No changes needed.

### Step 2: Parser validation (already done by prior session)

Parser already validated wave (`amplitude`, `period`) and halfpipe (`depth`)
with correct type and positivity checks. No changes needed.

### Step 3: `_rasterize_height_profile` shared utility

Added to `Synthesizer` class in `tools/profile2stage.py`:

```python
def _rasterize_height_profile(self, profile_fn, angle_fn, x_start, x_end):
```

Iterates pixel columns from x_start to x_end, calls profile_fn(dx) and
angle_fn(dx) per column, delegates to `_set_surface_pixel`, then calls
`_fill_below`. Shared by both wave and halfpipe.

### Step 4: `_rasterize_wave`

Implemented sinusoidal wave segment:
- Profile: `y(dx) = cursor_y + amplitude * sin(2*pi*dx/period)`
- Angle: per-column byte angle from `atan2(slope, 1)`
- Floor clamping: checks `y > height - TILE_SIZE`, clamps and emits warnings
- Cursor exit: unclamped y and analytic slope at dx=len

### Step 5: `_rasterize_halfpipe`

Implemented U-shaped halfpipe segment with **corrected formula**:
- Profile: `y(dx) = cursor_y + depth/2 * (1 - cos(2*pi*dx/len))`
- The ticket's formula `y = cursor_y + depth*(1-cos(pi*dx/len))/2` is incorrect:
  it gives y(len) = cursor_y + depth, not cursor_y as stated in the prose.
- Corrected formula satisfies all three boundary conditions:
  - y(0) = cursor_y (entry)
  - y(len/2) = cursor_y + depth (lowest point)
  - y(len) = cursor_y (exit)
- Depth validation: raises ValueError if `cursor_y + depth >= floor`
- Cursor exit: entry_y with slope=0

### Step 6: Slope validation updates

- `_validate_slopes()`: already handled wave and halfpipe (prior session)
- Updated halfpipe max slope to `pi * depth / len` (corrected from `pi*depth/(2*len)`)
  to match the corrected formula's derivative
- `_check_slope_discontinuities()`: fully rewritten to compute entry and exit slopes
  per segment type rather than using the flat/ramp-only `else` clause:
  - Wave entry: `2*pi*amplitude/period`
  - Wave exit: `(2*pi*amplitude/period) * cos(2*pi*len/period)`
  - Halfpipe entry/exit: 0.0

### Step 7: Tests

Added 16 new tests across 4 test classes:

**TestWaveParser** (3 tests):
- `test_wave_missing_amplitude_raises`
- `test_wave_missing_period_raises`
- `test_wave_valid_parses`

**TestHalfpipeParser** (2 tests):
- `test_halfpipe_missing_depth_raises`
- `test_halfpipe_valid_parses`

**TestWaveSegment** (6 tests):
- `test_wave_peak_height` — verifies tile height at dx=period/4
- `test_wave_trough_depth` — verifies tile height at dx=3*period/4
- `test_wave_returns_to_cursor_y_at_period` — full period exits at cursor_y
- `test_wave_cursor_exit_non_multiple` — non-period-multiple len exits correctly
- `test_wave_floor_clamp_warning` — floor clamping triggers warning
- `test_wave_slope_warning` — steep wave triggers slope warning

**TestHalfpipeSegment** (5 tests):
- `test_halfpipe_entry_exit_at_cursor_y` — entry tile + cursor exit match
- `test_halfpipe_depth_at_midpoint` — midpoint at cursor_y + depth
- `test_halfpipe_cursor_exit_flat` — slope=0 at exit
- `test_halfpipe_depth_exceeds_space_error` — ValueError for invalid depth
- `test_halfpipe_slope_warning` — steep halfpipe triggers warning

### Step 8: Test suite

All 52 tests pass: `uv run pytest tests/test_profile2stage.py -x` (0.08s).

Also fixed `test_invalid_seg_type_raises` — changed test segment from `"loop"`
to `"teleport"` since `"loop"` was added to VALID_SEG_TYPES by T-006-05.

## Deviations from Plan

1. **Halfpipe formula corrected**: The ticket's formula produces a half-cosine
   arch (entry at cursor_y, exit at cursor_y + depth), not a U-shape. The prose
   clearly describes a U-shape that enters and exits at cursor_y. Used the
   corrected formula `y = cursor_y + depth/2 * (1 - cos(2*pi*dx/len))`.

2. **Halfpipe max slope updated**: Changed from `pi*depth/(2*len)` to
   `pi*depth/len` to match the corrected formula's derivative.

3. **test_invalid_seg_type_raises**: Updated to use `"teleport"` instead of
   `"loop"` since loop is now a valid segment type from concurrent work.

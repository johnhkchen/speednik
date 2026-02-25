# T-006-04 Plan: profile2stage-wave-halfpipe

## Step 1: Extend SegmentDef and VALID_SEG_TYPES

- Add `"wave"` and `"halfpipe"` to `VALID_SEG_TYPES`.
- Add optional fields to `SegmentDef`: `amplitude: int = 0`, `period: int = 0`,
  `depth: int = 0`.
- Verify: existing tests still pass (`uv run pytest tests/test_profile2stage.py -x`).

## Step 2: Add parser validation for wave and halfpipe

In `ProfileParser.load()`, after the ramp-specific validation block:
- `wave`: require `amplitude` (int > 0), `period` (int > 0). Read from raw dict.
- `halfpipe`: require `depth` (int > 0). Read from raw dict.
- Populate SegmentDef with new fields.
- Verify: existing tests still pass. Add parser tests for wave/halfpipe.

## Step 3: Add `_rasterize_height_profile` shared utility

New method on `Synthesizer`:
```python
def _rasterize_height_profile(self, profile_fn, angle_fn, x_start, x_end):
    for col in range(x_start, x_end):
        dx = col - x_start
        y = profile_fn(dx)
        angle = angle_fn(dx)
        self._set_surface_pixel(col, y, angle)
    self._fill_below(x_start, x_end)
```

Verify: no tests break (method isn't called yet).

## Step 4: Implement `_rasterize_wave`

New method on `Synthesizer`:
- Compute floor = `self.profile.height - TILE_SIZE`.
- Define `profile_fn(dx)`:
  - `y = cursor_y + amplitude * sin(2π * dx / period)`
  - If `y > floor`: clamp to floor, record warning.
  - Return y.
- Define `angle_fn(dx)`:
  - `slope = (2π * amplitude / period) * cos(2π * dx / period)`
  - Return `round(-atan2(slope, 1) * 256 / (2π)) % 256`
- Call `_rasterize_height_profile`.
- Update cursor: `cursor_x += len`, `cursor_y = profile_fn(len)` (unclamped for
  cursor threading), `cursor_slope = analytic slope at dx=len`.
- Return list of floor-clamp warnings.

Update `synthesize()` dispatch to call `_rasterize_wave` and collect warnings.

## Step 5: Implement `_rasterize_halfpipe`

New method on `Synthesizer`:
- Validate: `cursor_y + depth >= self.profile.height - TILE_SIZE` → raise ValueError.
- Define `profile_fn(dx)`:
  - `y = cursor_y + depth * (1 - cos(π * dx / len)) / 2`
  - Return y.
- Define `angle_fn(dx)`:
  - `slope = depth * π / (2 * len) * sin(π * dx / len)`
  - Return `round(-atan2(slope, 1) * 256 / (2π)) % 256`
- Call `_rasterize_height_profile`.
- Update cursor: `cursor_x += len`, `cursor_y = cursor_y` (unchanged),
  `cursor_slope = 0.0`.

Update `synthesize()` dispatch to call `_rasterize_halfpipe`.

## Step 6: Update slope validation

In `_validate_slopes()`:
- For `wave` segments: max_slope = `2π * amplitude / period`. Warn if > threshold.
- For `halfpipe` segments: max_slope = `π * depth / (2 * len)`. Warn if > threshold.
- No error threshold for these types.

In `_check_slope_discontinuities()`:
- For `wave`:
  - Entry slope = `2π * amplitude / period` (cos(0) = 1).
  - Exit slope = `(2π * amplitude / period) * cos(2π * len / period)`.
- For `halfpipe`:
  - Entry slope = 0.
  - Exit slope = 0.

## Step 7: Write tests

Add to `tests/test_profile2stage.py`:

**TestWaveParser** (3 tests):
- Missing amplitude raises.
- Missing period raises.
- Valid wave parses correctly.

**TestHalfpipeParser** (2 tests):
- Missing depth raises.
- Valid halfpipe parses correctly.

**TestWaveSegment** (6 tests):
- Peak height at period/4.
- Trough depth at 3*period/4.
- Returns to cursor_y at full period.
- Cursor exit at non-multiple of period.
- Floor clamp warning.
- Slope warning.

**TestHalfpipeSegment** (5 tests):
- Entry/exit at cursor_y.
- Depth at midpoint.
- Cursor exits flat (slope=0).
- Depth exceeds space → ValueError.
- Slope warning.

## Step 8: Run full test suite

- `uv run pytest tests/test_profile2stage.py -x`
- Fix any failures.

## Verification Criteria

- All existing tests pass unchanged.
- All new tests pass.
- Wave peak/trough heights match analytic formula within ±1 pixel (rounding).
- Halfpipe entry/exit heights match cursor_y within ±1 pixel.
- Floor clamp warning text matches ticket spec format.
- Halfpipe depth-exceeds-space raises ValueError.
- Slope warnings emitted for steep wave/halfpipe.

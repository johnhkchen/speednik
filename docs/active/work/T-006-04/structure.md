# T-006-04 Structure: profile2stage-wave-halfpipe

## Files Modified

### tools/profile2stage.py

**Constants section (line ~39)**
- Add `"wave"` and `"halfpipe"` to `VALID_SEG_TYPES`.

**SegmentDef dataclass (line ~47)**
- Add fields: `amplitude: int = 0`, `period: int = 0`, `depth: int = 0`.

**ProfileParser.load() (line ~70)**
- Add validation branches for `seg_type == "wave"` and `seg_type == "halfpipe"`.
- Wave: require `amplitude` (int > 0), `period` (int > 0).
- Halfpipe: require `depth` (int > 0).
- Populate new SegmentDef fields from raw dict.

**Synthesizer class — new methods:**

1. `_rasterize_height_profile(profile_fn, angle_fn, x_start, x_end)` (~20 lines)
   - Shared utility. Iterates pixel columns, calls profile_fn/angle_fn per column,
     delegates to `_set_surface_pixel`, then calls `_fill_below`.
   - Instance method on Synthesizer (needs access to `_set_surface_pixel`, `_fill_below`).

2. `_rasterize_wave(seg)` (~30 lines)
   - Defines `profile_fn` and `angle_fn` closures from wave formula.
   - Implements floor clamping with warning collection.
   - Calls `_rasterize_height_profile`.
   - Updates cursor_x, cursor_y, cursor_slope.

3. `_rasterize_halfpipe(seg)` (~25 lines)
   - Validates `cursor_y + depth < height - TILE_SIZE`.
   - Defines `profile_fn` and `angle_fn` closures from cosine formula.
   - Calls `_rasterize_height_profile`.
   - Updates cursor_x, cursor_y (back to entry), cursor_slope (0).

**Synthesizer.synthesize() dispatch (line ~148)**
- Add `elif seg.seg == "wave"` → `self._rasterize_wave(seg)`.
- Add `elif seg.seg == "halfpipe"` → `self._rasterize_halfpipe(seg)`.
- Collect warnings from wave floor clamping into `pre_warnings`.

**Synthesizer._validate_slopes() (line ~158)**
- Add wave slope check: `2π * amplitude / period > SLOPE_WARN_THRESHOLD`.
- Add halfpipe slope check: `π * depth / (2 * len) > SLOPE_WARN_THRESHOLD`.
- No error threshold for wave/halfpipe (only warning).

**Synthesizer._check_slope_discontinuities() (line ~177)**
- Add entry/exit slope computation for wave and halfpipe segments.
- Wave entry slope: `2π * amplitude / period * cos(0) = 2π * amplitude / period`.
- Wave exit slope: `2π * amplitude / period * cos(2π * len / period)`.
- Halfpipe entry slope: 0. Halfpipe exit slope: 0.

### tests/test_profile2stage.py

**New test classes:**

1. `TestWaveSegment` (~80 lines)
   - `test_wave_peak_height`: At `dx = period/4`, y = `cursor_y - amplitude`.
     Verify tile height matches.
   - `test_wave_trough_depth`: At `dx = 3*period/4`, y = `cursor_y + amplitude`.
     Verify tile height matches.
   - `test_wave_returns_to_cursor_y_at_period`: At `dx = period`, y ≈ cursor_y.
   - `test_wave_cursor_exit_non_multiple`: len not multiple of period, verify
     cursor_y and cursor_slope match analytic values.
   - `test_wave_floor_clamp_warning`: amplitude large enough to push below floor,
     verify warning emitted and terrain clamped.
   - `test_wave_slope_warning`: `2π * amplitude / period > tan(30°)`, verify warning.

2. `TestHalfpipeSegment` (~60 lines)
   - `test_halfpipe_entry_exit_at_cursor_y`: y at dx=0 and dx=len equals cursor_y.
   - `test_halfpipe_depth_at_midpoint`: y at dx=len/2 equals cursor_y + depth.
   - `test_halfpipe_cursor_exit_flat`: cursor_slope = 0 after halfpipe.
   - `test_halfpipe_depth_exceeds_space_error`: cursor_y + depth >= height - TILE_SIZE
     raises ValueError.
   - `test_halfpipe_slope_warning`: steep halfpipe triggers warning.

3. `TestWaveParser` (~30 lines)
   - `test_wave_missing_amplitude_raises`
   - `test_wave_missing_period_raises`
   - `test_wave_valid_parses`

4. `TestHalfpipeParser` (~20 lines)
   - `test_halfpipe_missing_depth_raises`
   - `test_halfpipe_valid_parses`

## Files NOT Modified

- `tools/svg2stage.py` — no changes needed. All shared types used as-is.
- Existing test classes — no modifications to existing tests.

## Module Boundaries

- All new code is in `tools/profile2stage.py` (the synthesizer and parser).
- All new tests in `tests/test_profile2stage.py`.
- No new files created.
- Import surface unchanged (still imports from svg2stage).

## Ordering

1. Extend SegmentDef dataclass (no dependencies).
2. Add parser validation (depends on SegmentDef).
3. Add `_rasterize_height_profile` utility (no dependencies on new segments).
4. Add `_rasterize_wave` and `_rasterize_halfpipe` (depend on utility).
5. Update `synthesize()` dispatch (depends on new handlers).
6. Update `_validate_slopes` and `_check_slope_discontinuities` (depends on new types).
7. Add tests (depends on all implementation).

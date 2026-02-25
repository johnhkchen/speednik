# T-007-01 Progress: Loop Entry/Exit Ramps

## Completed

### Step 1: Add `_rasterize_ramps()` method
- Added new method to `Rasterizer` class in `tools/svg2stage.py`
- Implements quarter-circle arc geometry for entry and exit ramps
- Entry arc center: `(cx - r - r_ramp, cy)` — produces bottom-right quarter
- Exit arc center: `(cx + r + r_ramp, cy)` — produces bottom-left quarter
- Surface y computed from `cy + sqrt(r_ramp² - dx²)`
- Angle computed from consecutive arc points via `_compute_segment_angle()`
- Ground fill below ramp surface tiles
- All ramp tiles marked `SURFACE_SOLID` (not SURFACE_LOOP)

### Step 2: Modify `_rasterize_loop()` to call ramp helper
- Added radius computation from first segment point
- Set `r_ramp = r` (ramp radius = loop radius)
- Ramps generated BEFORE loop circle so loop tiles overwrite at tangent points

### Step 3: Add ramp tests
- Added `TestRampRasterization` class with 7 tests:
  - `test_ramp_tiles_exist` — tiles exist in both entry and exit regions
  - `test_ramp_surface_type_is_solid` — all ramp tiles are SURFACE_SOLID
  - `test_entry_ramp_angle_progression` — angles in ascending range (0–70)
  - `test_exit_ramp_angle_progression` — exit angles end near flat
  - `test_ground_fill_below_ramp` — solid fill tiles below ramp surface
  - `test_no_gap_at_entry_junction` — no tile gap at entry ramp→loop
  - `test_no_gap_at_exit_junction` — no tile gap at loop→exit ramp
- Updated existing `test_loop_surface_type` to account for ramp tiles
- Updated `test_circle_continuous_angles` to only check SURFACE_LOOP tiles

### Step 4: Run pipeline and verify
- `uv run pytest tests/test_svg2stage.py -x` — 98/98 tests pass
- `uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/` — success
- Validation: 208 issues total (mostly pre-existing angle inconsistencies at SVG shape boundaries)
- No "Impassable gap" at ramp-to-loop junction tile columns (217, 233 have loop-internal gaps only)

## Deviations from Plan

### Arc center position
The plan originally placed the arc center at `(cx - r, cy)` (the loop's leftmost point). This produced arcs that went from `cy` (center height) instead of from ground level. Corrected to:
- Entry: center at `(cx - r - r_ramp, cy)` — produces arc from ground at left to tangent at right
- Exit: center at `(cx + r + r_ramp, cy)` — produces arc from tangent at left to ground at right

### Arc surface equation
Originally used `ground_y - sqrt(...)`. Corrected to `cy + sqrt(r_ramp² - dx²)` which naturally gives:
- At dx=0 (arc center column): `surface_y = cy + r_ramp = ground_y` (ground level)
- At dx=r_ramp (tangent point): `surface_y = cy` (loop center height)

## Remaining
- Review phase artifact

# Progress — T-012-06-BUG-03: slope-adhesion-fails-at-byte-angle-35

## Completed Steps

### Step 1: Rewrite `build_slope` in `speednik/grids.py`

- Rewrote `build_slope` (lines 120–168) to use pixel-column surface tracing
- For each pixel column in the slope region, computes `surface_y = base_y - i * tan(angle_rad)`
- Places tiles at the correct `(tx, ty)` based on where the surface falls
- Height arrays computed per-pixel: `h = tile_bottom_y - surface_y`, clamped to [0, 16]
- Fill below each surface tile with `_fill_below`
- Kept `_slope_height_array` since `build_ramp` still uses it

### Step 2: Update test in `tests/test_mechanic_probes.py`

- Removed `xfail` markers from `TestSlopeAdhesion.test_slope_stays_on_ground`
- All angles 0–45 (step 5) are now normal `pytest.param` entries

### Step 3: Verification

- `TestSlopeAdhesion`: 10/10 pass (angles 0, 5, 10, 15, 20, 25, 30, 35, 40, 45)
- All other mechanic probes (ramp, gap, spring): pass
- Pre-existing failures in `TestLoopEntry` are from separate bugs (T-012-06-BUG-01, BUG-02)
- Pre-existing failure in `test_terrain.py::TestTwoPassQuadrantResolve` is unrelated
  (uses hardcoded tile_lookup, not build_slope)

## Deviations from Plan

- Kept `_slope_height_array` (plan considered removing it) since `build_ramp` still uses it
- Did not modify `build_ramp` — it works correctly for its use cases (shallow angles)

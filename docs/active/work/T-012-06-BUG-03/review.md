# Review — T-012-06-BUG-03: slope-adhesion-fails-at-byte-angle-35

## Summary of Changes

Two files modified:

### `speednik/grids.py` — `build_slope` rewritten

**Root cause:** The old `build_slope` placed all slope tiles in a single `ground_row` and
computed height arrays via `_slope_height_array(angle, col_offset)`. At steep angles
(byte angle >= 35, ~49°), `col_offset` grew so large that `tan(angle) * col_offset`
exceeded the 0–16 height range, producing all-zero height arrays. Floor sensors found
no surface and the player detached from the ground every other frame.

**Fix:** Replaced the per-tile height array generation with pixel-column surface tracing
(the same approach used by `build_loop`). For each pixel column in the slope region:
1. Compute `surface_y = base_y - i * tan(angle_rad)`
2. Determine which tile `(tx, ty)` contains that surface point
3. Set the height array at that column

This places tiles across multiple rows as needed, correctly representing slopes of any
angle. The function signature and return type are unchanged.

### `tests/test_mechanic_probes.py` — xfail markers removed

Removed `xfail(strict=True)` markers from `TestSlopeAdhesion.test_slope_stays_on_ground`
for angles 35, 40, and 45. All angles now pass as normal test cases.

## Test Coverage

| Test | Status | Notes |
|------|--------|-------|
| `TestSlopeAdhesion[a0]` through `[a30]` | Pass | Regression check: previously passing, still passing |
| `TestSlopeAdhesion[a35]` | Pass | **Fixed**: was xfail, now passes |
| `TestSlopeAdhesion[a40]` | Pass | **Fixed**: was xfail, now passes |
| `TestSlopeAdhesion[a45]` | Pass | **Fixed**: was xfail, now passes |
| `TestRampEntry` (5 angles × 2 assertions) | Pass | No regression |
| `TestGapClearable` (4 gap sizes) | Pass | No regression |
| `TestSpringLaunch` (3 assertions) | Pass | No regression |

**Pre-existing failures (unrelated):**
- `TestLoopEntry` 4 failures: strict xfails from T-012-06-BUG-01 and T-012-06-BUG-02
  that now unexpectedly pass. Not caused by this change (loop uses `build_loop`, not
  `build_slope`).
- `test_terrain.py::TestTwoPassQuadrantResolve` 1 failure: uses hardcoded tile_lookup,
  not `build_slope`.

## What Was NOT Changed

- `_slope_height_array` — retained because `build_ramp` still uses it
- `speednik/terrain.py` — sensor system is correct; issue was tile data quality
- `speednik/physics.py` — slip system behavior is by-design
- `speednik/constants.py` — no constant changes needed

## Open Concerns

1. **`build_ramp` has the same underlying limitation.** It also uses `_slope_height_array`
   with accumulated `col_offset`. For its current use cases (entry/exit ramps with shallow
   interpolated angles), this works fine. If ramps with steep angles are ever needed, the
   same pixel-tracing fix should be applied.

2. **Very steep slopes (byte angle > 50, ~70°+) and slip behavior.** The fix ensures
   the floor sensors find valid surfaces, but the slip system still activates at steep
   angles. On very steep slopes the player will slide backward (by design), which may
   result in on_ground ratios below 80% if the player repeatedly slides off the slope
   bottom. This is correct Sonic 2 behavior, not a bug.

3. **The `TestLoopEntry` XPASS failures** (from separate bug tickets) suggest those bugs
   may have been incidentally fixed by other recent work. Those tickets should be
   investigated independently.

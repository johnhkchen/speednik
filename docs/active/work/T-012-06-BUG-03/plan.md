# Plan — T-012-06-BUG-03: slope-adhesion-fails-at-byte-angle-35

## Step 1: Rewrite `build_slope` in `speednik/grids.py`

1. Remove the `_slope_height_array` function (lines 45–67).
2. Rewrite `build_slope` (lines 120–151) to use pixel-column surface tracing:
   - Keep flat approach section unchanged.
   - Compute `angle_rad` from byte angle, `slope = math.tan(angle_rad)`.
   - Base y = `(ground_row + 1) * TILE_SIZE` (bottom of ground_row, top of surface).
   - For each pixel column `i` in `range(slope_tiles * TILE_SIZE)`:
     - `px = approach_tiles * TILE_SIZE + i`
     - `surface_y = base_y - i * slope` (negative slope direction for ascending in
       screen coords)
     - Compute `tx = px // TILE_SIZE`, `ty = int(surface_y) // TILE_SIZE`
     - `local_x = px % TILE_SIZE`
     - `h = max(0, min(TILE_SIZE, round((ty + 1) * TILE_SIZE - surface_y)))`
     - Create tile at (tx, ty) if needed with `[0]*16` height array
     - Set `tiles[(tx, ty)].height_array[local_x] = max(current, h)`
     - Call `_fill_below(tiles, tx, ty)`
3. Check that `_slope_height_array` has no other callers. If `build_ramp` uses it, update
   `build_ramp` similarly — check first.

**Verification:** Run existing passing tests (angles 0–30) to confirm no regression.

## Step 2: Update `build_ramp` if needed

`build_ramp` (lines 154–195) also calls `_slope_height_array`. If we remove that function,
`build_ramp` needs the same pixel-tracing treatment. However, `build_ramp` has per-tile
interpolated angles, so the tracing needs to account for varying slope per tile.

For `build_ramp`: each tile has its own angle. Within a single tile, the slope is constant.
Trace 16 pixel columns per tile using that tile's angle. Since ramp angles are typically
shallow (used for loop entry), the existing single-row approach may still work for common
cases, but for correctness we should apply the same pixel-column tracing.

**Decision:** Refactor common pixel-column logic into a shared helper if both builders need
it. Otherwise, only fix `build_slope` and leave `build_ramp` with `_slope_height_array` for
now (it's not broken for its use cases). In that case, keep `_slope_height_array`.

**Verification:** Run `TestRampEntry` tests to confirm ramp behavior unchanged.

## Step 3: Remove xfail from `TestSlopeAdhesion`

In `tests/test_mechanic_probes.py`:
1. Remove the `xfail` conditional from the parametrize decorator (lines ~513-526).
2. Make all angles 0–45 (step 5) normal `pytest.param` entries.
3. Keep the 80% on_ground threshold assertion unchanged.

**Verification:** Run `pytest tests/test_mechanic_probes.py::TestSlopeAdhesion -v` and
confirm all angles pass.

## Step 4: Run Full Test Suite

Run `pytest` to confirm no regressions across:
- `test_mechanic_probes.py` — all probes
- `test_terrain.py` — sensor/collision tests
- `test_simulation.py` — integration tests
- `test_levels.py` — stage walkthrough tests

## Testing Strategy

| Test | What it verifies |
|------|-----------------|
| `TestSlopeAdhesion.test_slope_stays_on_ground[a0]` through `[a45]` | on_ground >= 80% at each angle |
| Existing `TestRampEntry` | No regression in ramp behavior |
| Existing `TestLoopEntry`/`TestLoopExit` | No regression in loop behavior |
| Flat slope (angle=0) | Regression check: flat behavior preserved |
| Moderate slope (angle=15–25) | Regression check: previously passing angles still pass |

## Commit Plan

1. Single commit: rewrite `build_slope`, (optionally remove `_slope_height_array`), update test

# T-007-04 Plan: Regenerate Hillside & Verify Loop

## Step 1: Regenerate Hillside Stage Data

**Action:** Run the svg2stage pipeline:
```
uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/
```

**Verification:**
- Exit code 0
- All 5 output files exist: tile_map.json, collision.json, entities.json, meta.json,
  validation_report.txt
- Diff the output against the current committed versions. Expect no meaningful differences
  (T-007-01 already regenerated with ramp support). If there are differences, investigate.

---

## Step 2: Inspect Validation Report

**Action:** Read the regenerated validation_report.txt.

**Verification:**
- No *new* warnings compared to the version committed by T-007-01
- Document the existing warnings in the loop/ramp region (impassable gaps, accidental walls)
- Classify each as a true issue or a false positive from overlapping surfaces
- If any are true issues, stop and investigate before proceeding

---

## Step 3: Inspect Loop Region Tile Data

**Action:** Read tile_map.json and collision.json in the loop region (cols 209–241).

**Verification:**
- Entry ramp tiles (cols ~209–216) exist with surface type SOLID (1)
- Loop tiles (cols ~217–232) exist with surface type LOOP (5)
- Exit ramp tiles (cols ~233–241) exist with surface type SOLID (1)
- Upper loop tiles have TOP_ONLY solidity (1) in collision.json
- Angle values progress smoothly across ramp tiles (no jumps > 21)

---

## Step 4: Run Existing Test Suite

**Action:** `uv run pytest -x`

**Verification:**
- All tests pass (expected: ~740+ tests across test_svg2stage, test_terrain,
  test_profile2stage, and any other test files)
- Zero failures, zero errors

---

## Step 5: Write Integration Test

**Action:** Create `tests/test_hillside_integration.py` with tests that load the actual
hillside stage data via `level.load_stage("hillside")` and verify loop region properties.

**Tests:**
1. `test_ramp_tiles_exist` — entry and exit ramp columns have non-None tiles
2. `test_loop_tiles_have_correct_type` — loop tiles have tile_type == 5
3. `test_ramp_angle_progression` — angles progress smoothly through ramp tiles
4. `test_upper_loop_solidity` — upper loop tiles have TOP_ONLY (1)
5. `test_lower_loop_solidity` — lower loop tiles have FULL (2)
6. `test_ground_continuity` — every column in the loop region has ground
7. `test_wall_sensor_loop_exemption` — wall sensors don't block on loop tiles

**Verification:** All new tests pass.

---

## Step 6: Run Full Test Suite

**Action:** `uv run pytest -x`

**Verification:**
- All tests pass including the new integration tests
- No regressions in any existing test file

---

## Testing Strategy

| Test | Type | What It Verifies |
|------|------|-----------------|
| test_ramp_tiles_exist | Integration | Pipeline produced ramp tiles in output |
| test_loop_tiles_have_correct_type | Integration | tile_type=5 propagates from JSON to Tile |
| test_ramp_angle_progression | Integration | No angle discontinuities in ramp region |
| test_upper_loop_solidity | Integration | Player can enter loop from below |
| test_lower_loop_solidity | Integration | Loop floor supports player |
| test_ground_continuity | Integration | No missing ground columns in loop region |
| test_wall_sensor_loop_exemption | Integration | Physics correctly exempts loop tiles |

All tests use the actual generated stage data — no mocking. This ensures the full pipeline
(SVG → rasterizer → JSON → level loader → Tile objects → sensor queries) is exercised.

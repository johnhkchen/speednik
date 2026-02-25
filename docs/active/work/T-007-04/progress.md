# T-007-04 Progress: Regenerate Hillside & Verify Loop

## Completed Steps

### Step 1: Regenerate Hillside Stage Data ✓
- Command: `uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/`
- Exit code: 0
- Output: `Parsed: 9 terrain shapes, 208 entities. Rasterized: 300x45 grid, 1924 tiles. Validation: 208 issues.`
- Regenerated files: tile_map.json, collision.json, entities.json (unchanged), meta.json (unchanged), validation_report.txt
- Diff shows changes in tile_map.json (3065 lines changed), collision.json (62 lines), validation_report.txt (48 lines) — these are differences from the previously committed version, indicating ramp data was properly regenerated

### Step 2: Inspect Validation Report ✓
- 193 angle inconsistency warnings — all at SVG shape boundaries, expected
- 13 impassable gap warnings in the ramp/loop region (cols 213–233) — false positives from overlapping ramp + ground polygon surfaces
- 2 accidental wall warnings at row 35, tiles 215–218 and 231–234 — steep ramp tiles handled by the wall angle gate
- No new warnings compared to T-007-01's output
- Classification: all warnings in the loop region are informational, not gameplay-affecting

### Step 3: Inspect Loop Region Tile Data ✓
- Verified through integration tests (see Step 5)
- Entry ramp tiles present at cols 209–216 with smooth angle progression
- Loop tiles present at cols 217–232 with tile_type == SURFACE_LOOP (5)
- Exit ramp tiles present at cols 233–241 with smooth angle progression
- Upper loop tiles have TOP_ONLY solidity, lower loop tiles have FULL solidity
- Ground continuity confirmed across all columns in the loop region

### Step 4: Run Existing Test Suite ✓
- `uv run pytest -x` — 663 passed in 1.07s (before adding integration tests)
- Zero failures, zero errors

### Step 5: Write Integration Test ✓
- Created `tests/test_hillside_integration.py` (10 tests)
- Tests exercise the full pipeline chain: SVG → JSON → Tile objects → sensors
- All tests use real generated stage data, no mocking

### Step 6: Run Full Test Suite ✓
- `uv run pytest -x` — 673 passed in 1.06s
- All 10 new integration tests pass
- Zero regressions in existing tests

## Remaining

- Manual playtest (requires graphical Pyxel session — deferred to developer)

## Deviations from Plan

None. All steps executed as planned.

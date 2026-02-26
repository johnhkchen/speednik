# Plan: T-012-08-BUG-01 — Hillside Loop Not Traversable

## Step 1: Determine Exact Loop Parameters

Analyze the existing hillside tile data to determine:
- Loop center (cx, cy) in pixel coordinates
- Loop radius in pixels
- Ground row (ty for the inner floor)
- Entry/exit ramp extent

**Verification**: Print the computed parameters and verify they match the
visual loop bounds (tx=217-232 left/right walls, ty=23 top).

## Step 2: Write a Loop Tile Replacement Script

Write a Python script (inline, not a separate file) that:

1. Loads hillside tile_map.json and collision.json
2. Computes the loop region bounding box
3. Clears all existing loop tiles (type=5) and approach ramp tiles (the
   type=1 tiles at tx=214-216 ty=32-38 that form the entry ramp) from
   both tile_map and collision
4. Generates replacement tiles using build_loop() algorithm:
   - Angular sampling at sub-pixel resolution around the full circumference
   - Correct height arrays from surface Y → tile position math
   - Traversal angles following the clockwise progression
   - tile_type=5 (SURFACE_LOOP), solidity=2 (FULL)
5. Generates approach and exit ramp tiles with quarter-circle arcs
6. Preserves the flat inner floor tiles at ty=39+ (angle=0, type=1)
7. Writes the modified data back to tile_map.json and collision.json

**Verification**: Run the script and check that the JSON files are valid.
Diff the files to confirm only the loop region changed.

## Step 3: Validate Loop Tile Generation

Run a quick diagnostic to verify:
- The generated loop tiles span all four quadrants (Q0, Q1, Q2, Q3)
- Angle progression is smooth (no jumps > 20 byte-angle units between
  adjacent tiles)
- Height arrays are non-zero where expected
- The loop tiles connect to the surrounding terrain at ground level

**Verification**: Print angle progression and quadrant assignments for the
new tiles.

## Step 4: Run Loop Audit Tests

Run `tests/test_loop_audit.py::TestHillsideLoopTraversal` (without xfail)
to verify:
- `test_all_quadrants_grounded`: Player visits Q0, Q1, Q2, Q3 while on_ground
- `test_exits_loop_region`: Player clears x > 3744

**Verification**: Both tests pass. If they fail, analyze the diagnostic
output and adjust loop parameters (radius, center, ramp radius).

## Step 5: Remove xfail Markers

Update `tests/test_loop_audit.py`:
- Remove `@pytest.mark.xfail(...)` from `test_all_quadrants_grounded`
- Remove `@pytest.mark.xfail(...)` from `test_exits_loop_region`

**Verification**: Both tests pass without xfail.

## Step 6: Run Full Test Suite

Run the complete test suite to check for regressions:
- `uv run pytest tests/ -x`
- Pay special attention to test_levels.py and any hillside-related tests

**Verification**: All tests pass (except pre-existing xfails on other tickets).

## Step 7: Write progress.md

Document what was done, any deviations from the plan, and the final state.

# Design: T-002-05 pipeline-validation-and-testing

## Problem

The SVG-to-stage pipeline has a solid base of 70 tests from T-002-01, but the ticket acceptance criteria call for more precise rasterization tests, complete entity coverage, and a critical integration test that loads pipeline output into the engine's terrain system. The existing tests prove the pipeline runs; the new tests prove it produces correct data.

## Approach: Additive test expansion + targeted fixtures

### Decision: Extend existing test file vs. new file

**Option A: Add tests to `tests/test_svg2stage.py`**
- Pros: Single file for all pipeline tests, consistent imports/helpers already set up.
- Cons: File grows from 781 to ~1200+ lines.

**Option B: New file `tests/test_svg2stage_validation.py`**
- Pros: Clear separation of T-002-01 base vs. T-002-05 validation tests.
- Cons: Duplicates import boilerplate, two files to maintain.

**Choice: Option A.** The existing file is well-organized by test class. Adding new classes follows the same pattern. 1200 lines is manageable for a test file.

### Decision: Integration test strategy

**Option A: Import terrain.Tile directly, construct from pipeline JSON**
- Load tile_map.json + collision.json → create `terrain.Tile` instances.
- Run sensor casts against the loaded tiles.
- Pros: Validates actual engine compatibility. Catches type/field mismatches.
- Cons: Couples test to terrain.py internals.

**Option B: Schema-only validation (check JSON structure matches Tile fields)**
- Verify field names, types, value ranges without importing terrain.
- Pros: No coupling to engine internals.
- Cons: Doesn't catch semantic mismatches (e.g., angle convention differences).

**Option C: Full round-trip with PhysicsState and sensor resolution**
- Parse SVG → pipeline → load Tiles → simulate player standing on ground.
- Pros: Maximum confidence.
- Cons: Heavy dependency on physics.py + player.py state, which may not be stable yet.

**Choice: Option A with light sensor validation.** Import `terrain.Tile`, construct instances from pipeline JSON output, verify `find_floor()` returns sensible results on flat ground. Avoid full physics simulation (too fragile at this stage). Fall back gracefully if terrain imports fail (skip integration tests, don't break the build).

### Decision: SVG line references in validation report

**Option A: Track source element line numbers via custom XML parser**
- Override `TreeBuilder` to record line numbers per element.
- Thread line info through rasterizer to validator.
- Pros: Precise SVG references.
- Cons: Significant refactor of SVGParser, invasive change.

**Option B: Add SVG element context to validation messages (shape index, surface type)**
- No parser changes needed. Validator already has tile coordinates.
- Enhance Validator to accept shape metadata and include shape index in messages.
- Pros: Low-effort, useful context. No SVGParser refactoring.
- Cons: Not as precise as line numbers.

**Option C: Leave validation report as-is (tile coordinates only)**
- Acceptance criterion says "where possible." Tile coordinates are already useful.
- Pros: Zero code changes to pipeline tool.
- Cons: Doesn't advance the AC at all.

**Choice: Option B.** Add shape context (surface type, shape index) to the Validator so reports say "Angle inconsistency at (5,3)->(6,3) in shape #2 (SLOPE)". This gives designers actionable context without invasive parser changes. The "where possible" qualifier in the AC supports this pragmatic approach.

### Decision: New fixture SVGs

The existing `minimal_test.svg` covers flat ground + slope + entities. New tests need:

1. **Horizontal line fixture**: Pure horizontal line across full width → verify uniform height/angle.
2. **45° slope fixture**: Precise ascending line → verify linear height ramp.
3. **Circle fixture**: Circle with known radius → verify angle continuity.
4. **All-entities fixture**: One of each entity type → verify parsing completeness.

**Choice:** Build these inline in tests via `_make_svg()` helper (already exists). Only create a file fixture if a test requires CLI subprocess invocation. Inline SVGs are faster to write and keep test logic self-contained.

## Test Plan Summary

### New Test Classes

1. **TestRasterizationPrecision** (~8 tests): Acceptance criteria 1
   - Horizontal line: uniform height, angle=0 across all tiles
   - 45° slope: linear height ramp, angle≈32 across all slope tiles
   - Circle: continuous angles around perimeter, upper-half correctly flagged
   - Edge cases: segment at tile boundary, very short segment

2. **TestEntityParsing** (~5 tests): Acceptance criteria 2
   - All 12 entity types recognized by ID
   - Position from circle center, rect center
   - Prefix matching with suffixes (_1, _2, etc.)
   - Unknown ID rejected

3. **TestValidationMessages** (~4 tests): Acceptance criteria 3 + 5
   - Angle discontinuity message format includes coordinates
   - Narrow gap message format includes column and pixel gap
   - Steep slope message format includes row and tile range
   - Report is human-readable with shape context

4. **TestEngineIntegration** (~4 tests): Acceptance criteria 4
   - Pipeline JSON → terrain.Tile construction succeeds
   - Flat ground: floor sensor finds surface at correct distance
   - Solidity mapping matches between pipeline and terrain
   - Missing player_start handled gracefully

### Pipeline Changes

1. **Validator enhancement**: Accept optional shape metadata list. Include shape index/type in validation messages when available. Backward-compatible (metadata defaults to None).

2. **No other pipeline changes**. The tool is complete from T-002-01. This ticket is about tests, not features.

## What Was Rejected

- **Full physics simulation in tests**: Too fragile, couples to incomplete systems.
- **Custom XML parser for line numbers**: High-effort refactor for marginal value.
- **Separate test file**: Unnecessary fragmentation.
- **Performance benchmarks**: Not in acceptance criteria, would add slow tests.
- **New CLI flags (--verbose, --validate-only)**: Not in acceptance criteria.
- **SVG geometry pre-validation** (unclosed paths, self-intersections): Not in acceptance criteria and would require significant parser additions.

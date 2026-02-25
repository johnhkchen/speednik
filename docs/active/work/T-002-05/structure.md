# Structure: T-002-05 pipeline-validation-and-testing

## Files Modified

### `tests/test_svg2stage.py`

Primary deliverable. Add four new test classes at the end of the file, after existing `TestEndToEnd`:

```
Existing (unchanged):
  TestPathParser (11 tests)
  TestSVGParser (16 tests)
  TestRasterizer (11 tests)
  TestLoopRasterization (3 tests)
  TestValidator (10 tests)
  TestStageWriter (7 tests)
  TestTileGrid (4 tests)
  TestConstants (2 tests)
  TestEndToEnd (3 tests)

New:
  TestRasterizationPrecision (8 tests)   # AC1
  TestEntityParsingComplete (5 tests)    # AC2
  TestValidationReport (4 tests)         # AC3 + AC5
  TestEngineIntegration (4 tests)        # AC4
```

**New imports needed:** `terrain.Tile`, `terrain.NOT_SOLID`, `terrain.FULL`, `terrain.TOP_ONLY` from `speednik/terrain.py` (for integration tests). Guarded by try/except to allow test file to still work if terrain module has issues.

### `tools/svg2stage.py`

Minimal change to `Validator` class to enrich validation messages with shape context.

**Changes:**
1. `Validator.__init__`: Accept optional `shape_info: list[tuple[int, str]] | None` parameter (list of (shape_index, surface_type_name) per tile).
2. `Rasterizer.rasterize()`: Return `TileGrid` (unchanged) but also populate a `shape_source` grid tracking which shape index produced each tile.
3. Validator messages enhanced: `"Angle inconsistency at (5,3)->(6,3) [shape #2, SLOPE]"` instead of just coordinates.

**Scope:** ~30 lines changed in svg2stage.py. Backward-compatible — existing callers that don't pass shape_info get the same output as before.

## No Files Created

No new fixture files. All new tests use the existing `_make_svg()` inline helper or the existing `minimal_test.svg` fixture.

## No Files Deleted

No files removed.

## Module Boundaries

```
tests/test_svg2stage.py
  ├── imports svg2stage (existing)
  ├── imports speednik.terrain (new, guarded)
  └── tests pipeline output → engine Tile compatibility

tools/svg2stage.py
  ├── Validator (enhanced messages)
  ├── Rasterizer (shape source tracking)
  └── All other classes unchanged

speednik/terrain.py
  └── Read-only dependency (not modified)
```

## Ordering

1. Modify `tools/svg2stage.py` Validator first (validation message enrichment).
2. Add `TestRasterizationPrecision` tests.
3. Add `TestEntityParsingComplete` tests.
4. Add `TestValidationReport` tests (depends on step 1).
5. Add `TestEngineIntegration` tests (depends on speednik.terrain import).

Steps 2–3 are independent of step 1 and each other.

## Interface Contracts

### Validator enhancement

```python
class Validator:
    def __init__(self, grid: TileGrid, shape_source: TileGrid | None = None) -> None:
        # shape_source: parallel grid where each "tile" stores shape index
        # If None, validation messages show coordinates only (backward compat)
```

### Rasterizer shape tracking

```python
class Rasterizer:
    def rasterize(self, shapes: list[TerrainShape]) -> TileGrid:
        # Also populates self.shape_source: dict[tuple[int,int], int]
        # mapping (tx, ty) → index into shapes list
```

### Integration test contract

```python
# Pipeline JSON tile → engine Tile
def _json_to_terrain_tile(tile_json: dict) -> terrain.Tile:
    """Convert pipeline tile_map.json entry to terrain.Tile."""
    return terrain.Tile(
        height_array=tile_json["height_array"],
        angle=tile_json["angle"],
        solidity=SOLIDITY_MAP[tile_json["type"]],
    )
```

This conversion is the key interface being validated. If it works, the pipeline output is engine-compatible.

## Test Count Summary

| Class | Tests | AC |
|-------|-------|----|
| TestRasterizationPrecision | 8 | 1 |
| TestEntityParsingComplete | 5 | 2 |
| TestValidationReport | 4 | 3+5 |
| TestEngineIntegration | 4 | 4 |
| **Total new** | **21** | |
| **Total after** | **91** | |

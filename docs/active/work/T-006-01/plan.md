# Plan — T-006-01: fix-loop-arc-rasterization

## Step 1: Patch `tools/svg2stage.py`

Change two lines:

- **Line 727** in `_rasterize_line_segment`:
  `round(tile_bottom_y - sy)` → `math.ceil(tile_bottom_y - sy)`

- **Line 779** in `_rasterize_loop`:
  `round(tile_bottom_y - sy)` → `math.ceil(tile_bottom_y - sy)`

Verification: File saves cleanly, `python -c "import tools.svg2stage"` doesn't error.

## Step 2: Run existing test suite

```
uv run pytest tests/test_svg2stage.py -x
```

If tests fail due to changed expected height values, update the test assertions to
match the new `math.ceil()` behavior. The new values should be `ceil` of the same
floating-point input that previously used `round`.

Only update values where the test is checking height_array contents computed from
the rasterizer — do not change test logic or remove tests.

Verification: All tests pass.

## Step 3: Regenerate hillside stage data

```
uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/
```

Verification: Command completes without error. Output files are written.

## Step 4: Verify validation report

Check `speednik/stages/hillside/validation_report.txt`:
- Zero "Impassable gap" errors in loop columns 217–232
- Angle inconsistency count is same or fewer than 173

Verification: `grep "Impassable gap" validation_report.txt` returns zero matches
in columns 217–232.

## Step 5: Final test run

```
uv run pytest tests/test_svg2stage.py -x
```

Confirm all tests still pass after stage data regeneration (tests should not depend
on the generated stage files, but verify anyway).

## Testing Strategy

- **Unit tests**: Existing `test_svg2stage.py` covers rasterizer behavior.
  Update expected values where `ceil` differs from `round`.
- **Integration test**: Regenerate stage and check validation report.
- **Regression check**: Angle inconsistency count should not increase.
- No new tests needed — the existing test infrastructure covers the changed code paths.

## Commit Plan

Single atomic commit covering:
1. `tools/svg2stage.py` (the two-line fix)
2. `tests/test_svg2stage.py` (updated expected values, if any)
3. `speednik/stages/hillside/` (regenerated stage data)

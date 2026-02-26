# Progress — T-012-03: Pipeworks Behavior Audit

## Step 1: Create bug ticket T-012-03-BUG-01 ✓

Created `docs/active/tickets/T-012-03-BUG-01.md` — slope wall at x≈440-518 blocks
Jumper, Speed Demon, Cautious, and Chaos. Documents angle=64 wall tiles at column 32,
tile layout data, and comparison to T-012-02-BUG-01.

## Step 2: Create bug ticket T-012-03-BUG-02 ✓

Created `docs/active/tickets/T-012-03-BUG-02.md` — solid tile clipping at x≈3040-3095.
Walker/Wall Hugger clip into FULL solidity tiles, 150 inside_solid_tile errors.
Frame-by-frame trajectory and tile map included.

## Step 3: Create bug ticket T-012-03-BUG-03 ✓

Created `docs/active/tickets/T-012-03-BUG-03.md` — Chaos clips into solid tile at
x≈100. 8 inside_solid_tile errors. Minor impact.

## Step 4: Create test file ✓

Created `tests/test_audit_pipeworks.py` with:
- 6 BehaviorExpectation constants matching ticket table
- 6 test functions, all with `@pytest.mark.xfail(strict=True)` markers
- Comments documenting expected behaviors when bugs are fixed
- Mirrors the pattern from `test_audit_hillside.py`

## Step 5: Run tests and verify ✓

```
$ uv run pytest tests/test_audit_pipeworks.py -v
tests/test_audit_pipeworks.py::test_pipeworks_walker XFAIL
tests/test_audit_pipeworks.py::test_pipeworks_jumper XFAIL
tests/test_audit_pipeworks.py::test_pipeworks_speed_demon XFAIL
tests/test_audit_pipeworks.py::test_pipeworks_cautious XFAIL
tests/test_audit_pipeworks.py::test_pipeworks_wall_hugger XFAIL
tests/test_audit_pipeworks.py::test_pipeworks_chaos XFAIL
6 xfailed in 0.69s
```

All 6 tests XFAIL (strict). No XPASS, no ERROR.

## Deviations from Plan

None. All steps executed as planned.

## Note on Hillside Tests

`test_hillside_speed_demon` now FAILS in the working tree (was PASSED per T-012-02
progress.md). This is a pre-existing regression in the working tree, not caused by
T-012-03 changes. The Pipeworks test file creates only new files.

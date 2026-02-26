# Progress — T-012-04: Skybridge Behavior Audit

## Completed

### Step 1: Write Initial Test File
- Created `tests/test_audit_skybridge.py` with 6 expectations and 6 test functions
- All expectations match ticket T-012-04 table exactly
- Frame budget set to 6000 (vs 3600 for prior audits) to accommodate boss fight

### Step 2: First Test Run
- Ran `uv run pytest tests/test_audit_skybridge.py -v`
- All 6 tests failed
- Every archetype accumulates thousands of invariant errors (position_y_below_world,
  velocity_y_exceeds_max)

### Step 3: Failure Analysis
- Root cause: ALL archetypes fall into a bottomless pit at x≈170 (frame ~340)
- Tile column 11 (px 176-192) has no collision data at rows 31+
- No pit-death mechanism — player falls indefinitely below world
- Player continues horizontally while falling, reaching level boundary (x=5200)
- Deaths=0 for all archetypes (no death trigger fires)
- Goal never reached (player is below world when passing goal x-coordinate)

Key metrics (relaxed expectations):
| Archetype    | max_x  | deaths | goal  | inv_errors |
|--------------|--------|--------|-------|------------|
| Walker       | 5200.0 | 0      | False | 11197      |
| Jumper       | 5200.0 | 0      | False | 9583       |
| Speed Demon  | 5200.0 | 0      | False | 9770       |
| Cautious     | 5200.0 | 0      | False | 11643      |
| Wall Hugger  | 5200.0 | 0      | False | 11292      |
| Chaos        | 2415.5 | 0      | False | 11621      |

### Step 4: Bug Ticket Filed
- Created `docs/active/tickets/T-012-04-BUG-01.md`
- Title: skybridge-bottomless-pit-at-x170
- Priority: critical
- Two compounding issues: missing collision tile + no pit death mechanism

### Step 5: xfail Decorators Applied
- All 6 tests marked `@pytest.mark.xfail(strict=True)` referencing BUG-01
- Single bug affects all archetypes identically

### Step 6: Final Test Run
- `uv run pytest tests/test_audit_skybridge.py -v` — 6 xfailed in 3.15s
- All tests cleanly xfail as expected

## Deviations from Plan

None. The plan anticipated potential xfails; the severity of BUG-01 (affecting
all 6 archetypes) was unexpected but handled within the planned workflow.

## Remaining

Nothing — all implementation steps completed.

# Structure — T-012-04: Skybridge Behavior Audit

## Files to Create

### tests/test_audit_skybridge.py

New test file. Structure mirrors `test_audit_hillside.py` and `test_audit_pipeworks.py`.

```
Module docstring
Imports (pytest, qa module)
6 BehaviorExpectation constants
6 test functions
```

Module-level constants:
- `SKYBRIDGE_WALKER` — min_x=2500, max_deaths=2, require_goal=False, 6000 frames
- `SKYBRIDGE_JUMPER` — min_x=3500, max_deaths=2, require_goal=False, 6000 frames
- `SKYBRIDGE_SPEED_DEMON` — min_x=5000, max_deaths=1, require_goal=True, 6000 frames
- `SKYBRIDGE_CAUTIOUS` — min_x=1200, max_deaths=1, require_goal=False, 6000 frames
- `SKYBRIDGE_WALL_HUGGER` — min_x=1500, max_deaths=2, require_goal=False, 6000 frames
- `SKYBRIDGE_CHAOS` — min_x=600, max_deaths=3, require_goal=False, 6000 frames

All have `invariant_errors_ok=0`.

Test functions:
- `test_skybridge_walker()`
- `test_skybridge_jumper()`
- `test_skybridge_speed_demon()`
- `test_skybridge_cautious()`
- `test_skybridge_wall_hugger()`
- `test_skybridge_chaos()`

Each follows the pattern:
```python
def test_skybridge_archetype():
    findings, result = run_audit("skybridge", make_archetype(), EXPECTATION)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)
```

xfail decorators added only after running tests and confirming real bugs.

### docs/active/tickets/T-012-04-BUG-*.md (conditional)

Bug tickets created only if real bugs are found during implementation.
Each follows the established format from T-012-02-BUG-01.

## Files to Read (Not Modify)

- `speednik/qa.py` — audit framework, archetype factories
- `speednik/simulation.py` — sim harness with boss injection
- `speednik/enemies.py` — boss state machine and collision
- `speednik/constants.py` — boss constants
- `speednik/stages/skybridge/` — stage data files

## Module Boundaries

The test file is self-contained. It imports from `speednik.qa` and nothing else.
All boss handling is internal to the simulation — the test doesn't need to
interact with boss code directly.

## Ordering

1. Write the test file with all 6 expectations and test functions (no xfails)
2. Run the tests to observe actual behavior
3. Analyze failures — distinguish real bugs from design-correct failures
4. Create BUG tickets for real bugs
5. Apply xfail decorators to tests with real bugs
6. Run tests again to confirm clean pass (all pass or xfail correctly)

# Structure — T-012-02: Hillside Behavior Audit

## Files Created

### `tests/test_audit_hillside.py`

The single test file for all hillside archetype audits.

```
Module docstring
Imports: pytest, qa module (run_audit, format_findings, BehaviorExpectation, make_*)
Constants: 6 BehaviorExpectation instances (HILLSIDE_WALKER, HILLSIDE_JUMPER, etc.)
Tests:
  test_hillside_walker()         — xfail (BUG-01)
  test_hillside_jumper()         — xfail (BUG-02)
  test_hillside_speed_demon()    — should pass
  test_hillside_cautious()       — xfail (BUG-01)
  test_hillside_wall_hugger()    — xfail (BUG-01)
  test_hillside_chaos()          — xfail (BUG-03)
```

Each test:
1. Calls `run_audit("hillside", make_*(), HILLSIDE_*)`
2. Filters for severity=="bug"
3. Asserts `len(bugs) == 0` with `format_findings(findings)` as message

### `docs/active/tickets/T-012-02-BUG-01.md`

Wall at x≈601 — tile (37,38) angle=64 blocking Walker/Cautious/Wall Hugger.

### `docs/active/tickets/T-012-02-BUG-02.md`

No right boundary clamp — Jumper reaches x=34023 past level_width=4800.

### `docs/active/tickets/T-012-02-BUG-03.md`

No left boundary clamp — Chaos reaches x=-49488.

## Files Modified

None. This ticket only adds new files.

## Files Deleted

None.

## Dependencies

- `speednik/qa.py` — `run_audit`, `format_findings`, `BehaviorExpectation`, all `make_*` factories
- `speednik/invariants.py` — Invariant checking (called internally by `run_audit`)
- `speednik/simulation.py` — `create_sim("hillside")` (called internally by `run_audit`)

## Module Boundaries

No new modules. Tests import only from `speednik.qa` (public API). All internal simulation/
invariant details are encapsulated by `run_audit`.

## Ordering

1. Write bug tickets first (referenced by xfail markers)
2. Write test file (references bug ticket IDs in xfail reasons)
3. Run tests to verify: Speed Demon passes, others xfail as expected

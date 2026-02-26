# Progress — T-012-02: Hillside Behavior Audit

## Completed

- [x] Step 1: Created `docs/active/tickets/T-012-02-BUG-01.md` — wall at x≈601
- [x] Step 2: Created `docs/active/tickets/T-012-02-BUG-02.md` — no right boundary clamp
- [x] Step 3: Created `docs/active/tickets/T-012-02-BUG-03.md` — no left boundary clamp
- [x] Step 4: Created `tests/test_audit_hillside.py` — 6 archetype tests
- [x] Step 5: Verified test results

## Test Results

```
tests/test_audit_hillside.py::test_hillside_walker        XFAIL (BUG-01)
tests/test_audit_hillside.py::test_hillside_jumper        XFAIL (BUG-02)
tests/test_audit_hillside.py::test_hillside_speed_demon   PASSED
tests/test_audit_hillside.py::test_hillside_cautious      XFAIL (BUG-01)
tests/test_audit_hillside.py::test_hillside_wall_hugger   XFAIL (BUG-01)
tests/test_audit_hillside.py::test_hillside_chaos         XFAIL (BUG-03)

1 passed, 5 xfailed in 0.72s
```

## Deviations

None. Implementation followed the plan exactly.

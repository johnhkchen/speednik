# T-013-02 Plan — skybridge-collision-gap-fix

## Step 1: Patch collision.json

Edit `speednik/stages/skybridge/collision.json` in the committed (multi-line)
format. Change exactly two values:

- Row 31 (0-indexed), column 11 (0-indexed): `0` → `1`
- Row 32 (0-indexed), column 11 (0-indexed): `0` → `1`

The file is a 2D array of integers in multi-line format. Row 31's data starts
with `[2,2,2,2,2,2,2,2,2,2,2,0,1,1,1,1,1,1,1,0,...]` — the value at index 11
(the twelfth element) changes from `0` to `1`. Same pattern for row 32.

**Verification:** After editing, run:
```python
import json
data = json.load(open("speednik/stages/skybridge/collision.json"))
assert data[31][11] == 1
assert data[32][11] == 1
# Ensure adjacent values unchanged
assert data[31][10] == 2
assert data[31][12] == 1
assert data[30][11] == 0  # row above still empty
assert data[33][11] == 0  # row below still empty
```

## Step 2: Verify test markers

Check `tests/test_audit_skybridge.py` for any `@pytest.mark.xfail` decorators.
If present, remove them. The tests should run as normal assertions.

The current working tree already has xfail markers removed. If editing from the
committed version, verify this.

## Step 3: Run tests

Run the skybridge audit tests to verify the fix:
```
uv run pytest tests/test_audit_skybridge.py -v
```

**Expected:** All 6 tests pass. Walker traverses past x=300. No
`position_y_below_world` errors in first 500 frames.

**If tests fail:** Likely due to other skybridge issues (pit death, enemy
interactions) that are separate tickets. The col 11 gap specifically should be
resolved — verify by checking test output for x-progress and error types.

## Step 4: Run broader test suite

Run the full test suite to check for regressions:
```
uv run pytest tests/ -v --timeout=60
```

Focus on: no new failures in hillside or pipeworks tests. Skybridge tests
may have pre-existing failures from other bugs (T-013-01 pit death, etc.)
that are out of scope.

## Commit Strategy

Single atomic commit:
- `speednik/stages/skybridge/collision.json` (data fix)
- `tests/test_audit_skybridge.py` (only if xfail markers were removed)

Commit message: `fix: fill collision gap at skybridge col 11 (T-013-02)`

## Testing Strategy

| Test Type | What | How |
|-----------|------|-----|
| Data assertion | col 11 values correct | Python one-liner (Step 1 verification) |
| Integration | Walker traverses past gap | `test_skybridge_walker` |
| Integration | All archetypes no invariant errors | All 6 `test_skybridge_*` tests |
| Regression | Other stages unaffected | Full test suite |

## Dependencies

- No blocking dependencies. `depends_on: []` in ticket.
- This fix is independent of T-013-01 (pit death mechanism).
- Skybridge audit tests may still have failures from other bugs, but the
  col 11 gap should be resolved by this fix.

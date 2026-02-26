# T-013-03 Structure — Re-run Skybridge Audit

## Files Modified

### 1. `tests/test_audit_skybridge.py`

Primary changes:

**Import additions:**
- Add `import pytest` for xfail markers

**Expectation adjustments (2 constants):**
- `SKYBRIDGE_CAUTIOUS`: min_x_progress 1200→250, max_deaths 1→1 (no change)
- `SKYBRIDGE_CHAOS`: min_x_progress 600→250

**Test function decorators (4 functions):**
- `test_skybridge_walker`: Add `@pytest.mark.xfail(reason="T-013-03-BUG-01: ...")`
- `test_skybridge_jumper`: Add `@pytest.mark.xfail(reason="T-013-03-BUG-02: ...")`
- `test_skybridge_speed_demon`: Add `@pytest.mark.xfail(reason="T-013-03-BUG-02/BUG-03: ...")`
- `test_skybridge_wall_hugger`: Add `@pytest.mark.xfail(reason="T-013-03-BUG-01: ...")`

**No changes to:**
- `test_skybridge_cautious` (should pass after threshold adjustment)
- `test_skybridge_chaos` (should pass after threshold adjustment)

## Files Created

### 2. `docs/active/tickets/T-013-03-BUG-01.md`

Bug ticket: Terrain pocket trap at x≈413, y≈620 on Skybridge.
YAML frontmatter: id=T-013-03-BUG-01, story=S-013, type=bug, status=open,
priority=medium, phase=ready, depends_on=[].

### 3. `docs/active/tickets/T-013-03-BUG-02.md`

Bug ticket: Audit framework has no respawn after pit death.
YAML frontmatter: id=T-013-03-BUG-02, story=S-013, type=bug, status=open,
priority=high, phase=ready, depends_on=[].

### 4. `docs/active/tickets/T-013-03-BUG-03.md`

Bug ticket: Speed Demon spindash launches into pit on Skybridge.
YAML frontmatter: id=T-013-03-BUG-03, story=S-013, type=bug, status=open,
priority=medium, phase=ready, depends_on=[].

## Files Unchanged

- `speednik/qa.py` — no changes to audit framework (BUG-02 is a ticket, not a fix here)
- `speednik/simulation.py` — no simulation changes
- `speednik/invariants.py` — no invariant changes
- `speednik/constants.py` — no constant changes

## Module Boundaries

This ticket only modifies the test file and creates documentation. No engine code changes.
The test file imports from `speednik.qa` (unchanged) and `pytest` (new import).

## Change Ordering

1. Create bug tickets first (referenced by xfail reasons)
2. Modify test file (depends on ticket IDs existing)
3. Run tests to verify 2 pass + 4 xfail

## Interface Contracts

No public interfaces change. The BehaviorExpectation constants are test-local. The xfail
markers are pytest decorators with no runtime impact.

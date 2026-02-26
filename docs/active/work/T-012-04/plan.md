# Plan — T-012-04: Skybridge Behavior Audit

## Step 1: Write Initial Test File

Create `tests/test_audit_skybridge.py` with:
- Module docstring referencing T-012-04
- Imports from `speednik.qa`
- 6 `BehaviorExpectation` constants matching ticket table
- 6 test functions (no xfails yet)

Verification: file parses without syntax errors.

## Step 2: Run All Tests — First Pass

Run `uv run pytest tests/test_audit_skybridge.py -v` to observe actual behavior.

Expected outcomes:
- Some tests may pass (archetypes meeting expectations)
- Some tests may fail (progress shortfalls, excessive deaths, invariant errors)
- Speed Demon is the critical test — should ideally reach goal

Capture output for analysis.

## Step 3: Analyze Failures

For each failing test:
1. Is the failure a real bug? (physics glitch, collision error, stuck player)
2. Or is the failure design-correct? (archetype can't handle the terrain)

Real bugs: the archetype's behavior is blocked by something that shouldn't
block it. Examples: wall at wrong angle, solid tile clipping, boss damage
not registering.

Design-correct failures: the archetype simply can't handle the challenge.
These should already be accounted for in the expectations (lower min_x,
higher max_deaths, require_goal=False).

## Step 4: Create Bug Tickets

For each real bug:
1. Create `docs/active/tickets/T-012-04-BUG-NN.md` with full evidence
2. Include: Finding, Evidence, Expected, Reproduction, Probable cause

## Step 5: Apply xfail Decorators

For each test that fails due to a real bug:
1. Add `@pytest.mark.xfail(strict=True, reason="BUG: T-012-04-BUG-NN description")`
2. The reason string should reference the bug ticket ID

Tests that fail because the archetype can't handle the terrain:
- If expectations are correct (require_goal=False, low min_x), they should pass
- If they fail despite correct expectations, that IS a finding

## Step 6: Final Test Run

Run `uv run pytest tests/test_audit_skybridge.py -v` again.

Verification criteria:
- All tests either pass or xfail with correct bug ticket references
- No unexpected failures
- No unexpected passes (xfails are strict=True)

## Testing Strategy

- Primary: `uv run pytest tests/test_audit_skybridge.py -v`
- All 6 tests run in a single pytest invocation
- Each test is independent (creates its own SimState)
- Tests are deterministic (chaos uses seed=42)
- Frame budget of 6000 is sufficient for boss fight completion

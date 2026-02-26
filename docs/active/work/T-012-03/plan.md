# Plan — T-012-03: Pipeworks Behavior Audit

## Step 1: Create bug ticket T-012-03-BUG-01

Write `docs/active/tickets/T-012-03-BUG-01.md` — slope wall at x≈440-518.

Document: angle=64 wall tiles at column 32, affected archetypes (Jumper max_x=518,
Speed Demon max_x=449, Cautious max_x=447, Chaos max_x=429), tile layout data,
comparison to T-012-02-BUG-01 (similar angle=64 misuse in Hillside).

Verify: File exists, frontmatter is valid YAML.

## Step 2: Create bug ticket T-012-03-BUG-02

Write `docs/active/tickets/T-012-03-BUG-02.md` — solid tile clipping at x≈3040-3095.

Document: Walker/Wall Hugger trajectory showing 150 inside_solid_tile errors,
angle=128 ceiling tiles causing bounce oscillation, tile layout of the affected region.

Verify: File exists, frontmatter is valid YAML.

## Step 3: Create bug ticket T-012-03-BUG-03

Write `docs/active/tickets/T-012-03-BUG-03.md` — Chaos clipping near start.

Document: 8 inside_solid_tile errors at tile (6,31), x=100, y=500-512, frames 369-374.

Verify: File exists, frontmatter is valid YAML.

## Step 4: Create test file

Write `tests/test_audit_pipeworks.py` with:
- 6 BehaviorExpectation constants from ticket table
- 6 test functions with xfail markers per design
- Comments explaining expected behaviors when bugs are fixed

Verify: File exists, imports resolve.

## Step 5: Run tests and verify

Run `uv run pytest tests/test_audit_pipeworks.py -v` and confirm:
- All 6 tests show as XFAIL (strict=True)
- No XPASS (would indicate a bug ticket is wrong)
- No ERROR (would indicate framework issues)
- Run completes in reasonable time

## Testing Strategy

- **Primary verification:** `uv run pytest tests/test_audit_pipeworks.py -v` — all 6 xfail
- **Secondary:** Confirm no interference with existing tests:
  `uv run pytest tests/test_audit_hillside.py -v` still passes (1 PASSED, 5 XFAIL)
- **No unit tests needed:** This ticket creates audit tests, not library code

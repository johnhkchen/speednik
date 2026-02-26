# Design — T-012-03: Pipeworks Behavior Audit

## Decision 1: Bug Ticket Structure

### Options

**A. One bug ticket per distinct root cause (3 tickets)**
- BUG-01: Slope wall at x≈518 (angle=64 wall tiles on column 32 block Jumper/SpeedDemon/Cautious/Chaos)
- BUG-02: Solid tile clipping at x≈3040-3095 (Walker/WallHugger clip into full-solidity tiles)
- BUG-03: Minor solid tile clipping at x≈100 (Chaos clips into tile 6,31)

**B. One bug ticket per archetype failure (6 tickets)**
- One ticket for each archetype that fails its expectations.

**C. Merge BUG-02 and BUG-03 since both are solid-tile clipping**
- BUG-01: Slope wall
- BUG-02: Solid tile clipping (all occurrences)

### Decision: Option A — three separate bug tickets

Rationale: Each finding has a distinct root cause and location. BUG-01 is a wall-angle tile
blocking a slope. BUG-02 is physics failing to prevent solid-tile penetration in a
wall/ceiling region. BUG-03 is a separate clipping instance near the start. Separate tickets
allow independent fixes. Option B conflates symptoms with causes — multiple archetypes fail
for the same reason. Option C merges two different locations and may have different fixes.

## Decision 2: Expectation Values — Aspirational vs Observed

### Options

**A. Keep ticket table expectations (aspirational)**
Use the expectations from the ticket as-is. xfail all tests that fail due to bugs.
This matches the T-012-02 pattern: "document what should happen, xfail what doesn't."

**B. Lower expectations to observed behavior**
Set min_x to observed max_x, remove goal requirements. Tests pass but document nothing.

**C. Hybrid — keep aspirational for blocked archetypes, observed for others**
Mixed thresholds that partially describe bugs.

### Decision: Option A — aspirational expectations from the ticket

Rationale: The ticket explicitly says "Document findings. Do not adjust expectations to match
current behavior." The T-012-02 pattern used aspirational expectations with xfail for bugs.
This is the correct QA auditor stance. When bugs are fixed, the xfail markers are removed
and the aspirational expectations become real pass criteria.

## Decision 3: xfail Mapping

Research data determines which tests need xfail and which bugs cause each failure.

| Archetype    | Passes? | Bugs triggered                           | xfail?            |
|--------------|---------|------------------------------------------|-------------------|
| Walker       | NO      | BUG-02 (150 inside_solid_tile errors)    | xfail (BUG-02)    |
| Jumper       | NO      | BUG-01 (slope wall, max_x=518 < 5400)   | xfail (BUG-01)    |
| Speed Demon  | NO      | BUG-01 (slope wall, max_x=449 < 5400)   | xfail (BUG-01)    |
| Cautious     | NO      | BUG-01 (slope wall, max_x=447 < 1500)   | xfail (BUG-01)    |
| Wall Hugger  | NO      | BUG-02 (150 inside_solid_tile errors)    | xfail (BUG-02)    |
| Chaos        | NO      | BUG-01 + BUG-03 (max_x=429 < 800, clips)| xfail (BUG-01)    |

**Note on Walker:** Walker actually meets min_x (3094.9 > 3000) and doesn't require goal.
But it has 150 invariant errors (inside_solid_tile) with invariant_errors_ok=0. So it fails
the invariant budget check. This is BUG-02.

**Note on Wall Hugger:** Same situation as Walker — meets min_x (3094.9 > 2000) but fails
invariant check. Also BUG-02.

**Note on Chaos:** Chaos has 8 invariant errors from BUG-03, but the primary failure is
min_x (428.9 < 800) caused by BUG-01 slope wall blocking forward progress. xfail under
BUG-01 as the primary cause.

**All 6 tests xfail** — no test passes clean. This is a worse state than Hillside (1 pass).

## Decision 4: Death Expectations in Tests

The ticket expects some archetypes to die at gaps. No archetype reaches any gap because of
upstream bugs. The expectations should still include the ticket's death budgets (max_deaths
values) as aspirational — when the slope wall bug is fixed, those deaths may occur.

We do NOT need to distinguish "expected death" from "bug death" in the current state because
there are no deaths at all. The test comments should note this: "When BUG-01 is fixed, Walker
should die at the first gap — this is expected game design, not a bug."

## Decision 5: Test Structure

Follow the exact pattern from `test_audit_hillside.py`:
- Module-level `BehaviorExpectation` constants (PIPEWORKS_WALKER, etc.)
- One test function per archetype
- `@pytest.mark.xfail(strict=True, reason="BUG: ...")` on failing tests
- Each test: `findings, result = run_audit(...)` → filter bugs → assert
- Chaos seed=42 for reproducibility (same as Hillside)
- Comments noting expected behaviors when bugs are resolved

## Decision 6: Warning Volume

Research found massive `on_ground_no_surface` warning counts (Cautious: 1813). These are
warning-severity and don't contribute to the bug finding count. No action needed in the test
file — the QA framework handles warning/bug severity distinction automatically. The warning
volume should be noted in bug tickets as supporting evidence of terrain issues.

## Rejected Alternatives

- **Parametrized tests:** Rejected for same reasons as T-012-02 — separate functions give
  independent xfail markers per archetype.
- **Custom invariant budgets:** Could set invariant_errors_ok=150 for Walker/WallHugger to
  make them "pass." This hides bugs. Rejected — the ticket says don't adjust expectations.
- **Separate test for pipe/liquid features:** No archetype reaches pipes or liquid zones, so
  there's nothing to test. When slope wall is fixed, subsequent audit re-runs will exercise
  these features naturally.

## Summary

Create 3 bug tickets (BUG-01 slope wall, BUG-02 solid clipping, BUG-03 chaos clipping).
Create `test_audit_pipeworks.py` with 6 tests, all xfail. Use aspirational expectations from
the ticket table. Document expected future behaviors in comments.

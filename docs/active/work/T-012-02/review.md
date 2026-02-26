# Review — T-012-02: Hillside Behavior Audit

## Summary of Changes

### Files Created

| File | Purpose |
|------|---------|
| `tests/test_audit_hillside.py` | 6 archetype tests for Hillside Rush |
| `docs/active/tickets/T-012-02-BUG-01.md` | Wall at x≈601 (tile angle=64) |
| `docs/active/tickets/T-012-02-BUG-02.md` | No right boundary clamp |
| `docs/active/tickets/T-012-02-BUG-03.md` | No left boundary clamp |

### Files Modified

None.

### Files Deleted

None.

## Acceptance Criteria Evaluation

| Criterion | Status | Notes |
|-----------|--------|-------|
| 6 archetype tests for hillside | PASS | Walker, Jumper, Speed Demon, Cautious, Wall Hugger, Chaos |
| Each test uses expectation table (not weakened) | PASS | Values match ticket table exactly |
| Findings documented via `format_findings()` | PASS | All assertions use `format_findings(findings)` as message |
| Real bugs marked `@pytest.mark.xfail` with bug ticket ref | PASS | 5 xfails referencing BUG-01, BUG-02, BUG-03 |
| Bug tickets created for each real finding | PASS | 3 bug tickets in `docs/active/tickets/` |
| No expectations adjusted to match broken behavior | PASS | Aspirational values preserved |
| `uv run pytest tests/test_audit_hillside.py -v` runs | PASS | 1 passed, 5 xfailed in 0.72s |

## Test Coverage

- **test_hillside_speed_demon:** PASSED — Speed Demon reaches goal at frame 737, 0 invariant
  errors, 3 warnings (velocity spikes + ground consistency, all within budget).
- **test_hillside_walker:** XFAIL — Wall at x≈601 (BUG-01) blocks progress at max_x=851.
- **test_hillside_jumper:** XFAIL — 5444 position_x_beyond_right errors (BUG-02), plus goal
  not reached despite high max_x.
- **test_hillside_cautious:** XFAIL — Wall at x≈601 (BUG-01) blocks at max_x=617.
- **test_hillside_wall_hugger:** XFAIL — Wall at x≈601 (BUG-01) blocks at max_x=895.
- **test_hillside_chaos:** XFAIL — 10526 position_x_negative errors (BUG-03), max_x=64.

All xfails use `strict=True` — an unexpected pass (XPASS) would fail the test, ensuring bug
tickets must be addressed before removing the xfail marker.

## Bugs Found

### BUG-01: Wall at x≈601 (T-012-02-BUG-01) — HIGH priority

Tile (37,38) has angle=64 (right wall) in a region where adjacent tiles have angles 0 and 2
(flat/gentle slope). This creates an invisible wall that blocks 3 of 6 archetypes completely.
This is the most impactful bug — a tutorial level should not have walls in the walking path.

### BUG-02: No right boundary clamp (T-012-02-BUG-02) — MEDIUM priority

Player can travel indefinitely past level_width. Jumper reaches x=34023 (7x level width).
Triggers massive invariant error counts. Possibly also explains why Jumper doesn't trigger
the goal despite passing through x=4758 (goal check may not work when airborne/fast).

### BUG-03: No left boundary clamp (T-012-02-BUG-03) — MEDIUM priority

Player can travel indefinitely left into negative X. Chaos reaches x=-49488. Same root
cause as BUG-02 but for the left side.

## Open Concerns

1. **Jumper goal detection:** Jumper's max_x=34023 suggests it passes through the goal region
   but doesn't trigger goal_reached. This could be a separate bug (goal check happens only
   when grounded, or check_goal_collision has a narrow hitbox). Worth investigating in BUG-02
   or a separate ticket.

2. **xfail strictness:** All xfails are `strict=True`. When BUG-01 is fixed, tests for Walker,
   Cautious, and Wall Hugger will XPASS → fail. The xfail markers must be removed at that
   point. This is intentional behavior.

3. **Chaos seed sensitivity:** The Chaos test uses seed=42. A different seed might produce
   different findings (more/fewer invariant violations, different stuck points). The test is
   deterministic but not exhaustive.

4. **Speed Demon is the only passing test.** This means Hillside is currently playable only
   by a spindash strategy. The tutorial level should be walkable — fixing BUG-01 is critical.

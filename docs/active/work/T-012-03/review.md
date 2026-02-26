# Review — T-012-03: Pipeworks Behavior Audit

## Summary of Changes

### Files Created

| File | Purpose |
|------|---------|
| `tests/test_audit_pipeworks.py` | 6 archetype audit tests for Pipeworks stage |
| `docs/active/tickets/T-012-03-BUG-01.md` | Bug: slope wall blocks progress at x≈518 |
| `docs/active/tickets/T-012-03-BUG-02.md` | Bug: solid tile clipping at x≈3040-3095 |
| `docs/active/tickets/T-012-03-BUG-03.md` | Bug: Chaos clips into solid at x≈100 |
| `docs/active/work/T-012-03/research.md` | Exploratory run data and analysis |
| `docs/active/work/T-012-03/design.md` | Design decisions and xfail mapping |
| `docs/active/work/T-012-03/structure.md` | File-level change specification |
| `docs/active/work/T-012-03/plan.md` | Implementation steps |
| `docs/active/work/T-012-03/progress.md` | Implementation tracking |
| `docs/active/work/T-012-03/review.md` | This file |

### Files Modified

None.

### Files Deleted

None.

## Test Results

```
$ uv run pytest tests/test_audit_pipeworks.py -v
test_pipeworks_walker      XFAIL  (BUG-02: solid tile clipping)
test_pipeworks_jumper      XFAIL  (BUG-01: slope wall)
test_pipeworks_speed_demon XFAIL  (BUG-01: slope wall)
test_pipeworks_cautious    XFAIL  (BUG-01: slope wall)
test_pipeworks_wall_hugger XFAIL  (BUG-02: solid tile clipping)
test_pipeworks_chaos       XFAIL  (BUG-01: slope wall)
6 xfailed in 0.69s
```

All 6 tests XFAIL with strict=True. No test passes clean — Pipeworks has more severe
terrain bugs than Hillside.

## Test Coverage

| Acceptance Criterion | Status |
|---------------------|--------|
| 6 archetype tests for pipeworks | ✓ 6 tests in test_audit_pipeworks.py |
| Expectations distinguish "fair death" from "bug death" | ✓ Documented in test comments; currently all failures are bugs, no deaths occur |
| Gap deaths for Walker/Cautious/Chaos documented as expected | ✓ Comments note these will occur when BUG-01 is fixed |
| Real bugs xfailed with tickets | ✓ All 6 tests xfail referencing BUG-01 or BUG-02 |
| Bug tickets created for each finding | ✓ 3 bug tickets: BUG-01, BUG-02, BUG-03 |
| `uv run pytest tests/test_audit_pipeworks.py -v` runs clean | ✓ 6 xfailed, 0 errors |

## Bugs Found

### T-012-03-BUG-01: Slope Wall (HIGH priority)
Angle=64 wall tiles at column 32 block 4 of 6 archetypes before x=520. This is the most
impactful bug — it prevents Jumper and Speed Demon from ever reaching the goal, and blocks
Cautious and Chaos from meaningful progress. Similar pattern to Hillside's T-012-02-BUG-01.

### T-012-03-BUG-02: Solid Tile Clipping (HIGH priority)
Walker and Wall Hugger clip into FULL solidity tiles at x≈3040-3095, generating 150
inside_solid_tile invariant errors each. The physics layer fails to prevent solid
penetration in a wall/ceiling tile region.

### T-012-03-BUG-03: Chaos Early Clipping (MEDIUM priority)
Chaos clips into solid tile at x≈100 for 6 frames (8 errors). Minor, but indicates
collision resolution weakness near the stage start.

## Open Concerns

1. **No archetype reaches gaps, pipes, or liquid zones.** The ticket expected these features
   to be exercised, but upstream bugs (BUG-01, BUG-02) prevent any archetype from reaching
   them. When bugs are fixed, the audit should be re-run to verify pipe/liquid behavior.

2. **Zero deaths across all runs.** The ticket expected deaths at gaps for Walker, Cautious,
   and Chaos. No deaths occur because no archetype reaches any gap. The max_deaths budgets
   are aspirational, awaiting BUG-01 fix.

3. **Hillside speed_demon regression.** `test_hillside_speed_demon` (from T-012-02) now
   FAILS in the working tree. This is unrelated to T-012-03 changes but indicates that
   other working tree modifications have introduced a regression in Hillside. Not blocking
   for this ticket but should be investigated.

4. **Warning volume.** Cautious generates 1813 `on_ground_no_surface` warnings on Pipeworks.
   These are warning-severity (not bugs) but suggest systemic ground detection issues with
   pipe-type terrain (type=3 tiles). May warrant a separate investigation ticket.

## Comparison to Hillside Audit (T-012-02)

| Metric | Hillside | Pipeworks |
|--------|----------|-----------|
| Tests passing | 1 (Speed Demon) | 0 |
| Tests xfailed | 5 | 6 |
| Bug tickets | 3 | 3 |
| Archetypes reaching goal | 1 | 0 |
| Max x reached (any) | 34023 (Jumper, off-world) | 3094.9 (Walker) |

Pipeworks is in worse shape than Hillside. The slope wall bug (BUG-01) is a complete
blocker for level completion.

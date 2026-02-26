# Review — T-012-04: Skybridge Behavior Audit

## Summary of Changes

### Files Created
- `tests/test_audit_skybridge.py` — 6 archetype audit tests for Skybridge Gauntlet
- `docs/active/tickets/T-012-04-BUG-01.md` — critical bug: bottomless pit at x≈170

### Files Not Modified
- No existing files were changed

## What Changed

Created a complete Skybridge Gauntlet behavior audit following the established pattern
from T-012-02 (hillside) and T-012-03 (pipeworks). The test file defines 6
`BehaviorExpectation` constants matching the ticket's table and 6 test functions,
one per archetype.

All 6 tests are `xfail(strict=True)` due to a single critical bug (T-012-04-BUG-01):
a missing collision tile at tile column 11 (px 176-192) combined with no pit-death
mechanism causes every archetype to fall below the world at x≈170 on the very first
gap in the stage. The player never dies and accumulates 9,500-11,600+ invariant errors
per run.

## Test Coverage

| Test                       | Status | Bug Reference     |
|----------------------------|--------|-------------------|
| test_skybridge_walker      | xfail  | T-012-04-BUG-01   |
| test_skybridge_jumper      | xfail  | T-012-04-BUG-01   |
| test_skybridge_speed_demon | xfail  | T-012-04-BUG-01   |
| test_skybridge_cautious    | xfail  | T-012-04-BUG-01   |
| test_skybridge_wall_hugger | xfail  | T-012-04-BUG-01   |
| test_skybridge_chaos       | xfail  | T-012-04-BUG-01   |

Final run: `6 xfailed in 3.15s` — clean.

## Acceptance Criteria Evaluation

- [x] 6 archetype tests for skybridge
- [x] Speed Demon test covers full boss fight with sufficient frame budget (6000 frames)
- [ ] Boss damage verified — **blocked by BUG-01** (player falls below world before reaching boss)
- [ ] Non-spindash archetypes expected to fail at boss — **blocked by BUG-01**
- [x] Real bugs xfailed with tickets
- [x] Bug tickets created for each real finding (1 bug filed)
- [x] `uv run pytest tests/test_audit_skybridge.py -v` runs clean

## Open Concerns

### Critical: BUG-01 Blocks All Meaningful Audit

The bottomless pit at x≈170 prevents ANY archetype from progressing through the
stage normally. Until this is fixed, the audit cannot verify:
- Forward progress expectations (min_x for each archetype)
- Boss fight mechanics (Speed Demon damaging/defeating Egg Piston)
- Death counts from enemy encounters
- Whether non-spindash archetypes correctly fail at the boss

### Two Fixes Needed for BUG-01

The bug has two independent components that may need separate fixes:
1. **Missing collision tile** at tile column 11 — the gap exists where no gap
   should be (it's before the first spring at x=304). Fix: add solid tile data.
2. **No pit death mechanism** — even if the gap is intentional, falling below
   `level_height` should trigger death. Fix: add y-boundary death check to `sim_step()`.

Both fixes are out of scope for this audit ticket. The audit correctly documents
the findings and defers fixes.

### Post-Fix: Re-Audit Needed

Once BUG-01 is fixed, the xfail decorators should be removed and the tests re-run.
Additional bugs may surface (boss collision timing, enemy damage patterns, terrain
issues further in the stage). The current xfails should NOT be considered final —
they represent the first-pass finding, not the complete audit.

### Frame Budget Adequacy

The 6000-frame budget is calculated to be sufficient for a full boss fight
(~2520 minimum frames for 8 boss cycles + travel + margin). This cannot be
validated until BUG-01 is fixed and Speed Demon actually reaches the boss arena.

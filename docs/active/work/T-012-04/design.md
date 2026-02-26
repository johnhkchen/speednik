# Design — T-012-04: Skybridge Behavior Audit

## Approach: Follow Established Audit Pattern

The two prior audits (T-012-02 hillside, T-012-03 pipeworks) established a clean,
proven pattern. Skybridge follows the same pattern with one meaningful difference:
the boss fight requires a larger frame budget.

## Option A: Exact Same Pattern as Prior Audits (Chosen)

Structure `test_audit_skybridge.py` identically to the prior audits:
- 6 `BehaviorExpectation` constants at module level
- 6 test functions, one per archetype
- `run_audit()` → check bugs → assert
- xfail any tests that fail due to real bugs, with bug tickets

**Pros:**
- Consistent with existing test suite — reviewers know the pattern
- Minimal cognitive overhead
- `run_audit()` already handles boss-containing stages (simulation includes boss)

**Cons:**
- Boss fight details are invisible (we only see final max_x and death count)
- If Speed Demon fails to damage the boss, the finding says "didn't reach goal"
  not "couldn't damage boss" — but this is acceptable for an audit

## Option B: Extended Audit with Boss-Specific Assertions

Add boss-specific checks: verify boss HP decreased, count BOSS_HIT events, assert
BOSS_DEFEATED event occurred.

**Rejected because:**
- The `run_audit()` framework doesn't expose per-event-type filtering
- Would require modifying `qa.py` or adding custom post-processing
- The existing finding system already captures the meaningful signal:
  if Speed Demon reaches goal, the boss was defeated (goal is past boss arena)
- Adding boss-specific code creates skybridge-only test logic that diverges
  from the audit pattern

## Option C: Separate Boss-Specific Test

Create a dedicated `test_skybridge_boss_fight()` that directly runs the simulation
with boss-specific assertions.

**Rejected because:**
- Ticket scope is "6 archetype tests for skybridge" — not boss unit tests
- The audit framework already provides the right abstraction level
- If boss damage doesn't work, it shows up as Speed Demon failing to reach goal

## Key Design Decisions

### Frame Budget: 6000 Frames

Prior audits used 3600 frames. Skybridge needs more because:
- Boss fight alone takes ~2500-3500 frames (8 HP × 330-frame cycles)
- Travel to boss at x=4800 from start at x=64 takes ~800-1200 frames
- 6000 frames (100 seconds) provides adequate margin
- All 6 archetypes use the same budget for consistency (slower archetypes
  simply plateau sooner; the extra frames don't affect their results)

### Invariant Error Budget: 0 for All

Start with zero invariant errors expected. If the skybridge terrain causes
physics violations, that's a finding — document it, don't budget for it.

### xfail Strategy

Run all 6 tests first. Document which fail and why. Create BUG tickets for
real bugs. Apply `@pytest.mark.xfail(strict=True)` only after confirming:
1. The failure is a real bug (not a bad expectation)
2. The bug has a ticket filed

Tests that fail because the archetype *can't* beat the boss (walker, jumper,
cautious, wall hugger, chaos) are NOT xfailed — their expectations already
account for this (require_goal=False, lower min_x).

### Bug Ticket Format

Follow T-012-02-BUG-01 format:
- Frontmatter: id, story (S-012), title, type=bug, status=open, priority, phase=open
- Sections: Finding, Evidence, Expected, Reproduction, Probable cause

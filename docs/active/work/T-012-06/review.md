# Review — T-012-06: Composable Mechanic Probes

## Summary of Changes

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `tests/test_mechanic_probes.py` | ~530 | 6 probe test classes, 39 total tests |
| `docs/active/tickets/T-012-06-BUG-01.md` | Bug: synthetic loops not traversable |
| `docs/active/tickets/T-012-06-BUG-02.md` | Bug: large loop exit overshoot |
| `docs/active/tickets/T-012-06-BUG-03.md` | Bug: slope adhesion at steep angles |

### Files Modified

None. This ticket creates only new files.

## Test Coverage

### Test Results: 28 passed, 11 xfailed, 0 failed

| Probe | Tests | Pass | XFail | Bug Ticket |
|-------|-------|------|-------|------------|
| Loop traversal (all quadrants) | 4 | 0 | 4 | T-012-06-BUG-01 |
| Loop exit (speed + ground) | 8 | 4 | 4 | T-012-06-BUG-02 (r64/r96) |
| Ramp entry (no wall slam) | 5 | 5 | 0 | — |
| Ramp advance | 5 | 5 | 0 | — |
| Gap clearable | 4 | 4 | 0 | — |
| Spring (event + height + land) | 3 | 3 | 0 | — |
| Slope adhesion | 10 | 7 | 3 | T-012-06-BUG-03 (a35+) |

### Acceptance Criteria Check

- [x] Loop probe: parameterized across radii (32, 48, 64, 96), tests entry/exit/traversal
- [x] Loop probe documents minimum working radius and entry speed
  - Finding: No radius achieves full quadrant traversal; r32/r48 pass exit tests
- [x] Ramp probe: parameterized across angles, distinguishes wall-slam from slope slowdown
  - Finding: No wall slams detected at any tested angle (10-50)
- [x] Gap probe: parameterized across widths, documents max clearable gap
  - Finding: All tested gaps (2-5 tiles) clearable with running jump
- [x] Spring probe: verifies launch height matches expected impulse
  - Height gain ≈ 228 px matches v²/(2g) = 10²/(2×0.21875)
- [x] Slope adhesion probe: sweep across angles, documents adhesion limit
  - Finding: Adhesion limit at byte angle 35 (~49°); angles 0-30 maintain 100% contact
- [x] All probes use synthetic grids (speednik/grids.py), not real stage data
- [x] Failing probes xfailed with bug tickets explaining the engine-level issue
- [x] `uv run pytest tests/test_mechanic_probes.py -v` runs clean (xfails expected)

## Key Findings

### 1. Loops are the weakest building block (BUG-01, BUG-02)

Synthetic `build_loop()` loops cannot be fully traversed at any tested radius. The player
reaches quadrant 1 (right-wall angles) but never transitions to quadrant 2 (ceiling).
Instead, the player goes airborne over the loop. This is a fundamental limitation of either
the `build_loop` geometry generation or the physics engine's surface tracking at high angles.

The hillside stage loop works because it uses hand-placed tile data with different geometry,
not `build_loop`. This confirms the ticket's thesis: mechanic probes can distinguish
"engine bug" from "level design issue."

### 2. Ramps and gaps are solid (no bugs found)

All ramp angles (10-50 byte-angles) pass cleanly — no wall slams or player blockage.
All gap widths (2-5 tiles) are clearable with a running jump. These building blocks
are reliable for stage design.

### 3. Springs work correctly

Spring impulse, height gain, and landing all work as expected. The only setup consideration
is providing enough ground for the player to land on (horizontal travel during the arc is
substantial due to air acceleration).

### 4. Slope adhesion has a sharp cliff (BUG-03)

Ground contact goes from 100% at angle 30 to 50% at angle 35. The transition is abrupt,
correlating with the SLIP_ANGLE_THRESHOLD=33. This may be by-design behavior (the slip
system intentionally detaches at steep angles) or a build_slope height array issue.

## Open Concerns

1. **build_loop geometry quality**: The loop builder may be generating tile angles that are
   too coarse for the physics engine to track. A comparison of `build_loop` output vs the
   hillside loop's actual tile data could clarify whether this is a builder or engine issue.

2. **Slope adhesion threshold**: The 35 byte-angle (~49°) limit may be intentional design
   (Sonic games typically have similar slope limits). If so, BUG-03 should be reclassified
   as "working as intended" and the threshold documented as a design constraint.

3. **Gap clearability upper bound**: All tested gap widths (2-5 tiles) pass, but the
   theoretical max isn't tested. The running jump arc at top speed covers ~22 tiles
   horizontally, so even large gaps should be clearable. Adding higher gap widths (8, 10)
   would fully document the limit.

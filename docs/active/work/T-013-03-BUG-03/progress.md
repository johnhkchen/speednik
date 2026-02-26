# Progress — T-013-03-BUG-03: Speed Demon Pit Death on Skybridge

## Completed

### Research
- Reproduced the bug: speed demon dies at x≈1590 (not x≈690 as ticket states)
- Mapped all collision data, spring positions, and terrain structure
- Identified root cause: FULL/TOP_ONLY solidity mismatch at bridge-to-slope transitions

### Design
- Evaluated 4 options (collision fix, spring, combo, bridge extension)
- Selected comprehensive approach: fix collision solidity + neutralize wall tiles + extend bridges

### Implementation

**Step 1 — Fix collision solidity at transition slope surfaces (rows 31-32)**
- Changed 18 cells from FULL(2) → TOP_ONLY(1) at slope surface tiles
- Affected transitions at cols 50-55, 100-107, 150-157

**Step 2 — Fix collision solidity at full transition pillars (rows 30-39)**
- Changed 260 cells from FULL(2) → TOP_ONLY(1) at ALL tiles where tile_map
  declares type=1 but collision.json had type=2
- Covered all three bridge-to-slope transitions AND the boss arena entrance

**Step 3 — Neutralize angle=64 left-wall tiles**
- Changed 27 tiles: set height_array=[0]*16, angle=0 for tiles that had angle=64
- These left-edge wall tiles caused wall-climbing behavior when solidity was TOP_ONLY

**Step 4 — Extend bridge tiles into gaps**
- Added 36 bridge tiles at rows 31-32 in three gap regions:
  - Gap 1 (cols 73-76): between slope exit and bridge segment 5
  - Gap 2 (cols 123-128): between slope exit and bridge segment 6
  - Gap 3 (cols 173-180): between slope exit and bridge segment 7
- These catch airborne players exiting slopes at high speed

**Step 5 — Remove unnecessary recovery spring**
- Initially added a spring at x=1190, y=608 in entities.json
- Removed it after terrain fixes alone proved sufficient

### Verification
- Speed demon: max_x=5136, deaths=0, goal=True, bugs=0
- All 6 archetypes tested: no regressions, no new deaths at fixed transitions
- Hillside tests: 10 passed, 5 xfailed, 1 pre-existing failure (chaos)
- test_skybridge_speed_demon: XPASS (now passes, was xfail)

## Deviations from Plan

1. The ticket described death at x≈690 but actual death occurs at x≈1590
   (earlier collision fixes in T-013-01/T-013-02 resolved the original location)
2. The initial approach (surface-only solidity fix) was insufficient — needed
   comprehensive pillar solidity fix + wall tile neutralization + bridge extensions
3. Recovery spring was planned but ultimately unnecessary

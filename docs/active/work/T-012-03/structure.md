# Structure — T-012-03: Pipeworks Behavior Audit

## Files Created

### 1. `docs/active/tickets/T-012-03-BUG-01.md`

Bug ticket: Slope wall at x≈440-518 blocks all jumping/dashing archetypes.

Frontmatter:
- id: T-012-03-BUG-01
- story: S-012
- title: pipeworks-slope-wall-blocks-progress
- type: bug
- status: open
- priority: high
- phase: ready

Body: Root cause (angle=64 wall tiles at column 32 atop angle=32 slope), affected archetypes
(Jumper, Speed Demon, Cautious, Chaos), observed max_x values, tile data.

### 2. `docs/active/tickets/T-012-03-BUG-02.md`

Bug ticket: Walker/Wall Hugger clip into solid tiles at x≈3040-3095.

Frontmatter:
- id: T-012-03-BUG-02
- story: S-012
- title: pipeworks-solid-tile-clipping
- type: bug
- status: open
- priority: high
- phase: ready

Body: Root cause (physics fails to prevent penetration into FULL solidity tiles with
angle=64/128 in the wall/ceiling region), 150 inside_solid_tile invariant errors,
frame-by-frame trajectory data, tile map of the affected region.

### 3. `docs/active/tickets/T-012-03-BUG-03.md`

Bug ticket: Chaos archetype clips into solid tile at x≈100.

Frontmatter:
- id: T-012-03-BUG-03
- story: S-012
- title: pipeworks-chaos-early-clipping
- type: bug
- status: open
- priority: medium
- phase: ready

Body: Chaos clips into tile (6,31) at x=100, y=500-512 for 6 frames. 8 inside_solid_tile
errors. Minor compared to BUG-01/BUG-02 but still a collision resolution bug.

### 4. `tests/test_audit_pipeworks.py`

Test module: 6 behavior audit tests for Pipeworks stage.

Structure (mirrors `test_audit_hillside.py`):
```
Module docstring
Imports: pytest, speednik.qa (BehaviorExpectation, format_findings, make_*, run_audit)
6 BehaviorExpectation constants: PIPEWORKS_WALKER through PIPEWORKS_CHAOS
6 test functions: test_pipeworks_walker through test_pipeworks_chaos
```

Constants section:
- PIPEWORKS_WALKER: min_x=3000, max_deaths=2, require_goal=False, max_frames=3600
- PIPEWORKS_JUMPER: min_x=5400, max_deaths=1, require_goal=True, max_frames=3600
- PIPEWORKS_SPEED_DEMON: min_x=5400, max_deaths=1, require_goal=True, max_frames=3600
- PIPEWORKS_CAUTIOUS: min_x=1500, max_deaths=1, require_goal=False, max_frames=3600
- PIPEWORKS_WALL_HUGGER: min_x=2000, max_deaths=2, require_goal=False, max_frames=3600
- PIPEWORKS_CHAOS: min_x=800, max_deaths=3, require_goal=False, max_frames=3600

All have invariant_errors_ok=0.

Tests section:
- test_pipeworks_walker: xfail BUG-02 (solid tile clipping)
- test_pipeworks_jumper: xfail BUG-01 (slope wall)
- test_pipeworks_speed_demon: xfail BUG-01 (slope wall)
- test_pipeworks_cautious: xfail BUG-01 (slope wall)
- test_pipeworks_wall_hugger: xfail BUG-02 (solid tile clipping)
- test_pipeworks_chaos: xfail BUG-01 (slope wall, primary cause)

Each test:
1. Calls `run_audit("pipeworks", make_<archetype>(), PIPEWORKS_<ARCHETYPE>)`
2. Filters findings for severity == "bug"
3. Asserts len(bugs) == 0 with format_findings output

## Files Modified

None. This ticket only creates new files.

## Files Deleted

None.

## Module Boundaries

The test file imports only from `speednik.qa` (public API) and `pytest`. No internal imports
needed. The QA framework handles all simulation, invariant checking, and finding generation.

## Ordering

1. Bug tickets first (they are referenced by xfail reasons in the test file)
2. Test file second
3. Verification run last

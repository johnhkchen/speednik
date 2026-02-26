# Research — T-012-03: Pipeworks Behavior Audit

## Pipeworks Stage

- **Player start:** (200.0, 510.0)
- **Goal:** (5558.0, 782.0)
- **Level dims:** 5600 × 1024 pixels (350 × 64 tiles at 16px)
- **Entities:** 300 rings, 4 springs, 2 checkpoints, 4 pipes, 1 liquid zone, 11 enemies

Pipeworks is larger and more complex than Hillside (4800×720). It has vertical terrain, pipes,
liquid zones, and enemies — features absent from Hillside.

## Audit Infrastructure

Same framework as T-012-02. `run_audit("pipeworks", archetype_fn, expectation)` from
`speednik/qa.py` creates the sim, steps for max_frames, captures snapshots, runs invariants,
builds findings. The test file pattern from `test_audit_hillside.py` is the exact template.

## Exploratory Runs (3600 frames each)

| Archetype    | max_x   | final_x    | goal? | dead? | deaths | inv_errors | inv_warnings |
|--------------|---------|------------|-------|-------|--------|------------|--------------|
| Walker       | 3094.9  | 2826.0     | no    | no    | 0      | 150        | 348          |
| Jumper       | 518.0   | 518.0      | no    | no    | 0      | 4          | 143          |
| Speed Demon  | 449.0   | 420.2      | no    | no    | 0      | 0          | 97           |
| Cautious     | 447.2   | 407.9      | no    | no    | 0      | 0          | 1813         |
| Wall Hugger  | 3094.9  | 2826.0     | no    | no    | 0      | 150        | 348          |
| Chaos (s=42) | 428.9   | 106.0      | no    | no    | 0      | 8          | 48           |

**No archetype reaches the goal.** No archetype dies. No archetype reaches the expected min_x
thresholds (except Walker reaches 3094.9 > 3000, and Wall Hugger reaches 3094.9 > 2000).

## Critical Finding 1: Steep Slope Wall at x≈440-518

Jumper, Speed Demon, Cautious, and Chaos all stall on a steep uphill slope in the early stage.
The slope is composed of angle=32, type=3 tiles (pipe-type terrain) forming a continuous ramp
from approximately tile (25,19) up to (32,10).

**Jumper behavior at stall:** Jumper reaches x=518 at tile (32,11-12) and oscillates — moving
+0.3px/frame then snapping back. The slope angle=32 combined with the angle=64 (wall) tiles at
column 32 creates an impassable barrier. The Jumper's jump impulse is absorbed by the slope
grade and wall tile.

**Speed Demon behavior:** Speed Demon stalls at x=449, trapped on the same slope. The
spindash state machine cycles but cannot generate enough momentum to climb the steep ramp.
Reaches max_x=449 at approximately tile (28,17).

**Root cause:** Tile column 32, rows 10-15 have angle=64 (wall angle) with solidity=2 (FULL).
These wall tiles form a vertical barrier at the top of the slope. In a real Sonic 2 stage,
this slope would either be gentler or the wall tiles would be TOP_ONLY to allow players to
climb over. The angle=32 approach tiles (type=3, pipe terrain) are steep enough to kill
horizontal momentum, and the angle=64 wall at the top prevents any further progress.

This is a **bug**: the level geometry prevents all jumping/dashing archetypes from progressing
past x≈518. This is not a gap death (expected) — it's a wall collision stopping progress far
before any gap.

## Critical Finding 2: Walker/Wall Hugger Solid Tile Clipping at x≈3040-3095

Walker and Wall Hugger take a different path (they don't jump, so they may bypass the upper
slope). They reach x≈3040 before entering a zone of FULL solidity tiles. The player clips
through 150 solid tiles between frames 788-940+.

**Trajectory at the bug:** At frame 787 (x=3036.5), Walker lands on ground. At frame 788
(x=3042.8, y=734.0), the player center is inside solid tile (190,45). The player then
bounces between solid tiles in an alternating pattern — ground/jumping state toggling
every frame. At frame 796 (x=3094.9), the player hits angle=128 (ceiling) and reverses
direction. Then enters a ceiling-bounce oscillation loop around x=3081-3094.

**Root cause:** The tile column 190 has angle=64 (wall) tiles in rows 40-41, angle=128
(ceiling) tiles in row 41+, and FULL solidity everywhere. The player enters a region where
collision resolution cannot find a valid position, leading to clipping into solid terrain.
The 150 inside_solid_tile invariant errors confirm the physics layer fails to prevent
penetration.

## Critical Finding 3: Chaos Clips Into Solid at x≈100

Chaos archetype clips into solid tile (6,31) at x=100, y=500-512 between frames 369-374.
This is 8 inside_solid_tile errors. Minor occurrence compared to Findings 1 and 2 but
still a collision bug.

## Finding 4: Massive Warning Volume

All archetypes generate large numbers of `on_ground_no_surface` warnings (Cautious: 1813).
These are warning-severity, not errors, but indicate systemic ground-detection issues in
Pipeworks terrain. The type=3 (pipe terrain) tiles may not register properly for the
ground sensor.

## Comparison to Ticket Expectations

| Archetype    | Expected min_x | Actual max_x | Met? | Expected goal | Actual | Met? |
|--------------|---------------|-------------|------|---------------|--------|------|
| Walker       | 3000          | 3094.9      | YES  | no            | no     | YES  |
| Jumper       | 5400          | 518.0       | NO   | yes           | no     | NO   |
| Speed Demon  | 5400          | 449.0       | NO   | yes           | no     | NO   |
| Cautious     | 1500          | 447.2       | NO   | no            | no     | YES  |
| Wall Hugger  | 2000          | 3094.9      | YES  | no            | no     | YES  |
| Chaos        | 800           | 428.9       | NO   | no            | no     | YES  |

4 of 6 archetypes fail min_x. Both goal-required archetypes fail. The failures are all caused
by the slope wall bug (Finding 1) or by clipping bugs (Findings 2, 3). No archetype actually
encounters a gap or pipe — all failures happen before reaching those features.

## Known Bugs from T-012-02

- **T-012-02-BUG-01:** Wall tile at x≈601 in Hillside (angle=64). Similar pattern to the
  Pipeworks angle=64 wall tiles at column 32 and column 190.
- **T-012-02-BUG-02:** No right boundary clamp. Not triggered in Pipeworks since no archetype
  reaches the right side.
- **T-012-02-BUG-03:** No left boundary clamp. Not triggered in Pipeworks — Chaos stays in
  bounds (min x=100, never goes negative).

## Files Involved

- `tests/test_audit_pipeworks.py` — test file to create
- `docs/active/tickets/T-012-03-BUG-*.md` — bug tickets to create
- `speednik/qa.py` — framework (read-only for this ticket)
- `speednik/simulation.py` — sim_step, create_sim (read-only)
- `speednik/invariants.py` — check_invariants (read-only)

## Key Observations for Design

1. Zero deaths across all runs — the ticket expected deaths at gaps, but no archetype reaches
   any gap. The death expectations (max_deaths > 0) are unreachable with current bugs.
2. The slope wall bug (Finding 1) blocks 4 of 6 archetypes before x=520.
3. The clipping bug (Finding 2) stops the other 2 archetypes at x≈3095.
4. All failures are bug-category, not "expected game design deaths."
5. Three distinct bugs need tickets: slope wall, solid clipping, chaos clipping.

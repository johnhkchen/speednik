# Research — T-012-02: Hillside Behavior Audit

## Audit Infrastructure

The QA framework lives in `speednik/qa.py` (421 lines). Key components:

- **`run_audit(stage, archetype_fn, expectation)`** — Creates sim via `create_sim(stage)`, steps for
  `max_frames` frames, captures `FrameSnapshot` + events each frame, runs `check_invariants()` on
  the full trajectory, builds findings via `_build_findings()`. Returns `(findings, AuditResult)`.
- **`BehaviorExpectation`** — Fields: name, stage, archetype, min_x_progress, max_deaths,
  require_goal, max_frames, invariant_errors_ok.
- **`AuditFinding`** — expectation, actual, frame, x, y, severity ("bug"/"warning"), details.
- **`format_findings()`** — Human-readable output: bug count header + per-finding detail lines.

## Archetypes (speednik/qa.py:102-253)

Six archetype factories, all `Callable[[int, SimState], InputState]`:

| Factory            | Behavior                                                        |
|--------------------|-----------------------------------------------------------------|
| `make_walker()`    | Hold right every frame                                          |
| `make_jumper()`    | Hold right + jump whenever grounded (edge-detected)             |
| `make_speed_demon()`| State machine: APPROACH→CROUCH→CHARGE→RELEASE→RUN→re-dash     |
| `make_cautious()`  | Tap-walk (10 right, 5 idle) + 15 left every 135 frames         |
| `make_wall_hugger()`| Hold right, jump when stalled ≥5 frames                       |
| `make_chaos(seed)` | Seeded RNG, new random InputState every 5-15 frames            |

## Hillside Stage

- **Player start:** (64.0, 610.0)
- **Goal:** (4758.0, 642.0)
- **Level dims:** 4800 × 720 pixels (300 × 45 tiles at 16px)
- **Entities:** 200 rings, 1 spring, 4 enemies, 1 checkpoint, 0 pipes, 0 liquid zones

## Exploratory Runs (3600 frames each)

| Archetype    | max_x    | final_x     | goal? | dead? | deaths | inv_errors | inv_warnings |
|--------------|----------|-------------|-------|-------|--------|------------|--------------|
| Walker       | 851.3    | 617.0       | no    | no    | 0      | 0          | 0            |
| Jumper       | 34023.0  | 34023.0     | no    | no    | 0      | 5444       | 37           |
| Speed Demon  | 4738.2   | 4738.2      | **yes** (f=737) | no | 0 | 0        | 3            |
| Cautious     | 617.1    | 617.1       | no    | no    | 0      | 0          | 0            |
| Wall Hugger  | 894.6    | 616.0       | no    | no    | 0      | 0          | 0            |
| Chaos (s=42) | 64.0     | -49488.2    | no    | no    | 0      | 10526      | 0            |

## Critical Finding: Wall at x≈601

Frame-by-frame analysis of Walker:
- **Frame 152:** x=595.0, angle=0, gs=6.0, on_ground — normal flat travel
- **Frame 153:** x=601.0, **angle=64** (quadrant 1 = right wall), gs=6.0
- **Frame 154:** Player launches upward (y_vel = -5.875), no longer on ground
- Player arcs back down, bounces at x≈614, gets trapped in a tight angle-64/angle-0 oscillation

**Root cause:** Tile (37, 38) at pixel x=592-608, y=608-624 has `angle=64` (wall angle) with
height_array starting at 4. The correct angle for a slight ramp should be 2 or 5, not 64.
Adjacent tiles (38,38) and (39,38) have angles 2 and 2/5 respectively — the 64 is an outlier.

This wall blocks Walker, Cautious, and Wall Hugger completely. Only Speed Demon has enough
momentum to blast through. Jumper escapes by jumping over the problematic region but then
flies past the level boundary (x=34023 vs level_width=4800) since there's no boundary clamping.

## Secondary Finding: Jumper position_x_beyond_right (5444 errors)

Jumper reaches x=34023, well past level_width=4800. The invariant checker flags every frame
past level_width+64=4864 as `position_x_beyond_right` (error severity). This is expected behavior
for the checker — the bug is the lack of boundary clamping in physics, not the test.

## Secondary Finding: Chaos position_x_negative (10526 errors)

Chaos archetype drives left, reaching x=-49488. No left boundary clamp either. The checker
flags `position_x_negative` every frame. Again, the invariant checker is correct — the missing
boundary is the real issue. However, for Chaos archetype, left drift is expected random behavior.

## Tile Layout Near Wall

| Tile     | angle | heights (first 4)  | interpretation        |
|----------|-------|--------------------|-----------------------|
| (36,38)  | 0     | [4,4,4,4]         | Flat lip              |
| (37,38)  | **64**| [4,4,4,4]...[5,5] | **Wall — BUG**        |
| (38,38)  | 2     | [5,5,5,5]         | Gentle slope          |
| (39,38)  | 2     | [5,5,6,6]         | Gentle slope          |
| (40,38)  | 5     | [6,6,6,6]         | Mild slope            |
| (41,38)  | 5     | [7,7,7,8]         | Mild slope continuing |

## Invariant Checker (speednik/invariants.py)

Six checks: position_bounds, inside_solid, velocity_limits, velocity_spikes, ground_consistency,
quadrant_jumps. Error budget in BehaviorExpectation.invariant_errors_ok allows known-noisy runs.

## Test File Location

Per ticket: `tests/test_audit_hillside.py`. Bug tickets: `docs/active/tickets/T-012-02-BUG-*.md`.

## Existing Tests

`tests/test_qa_framework.py` covers framework correctness on synthetic grids (20 tests passing).
No real-stage audit tests exist yet — that's this ticket's job.

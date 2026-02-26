# Research — T-012-04: Skybridge Behavior Audit

## Scope

Run all 6 player archetypes through Skybridge Gauntlet and document every finding.
Skybridge is Stage 3 — the hardest stage, featuring a boss encounter with Egg Piston.

## Existing Audit Pattern

Two prior audits established the pattern:
- `tests/test_audit_hillside.py` (T-012-02) — 6 tests, hillside stage
- `tests/test_audit_pipeworks.py` (T-012-03) — 6 tests, pipeworks stage

Both follow the same structure:
1. Module-level `BehaviorExpectation` constants (aspirational, not weakened)
2. Test functions calling `run_audit(stage, archetype_fn, expectation)`
3. Assert `len(bugs) == 0` with `format_findings()` for messages
4. `@pytest.mark.xfail(strict=True, reason="...")` for tests that fail due to real bugs

## Audit Framework (speednik/qa.py)

`BehaviorExpectation` dataclass fields:
- `name`, `stage`, `archetype`: identifiers
- `min_x_progress`: minimum x position reached
- `max_deaths`: maximum acceptable death count
- `require_goal`: whether goal must be reached
- `max_frames`: simulation frame budget
- `invariant_errors_ok`: physics invariant error budget

`run_audit()` runs the simulation, collects snapshots and events per frame,
checks invariants, builds findings from violations + expectation mismatches.

6 archetypes from `speednik/qa.py`:
- `make_walker()` — hold right every frame
- `make_jumper()` — hold right + jump when grounded
- `make_speed_demon()` — spindash → run → re-spindash when slow
- `make_cautious()` — tap-walk right with periodic left reversals
- `make_wall_hugger()` — hold right, jump when stalled
- `make_chaos(seed)` — seeded deterministic random inputs

## Skybridge Stage Layout

Stage dimensions: 5200×896 px (325×56 tiles).
Player start: (64, 490).
Checkpoints: x=780, x=3980.
Goal: (5158, 482).

Entity composition:
- 10+ enemy_crab, 3 enemy_buzzer — scattered across the stage
- 5 spring_up — at x=304, 440, 592, 1200, 2016, 2832, 3808
- 2 checkpoints — at x=780 and x=3980
- ~160 rings — distributed throughout
- 1 goal — at x=5158

Notable terrain features:
- Three "valley" sections with downhill/uphill slopes (rings follow the curves)
- A lower section around x=3300-3800 at y≈680 (rings and enemies at y≈692)
- Spring at x=3808, y=692 — launches player back to upper path
- Boss arena beyond x=4000 (second checkpoint)

## Boss Mechanics (speednik/enemies.py)

Egg Piston is injected by `create_sim("skybridge")` at (4800, 480).

State machine: IDLE → DESCEND → VULNERABLE → ASCEND → IDLE (repeat)
- IDLE: 120 frames, patrols ±128px of spawn at 1.0 px/frame
- DESCEND: 60 frames, linear interpolation from hover (y-80) to ground
- VULNERABLE: 90 frames (60 after escalation) — only damageable state
- ASCEND: 60 frames, rises back to hover

Damage requirements:
- Player must be rolling (`is_rolling=True`)
- `abs(ground_speed) >= 8.0` (SPINDASH_KILL_THRESHOLD)
- Boss must be in "vulnerable" state
- Boss `boss_hit_timer <= 0` (30-frame invuln between hits)

Boss HP: 8, escalates at HP=4 (faster patrol, shorter vulnerable window).
Full cycle: 120+60+90+60 = 330 frames per cycle (before escalation).
Escalated cycle: 120+60+60+60 = 300 frames.

Minimum boss fight duration (theoretical):
- 4 hits at normal speed: 4×330 = 1320 frames
- 4 hits at escalated speed: 4×300 = 1200 frames
- Total: ~2520 frames minimum just for the boss fight
- Plus travel time + spindash alignment → 6000+ frames needed

## Frame Budget Analysis

Prior audits used 3600 frames (60 seconds at 60fps).
Skybridge needs significantly more for Speed Demon to complete the boss fight.

Travel to boss (~4800px): ~800-1200 frames for Speed Demon at spindash speeds.
Boss fight: ~2520-3500 frames (8 hits across 8 cycles, with travel between hits).
Post-boss to goal (4800→5158): ~100-200 frames.
Total: ~3500-5000 frames. Using 6000 provides safety margin.

## Expected Behaviors (from ticket)

| Archetype    | min_x | max_deaths | goal? | rationale                     |
|--------------|-------|------------|-------|-------------------------------|
| Walker       | 2500  | 2          | no    | Can't spindash, blocked by boss |
| Jumper       | 3500  | 2          | no    | Reaches boss, can't damage it |
| Speed Demon  | 5000  | 1          | yes   | Spindash damages boss         |
| Cautious     | 1200  | 1          | no    | Slow, hostile terrain         |
| Wall Hugger  | 1500  | 2          | no    | Wall recovery in hard stage   |
| Chaos        | 600   | 3          | no    | Random inputs, hardest stage  |

## Key Risks

1. Speed Demon may not maintain spindash speed through the boss arena terrain
2. Boss collision detection relies on `is_rolling` flag — need to verify the
   Speed Demon actually enters rolling state at the right time
3. Non-spindash archetypes contacting the boss should take damage, not softlock
4. Lower section (y≈680 area around x=3300-3800) could trap slow archetypes
5. Multiple enemies (crabs, buzzers) may kill archetypes before reaching expected x
6. Prior audit bugs (slope walls, solid clipping) may also manifest in skybridge

## Files Involved

- `tests/test_audit_skybridge.py` — new test file (to create)
- `speednik/qa.py` — audit framework (read only)
- `speednik/simulation.py` — sim harness (read only)
- `speednik/enemies.py` — boss logic (read only)
- `speednik/constants.py` — boss constants (read only)
- `speednik/stages/skybridge/` — stage data (read only)
- `docs/active/tickets/T-012-04-BUG-*.md` — bug tickets (to create if findings)

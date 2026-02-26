# Review — T-012-01: Archetype Library & Expectation Framework

## Summary of Changes

### Files Created
| File | Lines | Purpose |
|------|-------|---------|
| `speednik/qa.py` | ~290 | Archetype library, expectation framework, audit runner |
| `tests/test_qa_framework.py` | ~230 | Framework unit tests (20 tests) |

### Files Modified
None.

---

## Acceptance Criteria Evaluation

| Criterion | Status |
|-----------|--------|
| 6 archetype strategy functions implemented and tested on synthetic grids | Done |
| `BehaviorExpectation` and `AuditFinding` dataclasses defined | Done |
| `run_audit()` runs archetype, collects trajectory, runs invariant checker, returns findings | Done |
| `format_findings()` produces readable output for assertion messages | Done |
| Chaos archetype uses seeded RNG for deterministic reproducibility | Done |
| Framework unit tests verify findings are generated for known bad terrain | Done |
| Framework unit tests verify clean terrain produces 0 findings | Done |
| No Pyxel imports | Done (test confirms) |
| `uv run pytest tests/test_qa_framework.py -x` passes | Done (20/20) |

---

## Test Coverage

### Archetype tests (8)
- Walker moves right on flat ground.
- Jumper becomes airborne.
- Speed demon achieves higher peak speed than walker.
- Cautious moves slower than walker.
- Wall hugger moves right on flat ground.
- Chaos is deterministic with same seed.
- Chaos diverges with different seeds.
- All 6 archetypes return valid `InputState` on every frame.

### Expectation framework tests (7)
- Clean flat terrain + lenient expectations → 0 bug findings.
- Unreachable min_x_progress → bug finding generated.
- Deaths exceeding budget → bug finding generated.
- Goal required but not reached → bug finding generated.
- Invariant violation → finding with correct details.
- Invariant error budget exceeded → bug finding generated.
- Warning-severity violations not counted against error budget.

### Format tests (4)
- Empty findings list → "0 bugs" header.
- Single bug → correct frame/position/expected/actual format.
- Multiple mixed-severity findings → all present, correct bug count.
- All fields appear in output.

### No-Pyxel test (1)
- Source file contains no `import pyxel` or `from pyxel`.

---

## Architecture Decisions

- **Archetype signature:** `Callable[[int, SimState], InputState]` — distinct from existing
  `Strategy` (`(int, Player)`) and `Agent` (`act(ndarray) → int`). Gives archetypes access
  to full game state for complex behaviors like speed demon re-spindash threshold.

- **Jump edge detection:** Each archetype manages its own `prev_jump` state via closure
  variables. This keeps the audit loop simple and lets archetypes have full control over
  input timing.

- **`AuditResult` return type:** The ticket mentioned `ProbeResult` which doesn't exist.
  Defined `AuditResult` with snapshots, events_per_frame, violations, and final sim state —
  provides all data downstream tests need for analysis.

- **Audit loop uses `sim_step`:** Not `strategies.run_scenario` (which only does
  `player_update` — no entities). The audit must test the full entity pipeline (rings,
  springs, enemies, goal detection) to catch real gameplay issues.

---

## Open Concerns

1. **Speed demon on flat ground with `sim_step`:** The spindash state machine interacts with
   `sim_step` (which calls `player_update`). After release, rolling friction slows the player
   significantly. On flat ground with no obstacles, the walker actually covers more distance.
   The speed demon's value is peak speed and obstacle penetration. Tests compare peak speed
   accordingly.

2. **Wall hugger wall detection:** The archetype detects walls by checking for near-zero
   `ground_speed` while on ground for 5+ consecutive frames. On flat ground without walls,
   it behaves like a walker. The actual wall-jumping behavior can only be tested with wall
   geometry (which real stages provide in T-012-02+).

3. **Death handling in `run_audit`:** The loop breaks immediately on `player_dead`. There is
   no respawn mechanism in `sim_step` — once dead, every subsequent frame returns `[DeathEvent()]`.
   If future respawn support is added, the loop should be updated to continue after death.

4. **Chaos jump_pressed edge detection:** The chaos archetype sets `jump_pressed` randomly,
   which may not always produce the rising-edge behavior needed for actual jumps. This is
   intentional — chaos tests unpredictable input, not optimal play.

---

## Full Test Suite Impact

All 1277 existing tests continue to pass. No regressions.

```
1277 passed, 16 skipped, 5 xfailed (10.86s)
```

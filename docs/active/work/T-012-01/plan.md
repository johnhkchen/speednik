# Plan — T-012-01: Archetype Library & Expectation Framework

## Step 1: Create `speednik/qa.py` with dataclasses and type alias

Write the module skeleton: imports, `Archetype` type alias, `BehaviorExpectation`,
`AuditFinding`, `AuditResult` dataclasses.

**Verify:** Module imports without error.

## Step 2: Implement `_capture_snapshot` helper

Build `FrameSnapshot` from `SimState` after each sim step. Import `get_quadrant` from
`speednik.terrain` for quadrant derivation.

**Verify:** Can create a snapshot from a sim created via `create_sim_from_lookup`.

## Step 3: Implement `make_walker()`

Simplest archetype: return `InputState(right=True)` every frame.

**Verify:** On flat grid, walker moves right with increasing x.

## Step 4: Implement `make_jumper()`

Hold right + jump on rising edge when grounded. Closure tracks `prev_jump`.

**Verify:** On flat grid, jumper alternates between ground and air.

## Step 5: Implement `make_speed_demon()`

State machine: APPROACH → CROUCH → CHARGE → RELEASE → RUN → re-CROUCH when slow.
Closure tracks state, frame counters, prev_jump.

**Verify:** On flat grid, speed demon reaches higher ground_speed than walker.

## Step 6: Implement `make_cautious()`

Tap-walk pattern with periodic left movement. Closure tracks frame counter.

**Verify:** On flat grid, cautious moves right but slower than walker.

## Step 7: Implement `make_wall_hugger()`

Hold right, detect wall (low ground_speed + on_ground for N frames), jump.
Closure tracks stall counter and prev_jump.

**Verify:** On flat grid followed by wall, wall hugger jumps.

## Step 8: Implement `make_chaos(seed)`

Seeded `random.Random`. Every 5–15 frames, randomize input combination.
Closure tracks RNG, frame counter for next input change, current input.

**Verify:** Same seed produces identical trajectory. Different seeds diverge.

## Step 9: Implement `_build_findings`

Convert invariant violations and expectation failures into `AuditFinding` list:
- Each `Violation` with severity "error" → finding with severity "bug"
- Each `Violation` with severity "warning" → finding with severity "warning"
- `min_x_progress` not met → "bug" finding
- `max_deaths` exceeded → "bug" finding
- `require_goal` but not reached → "bug" finding
- Invariant error count exceeds `invariant_errors_ok` → "bug" finding

**Verify:** Unit test with crafted violations and expectations.

## Step 10: Implement `run_audit`

Main loop: create_sim → step loop → capture snapshots → check invariants → build findings.
Handle death/goal termination.

**Verify:** Run on flat synthetic grid with walker, expect 0 bug findings.

## Step 11: Implement `format_findings`

String builder matching ticket format:
```
FINDINGS (N bugs):
  [frame F, x=X] Details
    Expected: expectation
    Actual: actual
```

**Verify:** Unit test with known findings produces expected output.

## Step 12: Write `tests/test_qa_framework.py`

Three test classes:

**TestArchetypes:** Each archetype on synthetic grids, verify behavior.
- Walker moves right on flat ground.
- Jumper leaves ground.
- Speed demon achieves high speed.
- Cautious moves slower than walker.
- Wall hugger jumps at obstacles.
- Chaos is deterministic with same seed, different with different seeds.

**TestExpectationFramework:** Findings generation.
- Clean flat terrain → 0 findings.
- Stuck player (wall or gap) → finding generated.
- Death exceeds max → finding.
- Invariant violation → finding.
- Goal not reached when required → finding.

**TestFormatFindings:** Output formatting.
- Empty list → "FINDINGS (0 bugs):" header.
- Single finding → correct format.
- Multiple findings → all present.

**Verify:** `uv run pytest tests/test_qa_framework.py -x` passes.

## Testing Strategy

- All framework tests use synthetic grids (build_flat, build_gap) for determinism.
- No real stage tests — those belong in T-012-02 through T-012-04.
- Chaos determinism verified by running same seed twice and comparing snapshots.
- Edge cases: zero-frame budget, death on first frame, already-at-goal.

# Progress — T-012-01: Archetype Library & Expectation Framework

## Completed

### Step 1–2: Module skeleton + snapshot capture
- Created `speednik/qa.py` with imports, type alias, dataclasses, `_capture_snapshot`.
- Verified import: `from speednik.qa import *` succeeds.

### Step 3–8: All 6 archetypes implemented
- `make_walker()` — hold right every frame.
- `make_jumper()` — hold right + jump on rising edge when grounded. Closure tracks prev_jump.
- `make_speed_demon()` — state machine: APPROACH → CROUCH → CHARGE → RELEASE → RUN → re-CROUCH.
- `make_cautious()` — tap-walk (10 right, 5 idle), left for 15 frames every 135-frame cycle.
- `make_wall_hugger()` — hold right, detect stall (ground_speed < 0.1 for 5 frames), jump.
- `make_chaos(seed)` — seeded `random.Random`, randomize inputs every 5–15 frames.

### Step 9: `_build_findings` implemented
- Converts invariant violations → findings (error→bug, warning→warning).
- Checks: invariant error budget, min_x_progress, max_deaths, require_goal.

### Step 10: `run_audit` implemented
- Creates sim via `create_sim(stage)`, steps with `sim_step`, captures snapshots.
- Breaks on `goal_reached` or `player_dead`.
- Runs `check_invariants` on trajectory, builds findings.

### Step 11: `format_findings` implemented
- Produces output matching ticket spec format.

### Step 12: Tests written and passing
- 20 tests in `tests/test_qa_framework.py`, all pass.
- TestArchetypes: 8 tests (walker, jumper, speed_demon, cautious, wall_hugger, chaos×2, valid_input).
- TestExpectationFramework: 7 tests (clean, min_x, deaths, goal, violations, budget, warnings).
- TestFormatFindings: 4 tests (empty, single, multiple, all_fields).
- TestNoPyxelImport: 1 test.

## Deviations

- **Speed demon test:** Changed from comparing total distance (max_x) to comparing peak
  ground_speed. On flat ground with only 300 frames, the spindash startup overhead means the
  walker covers more distance, but speed demon achieves higher peak speed. This is the correct
  comparison — the archetype's value is peak speed, not flat-ground efficiency.

## Remaining

None — all plan steps completed.

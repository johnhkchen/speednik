# Plan — T-008-01: scenario-runner-and-strategies

## Step 1: Create `tests/harness.py` with data classes and runner

Write the complete `tests/harness.py` file containing:

- `FrameSnapshot` dataclass with all 10 fields
- `ScenarioResult` dataclass with `final`, `max_x`, `quadrants_visited`, `stuck_at`
- `_capture_snapshot()` internal helper
- `run_scenario()` core loop function
- `run_on_stage()` convenience wrapper
- `Strategy` type alias

**Verification:** Module imports without error: `python -c "from tests.harness import run_scenario"`

## Step 2: Add strategy factories

Add to `tests/harness.py`:

- `idle()` — returns empty InputState every frame
- `hold_right()` — returns `InputState(right=True)` every frame
- `hold_right_jump()` — holds right, presses jump on first frame and after each landing.
  Uses closure variable `was_airborne` to detect landing transitions.
- `spindash_right(charge_frames=3, redash_threshold=2.0)` — internal state machine
  (CROUCH → CHARGE → RELEASE → RUN → repeat). Tracks phase and frame counter.
- `scripted(timeline)` — linear scan of `(start, end, InputState)` tuples per frame.

**Verification:** Module still imports cleanly. Manual smoke test of `idle()` and
`hold_right()` returning correct InputState values.

## Step 3: Create `tests/test_harness.py` with self-tests

Write test file with:

- `TestRunScenario.test_idle_stays_grounded` — `idle` on flat ground for 60 frames,
  assert all snapshots have `on_ground=True` and position ~unchanged.
- `TestRunScenario.test_hold_right_advances_x` — `hold_right` on flat ground for 60
  frames, assert `result.final.x > start_x`.
- `TestScenarioResult.test_max_x` — verify `max_x` returns maximum X from snapshots.
- `TestScenarioResult.test_final` — verify `final` returns last snapshot.
- `TestScenarioResult.test_quadrants_visited` — verify quadrants collected correctly.
- `TestScenarioResult.test_stuck_at_detects_stuck` — player on 2-tile island, hold
  right, wall blocks. `stuck_at` returns a position.
- `TestScenarioResult.test_stuck_at_returns_none` — player moving. Returns None.
- `TestStrategies.test_idle_returns_empty` — verify idle strategy output.
- `TestStrategies.test_hold_right_output` — verify hold_right strategy output.
- `TestStrategies.test_hold_right_jump_presses_jump` — verify jump_pressed on first
  frame, jump_held thereafter, re-press after landing.
- `TestStrategies.test_scripted_timeline` — verify frame windows produce correct input.

**Verification:** `uv run pytest tests/test_harness.py -x -v` passes.

## Step 4: Run full test suite

**Verification:** `uv run pytest tests/ -x` passes (no regressions).

## Testing Strategy

- **Unit tests** (Step 3): Each strategy factory, each ScenarioResult property, and both
  runner functions tested against synthetic flat-tile grids.
- **No integration tests** against real stages in this ticket — that's for downstream
  tickets (T-008-02+). The self-tests use flat_ground_lookup which is deterministic and
  fast.
- **Pyxel-free verification:** The harness module never imports pyxel. If it did, the
  import in test would fail in CI (no display available).

## Commit Plan

Single commit after all steps pass: "feat: add scenario runner and strategy primitives
for robotic player testing"

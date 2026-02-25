# Progress — T-008-01: scenario-runner-and-strategies

## Completed

### Step 1: Created `tests/harness.py` with data classes and runner
- `FrameSnapshot` dataclass with all 10 fields (frame, x, y, x_vel, y_vel,
  ground_speed, angle, on_ground, quadrant, state)
- `ScenarioResult` dataclass with `final`, `max_x`, `quadrants_visited`, `stuck_at`
- `_capture_snapshot()` internal helper
- `run_scenario()` core loop
- `run_on_stage()` convenience wrapper
- `Strategy` type alias
- Verified: module imports cleanly

### Step 2: Added strategy factories
- `idle()` — empty InputState every frame
- `hold_right()` — right=True every frame
- `hold_right_jump()` — right + jump with re-press after landing (closure state)
- `spindash_right(charge_frames, redash_threshold)` — 4-phase state machine
- `scripted(timeline)` — frame-windowed input playback
- Verified: all strategies produce correct output

### Step 3: Created `tests/test_harness.py` with 20 self-tests
- 4 tests for `run_scenario` (idle grounded, hold_right advances, frame count, airborne)
- 6 tests for `ScenarioResult` (final, max_x, quadrants_visited, stuck_at × 3)
- 10 tests for strategies (idle, hold_right, hold_right_jump × 3, scripted × 2,
  spindash_right × 3)
- All 20 pass

### Step 4: Full test suite
- `uv run pytest tests/ -x` → 693 passed in 1.10s, zero regressions

## Deviations from Plan

- `stuck_at` takes an additional `window` parameter (default 30) for flexibility.
  Design said "could be a parameter" — made it one.
- No commit made yet — leaving for review phase confirmation.

## Remaining

- Review phase artifact

# Review — T-008-01: scenario-runner-and-strategies

## Summary of Changes

### Files Created

| File                    | Lines | Purpose                                         |
|-------------------------|-------|-------------------------------------------------|
| `tests/harness.py`      | ~210  | Scenario runner, data classes, strategy factories |
| `tests/test_harness.py` | ~220  | 20 self-tests covering runner and strategies     |

### Files Modified

None. This ticket adds new modules only — no changes to existing game or test code.

## What Was Built

**Scenario runner:** `run_scenario()` places a player in a tile grid, feeds inputs
frame-by-frame via a strategy callable, and returns a `ScenarioResult` with per-frame
`FrameSnapshot` logs and the final `Player` object. Completely Pyxel-free.

**Stage runner:** `run_on_stage()` wraps `run_scenario` by loading a real stage via
`load_stage()` and starting at `player_start`.

**Data classes:** `FrameSnapshot` captures 10 fields per frame (position, velocity,
ground speed, angle, on_ground, quadrant, state). `ScenarioResult` provides analysis
helpers: `final`, `max_x`, `quadrants_visited`, `stuck_at`.

**Five strategy factories:**
- `idle()` — empty input (ground adhesion test)
- `hold_right()` — baseline beginner player
- `hold_right_jump()` — jump-spam player with automatic re-press after landing
- `spindash_right()` — power player with crouch/charge/release/run cycle
- `scripted()` — precise frame-windowed input playback

## Acceptance Criteria Checklist

- [x] `run_scenario` takes tile_lookup, start position, strategy, frame count
- [x] Returns `ScenarioResult` with per-frame `FrameSnapshot` list and final `Player`
- [x] `ScenarioResult` provides `max_x`, `final`, `quadrants_visited`, `stuck_at`
- [x] `run_on_stage` loads a named stage and runs from player_start
- [x] `idle` strategy implemented
- [x] `hold_right` strategy implemented
- [x] `hold_right_jump` strategy implemented
- [x] `spindash_right` strategy implemented
- [x] `scripted(timeline)` strategy implemented
- [x] No Pyxel imports anywhere in the module
- [x] Self-test: `idle` on flat tile grid keeps player grounded 60 frames
- [x] Self-test: `hold_right` on flat tile grid advances player X position
- [x] `uv run pytest tests/ -x` passes (693/693)

## Test Coverage

**20 tests in `test_harness.py`:**

- Runner tests (4): idle stays grounded, hold_right advances X, frame count correct,
  on_ground=False starts airborne.
- Result property tests (6): final, max_x, quadrants_visited, stuck_at detection,
  stuck_at returns None when moving, stuck_at with too few frames.
- Strategy unit tests (10): idle output, hold_right output, hold_right_jump first frame
  press, hold_right_jump airborne hold, hold_right_jump re-press after landing,
  scripted within window, scripted outside window, spindash crouch phase, spindash
  charge phase, spindash release phase.

**Coverage gaps (acceptable):**
- `run_on_stage` is not unit-tested here — it will be exercised heavily by T-008-02+
  which run robotic players on real stages. Testing it here would duplicate those tests.
- `spindash_right` RUN→re-CROUCH transition is not tested in isolation. The state
  machine logic is simple and will be validated end-to-end in integration tests.
- No edge case tests for `hold_right_jump` when player starts airborne (not a realistic
  scenario for the intended use).

## Open Concerns

1. **Strategy statefulness:** `hold_right_jump` and `spindash_right` use mutable closure
   lists (`[False]`, `[CROUCH]`). Each call to the factory returns a fresh closure, so
   strategies are not reusable across multiple runs from the same factory call. This is
   intentional — call the factory again for a fresh strategy.

2. **`stuck_at` sensitivity:** The sliding window approach may miss "micro-stuck" patterns
   (e.g., player oscillating ±3px at a wall with tolerance=2.0). The default tolerance
   and window size (2.0 px, 30 frames) are reasonable for typical gameplay scenarios.

3. **No object interactions:** The runner calls only `player_update` — it does not check
   ring collection, spring collisions, enemy collisions, or goal. This is by design for
   T-008-01 (physics-only runner). Object interactions may be added in a future ticket
   if needed.

## Conclusion

The harness is complete and all acceptance criteria are met. The module provides a clean,
Pyxel-free foundation for robotic player testing. Downstream tickets (T-008-02+) can
immediately import and use it.

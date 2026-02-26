# T-013-01 Review: World Boundary System

## Summary of Changes

### Files Modified

| File | Change |
|------|--------|
| `speednik/constants.py` | Added `PIT_DEATH_MARGIN = 32` constant |
| `speednik/simulation.py` | Added boundary enforcement block in `sim_step()` (~20 lines); added `level_width`/`level_height` kwargs to `create_sim_from_lookup()` |

### Files Created

| File | Purpose |
|------|---------|
| `tests/test_world_boundary.py` | 11 tests for left/right boundary clamping and pit death |

### Files Unchanged

- `speednik/player.py` — no changes to player_update or damage_player
- `speednik/physics.py` — no changes to physics pipeline
- `speednik/terrain.py` — no changes to collision system
- `speednik/invariants.py` — no changes (still detects violations post-hoc)

## What Was Implemented

### Boundary Enforcement in sim_step

After `player_update()` runs physics, three boundary checks execute:

1. **Left boundary (x < 0)**: Clamps x to 0, zeros negative x_vel and ground_speed
2. **Right boundary (x > level_width)**: Clamps x to level_width, zeros positive x_vel
   and ground_speed
3. **Pit death (y > level_height + 32)**: Sets player state to DEAD, sets on_ground=False,
   increments sim.deaths, emits DeathEvent

The checks run before entity collision checks (rings, springs, enemies), ensuring the
player is within bounds before any game-logic interactions.

### create_sim_from_lookup kwargs

Added keyword-only `level_width` and `level_height` parameters with defaults matching
the previous hardcoded values (99999). Backward compatible — no changes needed for
callers that don't pass these args.

## Test Coverage

### New Tests (11 total, all passing)

**TestLeftBoundary (3)**:
- Position clamped to >= 0
- Negative velocity zeroed on clamp
- No death at left boundary

**TestRightBoundary (2)**:
- Position clamped to <= level_width
- Positive velocity zeroed on clamp

**TestPitDeath (6)**:
- Death triggers below level_height + 32
- DeathEvent emitted
- sim.deaths counter incremented
- No death above threshold (level_height + 31)
- Death occurs regardless of ring count
- Idempotent — already-dead player doesn't re-trigger

### Previously Broken Tests Fixed

- `tests/test_invariants.py` — 22 tests, all passing. Previously `TestPositionInvariants`
  and all downstream tests failed with `TypeError: create_sim_from_lookup() got an
  unexpected keyword argument 'level_width'`.

### Existing Test Suite

- 1021 tests pass
- 24 pre-existing failures (loop traversal T-013-05, damage-kills bugs — unrelated)
- 34 xfail (expected failures with documented reasons)
- 5 test files excluded due to pre-existing ImportError (cast_terrain_ray not yet
  implemented, T-010-16)

## Coverage Gaps

1. **Boundary + terrain interaction**: No test covers a player hitting the left/right
   boundary while on a slope or during a roll. The velocity zeroing should be safe
   (ground_speed=0 just stops the player) but the angle/quadrant state is unchanged.
   Low risk.

2. **Pit death + respawn flow**: Tests verify death triggers, but don't test the full
   respawn cycle through sim_step. Respawn is handled by the caller (main.py or
   Gymnasium env), not sim_step itself. The caller detects `player.state == DEAD` and
   invokes their own respawn logic.

3. **Audit invariant error counts**: The acceptance criteria mention specific invariant
   error counts (= 0) on audit runs. Audit tests are marked xfail for unrelated
   reasons (loop traversal, damage mechanics). Once those bugs are fixed, the boundary
   enforcement here should reduce those invariant counts. Cannot verify zero-error
   audits until dependencies are resolved.

## Open Concerns

1. **SimState.player_dead is orphaned**: The `player_dead` field on SimState
   (simulation.py:119) is never set by any code path, including our new pit death.
   `sim_step` checks it as an early return but it's always False. This is pre-existing
   technical debt — we opted not to use it for pit death because it would prevent
   respawn. Recommend: either remove it or wire it to `player.state == DEAD` as a
   property.

2. **Harness-based tests don't get boundaries**: `tests/harness.py:run_scenario()`
   calls `player_update()` directly, bypassing `sim_step()`. Those test trajectories
   won't be boundary-enforced. This is by design — harness tests probe physics behavior,
   not game-level policy. But it means invariant checks on harness trajectories may
   still see boundary violations.

3. **No top boundary**: Player can go above y=0 (jumping high). This is normal Sonic
   behavior — gravity brings them back. Not a concern, but documenting the intentional
   omission.

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| `position_x_beyond_right` = 0 on Hillside jumper audit | Blocked on audit xfail |
| `position_x_negative` = 0 on Hillside chaos audit | Blocked on audit xfail |
| `position_y_below_world` = 0 on Skybridge walker audit | Blocked on audit xfail |
| Player dies and respawns when falling below level_height + 32 | Death verified; respawn is caller's responsibility |
| Existing tests remain green | Yes — 1021 passing, 0 new regressions |

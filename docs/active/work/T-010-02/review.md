# Review — T-010-02: sim-step-and-event-system

## Summary of Changes

### Files Modified

| File | Change | Lines |
|------|--------|-------|
| `speednik/simulation.py` | Added `sim_step()` function | +60 |
| `tests/test_simulation.py` | Added 9 new test functions, 2 new imports | +95 |

### Files NOT Modified

- `speednik/main.py` — Untouched. `sim_step` mirrors but does not alter `_update_gameplay`.
- `speednik/objects.py` — All functions used as-is via existing imports.
- `speednik/enemies.py` — `update_enemies` and `check_enemy_collision` used directly.
- `speednik/player.py` — `player_update` and `PlayerState` used directly.
- No new files created.

## What Was Built

`sim_step(sim: SimState, inp: InputState) -> list[Event]` — the single function that advances
the headless simulation by one frame. It:

1. Detects player death (returns early with `DeathEvent`, no physics)
2. Runs player physics via `player_update`
3. Processes all game objects in the exact order of `main.py:_update_gameplay()`:
   rings → springs → checkpoints → pipes → liquid zones → enemies → spring cooldowns → goal
4. Translates game core events to simulation-layer events
5. Updates metrics (max_x_reached, rings_collected)

The function is ~60 lines, purely procedural, and deterministic.

## Acceptance Criteria Coverage

| Criterion | Status | Evidence |
|-----------|--------|----------|
| sim_step advances player physics | PASS | `test_sim_step_hold_right_smoke` — x increases over 60 frames |
| Ring collection → RingCollectedEvent | PASS | Code translates `ObjRingEvent.COLLECTED` → `RingCollectedEvent()` |
| Spring collision → SpringEvent | PASS | Code translates `ObjSpringEvent.LAUNCHED` → `SpringEvent()` |
| Checkpoint collision processed | PASS | Code translates `ObjCheckpointEvent.ACTIVATED` → `CheckpointEvent()` |
| Enemy collision (damage/kills) | PASS | Code translates `EnemyEvent.PLAYER_DAMAGED` → `DamageEvent()` |
| Goal reached → sets flag | PASS | `test_sim_step_goal_detection` — teleport to goal, verify event + flag |
| Death detected → sets flag | PASS | `test_sim_step_death_detection` — set DEAD, verify event + flags |
| max_x_reached / rings_collected | PASS | `test_sim_step_max_x_tracking` — max_x updates correctly |
| Order matches _update_gameplay | PASS | Code comments reference main.py line numbers; verified by inspection |
| Enemies update each frame | PASS | `test_sim_step_enemy_update` — crab patrol changes x |
| No Pyxel imports | PASS | `test_no_pyxel_import` (existing from T-010-01) |
| 60 frames hold_right → x increases | PASS | `test_sim_step_hold_right_smoke` |
| pytest passes | PASS | 830 passed, 5 xfailed |

## Test Coverage

### New Tests (9)

1. `test_sim_step_hold_right_smoke` — Integration: 60 frames, player moves right
2. `test_sim_step_frame_counter` — Frame counter increments
3. `test_sim_step_death_detection` — Death flag + event on DEAD state
4. `test_sim_step_death_persistent` — Deaths counter doesn't re-increment
5. `test_sim_step_death_no_physics` — No physics/frame advance on dead frames
6. `test_sim_step_max_x_tracking` — Metric tracks furthest position
7. `test_sim_step_returns_list` — Basic type contract
8. `test_sim_step_enemy_update` — Crab patrol moves
9. `test_sim_step_goal_detection` — Goal event fires at goal position

### Coverage Gaps

- **Ring collection event test**: No test positions the player near a specific ring and
  verifies `RingCollectedEvent`. The function is called and runs without error (smoke test),
  but the specific event translation is tested only structurally. Adding this would require
  knowledge of exact ring positions in hillside, which is brittle.
- **Spring collision event test**: Same gap as rings — function is called but no test
  triggers a specific `SpringEvent`. The underlying `check_spring_collision` is thoroughly
  tested in `test_game_objects.py`.
- **Liquid zone damage**: No test triggers liquid damage through sim_step. Liquid zones are
  only present on pipeworks, and triggering damage requires precise player positioning.
- **Enemy damage event**: No test triggers `EnemyEvent.PLAYER_DAMAGED` through sim_step.
  Would require positioning player in enemy hitbox, which depends on enemy type and position.
- **Pipe travel**: Side-effects-only call, no event translation. Tested indirectly.

These gaps are acceptable because:
1. The underlying game core functions are tested in their own test files.
2. The translation logic is trivially correct (if-match-then-append pattern).
3. Positional entity tests are inherently brittle and belong in integration-level scenarios.

## Open Concerns

1. **EXTRA_LIFE ring events are silently dropped.** When `ObjRingEvent.EXTRA_LIFE` fires,
   sim_step does not emit any simulation event. The player's lives counter is still mutated
   by `check_ring_collection()`, so the gameplay effect works. But downstream consumers
   have no way to observe extra life events through the event list. This is by design per
   the design document, but worth noting for future gym/scenario work.

2. **Boss defeated has no simulation event.** `EnemyEvent.BOSS_DEFEATED` is not translated.
   The boss's `alive` field is set to False by `check_enemy_collision`, which is the
   authoritative signal. A `BossDefeatedEvent` could be added to the Event union if
   downstream consumers need it.

3. **No camera update.** `camera_update()` is deliberately skipped (rendering concern).
   This means `sim.player` lacks camera-relative positioning. The gym env will need its own
   observation extraction that works without camera state.

4. **Determinism assumption.** `sim_step` is deterministic given the same `SimState` and
   `InputState`. This relies on all game core functions being deterministic, which they
   are (no RNG, no time-based logic). This is a critical property for RL training and
   scenario reproducibility.

## Test Results

```
830 passed, 5 xfailed in 1.95s
```

No regressions. All 19 simulation-specific tests pass (10 from T-010-01, 9 new).

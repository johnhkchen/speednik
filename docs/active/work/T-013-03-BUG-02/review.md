# Review — T-013-03-BUG-02: audit-no-respawn-after-pit-death

## Summary of Changes

### Files Modified

1. **`speednik/qa.py`** — Two changes:
   - Added `_respawn_player(sim)` helper (lines 370–385): resets player state, physics,
     position, and rings to checkpoint/start values after death.
   - Modified `run_audit()` loop (lines 417–422): after each `sim_step()`, checks for
     `DeathEvent`. If deaths exceed `max_deaths`, sets `sim.player_dead = True` (terminates
     loop via existing break condition). Otherwise calls `_respawn_player(sim)` to reset
     the player and continue the audit.

2. **`tests/test_qa_framework.py`** — Added `TestAuditRespawn` class with 4 tests:
   - `test_respawn_after_pit_death`: Verifies player respawns at checkpoint after gap death
   - `test_death_budget_exceeded_terminates`: Verifies `player_dead` set when budget exceeded
   - `test_respawn_resets_player_state`: Verifies all player fields reset correctly
   - `test_max_x_tracks_across_respawns`: Verifies `max_x_reached` preserves pre-death progress

### Files NOT Modified

- `speednik/simulation.py`: `sim_step()` already correctly signals death via `DeathEvent`
  and `player.state = DEAD`. The `player_dead` flag is intentionally left as a caller-set
  signal for "permanently dead" (policy decision), not set by `sim_step()`.
- `speednik/player.py`, `speednik/objects.py`, `speednik/constants.py`: No changes needed.
- `speednik/main.py`: Game respawn is independent; not affected.
- `tests/test_audit_skybridge.py`: Not modified in this ticket. Xfail markers still
  reference T-013-03-BUG-02; these will need updating when the fix is verified in
  subsequent audit re-runs.

## Test Coverage

| Area | Coverage | Notes |
|------|----------|-------|
| `_respawn_player()` state reset | Direct | `test_respawn_resets_player_state` covers all 14 fields |
| Death → respawn flow | Direct | `test_respawn_after_pit_death` with synthetic gap |
| Death budget termination | Direct | `test_death_budget_exceeded_terminates` |
| `max_x_reached` persistence | Direct | `test_max_x_tracks_across_respawns` |
| Checkpoint-based respawn coords | Indirect | Uses default respawn (start position); checkpoint activation tested elsewhere |
| `run_audit()` integration | Indirect | Skybridge audit tests exercise the full flow |
| Existing behavior preserved | Full | All 20 pre-existing tests pass |

**Gap**: No test verifies that `respawn_rings` from checkpoint activation is preserved through
death+respawn in a real stage scenario. The unit test verifies the reset logic uses
`respawn_rings`, but checkpoint activation happens in `sim_step()` via `check_checkpoint_collision()`
which is tested separately. The end-to-end path (activate checkpoint → die → respawn with
saved rings) is not tested in this ticket.

## Design Decisions

1. **Respawn in `run_audit()`, not `sim_step()`**: `sim_step()` is a pure physics step. Respawn
   policy (death budgets, animation delays, lives) is caller-specific. The game (main.py)
   handles respawn with a 120-frame delay and lives system. The audit handles it immediately
   with a death budget. Putting respawn in `sim_step()` would create competing respawn paths.

2. **`player_dead` semantics**: "Caller has determined the player is permanently dead."
   Set by `run_audit()` when deaths exceed budget, not by `sim_step()` on each death. This
   preserves the existing contract where `sim_step()` signals death via `DeathEvent` and
   callers decide what to do.

3. **Immediate respawn**: No death animation delay in the audit. The 120-frame
   `DEATH_DELAY_FRAMES` constant is for the game's visual death sequence. The audit cares
   about physics behavior, not animation timing.

## Open Concerns

1. **Skybridge xfails still reference this ticket**: `test_skybridge_jumper` and
   `test_skybridge_speed_demon` are xfailed with reason T-013-03-BUG-02. With respawn now
   working, these archetypes may reach further than before, but they may still fail for
   other reasons (terrain traps, spindash trajectories). The xfail markers should be
   re-evaluated in a follow-up audit run.

2. **Archetype state not reset on respawn**: The archetype strategy functions (closures)
   carry internal state (phase counters, frame counters, prev_jump flags). Respawn resets
   the player but not the archetype's internal state. For example, `make_speed_demon()` may
   be in its RUN phase when the player dies, and after respawn it continues in RUN phase
   rather than starting fresh with APPROACH. This could affect audit results but is arguably
   correct — the "player" remembers their strategy even after respawning.

3. **`sim.frame` not reset**: The simulation frame counter continues incrementing through
   respawns. This is correct (total frames elapsed) but means the archetype sees monotonically
   increasing frame numbers, which could affect time-based strategies.

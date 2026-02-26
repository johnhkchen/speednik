# Progress — T-013-03-BUG-02: audit-no-respawn-after-pit-death

## Step 1: Add `_respawn_player()` helper — DONE

Added `_respawn_player(sim: SimState) -> None` to `speednik/qa.py` (lines 370–385).
Resets player state, physics, position, rings, and flags to checkpoint/start values.
`PlayerState` was already imported.

## Step 2: Modify `run_audit()` loop — DONE

Added death event handling after `events_per_frame.append(events)` in `run_audit()`
(lines 417–422). On `DeathEvent`:
- If `sim.deaths > expectation.max_deaths`: sets `sim.player_dead = True` (terminates loop)
- Otherwise: calls `_respawn_player(sim)` (resets player, continues loop)

## Step 3: Add respawn tests — DONE

Added `TestAuditRespawn` class with 4 tests to `tests/test_qa_framework.py`:
- `test_respawn_after_pit_death`: Walker falls into wide gap, respawns, verifies state
- `test_death_budget_exceeded_terminates`: max_deaths=0, first death sets player_dead
- `test_respawn_resets_player_state`: Verifies all player fields reset correctly
- `test_max_x_tracks_across_respawns`: max_x_reached preserves pre-death progress

Tests use synthetic grids (`build_gap` with 30-tile gap, `level_height = (GROUND_ROW+3)*TILE_SIZE`)
to create controllable pit-death scenarios.

## Step 4: Run test suite — DONE

- `tests/test_qa_framework.py`: 24/24 passed (20 existing + 4 new)
- `tests/test_audit_skybridge.py`: 2 passed, 4 xfailed (unchanged from before)
- Broader suite: 1020 passed, 30 failed (pre-existing failures), 31 xfailed, 1 xpassed

No regressions introduced.

## Deviations from Plan

- Gap dimensions in tests changed from (20, 5, 20) to (20, 30, 20) because a 5-tile gap
  was too narrow — the walker at top speed crossed it without falling far enough for pit
  death. Also set `level_height = (GROUND_ROW+3)*TILE_SIZE` instead of `(GROUND_ROW+5)` to
  reduce the fall distance needed.
- Did NOT modify `sim_step()` to set `player_dead = True`. Design analysis confirmed this
  is a caller-level policy decision, not a simulation-layer concern.

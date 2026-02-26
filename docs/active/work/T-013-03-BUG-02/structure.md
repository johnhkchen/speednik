# Structure — T-013-03-BUG-02: audit-no-respawn-after-pit-death

## Files Modified

### 1. `speednik/qa.py` (primary)

**Change**: Add respawn logic to `run_audit()` loop and extract a `_respawn_player()` helper.

#### New private function: `_respawn_player(sim: SimState) -> None`

Resets the player in-place to checkpoint coordinates:
- `sim.player.state = PlayerState.STANDING`
- `sim.player.physics.x = sim.player.respawn_x`
- `sim.player.physics.y = sim.player.respawn_y`
- `sim.player.physics.x_vel = 0.0`
- `sim.player.physics.y_vel = 0.0`
- `sim.player.physics.ground_speed = 0.0`
- `sim.player.physics.on_ground = True`
- `sim.player.physics.is_rolling = False`
- `sim.player.physics.is_charging_spindash = False`
- `sim.player.rings = sim.player.respawn_rings`
- `sim.player.invulnerability_timer = 0`
- `sim.player.scattered_rings = []`
- `sim.player.in_pipe = False`

Location: between `_capture_snapshot()` and the archetype factories (around line 95), or
between the archetype section and the finding builder. Placing it in the "Audit runner"
section near `run_audit()` is cleanest.

#### Modified function: `run_audit()`

After `events = sim_step(sim, inp)`, check for `DeathEvent`:

```python
for frame in range(expectation.max_frames):
    if sim.goal_reached or sim.player_dead:
        break

    inp = archetype_fn(frame, sim)
    events = sim_step(sim, inp)
    snapshots.append(_capture_snapshot(sim, frame + 1))
    events_per_frame.append(events)

    # Respawn after death
    if any(isinstance(e, DeathEvent) for e in events):
        if sim.deaths > expectation.max_deaths:
            sim.player_dead = True
        else:
            _respawn_player(sim)
```

New import needed: `DeathEvent` is already imported (line 18).
New import needed: `PlayerState` — add to existing imports from `speednik.player`.

### 2. `tests/test_qa_framework.py` (test additions)

**Change**: Add tests for the respawn behavior in `run_audit()`.

#### New test class: `TestAuditRespawn`

Tests to add:
- `test_respawn_after_pit_death`: Create a sim with a gap, run an archetype that falls in,
  verify that the player respawns at checkpoint/start and continues
- `test_death_budget_terminates`: Set `max_deaths=0`, verify that a single death sets
  `player_dead = True` and the loop terminates
- `test_respawn_preserves_checkpoint_rings`: Activate a checkpoint with rings, die, verify
  respawn has the checkpointed ring count
- `test_max_x_tracks_across_respawns`: Die, respawn, continue — `max_x_reached` should
  reflect the best progress across all lives

These tests should use synthetic grids (build_gap) to create controllable pit-death
scenarios, not real stages. This keeps them fast and deterministic.

## Files NOT Modified

- `speednik/simulation.py`: No changes. `sim_step()` already correctly signals death via
  `DeathEvent` and `player.state = DEAD`. The `player_dead` flag semantics are correct as
  "caller-set permanent death signal."
- `speednik/player.py`: No changes. Player already carries respawn data.
- `speednik/objects.py`: No changes. Checkpoint collision already updates respawn fields.
- `speednik/constants.py`: No changes.
- `speednik/main.py`: No changes. Game respawn is independent.
- `tests/test_audit_skybridge.py`: No changes in this ticket. Xfail markers referencing
  T-013-03-BUG-02 will need updating when this fix lands, but that's a separate ticket
  concern (T-013-03 itself).

## Module Boundaries

- `simulation.py` owns `sim_step()` — signals events, advances physics
- `qa.py` owns `run_audit()` — interprets events, applies policy (respawn/terminate)
- `player.py` owns `Player` — carries respawn coordinates, state machine
- `objects.py` owns checkpoint collision — updates `Player.respawn_*` fields

The respawn helper in `qa.py` reaches into `sim.player` to reset physics and state. This
is acceptable because `qa.py` already imports `PlayerState` and directly reads `sim.player`
throughout `_capture_snapshot()` and `_build_findings()`.

## Ordering

1. Add `_respawn_player()` helper to `qa.py`
2. Modify `run_audit()` loop to call it
3. Add tests to `test_qa_framework.py`
4. Run tests to verify

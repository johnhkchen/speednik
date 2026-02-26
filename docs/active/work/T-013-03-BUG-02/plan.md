# Plan — T-013-03-BUG-02: audit-no-respawn-after-pit-death

## Step 1: Add `_respawn_player()` helper to `speednik/qa.py`

Add a private function between the snapshot capture section and the archetype factories:

```python
def _respawn_player(sim: SimState) -> None:
    """Reset the player to checkpoint/start position after death."""
    p = sim.player
    p.state = PlayerState.STANDING
    p.physics.x = p.respawn_x
    p.physics.y = p.respawn_y
    p.physics.x_vel = 0.0
    p.physics.y_vel = 0.0
    p.physics.ground_speed = 0.0
    p.physics.on_ground = True
    p.physics.is_rolling = False
    p.physics.is_charging_spindash = False
    p.rings = p.respawn_rings
    p.invulnerability_timer = 0
    p.scattered_rings = []
    p.in_pipe = False
```

Add `PlayerState` to the existing import from `speednik.player` (line 19).

**Verification**: Module imports cleanly (`python -c "from speednik.qa import _respawn_player"`).

## Step 2: Modify `run_audit()` loop to handle death events

In the `run_audit()` function, after `events_per_frame.append(events)`, add:

```python
    # Respawn after death or terminate if budget exceeded
    if any(isinstance(e, DeathEvent) for e in events):
        if sim.deaths > expectation.max_deaths:
            sim.player_dead = True
        else:
            _respawn_player(sim)
```

The `DeathEvent` import already exists (line 18).

**Verification**: Existing tests still pass (`uv run pytest tests/test_qa_framework.py -x`).

## Step 3: Add respawn tests to `tests/test_qa_framework.py`

Add a new `TestAuditRespawn` class with these tests:

### 3a. `test_respawn_after_pit_death`

Create a gap sim where walker falls into the pit. Set `max_deaths=1` so one death is within
budget. Run `run_audit()` (or manually simulate the loop). After death+respawn, verify:
- `sim.deaths == 1`
- `sim.player.state != PlayerState.DEAD`
- `sim.player.physics.x` is near respawn coordinates
- Player continued to make progress after respawn

### 3b. `test_death_budget_exceeded_terminates`

Create a gap sim. Set `max_deaths=0`. Death should set `sim.player_dead = True` and the
loop should terminate early (fewer frames than max_frames).

### 3c. `test_max_x_tracks_across_respawns`

Verify that `sim.max_x_reached` reflects the best x-progress before death, not the respawn
position. After respawn, continued progress should update `max_x_reached` further.

### 3d. `test_respawn_resets_player_state`

Verify that after respawn, the player is in STANDING state with zero velocities and
on_ground=True.

**Verification**: All new tests pass (`uv run pytest tests/test_qa_framework.py -x -v`).

## Step 4: Run full test suite

Run `uv run pytest tests/test_qa_framework.py tests/test_audit_skybridge.py -v` to verify:
- All existing qa framework tests still pass
- Skybridge audit tests may change behavior (some xfails may flip) — document but don't
  change xfail markers in this ticket

## Testing Strategy

- **Unit tests** (Step 3): Synthetic grids only. `build_gap()` creates a controlled pit.
  Walker archetype walks into the gap deterministically. Tests verify respawn mechanics
  without depending on real stage data.
- **Integration verification** (Step 4): Run skybridge audit tests to see how respawn
  changes behavior. If any xfails flip, that's evidence the fix works but we don't modify
  those test files in this ticket.
- **No Pyxel dependency**: All changes are in the headless simulation layer. No imports
  from pyxel.

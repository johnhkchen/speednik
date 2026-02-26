# Structure — T-012-05: Cross-Stage Behavioral Invariants

## Files

### Created
- `tests/test_audit_invariants.py` — All 8 cross-stage behavioral invariant tests

### Not Modified
- No existing files are modified. This ticket adds a new test file only.

## Module Layout: tests/test_audit_invariants.py

```
Module docstring
Imports
Constants (STAGES list)
Helper functions section
  _place_buzzer(sim, dx, dy)
  _run_frames(sim, inp, n)
  _run_until_event(sim, inp, event_type, max_frames)
  _spindash_inputs(frame) → InputState
  _simple_camera_x(player_xs, start_camera_x) → list[float]
Invariant tests section (8 tests, each parametrized × 3 stages = 24 test cases)
  test_damage_with_rings_scatters(stage)
  test_damage_without_rings_kills(stage)
  test_invulnerability_after_damage(stage)
  test_wall_recovery(stage)
  test_slope_adhesion_at_low_speed(stage)
  test_fall_below_level_bounds(stage)
  test_spindash_reaches_base_speed(stage)
  test_camera_tracks_player(stage)
```

## Constants

```python
STAGES = ["hillside", "pipeworks", "skybridge"]
```

## Imports

```python
from speednik.simulation import create_sim, sim_step, DamageEvent, DeathEvent
from speednik.physics import InputState
from speednik.player import PlayerState
from speednik.constants import (
    INVULNERABILITY_DURATION,
    SPINDASH_BASE_SPEED,
    SCREEN_WIDTH,
    CAMERA_LEFT_BORDER,
    CAMERA_RIGHT_BORDER,
    CAMERA_H_SCROLL_CAP,
)
from speednik.enemies import Enemy
```

## Helper Functions

### _place_buzzer(sim, dx=40.0, dy=0.0)
Copied from test_entity_interactions.py. Injects a buzzer enemy at player.x + dx, player.y + dy.

### _run_frames(sim, inp, n)
Step sim N frames, return all events. Stop early on player_dead.

### _run_until_event(sim, inp, event_type, max_frames=300)
Step until event_type appears or max_frames reached. Returns (all_events, found).

### _spindash_inputs(frame)
Returns InputState for a scripted spindash sequence:
- Frame 0: down_held=True (enter spindash)
- Frames 1-3: down_held=True, jump_pressed=True, jump_held=True (charge)
- Frame 4+: right=True (release and run)

### _simple_camera_x(player_xs, start_camera_x)
Minimal camera model that scrolls to keep player within [camera_x + LEFT_BORDER, camera_x + RIGHT_BORDER], capped at H_SCROLL_CAP per frame.

## Test Function Signatures

Each test:
1. Creates sim via `create_sim(stage)`
2. Sets up preconditions (rings, enemies, position)
3. Steps simulation with controlled inputs
4. Asserts on specific behavioral outcome

No xfail markers. All 24 test cases (8 invariants × 3 stages) must pass.
If any fail, they are genuine bugs and get bug tickets.

## Interface Boundaries

- Tests depend only on speednik public APIs (simulation, physics, player, constants, enemies)
- No dependency on qa.py audit infrastructure (those are for progression testing)
- No dependency on terrain internals (tile lookups, sensors)
- No Pyxel imports

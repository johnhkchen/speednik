# T-013-01 Structure: World Boundary System

## Files Modified

### 1. speednik/constants.py

Add one constant:
```
PIT_DEATH_MARGIN = 32  # pixels below level_height before death
```

Location: After existing `DEATH_DELAY_FRAMES` / death-related constants (~line 110).

### 2. speednik/simulation.py

#### a. sim_step() — Add boundary enforcement block

Insert after `player_update(sim.player, inp, sim.tile_lookup)` (line 222) and before
the "Track progress" line (line 227).

New block (~15 lines):
- Get `p = sim.player.physics`
- Left clamp: if x < 0 → set x=0, zero negative x_vel and ground_speed
- Right clamp: if x > level_width → set x=level_width, zero positive x_vel and ground_speed
- Pit death: if y > level_height + PIT_DEATH_MARGIN → set player state to DEAD,
  emit DeathEvent, increment sim.deaths

Import additions: `PIT_DEATH_MARGIN` from constants, `PlayerState` from player.

#### b. create_sim_from_lookup() — Add optional kwargs

Change signature from:
```python
def create_sim_from_lookup(tile_lookup, start_x, start_y) -> SimState:
```
to:
```python
def create_sim_from_lookup(
    tile_lookup, start_x, start_y,
    *, level_width=99999, level_height=99999,
) -> SimState:
```

Use the kwargs in the SimState constructor instead of hardcoded values.

### 3. tests/test_invariants.py (indirectly fixed)

The existing `make_sim()` helper passes `level_width=...` / `level_height=...` kwargs
to `create_sim_from_lookup`. With the signature fix in simulation.py, these calls will
work correctly. No changes needed to the test file itself.

### 4. New test file: tests/test_world_boundary.py

Dedicated test file for world boundary behavior. Tests exercise `sim_step()` directly.

Test classes:

**TestLeftBoundary**
- `test_left_clamp_stops_at_zero`: Player moving left past x=0 gets clamped
- `test_left_clamp_zeros_velocity`: x_vel and ground_speed zeroed on clamp
- `test_left_boundary_no_death`: Player doesn't die at left boundary

**TestRightBoundary**
- `test_right_clamp_stops_at_level_width`: Player moving right past level_width gets clamped
- `test_right_clamp_zeros_velocity`: x_vel and ground_speed zeroed on clamp

**TestPitDeath**
- `test_pit_death_triggers_below_level_height`: Player below level_height + 32 dies
- `test_pit_death_emits_death_event`: DeathEvent in returned events list
- `test_pit_death_increments_deaths_counter`: sim.deaths incremented
- `test_no_death_above_pit_threshold`: Player at level_height + 31 survives
- `test_pit_death_regardless_of_rings`: Death occurs even with rings > 0

## Module Boundaries

The boundary enforcement is entirely within `sim_step()`. It does not:
- Modify player.py (no changes to player_update or damage_player)
- Modify physics.py (no changes to physics pipeline)
- Modify terrain.py (no changes to collision resolution)
- Add new modules

The change is localized to the sim_step function, which is the game-logic coordinator.

## Interface Contracts

### sim_step post-conditions (new)

After `sim_step()` returns:
- `player.physics.x >= 0` (left boundary)
- `player.physics.x <= sim.level_width` (right boundary)
- If `player.physics.y > sim.level_height + PIT_DEATH_MARGIN`, player is in DEAD state

### create_sim_from_lookup signature (updated)

```python
def create_sim_from_lookup(
    tile_lookup: TileLookup,
    start_x: float,
    start_y: float,
    *,
    level_width: int = 99999,
    level_height: int = 99999,
) -> SimState:
```

Backward compatible: existing callers without kwargs get same behavior (99999 defaults).

## Ordering

1. constants.py change (trivial, no dependencies)
2. simulation.py create_sim_from_lookup kwargs (fixes test infrastructure)
3. simulation.py sim_step boundary logic (core feature)
4. tests/test_world_boundary.py (validates feature)

Steps 1 and 2 can be committed together as infrastructure. Step 3 is the feature.
Step 4 is the test suite.

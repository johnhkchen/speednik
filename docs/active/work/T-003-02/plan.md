# Plan — T-003-02: Game Objects

## Step 1: Add constants

**File:** `speednik/constants.py`

Add spring, checkpoint, pipe, and liquid constants after the existing ring/damage section. Values:
- `SPRING_UP_VELOCITY = -10.0`
- `SPRING_RIGHT_VELOCITY = 10.0`
- `SPRING_HITBOX_W = 16`
- `SPRING_HITBOX_H = 16`
- `SPRING_COOLDOWN_FRAMES = 8`
- `CHECKPOINT_ACTIVATION_RADIUS = 20`
- `PIPE_ENTRY_HITBOX_W = 24`
- `PIPE_ENTRY_HITBOX_H = 24`
- `LIQUID_RISE_SPEED = 1.0`

**Verify:** Import succeeds, no syntax errors.

---

## Step 2: Add Player fields and pipe bypass

**File:** `speednik/player.py`

Add to Player dataclass:
- `respawn_x: float = 0.0`
- `respawn_y: float = 0.0`
- `respawn_rings: int = 0`
- `in_pipe: bool = False`

Modify `create_player()` to set `respawn_x=x, respawn_y=y`.

Modify `player_update()` to early-return when `player.in_pipe is True` (skip all physics, collision, and state machine — pipe system handles movement).

**Verify:** Existing test_rings.py tests still pass.

---

## Step 3: Implement springs in objects.py

**File:** `speednik/objects.py`

Add:
- `SpringEvent` enum with `LAUNCHED`
- `Spring` dataclass with `x, y, direction, cooldown`
- `load_springs()` — filter entities by types starting with `"spring_"`
- `aabb_overlap()` helper
- `check_spring_collision(player, springs)` — AABB check against player rect, velocity override based on direction, set cooldown
- `update_spring_cooldowns(springs)` — decrement cooldowns

Import `get_player_rect` from player.py. Import spring constants from constants.py.

**Verify:** Write spring unit tests (Step 7), run them.

---

## Step 4: Implement checkpoints in objects.py

**File:** `speednik/objects.py`

Add:
- `CheckpointEvent` enum with `ACTIVATED`
- `Checkpoint` dataclass with `x, y, activated`
- `load_checkpoints()` — filter by `"checkpoint"` type
- `check_checkpoint_collision(player, checkpoints)` — distance-based, set `player.respawn_x/y/rings`, mark activated

**Verify:** Write checkpoint unit tests (Step 7), run them.

---

## Step 5: Implement launch pipes in objects.py

**File:** `speednik/objects.py`

Add:
- `PipeEvent` enum with `ENTERED, EXITED`
- `LaunchPipe` dataclass with `x, y, exit_x, exit_y, vel_x, vel_y`
- `load_pipes()` — filter by `"pipe_h"` and `"pipe_v"` types, extract extra fields
- `update_pipe_travel(player, pipes)`:
  - If not `in_pipe`: check AABB overlap with each pipe entry zone → set `in_pipe=True`, override velocity, set invulnerability
  - If `in_pipe`: move player by pipe velocity, check if player reached exit → clear `in_pipe`, restore normal state

**Verify:** Write pipe unit tests (Step 7), run them.

---

## Step 6: Implement liquid zones in objects.py

**File:** `speednik/objects.py`

Add:
- `LiquidEvent` enum with `STARTED_RISING, DAMAGE`
- `LiquidZone` dataclass with `trigger_x, exit_x, floor_y, ceiling_y, current_y, active`
- `load_liquid_zones()` — filter by `"liquid_trigger"`, extract zone fields
- `update_liquid_zones(player, zones)`:
  - Activate when `player.x > trigger_x` and `player.x < exit_x`
  - Deactivate when `player.x >= exit_x`
  - While active: `current_y -= LIQUID_RISE_SPEED` (rises toward ceiling)
  - Damage check: if player overlaps liquid surface, call `damage_player()`

**Verify:** Write liquid unit tests (Step 7), run them.

---

## Step 7: Write tests

**File:** `tests/test_game_objects.py`

Test classes and cases:

**TestLoadSprings:**
- Loads spring_up and spring_right entities
- Ignores non-spring entities
- Parses direction from type string

**TestSpringCollision:**
- Up spring overrides y_vel to SPRING_UP_VELOCITY
- Right spring overrides x_vel to SPRING_RIGHT_VELOCITY
- Spring sets player airborne (on_ground=False)
- Cooldown prevents re-trigger
- Out-of-range player not affected
- Dead/hurt player not affected

**TestCheckpointActivation:**
- First contact saves respawn position and rings
- Already-activated checkpoint does not re-trigger
- Respawn data reflects checkpoint position

**TestPipeTravel:**
- Player entering pipe zone sets in_pipe=True
- Pipe overrides velocity correctly
- Player reaching exit clears in_pipe
- Player invulnerable during pipe travel

**TestLiquidRise:**
- Liquid activates when player crosses trigger_x
- Liquid rises at LIQUID_RISE_SPEED per update
- Liquid stops at ceiling_y
- Liquid deactivates when player exits zone
- Liquid contact applies damage
- Invulnerable player not damaged by liquid

**Verify:** `uv run pytest tests/test_game_objects.py -v` — all pass.

---

## Step 8: Add entity data for pipeworks

**File:** `speednik/stages/pipeworks/entities.json`

Add 4 pipe_h entries in the 800–2800px range with entry/exit coordinates and velocity vectors. Add 1 liquid_trigger entry for the section 3 zone (trigger_x=2800, exit_x=3800, floor_y=1024, ceiling_y=384).

**Verify:** JSON is valid, stage loads without error.

---

## Step 9: Integrate into main.py

**File:** `speednik/main.py`

- Import new loaders and collision functions from objects.py
- Import new SFX constants from audio.py
- In `__init__`: load springs, checkpoints, pipes, liquid zones from entity data
- In `update()`: call collision/update functions, map events to SFX
- In `draw()`: render springs (red rectangles), checkpoints (posts with color), pipes (rectangles with arrows), liquid (blue fill)

**Verify:** Game runs, objects visible, SFX play on interaction.

---

## Step 10: Run full test suite

`uv run pytest -v`

All existing tests + new tests pass. No regressions.

---

## Testing Strategy Summary

| Object | Test Type | Key Assertions |
|--------|-----------|----------------|
| Springs | Unit | Velocity override, cooldown, direction, player state guards |
| Checkpoints | Unit | Save position/rings, one-shot, distance boundary |
| Pipes | Unit | Entry/exit, velocity override, in_pipe flag, invulnerability |
| Liquid | Unit | Trigger/deactivation, rise speed, ceiling cap, damage, invulnerability guard |
| Loading | Unit | Type filtering, field extraction, empty input |
| Integration | Manual | Game runs, objects render, SFX play |

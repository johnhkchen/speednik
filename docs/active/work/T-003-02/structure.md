# Structure — T-003-02: Game Objects

## Files Modified

### speednik/constants.py

Add new constants:

```
SPRING_UP_VELOCITY = -10.0
SPRING_RIGHT_VELOCITY = 10.0
SPRING_HITBOX_W = 16
SPRING_HITBOX_H = 16
SPRING_COOLDOWN_FRAMES = 8
CHECKPOINT_ACTIVATION_RADIUS = 20
PIPE_LAUNCH_SPEED_H = 10.0
PIPE_LAUNCH_SPEED_V = -10.0
LIQUID_RISE_SPEED = 1.0
```

### speednik/objects.py

Extend with four new object systems alongside existing Ring code. Keep the same architecture:

**New dataclasses:**
- `Spring(x, y, direction, cooldown)` — direction is `"up"` or `"right"`
- `Checkpoint(x, y, activated)` — one-shot trigger
- `LaunchPipe(x, y, exit_x, exit_y, vel_x, vel_y, width, height)` — rectangular zone with exit
- `LiquidZone(trigger_x, exit_x, floor_y, ceiling_y, current_y, active, rising)` — zone state machine

**New event enums:**
- `SpringEvent(LAUNCHED)` — triggers SFX_SPRING
- `CheckpointEvent(ACTIVATED)` — triggers SFX_CHECKPOINT
- `PipeEvent(ENTERED, EXITED)` — triggers entry/exit behaviors
- `LiquidEvent(STARTED_RISING, DAMAGE)` — triggers SFX_LIQUID_RISING, damage

**New loader functions:**
- `load_springs(entities) -> list[Spring]`
- `load_checkpoints(entities) -> list[Checkpoint]`
- `load_pipes(entities) -> list[LaunchPipe]`
- `load_liquid_zones(entities) -> list[LiquidZone]`

**New update/collision functions:**
- `check_spring_collision(player, springs) -> list[SpringEvent]` — AABB overlap, velocity override, cooldown management
- `check_checkpoint_collision(player, checkpoints) -> list[CheckpointEvent]` — distance check, save respawn data
- `update_pipe_travel(player, pipes) -> list[PipeEvent]` — entry detection, travel update, exit detection
- `update_liquid_zones(player, zones) -> list[LiquidEvent]` — trigger activation, level rise, damage check

**Helper function:**
- `aabb_overlap(ax, ay, aw, ah, bx, by, bw, bh) -> bool` — shared by springs and pipes

**Spring cooldown update:**
- `update_spring_cooldowns(springs) -> None` — decrements cooldown timers each frame

### speednik/player.py

Add fields to `Player` dataclass:
- `respawn_x: float = 0.0` — checkpoint respawn X
- `respawn_y: float = 0.0` — checkpoint respawn Y
- `respawn_rings: int = 0` — checkpoint saved ring count
- `in_pipe: bool = False` — currently traveling through a pipe

Modify `create_player(x, y)` to set `respawn_x = x`, `respawn_y = y`.

Modify `player_update()` to early-return (skip normal physics) when `in_pipe is True`. The pipe system in objects.py handles movement during pipe travel.

### speednik/stages/pipeworks/entities.json

Add pipe and liquid entities:
- 4 `pipe_h` entries with `exit_x`, `exit_y`, `vel_x`, `vel_y` fields
- 1 `liquid_trigger` entry with `exit_x`, `floor_y`, `ceiling_y` fields

### speednik/main.py

Extend update loop to call new object functions after ring collection. Extend draw loop to render springs, checkpoints, pipes, liquid.

Integration order in update():
1. `player_update()` (existing)
2. `check_ring_collection()` (existing)
3. `check_spring_collision()` (new)
4. `check_checkpoint_collision()` (new)
5. `update_pipe_travel()` (new)
6. `update_liquid_zones()` (new)
7. `update_spring_cooldowns()` (new)
8. `update_audio()` (existing)
9. `camera_update()` (existing)

## Files Created

### tests/test_game_objects.py

New test file covering springs, checkpoints, pipes, and liquid zones. Follows patterns from test_rings.py.

Test classes:
- `TestLoadSprings` — loader filtering, direction parsing
- `TestSpringCollision` — velocity override, cooldown, direction variants
- `TestLoadCheckpoints` — loader filtering
- `TestCheckpointActivation` — save/restore, one-shot behavior
- `TestLoadPipes` — loader with extra fields
- `TestPipeTravel` — entry, travel, exit, invulnerability
- `TestLoadLiquidZones` — loader with zone fields
- `TestLiquidRise` — trigger activation, rise speed, damage, deactivation

## Module Boundaries

- **objects.py** owns all game object logic. It imports `Player`, `PlayerState` from player.py and `PhysicsState` from physics.py (for direct velocity mutation on springs/pipes). It does NOT import pyxel.
- **main.py** owns rendering and SFX mapping. It calls objects.py functions and maps returned events to `play_sfx()` calls.
- **player.py** owns player state machine. It checks `in_pipe` to skip physics. It does NOT know about springs, pipes, or liquid.
- **constants.py** owns all tuning values. Objects.py imports constants, never hardcodes.

## Ordering

1. Constants first (no dependencies)
2. Player.py changes (adds fields, no logic change beyond pipe check)
3. objects.py (depends on constants + player)
4. Entity data (pipeworks entities.json)
5. Tests (depends on objects.py)
6. main.py integration (depends on everything above)

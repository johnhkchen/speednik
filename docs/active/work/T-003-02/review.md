# Review — T-003-02: Game Objects

## Summary of Changes

### Files Modified

**speednik/constants.py** — Added 10 new constants for springs, checkpoints, pipes, and liquid rise. Organized in sections matching spec references.

**speednik/player.py** — Added 4 fields to Player dataclass: `respawn_x`, `respawn_y`, `respawn_rings` (checkpoint save/restore), `in_pipe` (pipe travel state). Modified `create_player()` to initialize respawn coordinates from start position. Added early-return in `player_update()` when `in_pipe` is True to bypass normal physics during pipe travel.

**speednik/objects.py** — Extended from ring-only to a full game object module. Added:
- 4 new event enums: `SpringEvent`, `CheckpointEvent`, `PipeEvent`, `LiquidEvent`
- 4 new entity dataclasses: `Spring`, `Checkpoint`, `LaunchPipe`, `LiquidZone`
- 4 loader functions: `load_springs()`, `load_checkpoints()`, `load_pipes()`, `load_liquid_zones()`
- 4 collision/update functions: `check_spring_collision()`, `check_checkpoint_collision()`, `update_pipe_travel()`, `update_liquid_zones()`
- Helper: `aabb_overlap()` for box-based collision (springs, pipes)
- Helper: `update_spring_cooldowns()` for per-frame cooldown decay

**speednik/main.py** — Integrated all new object systems into update loop (collision checks, event-to-SFX mapping) and draw loop (springs as red rectangles, checkpoints as posts, pipes as rectangles, liquid as animated blue fill).

**speednik/stages/pipeworks/entities.json** — Added `exit_x`, `exit_y`, `vel_x`, `vel_y` fields to existing 4 pipe_h entities. Added `exit_x`, `floor_y`, `ceiling_y` fields to existing liquid_trigger entity.

### Files Created

**tests/test_game_objects.py** — 43 unit tests across 10 test classes.

---

## Test Coverage

| Object | Tests | Coverage |
|--------|-------|----------|
| AABB helper | 3 | Overlap, non-overlap, edge touching |
| Spring loading | 4 | Up/right types, filtering, empty |
| Spring collision | 8 | Velocity override (up/right), cooldown set/prevent/decrement, out-of-range, dead/hurt guards |
| Checkpoint loading | 3 | Load, filter, empty |
| Checkpoint activation | 5 | Save respawn, one-shot, out-of-range, boundary distance, dead guard |
| Pipe loading | 4 | pipe_h/pipe_v, filter, empty |
| Pipe travel | 6 | Entry, invulnerability, movement, exit, dead guard, out-of-range |
| Liquid loading | 3 | Load, filter, empty |
| Liquid rise | 7 | Activation, deactivation, rise speed, ceiling cap, damage, invulnerability guard, pre-trigger |

**Total: 43 new tests. Full suite: 409 tests, 0 failures.**

### Coverage Gaps

- No test for spring horizontal momentum preservation (up spring keeps x velocity from ground_speed)
- No test for pipe vertical travel (only horizontal pipes tested with exit detection)
- No test for liquid zone reset (liquid doesn't recede when player leaves — per spec, it just stops rising)
- No integration test for main.py rendering of objects (requires Pyxel, manual verification)

---

## Design Decisions

1. **AABB for springs/pipes, distance for checkpoints** — Springs and pipes are directional surfaces with rectangular trigger zones per spec. Checkpoints are proximity triggers.

2. **Velocity override (not additive)** — Springs replace velocity rather than adding to it, matching Sonic 2 behavior where springs always launch at a consistent height/speed.

3. **Pipe as boolean flag** — `player.in_pipe` flag rather than a new PlayerState enum value. Simpler integration: player_update early-returns, pipe system handles movement.

4. **Invulnerability during pipe travel** — Set to 9999 frames on entry, cleared on exit. Prevents damage during transport.

5. **Liquid zones as entities** — Loaded from entities.json with trigger_x/exit_x/floor_y/ceiling_y fields, keeping the loading pattern consistent with all other objects.

---

## Open Concerns

1. **Pipe travel detection** — The exit detection in `update_pipe_travel()` iterates all pipes to find which one the player is in. This works but could mismatch if two pipes share similar coordinates. A cleaner approach would be storing a reference to the active pipe on the player. Low risk with current data (4 pipes, non-overlapping).

2. **Liquid doesn't recede** — Per spec, liquid rises when active and stops when player exits zone. It does NOT recede. If the player re-enters the zone, rising resumes from the current level. This matches implementation but may need clarification if level designers expect reset behavior.

3. **Missing pipe_v entities** — No vertical pipes exist in current stage data. The loader supports `pipe_v` type but the exit detection logic only handles axis-aligned travel. Diagonal pipes would need additional logic.

4. **Demo mode objects empty** — main.py loads empty object lists in demo mode (no stage data). Objects are only active when loading a real stage. This is correct for the current demo but means manual testing requires switching to a real stage loader.

5. **Respawn system not yet active** — Checkpoint save/restore writes to `player.respawn_x/y/rings` but nothing reads those values yet. The death/respawn system is a future ticket concern.

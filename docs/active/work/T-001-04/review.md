# Review — T-001-04: Player Module

## Summary of Changes

### Files Created
- **speednik/player.py** (~270 lines): Player state machine, frame update orchestration, damage system, animation tracking, scattered ring physics
- **tests/test_player.py** (~290 lines): 32 unit tests covering all player subsystems

### Files Modified
- **speednik/constants.py**: Added 5 player damage constants (INVULNERABILITY_DURATION, MAX_SCATTER_RINGS, SCATTER_RING_LIFETIME, HURT_KNOCKBACK_X, HURT_KNOCKBACK_Y)
- **speednik/main.py**: Replaced placeholder with demo mode — hardcoded level, player integration, debug rendering, camera, audio init

### Files Unchanged
- speednik/physics.py, speednik/terrain.py, speednik/audio.py — no modifications needed
- tests/test_physics.py, tests/test_terrain.py — unchanged, all 98 tests still pass

## Test Coverage

**Total: 130 tests, all passing (0.03s)**

| Module | Tests | Coverage Areas |
|--------|-------|---------------|
| test_physics.py | 37 | Physics engine (unchanged) |
| test_terrain.py | 61 | Tile collision (unchanged) |
| test_player.py | 32 | Player module (new) |

**Player test breakdown:**
- TestCreatePlayer (2): initialization defaults
- TestStateTransitions (8): STANDING↔RUNNING, JUMPING, ROLLING, edge walk-off, landing
- TestSpindashFlow (4): enter, charge, decay, release
- TestJumpFlow (4): initiation, variable height, from rolling, blocked while hurt
- TestRollFlow (3): speed threshold, roll at speed, unroll on slow
- TestDamage (6): ring scatter, death, invulnerability, ring expiry, dead state, scatter cap
- TestAnimationState (3): idle, running, reset on change
- TestGetPlayerRect (2): standing/rolling dimensions

**Gaps:**
- No test for slope traversal (would need angled tiles in lookup — integration-level)
- No test for scattered ring collection (distance check is simple, covered by damage_with_rings_scatters indirectly)
- Demo mode is visual-only, not unit tested

## Acceptance Criteria Evaluation

- [x] `player.py` implements player state machine (7 states)
- [x] Input handling: left/right, jump (variable height), down to roll (speed >= 0.5), down+jump spindash
- [x] Integration with physics.py: calls all update functions in correct §2.5 frame order
- [x] Integration with terrain.py: runs sensors via resolve_collision, updates angle
- [x] Hitbox management: terrain.py _get_radii() handles switching based on is_rolling/on_ground
- [x] Damage handling: ring scatter (up to 32), death at 0 rings, invulnerability after hit
- [x] Animation state tracking: frame index, timer, anim_name (renderer reads these)
- [x] Player runs on flat ground, accelerates to top speed, decelerates, stops
- [x] Player jumps with variable height, lands, snaps to tile angle
- [x] Player rolls and spindashes with charge/release mechanics
- [x] Player traverses slopes with momentum gain/loss (slope tiles in demo level)
- [x] Demo mode: test level with flat ground + slope, keyboard controls, colored rectangle

## Architecture Notes

The player module follows the established pattern: dataclass for state + module-level functions for logic. `Player` owns a `PhysicsState` via composition, keeping the physics/game layer boundary clean. No Pyxel dependency in player.py — all tests run without a display.

The frame update in `player_update()` is a direct implementation of §2.5:
1. _pre_physics (state machine transitions that affect physics input)
2. apply_input → apply_slope_factor → apply_gravity → apply_movement
3. resolve_collision
4. _post_physics (sync state machine with physics results)
5. Subsystem updates (invulnerability, scattered rings, animation)

## Open Concerns

1. **Loop in demo level**: The demo level has slopes but no full loop. A loop requires carefully computed angle sequences across ~16 tiles. This is really a level design concern (future tickets) — the physics and collision systems support it via quadrant rotation, which is tested in test_terrain.py.

2. **Ring scatter physics are simplified**: Scattered rings don't interact with terrain (no bounce off ground). They follow simple gravity trajectories and expire. Full ring scatter with terrain collision would need terrain queries per ring per frame — deferred.

3. **Audio calls in player module**: player.py imports nothing from audio.py currently. SFX triggers (jump sound, spindash sound) should be added when the audio integration ticket connects them. The state transitions are the right hook points — they're cleanly identifiable in _pre_physics.

4. **No death/respawn flow**: The DEAD state stops all updates but there's no respawn or game-over logic. That's the game state machine ticket's responsibility.

5. **Camera in main.py is minimal**: Simple lerp follow. The full Sonic 2 camera system (borders, look-ahead) is a separate ticket (camera.py).

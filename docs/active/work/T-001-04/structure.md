# Structure — T-001-04: Player Module

## Files Modified

### speednik/main.py (major rewrite)
Replace the placeholder App with demo mode integration:
- Import player module and terrain types
- Build hardcoded demo level tile lookup
- Create Player instance
- Read Pyxel input → InputState each frame
- Call `player_update()` each frame
- Draw debug visualization (colored rect, tile outlines, HUD text)
- Initialize audio

### speednik/constants.py (minor additions)
Add player-specific constants:
- `INVULNERABILITY_DURATION = 120` (2 seconds at 60fps)
- `MAX_SCATTER_RINGS = 32`
- `SCATTER_RING_LIFETIME = 180` (3 seconds)
- `HURT_KNOCKBACK_X = 2.0`
- `HURT_KNOCKBACK_Y = -4.0`

## Files Created

### speednik/player.py (~300 lines)
The player module. Contains:

**Data structures:**
```
PlayerState(Enum): STANDING, RUNNING, JUMPING, ROLLING, SPINDASH, HURT, DEAD

ScatteredRing(dataclass):
    x, y: float
    vx, vy: float
    timer: int

Player(dataclass):
    physics: PhysicsState
    state: PlayerState
    rings: int
    lives: int
    invulnerability_timer: int
    anim_frame: int
    anim_timer: int
    scattered_rings: list[ScatteredRing]
```

**Public functions:**
```
create_player(x, y) -> Player
    Initialize a Player at given position.

player_update(player, inp, tile_lookup) -> None
    Full frame update: input → state machine → physics → collision → sync.

damage_player(player) -> None
    Apply damage: scatter rings or die.

get_player_rect(player) -> tuple[float, float, int, int]
    Return (x, y, width, height) for rendering.
```

**Internal functions:**
```
_pre_physics(player, inp) -> None
    Handle state transitions that occur before physics:
    jump initiation, roll start, spindash charge/release.

_post_physics(player) -> None
    Sync state machine with physics results:
    landing, detachment, unroll detection.

_update_animation(player) -> None
    Advance frame timer, compute animation frame.

_update_invulnerability(player) -> None
    Decrement timer, transition HURT → STANDING when expired and grounded.

_update_scattered_rings(player) -> None
    Move scattered rings, apply gravity, decrement timers, remove expired.

_scatter_rings(player) -> None
    Create ScatteredRing objects in a fan pattern.

_collect_scattered_ring(player, ring_index) -> None
    Add ring to player's count, remove from list.
```

### tests/test_player.py (~300 lines)
Unit tests for the player module. Pyxel-free.

**Test classes:**
```
TestCreatePlayer: initialization defaults
TestStateTransitions: each transition path
TestFrameUpdate: correct physics call ordering
TestSpindashFlow: crouch → charge → decay → release
TestJumpFlow: initiation, variable height, landing sync
TestRollFlow: initiation threshold, unroll
TestDamage: ring scatter, invulnerability, death
TestAnimationState: correct anim selection per state
TestScatteredRings: movement, collection, expiry
```

## Module Boundaries

```
main.py (Pyxel layer)
  │
  ├── reads Pyxel buttons → InputState
  ├── calls player_update(player, inp, tile_lookup)
  ├── calls update_audio()
  └── draws debug rect from get_player_rect()

player.py (game layer)
  │
  ├── owns Player dataclass (contains PhysicsState)
  ├── orchestrates physics.py functions (steps 1-4)
  ├── orchestrates terrain.py resolve_collision (steps 5-7)
  ├── manages state machine, rings, damage, animation
  └── calls audio.py play_sfx() on transitions

physics.py (physics layer) — unchanged
terrain.py (collision layer) — unchanged
constants.py (shared constants) — minor additions
audio.py (audio layer) — unchanged
```

## Ordering of Changes

1. Add constants to constants.py (no dependencies)
2. Create player.py (depends on physics.py, terrain.py, constants.py, audio.py)
3. Create tests/test_player.py (depends on player.py)
4. Rewrite main.py for demo mode (depends on all above)

Steps 1-3 have no Pyxel dependency and can be tested independently.
Step 4 is the Pyxel integration that produces the visual demo.

## Demo Level Layout

Hardcoded in main.py as a dict of `(tile_x, tile_y) -> Tile`:

```
Tiles 0-19, y=12: flat ground (height=[16]*16, angle=0, FULL)
Tiles 10-14, y=11: 30° upslope (height arrays with gradual rise, angle=~21 byte)
Tiles 20-27, y=8-12: simplified loop (8 tiles forming a circle, angles 0→64→128→192→0)
```

The loop is approximate — just enough angled tiles to test quadrant rotation. Full loop fidelity is a level design concern for later tickets.

Player start: pixel (64, 12*16 - STANDING_HEIGHT_RADIUS) = (64, 172)

Controls: arrow keys for movement, Z for jump, Q to quit.

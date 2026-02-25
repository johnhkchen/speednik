# Design — T-001-04: Player Module

## Approach: Thin Orchestrator over Existing Systems

The player module is a state machine that orchestrates physics.py and terrain.py calls in the correct frame order, manages player-specific state (rings, lives, invulnerability, animation), and handles input translation.

### Option A: Player Class Wrapping PhysicsState (Chosen)

A `Player` dataclass/class that owns a `PhysicsState` plus additional player-specific fields (state enum, rings, lives, invulnerability timer, animation state). Module-level functions operate on `Player`, similar to the physics.py pattern.

**Pros:** Consistent with existing dataclass + functions pattern. PhysicsState reuse. Testable without Pyxel.
**Cons:** Player struct gets large with all the extra fields.

### Option B: Player Inheriting PhysicsState

Extend PhysicsState with player fields via inheritance or composition.

**Rejected:** Inheritance couples player to physics implementation details. PhysicsState is a physics-layer concept; player state is a game-layer concept. Composition (option A) preserves this boundary cleanly.

### Option C: All State in PhysicsState

Add rings, lives, animation fields directly to PhysicsState.

**Rejected:** Violates separation of concerns. PhysicsState is used by terrain.py too. Adding game state there bloats the physics layer.

## State Machine Design

### States

```python
class PlayerState(Enum):
    STANDING = "standing"
    RUNNING = "running"
    JUMPING = "jumping"
    ROLLING = "rolling"
    SPINDASH = "spindash"
    HURT = "hurt"
    DEAD = "dead"
```

### Transition Logic

State transitions happen at specific points in the frame:

**Before physics (input phase):**
- STANDING + directional input + ground_speed != 0 → RUNNING
- RUNNING + no input + ground_speed == 0 → STANDING
- STANDING/RUNNING + down + |ground_speed| >= 0.5 → ROLLING (set `is_rolling = True`)
- STANDING + down held + ground_speed ~0 → enter spindash crouch
- SPINDASH + jump_pressed → charge spindash
- SPINDASH + down released → release spindash → ROLLING
- STANDING/RUNNING + jump_pressed → JUMPING (call `apply_jump`)
- ROLLING + jump_pressed → JUMPING (call `apply_jump`)

**After collision (post-physics):**
- JUMPING + on_ground (landing detected by resolve_collision) → STANDING or RUNNING
- ROLLING + |ground_speed| < MIN_ROLL_SPEED → STANDING (already in physics.py)
- Airborne from any ground state → JUMPING

**On damage event:**
- rings > 0 → HURT, scatter rings, start invulnerability timer
- rings == 0 → DEAD

### Frame Update Sequence

```
1. Read input → InputState
2. State machine: pre-physics transitions (jump initiation, spindash, roll start)
3. apply_input(physics_state, input_state)     [step 1]
4. apply_slope_factor(physics_state)            [step 2]
5. apply_gravity(physics_state)                 [step 3]
6. apply_movement(physics_state)                [step 4]
7. resolve_collision(physics_state, tile_lookup) [steps 5-7]
8. update_slip_timer(physics_state)
9. State machine: post-physics sync (landing, detach, unroll)
10. Update animation frame timer
11. Update invulnerability timer
```

## Hitbox Switching

The terrain system already reads `is_rolling` and `on_ground` from PhysicsState to select radii. The player module just needs to:
- Set `is_rolling = True` when entering ROLLING or SPINDASH release
- Set `is_rolling = False` when entering STANDING/RUNNING
- When in JUMPING, `on_ground = False` and terrain uses rolling radii (correct per §3.2)

No additional hitbox management needed — terrain.py handles it.

## Damage System

**On hit (external caller invokes `damage_player`):**
1. If invulnerable, ignore
2. If rings > 0: scatter rings (up to 32), set rings to 0, enter HURT state, start invulnerability timer (120 frames), apply knockback (small upward + backward velocity)
3. If rings == 0: enter DEAD state

**Ring scatter:** Simplified for this ticket — scattered rings are visual-only objects with simple physics (fan outward, gravity, disappear after 180 frames). They can be collected during the window. Represented as a list of `ScatteredRing` dataclasses updated each frame.

**Decision:** Keep scattered ring logic minimal — just position/velocity/timer. Ring collection check is a simple distance test against player position.

## Animation State

```python
@dataclass
class AnimationState:
    frame_index: int = 0
    frame_timer: int = 0
    anim_name: str = "idle"
```

Animation definitions (frame count, speed):
- idle: 1 frame (static)
- running: 4 frames, speed scales inversely with |ground_speed|
- rolling: 1 frame (rotation tracked by angle)
- spindash: 1 frame (charge visual)
- hurt: 1 frame (knockback pose)
- dead: 1 frame

The player module updates `frame_timer`, advances `frame_index`, and sets `anim_name` on state transitions. The renderer (future ticket) reads these values.

## Demo Mode

**Test level layout:**
- 20 tiles wide flat ground at y=12 (tile coords)
- 5-tile 30-degree upslope starting at x=10
- Simple loop at x=20 (radius ~8 tiles, approximated with steep angle tiles)
- Player start at pixel (64, 12*16 - 20) = (64, 172)

**Rendering (temporary):**
- Colored rectangle at player position, sized to current hitbox
- Tile outlines showing the level
- Ground speed / state text overlay for debugging
- Arrow keys + Z for jump

**Integration with main.py:**
- Modify `App` to create a `Player`, build a tile lookup from hardcoded tiles, run the player update each frame, and draw the debug view.

## Audio Integration

Player state transitions trigger SFX:
- Jump → `play_sfx(SFX_JUMP)`
- Spindash charge → `play_sfx(SFX_SPINDASH_CHARGE)`
- Spindash release → `play_sfx(SFX_SPINDASH_RELEASE)`
- Hurt → `play_sfx(SFX_HURT)`

Audio calls are made from the player update function at transition points. `init_audio()` and `update_audio()` are called from main.py.

## Testing Strategy

Player module tests must be Pyxel-free (test the update logic with InputState, not key presses).

Key test areas:
1. State transitions: each valid transition produces correct state
2. Frame update order: physics called in correct sequence
3. Spindash flow: crouch → charge → release → rolling with correct speed
4. Jump: initiation, variable height, landing → state sync
5. Roll: initiation threshold, unroll
6. Damage: ring scatter, invulnerability, death
7. Animation state: correct anim_name after transitions

Demo mode is not unit-tested (it's a Pyxel visual integration test).

# T-013-01 Research: World Boundary System

## Problem Statement

The simulation has no enforcement of world boundaries. Players can move arbitrarily far
in any direction — negative X, beyond level_width, and below level_height — without being
clamped or killed. This causes invariant violations in audit runs and means bottomless
pits don't kill the player.

## Current Architecture

### Position Update Chain

1. `sim_step()` (`simulation.py:211`) calls `player_update()` on each frame
2. `player_update()` (`player.py:109`) runs the physics pipeline:
   - `_pre_physics()` — state machine transitions
   - `apply_input()` — acceleration/friction (physics.py:98)
   - `apply_slope_factor()` — slope gravity (physics.py:223)
   - `apply_gravity()` — airborne gravity (physics.py:251)
   - `apply_movement()` — **position update: x += x_vel, y += y_vel** (physics.py:262)
   - `resolve_collision()` — terrain collision response (terrain.py)
3. After `player_update()`, `sim_step()` processes entity collisions (rings, springs,
   enemies, checkpoints, goal)

Position is modified at `physics.py:269-270`:
```python
state.x += state.x_vel
state.y += state.y_vel
```

### Existing Velocity Clamping

`apply_input()` at `physics.py:113-117` clamps speed but not position:
```python
# Hard clamp
if state.on_ground:
    state.ground_speed = max(-MAX_X_SPEED, min(MAX_X_SPEED, state.ground_speed))
else:
    state.x_vel = max(-MAX_X_SPEED, min(MAX_X_SPEED, state.x_vel))
```

MAX_X_SPEED = 16.0 px/frame (`constants.py:16`).

### No Position Boundary Logic

There is **zero** position clamping in the physics or simulation layer:
- `player_update()` doesn't check boundaries
- `sim_step()` doesn't check boundaries
- `resolve_collision()` only handles tile-based collision, not level edges
- The only "boundary" that exists is terrain tiles — if there's no terrain, the
  player falls/moves indefinitely

### Invariant Checker

`invariants.py:71-106` (`_check_position_bounds`) flags violations post-hoc:
- `position_x_negative`: x < 0
- `position_y_below_world`: y > level_height + POSITION_MARGIN (64px)
- `position_x_beyond_right`: x > level_width + POSITION_MARGIN (64px)

These detect violations but don't prevent them.

### Death/Respawn System

**damage_player()** (`player.py:252-276`):
- If rings > 0: scatter rings, enter HURT state with knockback, start invulnerability
- If rings == 0: set state to DEAD, apply upward knockback, set on_ground=False

**Death handling in sim_step** (`simulation.py:218-219`):
- `if sim.player_dead: return events` — skips all updates when dead
- But `player_dead` is a SimState field, NOT derived from `player.state == DEAD`

**Death handling in main.py** (`main.py:343-357`):
- Checks `player.state == PlayerState.DEAD`
- After DEATH_DELAY_FRAMES (120 frames): respawn or game over

**Respawn** (`main.py:531-548`):
- Uses `player.respawn_x`, `respawn_y`, `respawn_rings`
- Creates fresh player at respawn position
- Respawn coordinates set by checkpoint activation (`objects.py:321-323`)
- Initial respawn = player start position (`player.py:102`)

### SimState.player_dead vs PlayerState.DEAD

`SimState.player_dead` (`simulation.py:119`) is a separate boolean, default False.
Nothing currently sets it. `sim_step` checks it but it's always False. The actual
death state lives in `player.state == PlayerState.DEAD`.

When `player.state == PlayerState.DEAD`, `player_update()` returns early (`player.py:111`),
so the player stops moving. But `sim_step()` doesn't check `player.state` — it only
checks `sim.player_dead`.

### Level Dimensions

Stored in `SimState.level_width` and `SimState.level_height` (simulation.py:112-113).
Populated from `meta["width_px"]` / `meta["height_px"]` in `level.py:88-89`.

### create_sim_from_lookup

`create_sim_from_lookup()` (`simulation.py:181-204`) is used by tests to create synthetic
simulations. Currently sets `level_width=99999, level_height=99999` and does NOT accept
kwargs to override these. Test files (`test_invariants.py:63`, `test_qa_framework.py:47`)
pass `level_width=...` kwargs that cause TypeErrors.

### Checkpoint System

Checkpoints (`objects.py:102-107`):
```python
@dataclass
class Checkpoint:
    x: float
    y: float
    activated: bool = False
```

On activation (`objects.py:319-323`): sets `player.respawn_x`, `respawn_y`, `respawn_rings`.

### Pit Death Constant

`DEATH_DELAY_FRAMES = 120` (`constants.py:110`) — 2 seconds at 60fps.
No constant for pit death margin. Ticket specifies 32px below bottom tile row.

## Key Observations

1. **No boundary logic exists anywhere** — this is a pure addition, not a fix
2. **sim_step is the right place** — it's the common path for headless sim, Gymnasium
   env, and live game
3. **player_dead flag is broken** — it's never set, so sim_step's early return never
   triggers
4. **Death needs a sim-layer mechanism** — main.py handles respawn via `_respawn_player`,
   but sim_step needs its own death + respawn for headless/Gym use
5. **create_sim_from_lookup needs kwargs** — multiple test files already assume this
6. **The invariant margin (64px) and pit death margin (32px) are different** — pit death
   should trigger before the invariant flags a violation
7. **Velocity zeroing on boundary clamp** — prevents player from continuously pushing
   against the wall and accumulating weird state

## Files Involved

| File | Role |
|------|------|
| `speednik/simulation.py` | sim_step(), SimState, create_sim_from_lookup |
| `speednik/player.py` | damage_player(), Player, respawn fields |
| `speednik/constants.py` | Will need PIT_DEATH_MARGIN constant |
| `speednik/invariants.py` | POSITION_MARGIN = 64 (reference) |
| `tests/test_invariants.py` | Uses create_sim_from_lookup with kwargs |
| `tests/test_qa_framework.py` | Uses create_sim_from_lookup with kwargs |

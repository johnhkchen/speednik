# Research — T-013-03-BUG-02: audit-no-respawn-after-pit-death

## Problem Summary

The `run_audit()` function in `speednik/qa.py` does not respawn the player after pit death.
When a player dies from falling below `level_height + PIT_DEATH_MARGIN`, the simulation
continues running for thousands of frames with a dead player who never moves. The
`player_dead` flag on `SimState` is never set, so the loop's break condition never triggers.

## Affected Code Paths

### 1. `run_audit()` — `speednik/qa.py:370–402`

The main audit loop:

```python
for frame in range(expectation.max_frames):
    if sim.goal_reached or sim.player_dead:
        break
    inp = archetype_fn(frame, sim)
    events = sim_step(sim, inp)
    ...
```

Two problems:
- **No respawn logic**: When the player dies, the loop should either respawn or terminate.
  It does neither — it keeps calling `sim_step()` which returns early because `player_dead`
  (if it were set) or because `player.state == DEAD` (which `sim_step` does check at line 221).
- **`player_dead` never set**: The break condition `sim.player_dead` is never set to True
  by any code path. Pit death at `simulation.py:248` sets `player.state = DEAD` and
  increments `sim.deaths`, but does not set `sim.player_dead = True`.

### 2. `sim_step()` — `speednik/simulation.py:214–299`

The per-frame simulation step:

```python
def sim_step(sim: SimState, inp: InputState) -> list[Event]:
    events: list[Event] = []
    if sim.player_dead:       # <— guard on player_dead, never set
        return events
    ...
    if p.y > sim.level_height + PIT_DEATH_MARGIN:
        if sim.player.state != PlayerState.DEAD:
            sim.player.state = PlayerState.DEAD
            sim.player.physics.on_ground = False
            sim.deaths += 1
            events.append(DeathEvent())
```

The pit death code sets `player.state = DEAD` and `sim.deaths += 1` and emits `DeathEvent`,
but does **not** set `sim.player_dead = True`. So:
- `sim_step` continues to be called each frame
- The `player_dead` guard at line 221 never triggers
- `player_update` returns early because `player.state == DEAD` (player.py:111–112)
- No further physics runs, so the player never moves
- No further events are emitted (the `if sim.player.state != PlayerState.DEAD` guard
  prevents duplicate DeathEvents)

### 3. `_respawn_player()` — `speednik/main.py:531–548`

The game's respawn logic exists only in `main.py` (the Pyxel App class):

```python
def _respawn_player(self):
    rx = self.player.respawn_x
    ry = self.player.respawn_y
    rr = self.player.respawn_rings
    self.player = create_player(rx, ry)
    self.player.lives = self.lives
    self.player.rings = rr
    self.player.respawn_x = rx
    self.player.respawn_y = ry
    self.player.respawn_rings = rr
    self.death_timer = 0
```

This is not callable from the headless simulation layer. It depends on `self.lives`,
camera state, and the `death_timer` pattern. The simulation layer (`simulation.py`) has
no equivalent.

### 4. Checkpoint system — `speednik/objects.py:102–107, 299–324`

Checkpoints store respawn data on the Player object:
- `Checkpoint` dataclass: `x`, `y`, `activated` fields
- `check_checkpoint_collision()`: sets `player.respawn_x`, `player.respawn_y`,
  `player.respawn_rings` when activated
- `Player` dataclass: `respawn_x`, `respawn_y`, `respawn_rings` fields
- `create_player()`: initializes `respawn_x = x`, `respawn_y = y` (start position)

The Player already carries respawn coordinates. The checkpoint collision in `sim_step()`
at line 269 updates them during normal play. The data is there; nothing reads it after death.

### 5. `SimState` — `speednik/simulation.py:98–119`

```python
@dataclass
class SimState:
    ...
    deaths: int = 0
    goal_reached: bool = False
    player_dead: bool = False     # Never set to True by any code
```

The `player_dead` field exists but is unused. It was presumably intended to signal
terminal death (game over), but no code path sets it.

## Existing Death Flow

### main.py (Pyxel game)

1. Player falls below pit → `player.state = DEAD` (in sim_step or player_update)
2. `_update_gameplay()` detects `player.state == DEAD`, increments `death_timer`
3. After `DEATH_DELAY_FRAMES` (120 frames = 2s):
   - If lives > 1: decrement lives, call `_respawn_player()`
   - If lives ≤ 1: game over
4. Respawn creates a fresh Player at `(respawn_x, respawn_y)` with saved rings

### run_audit() (headless QA)

1. Player falls below pit → `player.state = DEAD`, `sim.deaths += 1`
2. Loop continues calling `sim_step()`
3. `sim_step()` runs but `player_update()` returns early (DEAD check at player.py:111)
4. No progress, no events, loop runs to `max_frames` exhaustion

## Relevant Constants

- `PIT_DEATH_MARGIN = 32` — pixels below level_height before pit death
- `DEATH_DELAY_FRAMES = 120` — 2-second delay in main.py before respawn
- `BehaviorExpectation.max_deaths` — already exists in the expectation schema

## Impact

- Speed Demon: dies frame 217 (x=690), wastes 5783 frames → suppresses real x-progress
- Jumper: dies frame 1346 (x=2415), wastes 4654 frames
- Chaos: dies frame ~200, same pattern
- Any archetype that dies once can never show its true potential
- Skews audit findings: x-progress findings blame the archetype when the bug is in the audit

## Boundary Conditions

- `max_deaths` in BehaviorExpectation: should respawn up to this limit, then terminate
- Checkpoint activation: already works in `sim_step()` — respawn data is correct
- No lives system in QA (no `lives` field in SimState or BehaviorExpectation)
- Death delay: main.py waits 120 frames; audit should respawn immediately (no animation)
- `player_dead` semantics: should mean "permanently dead" (exceeded death budget), not
  "currently in death state"

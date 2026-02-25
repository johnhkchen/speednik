# Design — T-003-02: Game Objects

## Decision 1: Collision Model

### Options

**A. Distance-based (circle) for all objects** — Same as rings. Simple, consistent.
- Pro: Uniform pattern, easy to reason about.
- Con: Springs have a directional surface — a circle doesn't model "landing on top of a spring" vs "walking past it." Player could trigger a spring from the side.

**B. AABB (bounding box) for springs/pipes, distance for checkpoints** — Springs and pipes are rectangular surfaces. Checkpoints are point triggers.
- Pro: Springs fire only when the player overlaps their bounding box, which better matches the physical metaphor. Pipes are explicitly "rectangular trigger zones" per spec.
- Con: Slightly more code, two collision models.

**C. AABB for everything** — Uniform box-based collision.
- Pro: Consistent.
- Con: Checkpoints don't need directional precision. Over-engineering.

### Decision: Option B

Springs and pipes use AABB overlap. Checkpoints use distance-based collision (like rings). Rationale: the spec explicitly says pipes have "rectangular trigger zones," and springs are directional surfaces that should only trigger on appropriate contact. Checkpoints are simple proximity triggers — a post you run past.

AABB helper:
```python
def aabb_overlap(px, py, pw, ph, ox, oy, ow, oh) -> bool:
    return px < ox + ow and px + pw > ox and py < oy + oh and py + ph > oy
```

Player hitbox comes from `get_player_rect()` already in player.py.

---

## Decision 2: Spring Design

### Options

**A. Springs override velocity immediately** — On overlap, set `y_vel` (up spring) or `x_vel` (right spring) to a constant, set `on_ground = False`.
- Pro: Simple, matches Sonic 2 behavior exactly.
- Con: Need a "cooldown" to prevent re-triggering every frame while overlapping.

**B. Springs apply an impulse (additive)** — Add to existing velocity rather than overriding.
- Con: Not how Sonic springs work. A spring at the bottom of a fall would add to downward velocity instead of reversing it.

### Decision: Option A — velocity override

Spring constants:
- `SPRING_UP_VELOCITY = -10.0` (strong upward — Sonic 2 uses ~10 px/frame for red springs)
- `SPRING_RIGHT_VELOCITY = 10.0` (rightward launch)

Up spring: `y_vel = SPRING_UP_VELOCITY`, `on_ground = False`, `ground_speed = 0`.
Right spring: `x_vel = SPRING_RIGHT_VELOCITY`, `on_ground = False`, `ground_speed = 0`.

**Cooldown:** Spring has a `cooldown` timer (frames). Set to ~8 frames on trigger. While > 0, won't re-trigger. Decremented each frame. This also drives the visual compressed/extended state.

---

## Decision 3: Checkpoint Save/Restore

### Options

**A. Store respawn data on Player** — Add `respawn_x`, `respawn_y`, `respawn_rings` fields.
- Pro: Simple, co-located with player state. Player already holds all game state.
- Con: Slightly expands Player dataclass.

**B. Separate RespawnState object** — Managed by main loop alongside player.
- Pro: Separation of concerns.
- Con: Extra indirection for no real benefit at this scale.

### Decision: Option A

Add three fields to Player: `respawn_x: float`, `respawn_y: float`, `respawn_rings: int`. Initialized from player start position. Checkpoint activation overwrites them. The death/respawn system (future ticket) reads them.

---

## Decision 4: Launch Pipe Entity Format

### Options

**A. Single entity with extra fields** — `{"type": "pipe_h", "x": 1200, "y": 640, "exit_x": 1600, "exit_y": 640, "vel_x": 10, "vel_y": 0}`.
- Pro: Self-contained. Loader extracts all data from one entity.
- Con: More fields than other entities.

**B. Paired entities (entry + exit)** — Two entities linked by a shared `pipe_id`.
- Pro: Matches visual placement (draw pipe from entry to exit).
- Con: More complex loading, need to match pairs.

### Decision: Option A

Single entity with explicit exit coordinates and launch velocity. This is simpler to load, simpler to test, and the visual (filled rectangle from entry to exit) can be derived from the coordinates. Add these entities to pipeworks entities.json.

**Pipe behavior:**
1. Player overlaps entry AABB → set player velocity to `(vel_x, vel_y)`, mark player as "in pipe" (invulnerable, no input).
2. Each frame while in pipe: player moves at pipe velocity, no gravity, no input.
3. When player position reaches exit coordinates → resume normal physics, clear pipe state.

**Player state:** Add a `in_pipe: bool` flag to Player. When true, `player_update` skips normal physics and moves player along pipe velocity. Simpler than a new PlayerState enum value — pipes are a temporary override, not a full state.

Actually, reconsidering: a flag on Player is cleaner than a new state. The pipe system in objects.py sets the flag and velocity, player_update checks it and bypasses normal physics. When the pipe system detects arrival at exit, it clears the flag.

---

## Decision 5: Liquid Rise System

### Options

**A. Zone-based state machine in objects.py** — `LiquidZone(trigger_x, exit_x, floor_y, ceiling_y, current_y, active)`. Activated when `player.x > trigger_x`, deactivated when `player.x > exit_x`.
- Pro: Self-contained, testable. The liquid zone is a world object with state.
- Con: Needs per-frame update even when inactive (to check trigger).

**B. Stage metadata driven** — Liquid defined in meta.json with zone bounds.
- Pro: Matches "liquid is a level feature, not a placed entity."
- Con: Different loading path from other objects.

### Decision: Option A

Liquid zones are loaded from entities.json (as `liquid_trigger` entries with extra fields: `exit_x`, `floor_y`, `ceiling_y`). They're world objects managed in objects.py. The update function checks player position, toggles activation, and advances the liquid level.

**Liquid rise constants:**
- `LIQUID_RISE_SPEED = 1.0` (1px/frame per spec)

**Damage:** Liquid contact checked by comparing player Y + height_radius against liquid surface Y. If overlapping, call `damage_player()`. The liquid doesn't kill instantly — just ring loss with invulnerability.

---

## Decision 6: Entity Data for Pipeworks

Pipes and liquid triggers are missing from entities.json. We'll add them based on spec §7.2:

- 4 horizontal launch pipes (`pipe_h`) in the mid route (800–2800px range)
- 1 liquid trigger zone for section 3 (x=2800 to x=3800)

---

## Rejected Alternatives

- **New PlayerState for pipes:** Rejected — adding PIPE_TRAVEL to the state enum would require changes throughout player.py's state machine. A boolean flag is simpler and correctly models the temporary override.
- **Additive spring impulse:** Rejected — doesn't match Sonic 2 behavior where springs always launch at a consistent height.
- **Global liquid state:** Rejected — the zone-based approach from entities.json is consistent with how all other objects load.

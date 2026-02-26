# T-011-02 Research: physics-invariant-checker

## Objective

Build a reusable invariant checker (`speednik/invariants.py`) that scans a simulation
trajectory and flags impossible physics states. Used by tests and the scenario runner,
not a test itself.

## Key Types and Locations

### FrameSnapshot — `tests/harness.py:29-40`

```python
@dataclass
class FrameSnapshot:
    frame: int
    x: float
    y: float
    x_vel: float
    y_vel: float
    ground_speed: float
    angle: int
    on_ground: bool
    quadrant: int
    state: str  # PlayerState.value
```

This is the snapshot type used in the ticket's API signature. It lives in `tests/harness.py`,
not in the main package. The invariant checker (a package module) will need to reference
this type — but importing from `tests/` in production code is a code-smell concern.

### SimState — `speednik/simulation.py:91-113`

Provides `tile_lookup: TileLookup`, `level_width: int`, `level_height: int`. The checker
needs `sim` to perform spatial queries (tile solidity) and boundary checks.

### Event types — `speednik/simulation.py:47-84`

Union type: `RingCollectedEvent | DamageEvent | DeathEvent | SpringEvent | GoalReachedEvent | CheckpointEvent`. The checker needs `SpringEvent` to excuse velocity spikes from springs.

### Tile / solidity — `speednik/terrain.py`

- `TILE_SIZE = 16`
- Solidity constants: `NOT_SOLID=0`, `TOP_ONLY=1`, `FULL=2`, `LRB_ONLY=3`
- `Tile.height_array: list[int]` — 16 values, 0-16 per column
- `TileLookup = Callable[[int, int], Optional[Tile]]`
- `get_quadrant(angle: int) -> int` — maps byte angle to quadrant 0-3

### Physics constants — `speednik/constants.py`

- `MAX_X_SPEED = 16.0` — hard velocity cap in physics code
- `SPRING_UP_VELOCITY = -10.0`, `SPRING_RIGHT_VELOCITY = 10.0`
- `SPINDASH_BASE_SPEED = 8.0`, `SPINDASH_MAX_CHARGE = 8.0` → max spindash = 12.0
- Ticket specifies 20.0 as the "sane max" for both |x_vel| and |y_vel|

### PlayerState — `speednik/player.py:49-56`

Enum with values: standing, running, jumping, rolling, spindash, hurt, dead.

### Quadrant adjacency — `speednik/terrain.py:100-115`

Cyclic: 0↔1↔2↔3↔0. Legal one-frame transitions: same or ±1 (mod 4).
Illegal: 0↔2, 1↔3 (diagonal jumps = collision glitch).

## Solid-tile intersection check

To determine if a player center `(x, y)` is inside a fully solid tile:

```python
tx, ty = int(x) // 16, int(y) // 16
col = int(x) % 16
tile = tile_lookup(tx, ty)
if tile and tile.solidity == FULL:
    height = tile.height_array[col]
    solid_top = (ty + 1) * 16 - height
    if y >= solid_top:  # inside solid region
        ...
```

## On-ground validation

When `on_ground=True`, there should be a solid tile surface within sensor range below
the player. The full sensor logic is complex (terrain.py has sensor casts with MAX_SENSOR_RANGE=32).
A simpler invariant: check that the tile at the player's feet exists and isn't completely empty.

## Velocity spike excusal

Springs produce `SpringEvent` and set velocity to ±10.0. Spindash can set ground_speed
up to 12.0. A velocity spike threshold of ~12.0 per frame without a spring/spindash event
would be suspicious. The ticket asks for delta_vel threshold between consecutive frames.

## Trajectory construction pattern

Callers build trajectories by calling `sim_step` in a loop:
```python
for frame in range(N):
    events = sim_step(sim, inp)
    snap = _capture_snapshot(frame, player)
    snapshots.append(snap)
    events_per_frame.append(events)
```

The checker receives the completed `snapshots` and `events_per_frame` lists.

## Existing test patterns

Tests use `pytest`, plain functions. Synthetic grids via `tests/grids.build_flat()`.
Scenarios via `tests/harness.run_scenario()`. No existing invariant checking code.

## Import boundary concern

`FrameSnapshot` lives in `tests/harness.py`. The invariant checker is in `speednik/`.
Options: (1) import from tests (works at runtime, smells), (2) define a Protocol,
(3) move FrameSnapshot to speednik, (4) duck-type with attribute access.
The ticket spec shows `FrameSnapshot` in the signature explicitly.

## Constraints

- No Pyxel imports allowed in `speednik/invariants.py`
- Must be importable by both tests and the scenario runner
- Library, not a test — tests assert on its output

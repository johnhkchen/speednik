# T-011-02 Structure: physics-invariant-checker

## New files

### `speednik/invariants.py`

Public interface:

```python
@dataclass
class Violation:
    frame: int
    invariant: str   # e.g. "position_x_negative"
    details: str     # human-readable
    severity: str    # "error" | "warning"

def check_invariants(
    sim: SimState,
    snapshots: list[SnapshotLike],
    events_per_frame: list[list[Event]],
) -> list[Violation]:
```

Internal structure (private functions):

```
_check_position_bounds(sim, snapshots) -> list[Violation]
    - x < 0
    - y > level_height + 64
    - x > level_width + 64

_check_inside_solid(sim, snapshots) -> list[Violation]
    - player center inside FULL solid tile

_check_velocity_limits(snapshots) -> list[Violation]
    - |x_vel| > MAX_VEL (20.0)
    - |y_vel| > MAX_VEL (20.0)

_check_velocity_spikes(snapshots, events_per_frame) -> list[Violation]
    - |delta_x_vel| or |delta_y_vel| > SPIKE_THRESHOLD (12.0)
    - excused by SpringEvent or spindash release

_check_ground_consistency(sim, snapshots) -> list[Violation]
    - on_ground=True but no tile at feet

_check_quadrant_jumps(snapshots) -> list[Violation]
    - quadrant changes by ±2 in one frame
```

Imports:
- `speednik.simulation.SimState`, `Event`, `SpringEvent`
- `speednik.terrain.TILE_SIZE`, `FULL`, `NOT_SOLID`
- `speednik.constants.STANDING_HEIGHT_RADIUS`
- NO Pyxel imports

Protocol type for snapshots:

```python
class SnapshotLike(Protocol):
    frame: int
    x: float
    y: float
    x_vel: float
    y_vel: float
    on_ground: bool
    quadrant: int
    state: str
```

Constants (module-level):

```python
MAX_VEL = 20.0
SPIKE_THRESHOLD = 12.0
POSITION_MARGIN = 64
```

### `tests/test_invariants.py`

Test structure:

```
class TestViolationDataclass:
    test_violation_fields

class TestPositionInvariants:
    test_x_negative_flagged
    test_y_fell_through_world
    test_x_escaped_right
    test_clean_position_no_violations

class TestSolidTileInvariant:
    test_inside_solid_flagged
    test_above_solid_clean

class TestVelocityInvariants:
    test_x_vel_exceeds_max
    test_y_vel_exceeds_max
    test_normal_velocity_clean

class TestVelocitySpikes:
    test_spike_without_excuse_flagged
    test_spike_with_spring_excused
    test_spike_with_spindash_excused
    test_gradual_acceleration_clean

class TestGroundConsistency:
    test_on_ground_no_tile_flagged
    test_on_ground_with_tile_clean

class TestQuadrantJumps:
    test_diagonal_quadrant_jump_flagged
    test_adjacent_quadrant_transition_clean

class TestCleanTrajectory:
    test_full_clean_trajectory_zero_violations

class TestNoPyxelImport:
    test_no_pyxel_import
```

Imports:
- `speednik.invariants.Violation`, `check_invariants`
- `tests.harness.FrameSnapshot`
- `speednik.simulation.SimState`, `SpringEvent`
- `speednik.terrain.TILE_SIZE`, `FULL`, `NOT_SOLID`, `Tile`
- Helper to build synthetic snapshots and minimal SimState

Helpers (test-local):

```python
def make_snap(**overrides) -> FrameSnapshot:
    """Factory with sane defaults for a standing player."""

def make_sim(tile_lookup=None, level_width=10000, level_height=10000) -> SimState:
    """Minimal SimState with given tile_lookup."""
```

## Modified files

None. This is a new module with new tests.

## Module boundaries

- `speednik/invariants.py` imports only from `speednik.*` — no Pyxel, no tests
- `tests/test_invariants.py` imports from both `speednik.invariants` and `tests.harness`
- The `SnapshotLike` protocol allows the checker to work with any snapshot type
  (FrameSnapshot from harness, FrameRecord from scenarios, etc.)

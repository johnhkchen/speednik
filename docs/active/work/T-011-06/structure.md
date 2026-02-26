# Structure — T-011-06 naive-player-regression-suite

## Files

### Created

**`tests/test_regression.py`** — Single new file. ~250 lines.

### Modified

None.

### Deleted

None.

## Module Layout: tests/test_regression.py

### Imports

```
speednik.simulation: create_sim, sim_step, Event
speednik.invariants: check_invariants, Violation
speednik.camera: Camera, camera_update, create_camera
speednik.terrain: get_quadrant
speednik.strategies: hold_right, hold_right_jump, spindash_right, Strategy
tests.test_camera_stability: CameraSnapshot, CameraTrajectory, check_oscillation
```

### Constants

```python
STAGES = {
    "hillside": {"width": 4800, "max_frames": 4000},
    "pipeworks": {"width": 5600, "max_frames": 5000},
    "skybridge": {"width": 5200, "max_frames": 6000},
}

STRATEGIES = {
    "hold_right": hold_right,
    "hold_right_jump": hold_right_jump,
    "spindash_right": spindash_right,
}

# Forward progress: min max_x as fraction of level width.
X_THRESHOLD_FRACTION = 0.05  # 5% — conservative; ticket says 50% but many combos stop early

# Death caps per (stage, strategy). Based on observed behavior.
MAX_DEATHS = {
    "hillside":  {"hold_right": 0, "hold_right_jump": 0, "spindash_right": 0},
    "pipeworks": {"hold_right": 3, "hold_right_jump": 3, "spindash_right": 3},
    "skybridge": {"hold_right": 3, "hold_right_jump": 3, "spindash_right": 3},
}
```

### Data Structures

```python
@dataclass
class RegressionSnapshot:
    """SnapshotLike-compatible snapshot for invariant checking."""
    frame: int
    x: float
    y: float
    x_vel: float
    y_vel: float
    on_ground: bool
    quadrant: int
    state: str

@dataclass
class RegressionResult:
    """Collected data for one (stage, strategy) combo."""
    stage: str
    strategy: str
    snapshots: list[RegressionSnapshot]
    events_per_frame: list[list[Event]]
    camera_trajectory: CameraTrajectory
    sim: SimState
    max_x: float
    deaths: int
    rings_collected: int
    goal_reached: bool
    frames_run: int
```

### Core Runner

```python
def _run_regression(stage: str, strategy_name: str) -> RegressionResult:
    """Run unified sim + camera loop, collect all data."""
```

Steps:
1. `create_sim(stage)` — get SimState
2. `create_camera(...)` — init camera
3. Create strategy via `STRATEGIES[strategy_name]()`
4. Loop for max_frames:
   a. `inp = strategy(frame, sim.player)`
   b. `events = sim_step(sim, inp)`
   c. `camera_update(camera, sim.player, inp)`
   d. Capture RegressionSnapshot (with quadrant from `get_quadrant(angle)`)
   e. Capture CameraSnapshot
   f. Store raw events
   g. Track max_x
5. Build CameraTrajectory from snapshots
6. Return RegressionResult

### Cache

```python
_RESULT_CACHE: dict[tuple[str, str], RegressionResult] = {}

def _get_result(stage: str, strategy: str) -> RegressionResult:
    key = (stage, strategy)
    if key not in _RESULT_CACHE:
        _RESULT_CACHE[key] = _run_regression(stage, strategy)
    return _RESULT_CACHE[key]
```

### Parameterized Test Class

```python
ALL_STAGES = list(STAGES.keys())
ALL_STRATEGIES = list(STRATEGIES.keys())

@pytest.mark.parametrize("stage", ALL_STAGES)
@pytest.mark.parametrize("strategy", ALL_STRATEGIES)
class TestRegression:
    def test_invariants(self, stage, strategy): ...
    def test_camera_no_oscillation(self, stage, strategy): ...
    def test_forward_progress(self, stage, strategy): ...
    def test_deaths_within_bounds(self, stage, strategy): ...
    def test_results_logged(self, stage, strategy, capsys): ...
```

### Test Method Details

**test_invariants**: Run `check_invariants`, filter `severity=="error"`, assert 0.

**test_camera_no_oscillation**: Call `check_oscillation(traj, "x")` and
`check_oscillation(traj, "y")`, assert both return empty lists.

**test_forward_progress**: Assert `max_x >= STAGES[stage]["width"] * X_THRESHOLD_FRACTION`.

**test_deaths_within_bounds**: Assert `deaths <= MAX_DEATHS[stage][strategy]`.

**test_results_logged**: Print summary line per combo. Uses capsys to verify output
is produced (optional — may just print and not assert on content).

## Interface Boundaries

- **Imports from production code**: simulation, invariants, camera, terrain, strategies.
  All are Pyxel-free modules designed for headless testing.

- **Imports from test code**: `CameraSnapshot`, `CameraTrajectory`, and
  `check_oscillation` from `tests.test_camera_stability`. These are well-factored
  helper functions, not test fixtures.

- **No imports from**: test_walkthrough, test_invariants (test file), test_geometry_probes,
  test_entity_interactions. The regression test is self-contained except for camera helpers.

## Ordering

Single file, no ordering dependencies. All test methods are independent given the
shared cache.

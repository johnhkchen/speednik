# Structure — T-011-04: camera-stability-tests

## Files

### New file: `tests/test_camera_stability.py`

Single new test file. No production code modified.

## Module layout

```
tests/test_camera_stability.py
├── Imports
│   ├── speednik.camera: Camera, camera_update, create_camera
│   ├── speednik.constants: SCREEN_WIDTH, SCREEN_HEIGHT, CAMERA_H_SCROLL_CAP,
│   │   CAMERA_V_SCROLL_GROUND_FAST, CAMERA_V_SCROLL_AIR
│   ├── speednik.simulation: SimState, create_sim, sim_step
│   ├── speednik.physics: InputState
│   └── tests.harness: hold_right, spindash_right (strategy factories)
│
├── CameraSnapshot (dataclass)
│   ├── frame: int
│   ├── cam_x: float
│   ├── cam_y: float
│   ├── player_x: float
│   ├── player_y: float
│   └── player_dead: bool
│
├── CameraTrajectory (dataclass)
│   ├── snapshots: list[CameraSnapshot]
│   ├── level_width: int
│   └── level_height: int
│
├── run_with_camera(stage, strategy_factory, frames) -> CameraTrajectory
│   # Core loop: create_sim → create_camera → frame loop →
│   # sim_step + camera_update → record snapshot
│
├── _TRAJECTORY_CACHE (dict)
│   # (stage, strategy_name) → CameraTrajectory
│   # Avoids re-running same combo for each test method
│
├── get_trajectory(stage, strategy_name) -> CameraTrajectory
│   # Cache wrapper
│
├── Constants
│   ├── STAGES: dict (stage → {frames})
│   ├── STRATEGIES: dict (name → factory)
│   ├── OSCILLATION_WINDOW = 10
│   ├── OSCILLATION_MAX_FLIPS = 5
│   └── DELTA_MARGIN = 1.0
│
├── Assertion helpers
│   ├── check_oscillation(trajectory, axis) -> list[int]
│   │   # Returns frames where oscillation detected
│   ├── check_delta_bounds(trajectory) -> list[tuple[int, str, float]]
│   │   # Returns (frame, axis, delta) for violations
│   ├── check_level_bounds(trajectory) -> list[tuple[int, str, float]]
│   │   # Returns (frame, axis, value) for violations
│   └── check_player_visible(trajectory) -> list[tuple[int, str]]
│       # Returns (frame, axis) for violations
│
└── Test classes (parametrized by stage × strategy)
    ├── TestNoOscillation
    │   ├── test_no_horizontal_oscillation
    │   └── test_no_vertical_oscillation
    ├── TestNoDeltaSpike
    │   └── test_no_extreme_camera_jumps
    ├── TestBoundsRespected
    │   └── test_camera_within_level_bounds
    └── TestPlayerVisible
        └── test_player_on_screen
```

## Interfaces

### `run_with_camera`

```python
def run_with_camera(
    stage: str,
    strategy_factory: Callable[[], Strategy],
    frames: int,
) -> CameraTrajectory:
```

- Creates `SimState` via `create_sim(stage)`.
- Creates `Camera` via `create_camera(sim.level_width, sim.level_height, player.x, player.y)`.
- Runs `frames` iterations: strategy → sim_step → camera_update → snapshot.
- Returns trajectory with all snapshots + level dimensions.

### Assertion helpers

Each returns a list of violations (empty = pass). Tests call the helper then
`assert not violations, f"..."`. This pattern gives clear failure messages listing
which frames failed and why.

### Parametrization

```python
ALL_STAGES = ["hillside", "pipeworks", "skybridge"]
ALL_STRATEGIES = ["hold_right", "spindash_right"]

@pytest.mark.parametrize("stage", ALL_STAGES)
@pytest.mark.parametrize("strategy", ALL_STRATEGIES)
```

6 combos total. Each test method fetches the cached trajectory and runs one assertion.

## Dependencies

- `tests/harness.py` — reuse `hold_right()` and `spindash_right()` strategy factories.
- `speednik.camera` — `Camera`, `create_camera`, `camera_update`.
- `speednik.simulation` — `create_sim`, `sim_step`.
- `speednik.constants` — screen dimensions, scroll caps.
- No new production code. No modifications to existing files.

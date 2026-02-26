# T-011-03 Structure: Geometric Feature Probes

## Files

### New: `tests/test_geometry_probes.py`

Single test file containing all geometric feature probes.

**Internal structure:**

```
# Module docstring with coordinate reference table

# Helper types
@dataclass ProbeResult:
    snapshots: list[dict]     # per-frame {x, y, x_vel, y_vel, ground_speed, angle, on_ground, quadrant, state}
    events: list[list[Event]] # events per frame
    sim: SimState             # final sim state

# Helper function
def _run_probe(stage, start_x, start_y, strategy, frames) -> ProbeResult

# Strategy functions (reuse pattern from harness.py)
def _spindash_strategy(frame, sim) -> InputState
def _hold_right_strategy(frame, sim) -> InputState
def _hold_right_jump_strategy(frame, sim) -> InputState

# Test classes
class TestLoopTraversal           # hillside loop
class TestSpringLaunch            # hillside spring_up
class TestGapClearing             # skybridge gaps
class TestRampTransition          # hillside slope transitions
class TestCheckpointActivation    # hillside checkpoint
```

## Module Boundaries

- `_run_probe()` uses `create_sim()` + `sim_step()` directly. No harness dependency.
- Strategies are simple callables `(frame: int, sim: SimState) -> InputState` — slightly
  different signature from harness (which uses `(frame, player)`), because we need sim
  access for full state awareness (e.g., player state for spindash re-dash logic).
- ProbeResult captures both trajectory and events, enabling assertions on both physics
  outcomes and entity interactions.

## Interface Contracts

### `_run_probe()`

```python
def _run_probe(
    stage: str,
    start_x: float,
    start_y: float,
    strategy: Callable[[int, SimState], InputState],
    frames: int = 300,
) -> ProbeResult:
```

- Creates sim, overrides player position, runs frame loop
- Captures snapshot + events each frame
- Returns ProbeResult with full trajectory

### Test Assertions Pattern

Each test:
1. Calls `_run_probe()` with documented coordinates
2. Extracts relevant data from ProbeResult
3. Makes range-based assertions (not frame-exact)

## Dependencies

- `speednik.simulation`: `create_sim`, `sim_step`, `SimState`, event types
- `speednik.physics`: `InputState`
- `speednik.player`: `PlayerState`
- `speednik.terrain`: `get_quadrant`
- No dependency on `tests/harness.py` (self-contained)
- No dependency on `speednik/scenarios/` (direct sim control)

## No Files Modified

This ticket creates one new file only. No modifications to existing code.

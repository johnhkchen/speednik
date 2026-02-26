# Structure: T-012-08 — loop-traversal-audit

## Files Created

### `tests/test_loop_audit.py` — Main audit test file

Module docstring: "Loop traversal QA audit" with table of test categories.

#### Imports

```python
from speednik.grids import build_loop
from speednik.simulation import create_sim, create_sim_from_lookup, sim_step
from speednik.terrain import TILE_SIZE, get_quadrant
from speednik.physics import InputState
from speednik.player import PlayerState
```

#### Constants

```python
GROUND_ROW = 20
GROUND_Y = GROUND_ROW * TILE_SIZE - 20
```

#### Data classes

`LoopAuditSnap` — per-frame snapshot with fields: frame, x, y, ground_speed,
on_ground, quadrant, angle, state. Subset of what mechanic probes track.

`LoopAuditResult` — result container with:
- `snaps: list[LoopAuditSnap]`
- `grounded_quadrants: set[int]` — {q for s in snaps if s.on_ground}
- `all_quadrants: set[int]` — {q for s in snaps}
- `loop_region_snaps(loop_start_x, loop_end_x) -> list[LoopAuditSnap]`
- `ground_loss_frame(loop_start_x) -> int | None` — first frame after loop
  entry where on_ground transitions from True to False

#### Diagnostic formatter

```python
def format_loop_diagnostic(
    result: LoopAuditResult,
    loop_start_x: float,
    loop_end_x: float,
    *,
    radius: int | None = None,
    entry_speed: float | None = None,
    label: str = "",
) -> str:
```

Returns multi-line diagnostic string:
```
LOOP AUDIT FAILED (radius=48, entry_speed=8.0):
  Grounded quadrants: {0, 1}  (expected {0, 1, 2, 3})
  All quadrants (incl. airborne): {0, 1, 2}

  Trajectory through loop region (x=3472..3744):
    f=102: x=3465 y=610 gs=7.8 og=True  q=0  state=rolling
    f=103: x=3473 y=608 gs=7.5 og=True  q=1  state=rolling
    ...

  Ground contact lost at frame 104 (x=3480).
  Probable cause: [heuristic based on data]
```

Limited to 30 frames of trajectory to keep output manageable.

#### Spindash strategy

```python
def _spindash_strategy() -> Callable
```

Same state machine as `test_mechanic_probes.py::_make_spindash_strategy`:
CROUCH → CHARGE (3 frames) → RELEASE → RUN (re-dash if speed < 2.0).

Takes `frame: int, sim: SimState` (matches `sim_step` usage).

#### Runner

```python
def _run_loop_audit(
    sim: SimState,
    strategy: Callable,
    frames: int = 600,
) -> LoopAuditResult:
```

Runs `sim_step()` per frame, captures `LoopAuditSnap` per frame.

#### Test classes

##### `TestSyntheticLoopTraversal`

Parameterized across radii (32, 48, 64, 96).

```python
@staticmethod
def _build_and_run(radius: int) -> LoopAuditResult:
    # build_loop, create_sim_from_lookup, _run_loop_audit

def test_all_quadrants_grounded(self, radius):
    # Assert grounded_quadrants == {0, 1, 2, 3}
    # xfail for r=32

def test_exit_positive_speed(self, radius):
    # Assert player exits with positive ground_speed
    # xfail for r=64, r=96 (BUG-02)

def test_exit_on_ground(self, radius):
    # Assert player is on_ground past loop exit
    # xfail for r=64, r=96 (BUG-02)
```

##### `TestSyntheticLoopSpeedSweep`

Parameterized across speeds (4.0 to 12.0 step 1.0) at radius=48.

```python
def test_minimum_traversal_speed(self, speed):
    # Set ground_speed=speed, x_vel=speed directly
    # Hold right (no spindash)
    # Assert grounded_quadrants == {0, 1, 2, 3}
    # xfail for speeds that don't complete the loop
```

##### `TestHillsideLoopTraversal`

Single test for the real hillside stage loop.

```python
def test_hillside_loop_all_quadrants_grounded(self):
    # create_sim("hillside"), override position to x=3100, y=610
    # Spindash strategy
    # Assert grounded_quadrants == {0, 1, 2, 3}
    # xfail: T-012-08-BUG-01

def test_hillside_loop_exits(self):
    # Assert player x > 3744 after 600 frames
    # xfail: T-012-08-BUG-01
```

### `docs/active/tickets/T-012-08-BUG-01.md` — Bug ticket

Hillside loop not traversable. Player gets stuck oscillating in Q1 around
x=3445–3449. Diagnostic output from the audit test.

## Files NOT Modified

- `speednik/grids.py` — No changes
- `speednik/simulation.py` — No changes
- `speednik/terrain.py` — No changes
- `speednik/physics.py` — No changes
- `tests/test_mechanic_probes.py` — Separate tests, no changes
- `tests/test_elementals.py` — Separate tests, no changes

## Module Boundaries

The audit test file is fully self-contained. It imports from `speednik.*` but
does not export anything. The diagnostic formatter is internal to the test file.

The runner function takes `SimState` and returns `LoopAuditResult`. This is
distinct from (and simpler than) the `ProbeResult` used by mechanic probes.

## Ordering

1. Create `tests/test_loop_audit.py` with all test infrastructure
2. Run tests, verify expected pass/fail/xfail pattern
3. Create bug ticket `T-012-08-BUG-01` with diagnostic evidence

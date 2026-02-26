# Structure — T-012-01: Archetype Library & Expectation Framework

## Files

### Create: `speednik/qa.py`

Single module containing all QA audit framework components. No subpackage needed —
everything fits in one file.

#### Type Alias

```python
Archetype = Callable[[int, SimState], InputState]
```

#### Dataclasses

```python
@dataclass
class BehaviorExpectation:
    name: str
    stage: str
    archetype: str
    min_x_progress: float
    max_deaths: int
    require_goal: bool
    max_frames: int
    invariant_errors_ok: int

@dataclass
class AuditFinding:
    expectation: str
    actual: str
    frame: int
    x: float
    y: float
    severity: str          # "bug" | "warning"
    details: str

@dataclass
class AuditResult:
    snapshots: list[FrameSnapshot]
    events_per_frame: list[list[Event]]
    violations: list[Violation]
    sim: SimState
```

#### Archetype Factories (6 functions)

```python
def make_walker() -> Archetype: ...
def make_jumper() -> Archetype: ...
def make_speed_demon() -> Archetype: ...
def make_cautious() -> Archetype: ...
def make_wall_hugger() -> Archetype: ...
def make_chaos(seed: int) -> Archetype: ...
```

Each returns a closure that captures mutable state (prev_jump, counters, RNG).
Signature of returned callable: `(frame: int, sim: SimState) -> InputState`.

#### Audit Functions

```python
def run_audit(
    stage: str,
    archetype_fn: Archetype,
    expectation: BehaviorExpectation,
) -> tuple[list[AuditFinding], AuditResult]: ...

def format_findings(findings: list[AuditFinding]) -> str: ...
```

#### Internal Helpers

```python
def _capture_snapshot(sim: SimState, frame: int) -> FrameSnapshot: ...
def _build_findings(
    sim: SimState,
    snapshots: list[FrameSnapshot],
    violations: list[Violation],
    expectation: BehaviorExpectation,
) -> list[AuditFinding]: ...
```

### Create: `tests/test_qa_framework.py`

Unit tests for the framework itself. Uses synthetic grids, not real stages.

#### Test Classes

```python
class TestArchetypes:
    """Verify each archetype produces valid InputState and expected behavior."""
    test_walker_moves_right_on_flat()
    test_jumper_leaves_ground_on_flat()
    test_speed_demon_reaches_high_speed()
    test_cautious_moves_slowly()
    test_wall_hugger_jumps_at_wall()
    test_chaos_deterministic()
    test_chaos_different_seeds_differ()

class TestExpectationFramework:
    """Verify findings are generated correctly."""
    test_clean_flat_no_findings()
    test_stuck_player_generates_finding()
    test_death_exceeds_max_generates_finding()
    test_invariant_violation_becomes_finding()
    test_goal_not_reached_generates_finding()

class TestFormatFindings:
    """Verify format_findings output."""
    test_empty_findings()
    test_single_bug()
    test_multiple_findings()
```

---

## Module Dependencies

```
speednik/qa.py imports:
    speednik.simulation  → SimState, create_sim, sim_step, Event, DeathEvent, GoalReachedEvent
    speednik.physics     → InputState
    speednik.strategies  → FrameSnapshot
    speednik.invariants  → check_invariants, Violation
    speednik.player      → PlayerState
    random               → Random (for chaos archetype)
    dataclasses          → dataclass

tests/test_qa_framework.py imports:
    speednik.qa          → all public names
    speednik.grids       → build_flat, build_gap
    speednik.simulation  → create_sim_from_lookup
    pytest
```

No Pyxel imports anywhere in the chain. All dependencies are already Pyxel-free.

---

## Interface Boundaries

- `speednik/qa.py` depends on simulation/invariants but NOT on agents, scenarios, or observation.
- Tests use `create_sim_from_lookup` with synthetic grids for isolation.
- Real stage tests (hillside, pipeworks, skybridge) belong in T-012-02 through T-012-04,
  not here.

---

## Snapshot Capture

`_capture_snapshot` builds a `FrameSnapshot` from SimState after each `sim_step`:

```python
def _capture_snapshot(sim: SimState, frame: int) -> FrameSnapshot:
    p = sim.player.physics
    return FrameSnapshot(
        frame=frame,
        x=p.x, y=p.y,
        x_vel=p.x_vel, y_vel=p.y_vel,
        ground_speed=p.ground_speed,
        angle=p.angle,
        on_ground=p.on_ground,
        quadrant=get_quadrant(p.angle),
        state=sim.player.state.value,
    )
```

Uses `get_quadrant` from `speednik.terrain` to derive quadrant from angle.

# Design — T-012-01: Archetype Library & Expectation Framework

## Decision 1: Archetype Signature

**Chosen:** `Callable[[int, SimState], InputState]` — matches the ticket spec exactly.

Type alias: `Archetype = Callable[[int, SimState], InputState]`

**Why not reuse Strategy?** Strategy takes `(int, Player)`, but archetypes need SimState-level
info (player_dead, goal_reached) and the richer context lets behaviors like speed demon read
ground_speed directly from `sim.player.physics.ground_speed`.

**Why not reuse Agent?** Agents operate on observation vectors and return discrete actions.
Archetypes need direct game state access and return InputState directly. The audit loop
handles frame stepping — agents add unnecessary indirection.

## Decision 2: Jump Edge Detection

**Chosen:** Each archetype factory closure tracks `prev_jump_held` internally.

When the archetype wants to jump, it sets `jump_held=True`. On the frame where it transitions
from not-jumping to jumping, it also sets `jump_pressed=True`. This mirrors how `action_to_input`
works in the agent system but keeps it self-contained within each archetype.

Pattern:
```python
def make_jumper() -> Archetype:
    prev_jump = False
    def strategy(frame: int, sim: SimState) -> InputState:
        nonlocal prev_jump
        want_jump = sim.player.physics.on_ground
        pressed = want_jump and not prev_jump
        prev_jump = want_jump
        return InputState(right=True, jump_pressed=pressed, jump_held=want_jump)
    return strategy
```

## Decision 3: Audit Result Type

**Chosen:** Define `AuditResult` dataclass in `speednik/qa.py`.

```python
@dataclass
class AuditResult:
    snapshots: list[FrameSnapshot]
    events_per_frame: list[list[Event]]
    violations: list[Violation]
    sim: SimState                     # final state
```

The ticket says `-> tuple[list[AuditFinding], ProbeResult]` but `ProbeResult` doesn't exist.
`AuditResult` carries everything the caller needs: trajectory for replay analysis, invariant
violations for cross-referencing, and final sim state for metric extraction.

Return type: `tuple[list[AuditFinding], AuditResult]`.

## Decision 4: Finding Generation

Findings come from two sources:

1. **Expectation comparison** — checked after the full run:
   - `min_x_progress`: player didn't reach expected X → bug
   - `max_deaths`: too many deaths → bug
   - `require_goal`: goal not reached → bug
   - `max_frames`: ran full budget without goal (if required) → already covered by require_goal
   - `invariant_errors_ok`: more invariant errors than expected → bug

2. **Invariant violations** — from `check_invariants`:
   - Errors → severity "bug"
   - Warnings → severity "warning"

Each violation or failed expectation becomes an `AuditFinding`. The mapping is straightforward
and happens at the end of `run_audit`.

## Decision 5: Audit Loop Structure

```
run_audit(stage, archetype_fn, expectation):
    sim = create_sim(stage)
    snapshots = []
    events_per_frame = []
    for frame in range(expectation.max_frames):
        if sim.goal_reached or sim.player_dead:
            # Dead players stay dead, goal means we're done
            if sim.goal_reached:
                break
            if sim.player_dead:
                # Record the death frame but stop
                break
        inp = archetype_fn(frame, sim)
        events = sim_step(sim, inp)
        snapshot = _capture_snapshot(sim, frame)
        snapshots.append(snapshot)
        events_per_frame.append(events)
    violations = check_invariants(sim, snapshots, events_per_frame)
    findings = _build_findings(sim, snapshots, violations, expectation)
    result = AuditResult(snapshots, events_per_frame, violations, sim)
    return findings, result
```

**Death handling:** When the player dies, `sim_step` returns `[DeathEvent()]` and sets
`player_dead=True`. On subsequent frames, `sim_step` immediately returns `[DeathEvent()]`
again. We should continue stepping to allow respawn mechanics if they exist, but cap at
max_frames. Actually, looking at the sim code: once `player_dead=True`, every subsequent
`sim_step` returns `[DeathEvent()]` immediately — there is no respawn in sim_step. So we
should break on death (or goal) to avoid wasting frames.

**Correction:** Re-reading the sim code, `sim.deaths` increments on death. We should let
the sim run and check if the player somehow revives (future respawn support). For now,
break on `player_dead` or `goal_reached`.

## Decision 6: Archetype Behaviors

### Walker — `make_walker()`
Hold right every frame. No jump. Simplest possible.
```
InputState(right=True)
```

### Jumper — `make_jumper()`
Hold right + jump whenever grounded.
Edge detection: press jump when `on_ground` and not already holding jump.

### Speed Demon — `make_speed_demon()`
State machine:
- APPROACH: hold right until frame 10 (build some speed)
- CROUCH: hold down for 1 frame (enter spindash)
- CHARGE: hold down + press jump for N frames (charge spindash)
- RELEASE: release down (launch spindash)
- RUN: hold right. If `ground_speed < threshold`, go to CROUCH.

### Cautious — `make_cautious()`
Tap-walk pattern: right for 10 frames, nothing for 5, right for 10, etc.
Occasionally (every ~120 frames) walk left for 15 frames.
Stop (release right) when on steep slopes (angle indicates slope).

### Wall Hugger — `make_wall_hugger()`
Hold right. When `abs(sim.player.physics.ground_speed) < 0.1` and
`sim.player.physics.on_ground` for several consecutive frames (wall detected), jump.

### Chaos — `make_chaos(seed: int)`
Seeded `random.Random(seed)`. Every 5–15 frames, pick random combo of directions/actions.
Deterministic because the RNG is seeded.

## Decision 7: format_findings

Simple string builder matching the ticket's example format:
```
FINDINGS (N bugs):
  [frame F, x=X] Description
    Expected: ...
    Actual: ...
```

Filter to bugs only or all findings based on the list passed in.

## Rejected Alternatives

### Reuse ScenarioOutcome as return type
Too coupled to the scenario/agent system. Would require faking a ScenarioDef. The audit
framework should be independent.

### Use agents instead of archetypes
Agents require observation extraction (`extract_observation`) which adds numpy dependency
to the audit path. Archetypes reading SimState directly are simpler and faster.

### Put archetypes in speednik/strategies.py
The ticket explicitly says `speednik/qa.py`. Strategies use `(int, Player)` signature;
mixing signatures in one module would be confusing.

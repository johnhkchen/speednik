# Design — T-010-10: scenario-runner-and-conditions

## Decision 1: Reward function reuse

### Options

**A. Extract free function from env.py** — Move reward logic into a shared module (e.g.,
`speednik/reward.py`). Both env and runner import it.

**B. Duplicate reward logic in runner** — Runner implements its own reward. Simpler but
risks drift between env and runner reward signals.

**C. Compute reward inline in runner, tracking prev_max_x locally** — Runner computes
reward with the same formula as env but doesn't extract a shared function. Keeps env
unchanged (no refactor of working code).

### Decision: Option C

Rationale: The env's `_compute_reward` is 15 lines. Extracting it to a shared function
requires refactoring env.py, which is outside this ticket's scope and risks breaking
T-010-06's tests. The runner can compute reward with the same formula by tracking
`prev_max_x` as a local variable in the loop. The formulas are simple enough that drift
is unlikely, and any future unification (T-010-11+) can extract the shared function then.

## Decision 2: check_conditions placement

### Options

**A. Add check_conditions to conditions.py** — Extend the existing conditions module with
the runtime checker alongside the dataclasses.

**B. New file conditions_checker.py** — Separate data definitions from runtime logic.

### Decision: Option A

Rationale: The ticket explicitly says "extend `speednik/scenarios/conditions.py`". The
conditions module already defines the types; adding the checker function keeps related code
together. The function is ~60 lines, not enough to justify a new file.

## Decision 3: alive_at_end semantics

The `alive_at_end` success condition only fires when the loop reaches max_frames without
earlier termination. During the loop, it returns `(None, None)`. On the final frame
(frame == max_frames - 1), if the player is alive, it returns `(True, "alive_at_end")`.

Implementation: `check_conditions` receives the current frame index. For `alive_at_end`,
it checks `frame == scenario.max_frames - 1 and not sim.player_dead`.

## Decision 4: stuck detection algorithm

### Options

**A. Position variance** — Compute variance of x-positions over the window. If variance
< tolerance, player is stuck. Requires squaring and summing.

**B. Position spread (max - min)** — If `max(x) - min(x) < tolerance` over the window,
player is stuck. Simpler and more intuitive — "player hasn't moved more than N pixels."

### Decision: Option B

Rationale: The ticket says "checks position variance over a sliding window" but the YAML
uses `tolerance: 2.0, window: 120` which reads as "moved less than 2 pixels in 120 frames."
Max-min spread matches the harness's `stuck_at()` concept and is easier to reason about.
The spec's `tolerance` parameter maps directly to the spread threshold.

## Decision 5: compute_metrics implementation

### Options

**A. Dict dispatch** — Map metric names to lambda/callables. Loop through requested
metrics, call each.

**B. Inline if-chain** — Simple if/elif for each metric name.

### Decision: Option A

Rationale: 9 metrics is enough that a dispatch dict is cleaner than a long if-chain.
Each metric is a small function of `(trajectory, sim, success)`. A dict of
`str -> Callable` keeps it extensible without complexity.

## Decision 6: FrameRecord.state type

The spec shows `state: str` in FrameRecord. PlayerState is an enum with `.value` string
attribute. Store `sim.player.state.value` (the string like "standing", "jumping", etc.)
to keep FrameRecord serialization-friendly without importing player module types.

## Decision 7: Tests organization

Extend `tests/test_scenarios.py` with new test classes for:
- `TestCheckConditions` — Unit tests for each of the 8 condition types.
- `TestRunScenario` — Integration tests using real stages.
- `TestDeterminism` — Two runs produce identical trajectories.
- `TestFrameRecord` / `TestScenarioOutcome` — Dataclass sanity.

This keeps all scenario-related tests in one file as the ticket specifies.

## Architecture

```
ScenarioDef (YAML)
    │
    ▼
run_scenario(scenario_def)
    ├── create_sim(stage)
    ├── apply start_override
    ├── resolve_agent(name, params)
    ├── agent.reset()
    │
    ├── LOOP (max_frames):
    │   ├── extract_observation(sim)
    │   ├── agent.act(obs) → action
    │   ├── action_to_input(action, prev) → inp
    │   ├── sim_step(sim, inp) → events
    │   ├── compute reward (inline)
    │   ├── append FrameRecord
    │   ├── check_conditions() → (success?, reason?)
    │   └── break if terminal
    │
    ├── compute_metrics(requested, trajectory, sim)
    └── return ScenarioOutcome

check_conditions(scenario, sim, trajectory, frame)
    ├── check success condition
    ├── check failure condition
    └── return (bool|None, str|None)
```

## Not in scope

- CLI entry point (§6.2) — separate ticket.
- Metrics comparison/baseline (§7.3) — separate ticket.
- Trajectory JSON serialization (§7.2) — separate ticket.
- velocity_profile metric (array, not scalar) — deferred.

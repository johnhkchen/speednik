# Research — T-010-10: scenario-runner-and-conditions

## What exists

### Scenario data layer (T-010-07/09 — complete)

- `speednik/scenarios/conditions.py` — Dataclasses: `SuccessCondition`, `FailureCondition`, `StartOverride`.
  Valid types defined as frozensets: 5 success types, 3 failure types.
- `speednik/scenarios/loader.py` — `ScenarioDef` dataclass and YAML parse/load functions.
  `load_scenario(path)`, `load_scenarios(paths, run_all, base)`.
- `speednik/scenarios/__init__.py` — Re-exports all public symbols.
- `scenarios/*.yaml` — 5 scenario files: `hillside_complete`, `hillside_hold_right`,
  `hillside_loop`, `gap_jump`, `pipeworks_jump`.

### Simulation layer (T-010-02/04 — complete)

- `speednik/simulation.py` — `SimState` dataclass, `create_sim(stage_name)`, `sim_step(sim, inp)`.
  Event types: `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`,
  `GoalReachedEvent`, `CheckpointEvent`. Union type alias `Event`.
- `create_sim_from_lookup()` — Synthetic terrain factory for tests.
- `sim_step` returns `list[Event]`, mutates `SimState` in place.
- Tracks: `frame`, `max_x_reached`, `rings_collected`, `deaths`, `goal_reached`, `player_dead`.

### Agent layer (T-010-05 — complete)

- `speednik/agents/base.py` — `Agent` Protocol: `act(obs) -> int`, `reset() -> None`.
- `speednik/agents/actions.py` — 8 discrete actions, `ACTION_MAP`, `action_to_input(action, prev_jump_held)`.
- `speednik/agents/registry.py` — `AGENT_REGISTRY` dict, `resolve_agent(name, params)`.
- 5 agents: `IdleAgent`, `HoldRightAgent`, `JumpRunnerAgent`, `SpindashAgent`, `ScriptedAgent`.

### Observation layer (T-010-09 — complete)

- `speednik/observation.py` — `OBS_DIM = 12`, `extract_observation(sim) -> np.ndarray`.
  12-dim flat vector: position, velocity, ground state, angle, progress, time.

### Environment layer (T-010-06 — complete)

- `speednik/env.py` — `SpeednikEnv(gym.Env)`. Uses `create_sim`, `sim_step`,
  `extract_observation`, `action_to_input`. Has `_compute_reward(events)`.
- Reward function: progress delta, speed bonus, goal bonus, death penalty, ring bonus, time cost.
- Jump edge detection via `_prev_jump_held` state tracked across frames.

### Player state model

- `speednik/player.py` — `PlayerState` enum: STANDING, RUNNING, JUMPING, ROLLING, SPINDASH, HURT, DEAD.
- `Player` has `.state` (PlayerState), `.physics` (PhysicsState), `.rings` (int).
- `PhysicsState` has: `x`, `y`, `x_vel`, `y_vel`, `ground_speed`, `angle`, `on_ground`,
  `is_rolling`, `facing_right`.

### Existing tests

- `tests/test_scenarios.py` — Tests YAML loading, condition parsing, validation. No runner tests.
- `tests/test_agents.py` — Protocol conformance, action mapping, behavior, registry, smoke tests.
- `tests/test_observation.py` — Shape, normalization, integration.
- `tests/test_simulation.py` — SimState creation, sim_step behavior, events, entities.

## What this ticket adds

The runner module (`speednik/scenarios/runner.py`) sits at Layer 4 — between agents (Layer 3)
and the Gymnasium wrapper (Layer 5). It orchestrates:

1. **Sim creation + start override** — `create_sim(stage)`, optionally reposition player.
2. **Agent resolution** — `resolve_agent(name, params)`, `agent.reset()`.
3. **Frame loop** — `extract_observation` → `agent.act` → `action_to_input` → `sim_step` → reward.
4. **Trajectory recording** — `FrameRecord` per frame with full state snapshot.
5. **Condition checking** — `check_conditions()` evaluates success/failure each frame.
6. **Metrics computation** — Aggregate stats from trajectory (max_x, avg speed, etc.).
7. **Wall-time measurement** — `time.perf_counter()` around the loop.

## Key interfaces to consume

| Symbol | Source | Used for |
|--------|--------|----------|
| `create_sim(stage)` | simulation.py | Initialize game state |
| `sim_step(sim, inp)` | simulation.py | Advance one frame |
| `SimState` | simulation.py | Read player state, metrics |
| `extract_observation(sim)` | observation.py | Get obs for agent |
| `action_to_input(action, prev)` | agents/actions.py | Convert action to InputState |
| `resolve_agent(name, params)` | agents/registry.py | Instantiate agent by name |
| `ScenarioDef` | scenarios/loader.py | Input to run_scenario |
| `SuccessCondition` | scenarios/conditions.py | Condition type + params |
| `FailureCondition` | scenarios/conditions.py | Condition type + params |

## Reward reuse

The spec says `compute_reward(sim, events)` is "same function as env." `SpeednikEnv._compute_reward`
is a method that uses `self._prev_max_x`, `self._step_count`, `self.max_steps`. The runner needs
a standalone version. Two approaches:
1. Extract env's reward logic into a free function.
2. Duplicate the reward logic in the runner.

The env's reward uses `_prev_max_x` which tracks per-step delta. The runner can track this
identically. The cleanest approach: extract a `compute_reward` free function that both env and
runner can call.

## Condition checking — the 8 types

From the spec §5.2:

| Condition | Category | Logic |
|-----------|----------|-------|
| `goal_reached` | success | `sim.goal_reached == True` |
| `position_x_gte` | success | `sim.player.physics.x >= value` (+ optional `min_speed`) |
| `position_y_lte` | success | `sim.player.physics.y <= value` |
| `alive_at_end` | success | Only at max_frames (loop exit without early termination) |
| `rings_gte` | success | `sim.rings_collected >= value` |
| `player_dead` | failure | `sim.player_dead == True` |
| `stuck` | failure | Position variance < tolerance over sliding window |
| `any` | failure | Any sub-condition triggers |

`alive_at_end` is special: it's a success-if-survived condition that only fires when the loop
ends naturally (frame == max_frames - 1). During the loop, it should return (None, None).

`stuck` needs a sliding window over trajectory x-positions. Check last N frames, compute
variance or max-min spread. If spread < tolerance, player is stuck.

## Determinism

SimState is fully deterministic — no RNG in physics, collision, or enemy AI. Same inputs produce
identical outputs. The ticket requires a test: run scenario twice, assert identical trajectories.
This is straightforward since `action_to_input` and `sim_step` are pure functions of state.

## Metrics

Spec §7.1 lists 9 metrics. The scenario YAML specifies which metrics to compute via the
`metrics` list field. The runner computes only requested metrics. Common ones:
- `completion_time`: `len(trajectory)` if success, else null
- `max_x`: `max(r.x for r in trajectory)`
- `rings_collected`: `sim.rings_collected`
- `death_count`: `sim.deaths`
- `total_reward`: `sum(r.reward for r in trajectory)`
- `average_speed`: `mean(abs(r.x_vel) for r in trajectory)`
- `peak_speed`: `max(abs(r.x_vel) for r in trajectory)`
- `time_on_ground`: `count(r.on_ground) / len(trajectory)`
- `stuck_at`: x position where stuck was detected (or null)

## File locations (per ticket)

- `speednik/scenarios/runner.py` — `run_scenario`, `ScenarioOutcome`, `FrameRecord`
- `speednik/scenarios/conditions.py` — Extend with `check_conditions` implementation
- `tests/test_scenarios.py` — Extend with runner and condition tests

## Constraints

- No Pyxel imports anywhere in the runner or conditions.
- All existing tests must continue to pass.
- `uv run pytest tests/test_scenarios.py -x` must pass.

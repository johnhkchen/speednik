# T-011-01 Research: Stage Walkthrough Smoke Tests

## Simulation Infrastructure

### `create_sim(stage_name: str) → SimState`
- Loads a stage by name: `"hillside"`, `"pipeworks"`, `"skybridge"`
- Returns `SimState` dataclass with player, entities, metrics, and level bounds
- Skybridge injects a boss enemy (`enemy_egg_piston`) at spawn position

### `sim_step(sim: SimState, inp: InputState) → list[Event]`
- Advances simulation by one frame
- Updates physics, entity collisions, ring collection, spring activation,
  checkpoint, pipe travel, liquid zone damage, enemy collision, goal detection
- Tracks metrics: `sim.max_x_reached`, `sim.rings_collected`, `sim.deaths`
- Sets `sim.goal_reached` and `sim.player_dead` flags
- Returns list of typed events (RingCollectedEvent, DeathEvent, GoalReachedEvent, etc.)
- Dead player guard: if `player_dead`, returns `[DeathEvent()]` without advancing physics

### SimState Metrics Fields
| Field | Type | Description |
|-------|------|-------------|
| `frame` | int | Frame counter (incremented by sim_step) |
| `max_x_reached` | float | Furthest X position ever seen |
| `rings_collected` | int | Total rings picked up |
| `deaths` | int | Death count |
| `goal_reached` | bool | True once player touches goal |
| `player_dead` | bool | True when player enters DEAD state |

## Stage Data (Verified from Runtime)

| Stage | Start | Goal | Width | Height | Rings | Springs | Enemies |
|-------|-------|------|-------|--------|-------|---------|---------|
| hillside | (64, 610) | (4758, 642) | 4800 | 720 | 200 | 1 | 4 |
| pipeworks | (200, 510) | (5558, 782) | 5600 | 1024 | 300 | 4 | 11 |
| skybridge | (64, 490) | (5158, 482) | 5200 | 896 | 250 | 7 | 17 |

- Hillside: easiest stage, few enemies, one spring, simple terrain
- Pipeworks: has pipes, liquid zones (damage hazards), more enemies
- Skybridge: highest enemy count plus a boss; springs provide vertical traversal

## Agent System

### Agent Protocol
```python
class Agent(Protocol):
    def act(self, obs: np.ndarray) -> int  # Returns action 0-7
    def reset(self) -> None
```

### Available Agents (via `resolve_agent`)
| Registry Name | Class | Behavior |
|---------------|-------|----------|
| `hold_right` | HoldRightAgent | ACTION_RIGHT every frame |
| `jump_runner` | JumpRunnerAgent | ACTION_RIGHT, jumps on landing |
| `spindash` | SpindashAgent | CROUCH→CHARGE→RELEASE→RUN cycle |

### `action_to_input(action: int, prev_jump_held: bool) → (InputState, bool)`
- Converts discrete action to InputState with jump edge detection
- Returns updated prev_jump_held for next frame
- Essential: jump_pressed only fires on rising edge

### Ticket Strategy Mapping
| Ticket strategy | Agent registry | Params |
|-----------------|----------------|--------|
| `hold_right` | `hold_right` | None |
| `hold_right_jump` | `jump_runner` | None |
| `spindash_right` | `spindash` | `{charge_frames: 3, redash_speed: 0.15}` |

## Scenario System (Alternative Approach)

The `speednik.scenarios` module provides `run_scenario(ScenarioDef) → ScenarioOutcome`:
- Handles agent resolution, simulation loop, event tracking, condition checking
- Computes metrics: `max_x`, `stuck_at`, `rings_collected`, `death_count`, `completion_time`
- `stuck_at` metric: checks last 120 frames, returns X position if spread < 2.0px

### ScenarioOutcome Fields
- `success: bool` — whether success condition triggered
- `reason: str` — "goal_reached", "player_dead", "stuck", "timed_out"
- `frames_elapsed: int` — total frames run
- `metrics: dict` — computed metric values
- `trajectory: list[FrameRecord]` — per-frame snapshots

## Existing Test Patterns

### `tests/test_simulation.py` (487 lines)
- Uses `create_sim` + `sim_step` directly
- Tests frame-by-frame with InputState objects
- Parity tests comparing harness vs sim_step

### `tests/test_scenarios.py` (817 lines)
- Tests ScenarioDef loading, condition checking, metric computation
- Integration tests run `run_scenario` on real YAML scenarios
- Determinism test: two identical runs produce identical trajectories

### `tests/test_agents.py` (533 lines)
- Protocol conformance, action mapping, behavioral correctness
- Smoke tests: agents driving real simulation

## Observation Module

`extract_observation(sim) → np.ndarray(12)`:
- Provides normalized player state (position, velocity, angles, progress)
- Required by agents for `act(obs)` calls

## Key Dependencies

- `pytest>=9.0.2` — test framework
- `gymnasium>=1.2.3` — not needed for this ticket
- No Pyxel imports in simulation/agent/scenario code — fully headless

## Constraints and Assumptions

1. All simulation is deterministic — same inputs produce same outputs
2. `sim_step` runs ~20k-50k calls/sec — 6000 frames ≈ 0.1-0.3 seconds wall time
3. The ticket wants tests in `tests/test_walkthrough.py` (new file)
4. Must use `sim_step` / `create_sim`, not the old harness
5. The scenario runner is a higher-level wrapper that uses sim_step internally
6. Three stages × three strategies = 9 parameterized test cases

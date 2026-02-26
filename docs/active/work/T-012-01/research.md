# Research — T-012-01: Archetype Library & Expectation Framework

## Scope

Build 6 player archetype strategy functions and a QA audit framework (`run_audit`,
`BehaviorExpectation`, `AuditFinding`, `format_findings`) that treats failures as findings,
not broken tests. Output: `speednik/qa.py` + `tests/test_qa_framework.py`.

---

## Existing Systems

### Simulation Layer (`speednik/simulation.py`)

- `SimState` holds all game state: player, entities, rings, frame counter, metrics.
- `create_sim(stage_name)` loads a real stage ("hillside", "pipeworks", "skybridge").
- `create_sim_from_lookup(tile_lookup, x, y)` creates sim from synthetic grids.
- `sim_step(sim, inp: InputState) -> list[Event]` advances one frame. Returns typed events:
  `RingCollectedEvent`, `DamageEvent`, `DeathEvent`, `SpringEvent`, `GoalReachedEvent`,
  `CheckpointEvent`.
- Tracks `max_x_reached`, `rings_collected`, `deaths`, `goal_reached`, `player_dead`.

### Input System (`speednik/physics.py`)

- `InputState(left, right, jump_pressed, jump_held, down_held, up_held)`.
- `jump_pressed` is rising-edge only — must be False → True transition.
- `PhysicsState` holds position, velocity, ground_speed, angle, on_ground, is_rolling,
  facing_right, spinrev, is_charging_spindash, slip_timer.

### Player (`speednik/player.py`)

- `Player` wraps `PhysicsState` + `PlayerState` enum (STANDING, RUNNING, JUMPING, ROLLING,
  SPINDASH, HURT, DEAD) + rings, lives, invulnerability.
- Respawn coordinates tracked per checkpoint.

### Existing Strategies (`speednik/strategies.py`)

- `Strategy = Callable[[int, Player], InputState]` — takes `(frame, player)`.
- Existing: `idle()`, `hold_right()`, `hold_left()`, `hold_right_jump()`,
  `spindash_right(charge_frames, redash_threshold)`, `scripted(timeline)`.
- `run_scenario(tile_lookup, x, y, strategy, frames)` — lightweight loop using
  `player_update` directly (no entities). Returns `ScenarioResult`.
- `run_on_stage(stage_name, strategy, frames)` — wrapper using real stage terrain only.
- `FrameSnapshot` satisfies `SnapshotLike` protocol for invariant checking.

**Key gap:** `run_scenario` / `run_on_stage` skip entities — no rings, springs, enemies,
goals. For audit purposes we need `sim_step` which handles the full entity pipeline.

### Agent System (`speednik/agents/`)

- `Agent` protocol: `act(obs: ndarray) -> int`, `reset()`.
- Discrete actions 0–7 mapped via `action_to_input(action, prev_jump_held)`.
- Registry: idle, hold_right, jump_runner, spindash, scripted, ppo.

**Key distinction:** Agents take observations (ndarray), strategies take `(frame, Player)`.
The ticket specifies strategy signature `(frame, SimState) -> InputState`. This is a new
third form — takes SimState instead of Player, for access to game-level info.

### Invariant Checker (`speednik/invariants.py`)

- `check_invariants(sim, snapshots, events_per_frame) -> list[Violation]`.
- `Violation(frame, invariant, details, severity)`.
- Requires `SnapshotLike` protocol: frame, x, y, x_vel, y_vel, on_ground, quadrant, state.
- `FrameSnapshot` from strategies satisfies this protocol directly.

### Synthetic Grids (`speednik/grids.py`)

- `build_flat(width, ground_row)`, `build_gap(approach, gap, landing, ground_row)`,
  `build_slope(approach, slope, angle, ground_row)`, `build_ramp(...)`, `build_loop(...)`.
- All return `(dict, TileLookup)`.

### Scenario Engine (`speednik/scenarios/`)

- `ScenarioDef`, `ScenarioOutcome`, `FrameRecord`, `run_scenario`.
- Uses agents (not strategies) — different abstraction layer.
- `FrameRecord` lacks `quadrant` field, so not directly usable with invariant checker.

---

## Signature Decision

The ticket specifies archetype signature `(frame: int, sim: SimState) -> InputState`.
This differs from:
- `Strategy = Callable[[int, Player], InputState]` (existing strategies)
- `Agent.act(obs: ndarray) -> int` (agent system)

The SimState signature is richer: archetypes can read `sim.player_dead`, `sim.goal_reached`,
`sim.frame`, `sim.player.physics.*`, `sim.player.state`. This is appropriate for complex
behaviors like speed demon (needs ground_speed to decide when to re-spindash) and wall hugger
(needs velocity to detect walls).

---

## Audit Loop Design Constraints

`run_audit` must:
1. Create a SimState via `create_sim(stage)` for real stages.
2. Step frame-by-frame with `sim_step(sim, inp)`, collecting events.
3. Build `FrameSnapshot` per frame for invariant checking.
4. Pass full trajectory to `check_invariants`.
5. Compare trajectory metrics against `BehaviorExpectation`.
6. Return `(list[AuditFinding], ProbeResult)`.

**ProbeResult ambiguity:** The ticket signature says `-> tuple[list[AuditFinding], ProbeResult]`
but `ProbeResult` doesn't exist in the codebase. The closest types are:
- `ScenarioResult` (from strategies) — has snapshots, final, max_x, stuck_at.
- `ScenarioOutcome` (from scenarios) — has success, reason, metrics, trajectory.

The most useful return alongside findings is trajectory data. We should define a lightweight
result type or reuse `ScenarioResult` adapted for the sim_step loop. A simple dataclass
with snapshots, events, final sim state, and summary metrics is cleanest.

---

## Jump Edge Detection

Critical detail: `InputState.jump_pressed` must be True only on the rising edge. The archetype
functions receive `(frame, sim)` and return `InputState`. The caller must NOT set
`jump_pressed=True` on consecutive frames — only on the first frame of a jump request.

Options:
1. Archetypes manage their own edge detection via closure state.
2. The audit loop manages edge detection by tracking previous jump state.
3. Use `action_to_input` which handles this.

Option 1 is cleanest — each archetype closure tracks `prev_jump` internally and only sets
`jump_pressed=True` on the 0→1 transition. This keeps the audit loop simple.

---

## Test Strategy for Framework Tests

`tests/test_qa_framework.py` needs to verify:
- Walker on flat grid → 0 findings (clean terrain works).
- Walker on grid with gap too wide → finding generated (stuck or fell).
- Invariant violations surface as findings.
- `format_findings` produces expected string format.
- Chaos archetype is deterministic (same seed → same trajectory).
- Each archetype produces valid InputState values.

Use synthetic grids from `speednik/grids.py` to create controlled scenarios.

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `speednik/qa.py` | Create | Archetypes, expectations, run_audit, findings |
| `tests/test_qa_framework.py` | Create | Framework unit tests |

No modifications to existing files needed.

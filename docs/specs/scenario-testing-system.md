# Speednik Scenario & Testing System — Technical Specification

## 1. Architecture Overview

Six layers compose the system. Each is a distinct module with a unidirectional dependency chain — no layer reaches upward.

```
┌──────────────────────────────────────────────────────────┐
│  6. CleanRL Entry Point (ppo_speednik.py)                │
│     Forked single-file PPO → gym.make("speednik/...")    │
├──────────────────────────────────────────────────────────┤
│  5. Gymnasium Wrapper (speednik/env.py)                  │
│     reset() / step() / observation_space / action_space  │
├──────────────────────────────────────────────────────────┤
│  4. Scenario Runner (speednik/scenarios/runner.py)       │
│     Loads scenario defs, runs agent, collects metrics    │
├──────────────────────────────────────────────────────────┤
│  3. Agent Interface (speednik/agents/base.py)            │
│     Protocol: observe(obs) → action. All agents conform  │
├──────────────────────────────────────────────────────────┤
│  2. Headless Simulation (speednik/simulation.py)         │
│     Pyxel-free game loop: input → physics → collision →  │
│     objects → enemies → state. No rendering, no audio.   │
├──────────────────────────────────────────────────────────┤
│  1. Game Core (existing modules)                         │
│     physics.py, terrain.py, player.py, objects.py,       │
│     enemies.py, camera.py, level.py, constants.py        │
└──────────────────────────────────────────────────────────┘
```

**Data flow for a single frame:**

```
Agent.act(observation)
  → action (int)
  → Simulation.step(action)
    → InputState mapping
    → player_update(player, inp, tile_lookup)
    → check_ring_collection, check_spring_collision, ...
    → check_enemy_collision, update_enemies, ...
    → collision events processed (rings gained, damage taken, etc.)
    → new observation extracted from game state
  → (observation, reward, terminated, truncated, info)
```

### Key Constraint

The game core (Layer 1) already has zero Pyxel dependencies in its logic modules. The existing test harness (`tests/harness.py`) proves this works. The simulation layer (Layer 2) extends the harness to include objects and enemies, which `harness.py` currently omits.

---

## 2. Headless Mode

### 2.1 Why Pyxel Cannot Be Used Headless

Pyxel v2.x unconditionally calls `SDL_Init(VIDEO)` and `SDL_CreateWindow` with `SDL_WINDOW_OPENGL` during `pyxel.init()`. There is no flag, environment variable, or API parameter to bypass this. `SDL_VIDEODRIVER=dummy` fails because the dummy driver lacks OpenGL context support. `SDL_VIDEODRIVER=offscreen` fails on macOS (no EGL). The Pyxel event loop (`pyxel.run`) couples update and draw in a single loop body with `SDL_GL_SwapWindow` and `SDL_Delay` for frame timing.

**Bottom line**: Pyxel's rendering pipeline cannot be disabled. The headless approach must bypass Pyxel entirely.

### 2.2 The Bypass Architecture

The game core modules (`physics.py`, `player.py`, `terrain.py`, `objects.py`, `enemies.py`, `level.py`, `camera.py`) do not import Pyxel. Only three modules do: `main.py`, `renderer.py`, `audio.py`. The simulation layer replaces `main.py`'s orchestration loop with a pure-Python equivalent that never imports Pyxel.

**Measured performance**: The existing `tests/harness.py` achieves ~140,000 updates/second (pure player+terrain simulation) vs ~500 FPS with `pyxel.flip()`. This is a **280x speedup**. Full simulation with objects and enemies will be slower but still far above real-time — estimated 20,000–50,000 updates/second depending on entity count.

### 2.3 Simulation Module Design

```python
# speednik/simulation.py

@dataclass
class SimState:
    """Complete headless game state — everything main.py:App tracks
    for gameplay, minus rendering/audio state."""
    player: Player
    tile_lookup: TileLookup
    rings: list[Ring]
    springs: list[Spring]
    checkpoints: list[Checkpoint]
    pipes: list[LaunchPipe]
    liquid_zones: list[LiquidZone]
    enemies: list[Enemy]
    goal_x: float
    goal_y: float
    level_width: int
    level_height: int
    frame: int = 0
    # Metrics tracking
    max_x_reached: float = 0.0
    rings_collected: int = 0
    deaths: int = 0
    # Terminal state
    goal_reached: bool = False
    player_dead: bool = False


def create_sim(stage_name: str) -> SimState:
    """Load a stage and initialize all game state. No Pyxel."""
    stage = load_stage(stage_name)
    sx, sy = stage.player_start
    player = create_player(float(sx), float(sy))
    return SimState(
        player=player,
        tile_lookup=stage.tile_lookup,
        rings=load_rings(stage.entities),
        springs=load_springs(stage.entities),
        checkpoints=load_checkpoints(stage.entities),
        pipes=load_pipes(stage.entities),
        liquid_zones=load_liquid_zones(stage.entities),
        enemies=load_enemies(stage.entities),
        goal_x=...,  # extracted from entities
        goal_y=...,
        level_width=stage.level_width,
        level_height=stage.level_height,
    )


def sim_step(sim: SimState, inp: InputState) -> list[Event]:
    """Advance one frame. Returns list of events that occurred.
    Mirrors main.py:_update_gameplay() without rendering/audio."""
    if sim.player.state == PlayerState.DEAD:
        sim.player_dead = True
        return [DeathEvent()]

    player_update(sim.player, inp, sim.tile_lookup)
    sim.frame += 1

    events = []
    events.extend(check_ring_collection(sim.player, sim.rings))
    events.extend(check_spring_collision(sim.player, sim.springs))
    events.extend(check_checkpoint_collision(sim.player, sim.checkpoints))
    update_pipe_travel(sim.player, sim.pipes)
    events.extend(update_liquid_zones(sim.player, sim.liquid_zones))
    update_enemies(sim.enemies)
    events.extend(check_enemy_collision(sim.player, sim.enemies))
    update_spring_cooldowns(sim.springs)

    goal = check_goal_collision(sim.player, sim.goal_x, sim.goal_y)
    if goal == GoalEvent.REACHED:
        sim.goal_reached = True
        events.append(goal)

    # Track metrics
    sim.max_x_reached = max(sim.max_x_reached, sim.player.physics.x)
    sim.rings_collected += sum(1 for e in events if isinstance(e, RingEvent) and e == RingEvent.COLLECTED)

    return events
```

This is the single source of truth for "what happens in one frame." Both the Gymnasium wrapper and the scenario runner call `sim_step`.

---

## 3. Gymnasium Wrapper

### 3.1 Environment Class

```python
# speednik/env.py

import gymnasium as gym
from gymnasium import spaces
import numpy as np

# Action enumeration — all meaningful button combinations
ACTION_NOOP       = 0
ACTION_LEFT       = 1
ACTION_RIGHT      = 2
ACTION_JUMP       = 3
ACTION_LEFT_JUMP  = 4
ACTION_RIGHT_JUMP = 5
ACTION_DOWN       = 6
ACTION_DOWN_JUMP  = 7  # spindash charge

NUM_ACTIONS = 8

# Maps action int → InputState
ACTION_MAP = {
    ACTION_NOOP:       InputState(),
    ACTION_LEFT:       InputState(left=True),
    ACTION_RIGHT:      InputState(right=True),
    ACTION_JUMP:       InputState(jump_pressed=True, jump_held=True),
    ACTION_LEFT_JUMP:  InputState(left=True, jump_pressed=True, jump_held=True),
    ACTION_RIGHT_JUMP: InputState(right=True, jump_pressed=True, jump_held=True),
    ACTION_DOWN:       InputState(down_held=True),
    ACTION_DOWN_JUMP:  InputState(down_held=True, jump_pressed=True, jump_held=True),
}


class SpeednikEnv(gym.Env):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 60}

    def __init__(self, stage: str = "hillside", render_mode=None, max_steps=3600):
        super().__init__()
        self.stage_name = stage
        self.render_mode = render_mode
        self.max_steps = max_steps  # 60 seconds at 60 FPS

        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(OBS_DIM,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(NUM_ACTIONS)

        self.sim: SimState | None = None
        self._step_count = 0
        self._prev_jump_held = False

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.sim = create_sim(self.stage_name)
        self._step_count = 0
        self._prev_jump_held = False
        return self._get_obs(), self._get_info()

    def step(self, action: int):
        inp = self._action_to_input(action)
        events = sim_step(self.sim, inp)
        self._step_count += 1

        obs = self._get_obs()
        reward = self._compute_reward(events)
        terminated = self.sim.goal_reached or self.sim.player_dead
        truncated = self._step_count >= self.max_steps
        info = self._get_info()

        return obs, reward, terminated, truncated, info

    def _action_to_input(self, action: int) -> InputState:
        base = ACTION_MAP[action]
        # Handle jump_pressed vs jump_held across frames:
        # jump_pressed should only be True on the first frame of a jump action
        jump_in_action = base.jump_pressed
        inp = InputState(
            left=base.left,
            right=base.right,
            jump_pressed=jump_in_action and not self._prev_jump_held,
            jump_held=jump_in_action,
            down_held=base.down_held,
            up_held=base.up_held,
        )
        self._prev_jump_held = jump_in_action
        return inp
```

### 3.2 Observation Space

Flat `Box` with structured state. This is CleanRL-compatible with zero modifications.

```python
OBS_DIM = 26  # Total observation vector size

def _get_obs(self) -> np.ndarray:
    p = self.sim.player.physics
    sim = self.sim

    obs = np.zeros(OBS_DIM, dtype=np.float32)

    # --- Player kinematics (6 values) ---
    obs[0] = p.x / sim.level_width                    # normalized x position
    obs[1] = p.y / sim.level_height                    # normalized y position
    obs[2] = p.x_vel / MAX_X_SPEED                     # normalized x velocity
    obs[3] = p.y_vel / MAX_X_SPEED                     # normalized y velocity
    obs[4] = float(p.on_ground)                        # grounded flag
    obs[5] = p.ground_speed / MAX_X_SPEED              # normalized ground speed

    # --- Player state (3 values) ---
    obs[6] = float(p.is_rolling)                       # rolling flag
    obs[7] = float(p.facing_right)                     # facing direction
    obs[8] = p.angle / 255.0                           # normalized surface angle

    # --- Progress (3 values) ---
    obs[9]  = sim.max_x_reached / sim.level_width      # max progress
    obs[10] = (sim.goal_x - p.x) / sim.level_width     # distance to goal
    obs[11] = float(self._step_count) / self.max_steps  # time fraction

    # --- Terrain raycasts (7 rays × 2 = 14 values) ---
    # Cast rays at angles: -45, -30, -15, 0, 15, 30, 45 degrees relative to player
    # Each ray returns: (distance / max_range, surface_angle / 255)
    ray_angles = [-45, -30, -15, 0, 15, 30, 45]
    max_ray_range = 128.0  # pixels
    for i, angle_deg in enumerate(ray_angles):
        dist, surf_angle = self._cast_terrain_ray(p.x, p.y, angle_deg, max_ray_range)
        obs[12 + i * 2]     = dist / max_ray_range
        obs[12 + i * 2 + 1] = surf_angle / 255.0

    return obs
```

The terrain raycast function uses the existing sensor casting infrastructure in `terrain.py` to probe for surfaces in a given direction from the player's position.

### 3.3 Reward Signal

```python
def _compute_reward(self, events) -> float:
    reward = 0.0
    sim = self.sim
    p = sim.player.physics

    # Primary: delta max(x) — rightward progress into new territory
    new_max = max(sim.max_x_reached, p.x)
    progress_delta = (new_max - sim.max_x_reached) / sim.level_width
    reward += progress_delta * 10.0

    # Speed bonus: reward maintaining high horizontal speed
    reward += abs(p.x_vel) / MAX_X_SPEED * 0.01

    # Goal completion: large bonus scaled by remaining time
    if sim.goal_reached:
        time_bonus = max(0.0, 1.0 - self._step_count / self.max_steps)
        reward += 10.0 + 5.0 * time_bonus

    # Death penalty
    if sim.player_dead:
        reward -= 5.0

    # Ring collection: small bonus per ring
    for e in events:
        if e == RingEvent.COLLECTED:
            reward += 0.1

    # Time penalty: small per-frame cost to discourage stalling
    reward -= 0.001

    return reward
```

**Design rationale**: The `delta_max(x)` reward is proven for Sonic-style games (OpenAI Retro Contest, 2018). It only rewards reaching new rightward positions, so backtracking through loops or over obstacles has zero penalty. The speed bonus is small enough to not dominate but encourages momentum maintenance. Ring collection provides a shaping signal for local exploration.

### 3.4 Registration

```python
# speednik/__init__.py (or speednik/env_registration.py)

import gymnasium as gym

gym.register(
    id="speednik/Hillside-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "hillside"},
    max_episode_steps=3600,
)

gym.register(
    id="speednik/Pipeworks-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "pipeworks"},
    max_episode_steps=5400,
)

gym.register(
    id="speednik/Skybridge-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "skybridge"},
    max_episode_steps=7200,
)
```

---

## 4. Agent Interface

### 4.1 Protocol

All agents — programmed behavior, RL policies, human replay — implement the same protocol.

```python
# speednik/agents/base.py

from typing import Protocol, runtime_checkable
import numpy as np

@runtime_checkable
class Agent(Protocol):
    """Anything that maps observations to actions."""

    def act(self, obs: np.ndarray) -> int:
        """Given an observation vector, return a discrete action index."""
        ...

    def reset(self) -> None:
        """Called at episode start. Reset internal state if any."""
        ...
```

Using `Protocol` instead of an ABC means agents don't need to inherit from anything — they just need the right method signatures. This is duck typing with static type checking.

### 4.2 Programmed Agents

```python
# speednik/agents/hold_right.py

class HoldRightAgent:
    """The simplest agent: always run right. Baseline for any scenario."""

    def act(self, obs: np.ndarray) -> int:
        return ACTION_RIGHT

    def reset(self) -> None:
        pass


# speednik/agents/jump_runner.py

class JumpRunnerAgent:
    """Run right, jump when approaching obstacles or gaps."""

    def __init__(self):
        self._airborne_last = False

    def act(self, obs: np.ndarray) -> int:
        on_ground = obs[4] > 0.5
        forward_ray_dist = obs[18]  # ray at 0 degrees

        # Jump if on ground and wall/obstacle detected within close range
        if on_ground and forward_ray_dist < 0.25:
            self._airborne_last = False
            return ACTION_RIGHT_JUMP

        # Re-jump after landing
        just_landed = self._airborne_last and on_ground
        self._airborne_last = not on_ground
        if just_landed:
            return ACTION_RIGHT_JUMP

        return ACTION_RIGHT

    def reset(self) -> None:
        self._airborne_last = False


# speednik/agents/spindash.py

class SpindashAgent:
    """Charge spindash, release, run right, re-dash when slow.
    Equivalent to the existing tests/harness.py spindash_right strategy
    but using the observation-based interface."""

    CROUCH, CHARGE, RELEASE, RUN = 0, 1, 2, 3

    def __init__(self, charge_frames=3, redash_speed=0.15):
        self.charge_frames = charge_frames
        self.redash_speed = redash_speed  # normalized ground_speed threshold
        self._phase = self.CROUCH
        self._counter = 0

    def act(self, obs: np.ndarray) -> int:
        on_ground = obs[4] > 0.5
        ground_speed = abs(obs[5])

        if self._phase == self.CROUCH:
            self._phase = self.CHARGE
            self._counter = 0
            return ACTION_DOWN

        if self._phase == self.CHARGE:
            self._counter += 1
            if self._counter >= self.charge_frames:
                self._phase = self.RELEASE
            return ACTION_DOWN_JUMP

        if self._phase == self.RELEASE:
            self._phase = self.RUN
            return ACTION_RIGHT

        # RUN phase
        if on_ground and ground_speed < self.redash_speed:
            self._phase = self.CROUCH
            return ACTION_DOWN

        return ACTION_RIGHT

    def reset(self) -> None:
        self._phase = self.CROUCH
        self._counter = 0
```

### 4.3 RL Policy Agent (Wraps a Trained Model)

```python
# speednik/agents/ppo_agent.py

import torch
import numpy as np

class PPOAgent:
    """Wraps a trained CleanRL PPO model as an Agent."""

    def __init__(self, model_path: str, device: str = "cpu"):
        self.device = torch.device(device)
        self.model = torch.load(model_path, map_location=self.device)
        self.model.eval()

    def act(self, obs: np.ndarray) -> int:
        with torch.no_grad():
            obs_tensor = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
            action, _, _, _ = self.model.get_action_and_value(obs_tensor)
            return action.item()

    def reset(self) -> None:
        pass
```

---

## 5. Scenario Definition

### 5.1 Format

Scenarios are YAML files. Code-driven scenarios for complex logic can also be defined as Python functions, but the standard path is declarative YAML.

```yaml
# scenarios/hillside_complete.yaml
name: hillside_complete
description: Complete Hillside Rush from start to goal
stage: hillside
agent: spindash          # agent class name (resolved from speednik/agents/)
agent_params:            # passed as kwargs to agent constructor
  charge_frames: 3
  redash_speed: 0.15
max_frames: 3600         # 60 seconds
success:
  type: goal_reached     # one of: goal_reached, position_x_gte, alive_at_end
failure:
  type: player_dead
metrics:
  - completion_time      # frames to success (if succeeded)
  - max_x               # furthest x reached
  - rings_collected      # total rings
  - death_count          # number of deaths (for multi-life scenarios)
  - velocity_profile     # x_vel per frame (for visualization)
```

```yaml
# scenarios/hillside_loop.yaml
name: hillside_loop
description: Navigate the loop-de-loop without losing speed
stage: hillside
agent: hold_right
max_frames: 600
start_override:          # optional: override stage's default start
  x: 800
  y: 300
success:
  type: position_x_gte
  value: 1200
  min_speed: 4.0         # must still be moving this fast at success point
failure:
  type: any
  conditions:
    - player_dead
    - stuck: { tolerance: 2.0, window: 30 }  # reuse harness stuck_at logic
```

```yaml
# scenarios/gap_jump.yaml
name: gap_jump
description: Cross a gap sequence using timed jumps
stage: hillside
agent: scripted
agent_params:
  timeline:
    - [0, 120, { right: true }]
    - [120, 122, { right: true, jump_pressed: true, jump_held: true }]
    - [122, 200, { right: true, jump_held: true }]
    - [200, 300, { right: true }]
max_frames: 300
success:
  type: position_x_gte
  value: 500
failure:
  type: player_dead
```

### 5.2 Success/Failure Conditions

| Condition | Parameters | Semantics |
|-----------|-----------|-----------|
| `goal_reached` | — | Stage goal entity reached |
| `position_x_gte` | `value`, optional `min_speed` | Player x >= value (and optionally still moving fast) |
| `position_y_lte` | `value` | Player y <= value (reached a height) |
| `player_dead` | — | Player entered DEAD state |
| `alive_at_end` | — | Success if player survives to max_frames |
| `stuck` | `tolerance`, `window` | Failure if player position variance < tolerance within window frames |
| `rings_gte` | `value` | Success if rings collected >= value |
| `any` | `conditions` | Compound: any sub-condition triggers |

---

## 6. Scenario Runner

### 6.1 Runner Module

```python
# speednik/scenarios/runner.py

@dataclass
class ScenarioOutcome:
    name: str
    success: bool
    reason: str                        # "goal_reached", "timed_out", "player_dead", etc.
    frames_elapsed: int
    metrics: dict[str, Any]            # completion_time, max_x, etc.
    trajectory: list[FrameRecord]      # per-frame state for replay/visualization
    wall_time_ms: float                # actual elapsed wall-clock time


@dataclass
class FrameRecord:
    frame: int
    x: float
    y: float
    x_vel: float
    y_vel: float
    ground_speed: float
    angle: int
    on_ground: bool
    state: str
    action: int
    reward: float
    rings: int
    events: list[str]


def run_scenario(scenario_def: ScenarioDef) -> ScenarioOutcome:
    """Execute a single scenario to completion."""
    sim = create_sim(scenario_def.stage)

    # Apply start override if specified
    if scenario_def.start_override:
        sim.player.physics.x = scenario_def.start_override.x
        sim.player.physics.y = scenario_def.start_override.y

    agent = resolve_agent(scenario_def.agent, scenario_def.agent_params)
    agent.reset()

    trajectory = []
    start_time = time.perf_counter()

    for frame in range(scenario_def.max_frames):
        obs = extract_observation(sim)
        action = agent.act(obs)
        inp = action_to_input(action)
        events = sim_step(sim, inp)
        reward = compute_reward(sim, events)  # same function as env

        trajectory.append(FrameRecord(
            frame=frame,
            x=sim.player.physics.x,
            y=sim.player.physics.y,
            x_vel=sim.player.physics.x_vel,
            y_vel=sim.player.physics.y_vel,
            ground_speed=sim.player.physics.ground_speed,
            angle=sim.player.physics.angle,
            on_ground=sim.player.physics.on_ground,
            state=sim.player.state.value,
            action=action,
            reward=reward,
            rings=sim.player.rings,
            events=[str(e) for e in events],
        ))

        # Check terminal conditions
        success, reason = check_conditions(scenario_def, sim, trajectory)
        if success is not None:
            break

    wall_time = (time.perf_counter() - start_time) * 1000
    metrics = compute_metrics(scenario_def.metrics, trajectory, sim)

    return ScenarioOutcome(
        name=scenario_def.name,
        success=success if success is not None else False,
        reason=reason or "timed_out",
        frames_elapsed=len(trajectory),
        metrics=metrics,
        trajectory=trajectory,
        wall_time_ms=wall_time,
    )
```

### 6.2 CLI Entry Point

```python
# speednik/scenarios/cli.py — invoked as: uv run python -m speednik.scenarios.cli

def main():
    parser = argparse.ArgumentParser(description="Run Speednik scenarios")
    parser.add_argument("scenarios", nargs="*", help="Scenario YAML files or glob patterns")
    parser.add_argument("--all", action="store_true", help="Run all scenarios in scenarios/")
    parser.add_argument("--agent", help="Override agent for all scenarios")
    parser.add_argument("--output", "-o", help="Output directory for results JSON")
    parser.add_argument("--trajectory", action="store_true", help="Include full trajectory in output")
    parser.add_argument("--compare", help="Compare against baseline results JSON")
    args = parser.parse_args()

    scenarios = load_scenario_defs(args.scenarios, run_all=args.all)
    results = []

    for scenario_def in scenarios:
        if args.agent:
            scenario_def.agent = args.agent
        outcome = run_scenario(scenario_def)
        results.append(outcome)
        print_outcome(outcome)

    if args.output:
        save_results(results, args.output, include_trajectory=args.trajectory)
    if args.compare:
        compare_results(results, args.compare)
```

Usage:

```bash
# Run one scenario
uv run python -m speednik.scenarios.cli scenarios/hillside_complete.yaml

# Run all scenarios
uv run python -m speednik.scenarios.cli --all

# Run with a different agent
uv run python -m speednik.scenarios.cli --all --agent hold_right

# Save results and compare to baseline
uv run python -m speednik.scenarios.cli --all -o results/run_001.json --compare results/baseline.json
```

---

## 7. Metrics and Recording

### 7.1 Per-Scenario Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `completion_time` | `int` | Frames to success condition (null if failed) |
| `max_x` | `float` | Furthest rightward position reached |
| `rings_collected` | `int` | Total rings picked up |
| `death_count` | `int` | Times player died |
| `total_reward` | `float` | Sum of per-frame rewards |
| `average_speed` | `float` | Mean |x_vel| across all frames |
| `peak_speed` | `float` | Maximum |x_vel| observed |
| `time_on_ground` | `float` | Fraction of frames where on_ground=True |
| `stuck_at` | `float|null` | X position where player got stuck (or null) |

### 7.2 Trajectory Format

The trajectory is a list of `FrameRecord` objects (one per frame). When serialized to JSON:

```json
{
  "name": "hillside_complete",
  "success": true,
  "reason": "goal_reached",
  "frames_elapsed": 1847,
  "wall_time_ms": 42.3,
  "metrics": {
    "completion_time": 1847,
    "max_x": 3200.5,
    "rings_collected": 47,
    "average_speed": 4.2,
    "peak_speed": 12.1
  },
  "trajectory": [
    {"frame": 0, "x": 128.0, "y": 400.0, "x_vel": 0.0, "y_vel": 0.0, ...},
    {"frame": 1, "x": 128.05, "y": 400.0, "x_vel": 0.05, "y_vel": 0.0, ...},
    ...
  ]
}
```

Trajectories can be large (3600 frames × ~12 fields = ~43K entries). By default the CLI omits them unless `--trajectory` is passed. For comparison runs, only the metrics dict is needed.

### 7.3 Comparison

When `--compare baseline.json` is passed, the runner prints a diff:

```
hillside_complete:
  completion_time: 1847 → 1623 (-12.1%)  ✓ faster
  max_x:           3200 → 3200 (0.0%)
  average_speed:   4.2  → 4.8  (+14.3%)  ✓ faster
  rings_collected:  47  →  52  (+10.6%)
```

This enables regression testing: run all scenarios, compare to a known-good baseline, flag regressions.

---

## 8. CleanRL Integration

### 8.1 Minimal Fork

Copy CleanRL's `ppo.py` (not `ppo_atari.py` — we use structured observations, not pixels) into the project as `tools/ppo_speednik.py`. The required changes are:

**Change 1**: Add the registration import at the top.

```python
import speednik.env_registration  # triggers gym.register() calls
```

**Change 2**: Change the default `env_id` in the `Args` dataclass.

```python
env_id: str = "speednik/Hillside-v0"
```

That's it. CleanRL's `ppo.py` uses `Discrete` action space with `Categorical` distribution and `Box` observation space with MLP actor/critic — both match our env exactly.

### 8.2 Recommended Wrapper Stack

In the forked `make_env`:

```python
def make_env(env_id, idx, capture_video, run_name):
    def thunk():
        env = gym.make(env_id)
        env = gym.wrappers.RecordEpisodeStatistics(env)
        # Normalize obs for stable gradients
        env = gym.wrappers.NormalizeObservation(env)
        env = gym.wrappers.TransformObservation(
            env, lambda obs: np.clip(obs, -10, 10), observation_space=env.observation_space
        )
        # Normalize rewards
        env = gym.wrappers.NormalizeReward(env, gamma=0.99)
        env = gym.wrappers.TransformReward(env, lambda r: np.clip(r, -10, 10))
        return env
    return thunk
```

### 8.3 Running Training

```bash
uv run python tools/ppo_speednik.py \
    --env-id speednik/Hillside-v0 \
    --total-timesteps 1000000 \
    --num-envs 8 \
    --num-steps 256 \
    --learning-rate 2.5e-4 \
    --track  # enables Weights & Biases logging
```

### 8.4 Loading a Trained Policy as an Agent

After training, CleanRL saves the model. The `PPOAgent` class (Section 4.3) loads it and conforms to the Agent protocol. This means a trained policy can be used in the scenario runner identically to a programmed agent:

```yaml
# scenarios/hillside_ppo.yaml
name: hillside_ppo_eval
stage: hillside
agent: ppo
agent_params:
  model_path: models/ppo_hillside_1M.pt
max_frames: 3600
success:
  type: goal_reached
```

---

## 9. Implementation Order

Each step produces something testable before moving to the next.

### Step 1: Simulation Module

**File**: `speednik/simulation.py`

Extract the gameplay update loop from `main.py:_update_gameplay()` into a pure-Python function. This is the critical foundation — everything else builds on it.

**Test**: Run 600 frames of `hold_right` through the new simulation with Hillside loaded. Assert the player reaches x > 500. Compare trajectory to existing `tests/harness.py` output for the player-only case to verify physics match. This validates that the simulation produces identical results to the existing harness for the player+terrain subset.

**Deliverable**: `speednik/simulation.py` with `create_sim()`, `sim_step()`, and a smoke test.

### Step 2: Agent Interface + Programmed Agents

**Files**: `speednik/agents/base.py`, `speednik/agents/hold_right.py`, `speednik/agents/spindash.py`, `speednik/agents/scripted.py`

Define the `Agent` protocol. Port the existing harness strategies (`hold_right`, `spindash_right`, `scripted`) to observation-based agents. The observation extraction function (`extract_observation`) lives in `speednik/env.py` but can be developed here since the sim exists.

**Test**: Run each programmed agent through the simulation for 300 frames. Assert basic sanity (hold_right moves right, spindash reaches higher speed, scripted follows its timeline).

**Deliverable**: Working agents that drive the simulation through the same interface an RL agent will use.

### Step 3: Gymnasium Wrapper

**File**: `speednik/env.py`, `speednik/env_registration.py`

Implement `SpeednikEnv` with `reset()`, `step()`, `_get_obs()`, `_compute_reward()`. Register the three stage environments.

**Test**: Run the standard Gymnasium env checker:
```python
from gymnasium.utils.env_checker import check_env
env = SpeednikEnv(stage="hillside")
check_env(env)
```

Also run a manual loop for 100 steps with random actions and verify observations are in the correct range, rewards are reasonable, and termination works.

**Deliverable**: A valid Gymnasium environment that passes `check_env`.

### Step 4: Scenario Definition + Runner

**Files**: `speednik/scenarios/runner.py`, `speednik/scenarios/loader.py`, `speednik/scenarios/conditions.py`, `scenarios/*.yaml`

Implement the YAML scenario loader, condition checker, metrics computation, and the `run_scenario()` function. Write 3-5 initial scenario definitions covering: stage completion, speed maintenance, gap crossing, idle survival.

**Test**: Run all scenarios via the CLI. Verify that `hold_right` on `hillside_complete` produces a consistent `max_x` across runs (deterministic simulation). Verify that `spindash` achieves higher `average_speed` than `hold_right`.

**Deliverable**: `uv run python -m speednik.scenarios.cli --all` prints pass/fail for each scenario.

### Step 5: Metrics + Comparison

**Files**: `speednik/scenarios/metrics.py`, `speednik/scenarios/compare.py`

Implement trajectory serialization, metrics computation, JSON output, and baseline comparison.

**Test**: Run all scenarios twice, save both results. Compare — should show 0% delta (deterministic). Intentionally modify an agent parameter and re-run to verify delta detection.

**Deliverable**: `--compare` flag works, regression detection is functional.

### Step 6: CleanRL Integration

**File**: `tools/ppo_speednik.py`

Fork CleanRL's `ppo.py`. Apply the two changes (import + default env_id). Add the wrapper stack.

**Test**: Run 10,000 timesteps (a very short training run). Verify no crashes, observations flow correctly, loss decreases, and the model checkpoint saves. This is a smoke test, not convergence.

**Deliverable**: Training runs end-to-end. `PPOAgent` loads the checkpoint and runs through a scenario.

### Step 7: Terrain Raycast for Observations

**File**: Extend `speednik/terrain.py` or add `speednik/observation.py`

Implement the directional raycast function used by `_get_obs()`. This uses the existing sensor casting infrastructure but with arbitrary directions rather than the fixed 6-sensor layout.

**Note**: This is listed after the Gym wrapper because the wrapper can ship with a simplified observation (position + velocity + progress, no raycasts) and still be functional. Raycasts are an optimization for richer observations.

**Test**: Cast rays in known terrain configurations and verify distances match expected values. Test edge cases: player at level boundary, player in mid-air, player on steep slope.

**Deliverable**: Full 26-dimensional observation vector is populated correctly.

---

## Appendix A: Relationship to Existing Test Infrastructure

The existing `tests/harness.py` is the spiritual predecessor of the simulation module. Key differences:

| Aspect | `tests/harness.py` | `speednik/simulation.py` |
|--------|--------------------|-----------------------|
| Scope | Player + terrain only | Full game state (objects, enemies, events) |
| Input | `Strategy` callable (frame, player → InputState) | `InputState` per step (caller decides) |
| Output | `ScenarioResult` with snapshots | Events list + mutated `SimState` |
| Agent model | Closure-based strategies | Protocol-based agents with observation input |
| Observations | Direct player access | Structured numpy vector |
| Dependencies | `player_update` + `tile_lookup` | All of `main.py:_update_gameplay`'s logic |

The harness remains useful for focused physics tests. The simulation module is for full-game scenarios and RL training.

## Appendix B: Observation Space Rationale

**Why structured state, not pixels?**

1. **Speed**: Structured obs extraction is O(1) per frame. Pixel rendering requires the full `renderer.py` pipeline and a framebuffer.
2. **Interpretability**: You can read the observation vector and understand what the agent "sees." This is critical for debugging programmed agents and understanding RL behavior.
3. **Sample efficiency**: RL on structured state converges orders of magnitude faster than pixel-based training. CartPole-style PPO solves in ~50K steps; Atari PPO needs ~10M+.
4. **Headless compatibility**: Pixels would require Pyxel rendering, defeating the headless architecture.

**Why flat Box instead of Dict?**

CleanRL's `ppo.py` expects `observation_space.shape` to be a simple tuple. `Dict` spaces require `FlattenObservation` wrapper. A flat Box is simpler, equally expressive for MLP-based policies, and works with zero modifications to CleanRL.

## Appendix C: Action Space Rationale

**Why `Discrete(8)` with enumerated combos, not `MultiBinary(3)`?**

1. CleanRL's `ppo.py` uses `Categorical` distribution, which requires `Discrete` action space. `MultiBinary` would need `Bernoulli` distributions — a non-trivial fork.
2. `Discrete` prevents invalid combinations (left + right simultaneously).
3. The OpenAI Retro Sonic contest winners used the same approach: reduce 12 buttons to 7-8 meaningful combinations.
4. 8 actions is a small enough space that enumeration has no disadvantage over factored representations.

**Why include DOWN and DOWN+JUMP?**

The spindash is a core mechanic. An agent that cannot charge and release a spindash is missing the primary speed tool. `ACTION_DOWN` initiates spindash/roll, `ACTION_DOWN_JUMP` charges it.

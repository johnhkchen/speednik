"""speednik/scenarios/runner — Scenario execution engine (Layer 4).

Executes a ScenarioDef to completion, collecting trajectory and metrics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from speednik.agents.actions import action_to_input
from speednik.agents.registry import resolve_agent
from speednik.constants import MAX_X_SPEED
from speednik.observation import extract_observation
from speednik.scenarios.conditions import check_conditions
from speednik.scenarios.loader import ScenarioDef
from speednik.simulation import RingCollectedEvent, SimState, create_sim, sim_step


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class FrameRecord:
    """Per-frame snapshot of simulation state."""

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


@dataclass
class ScenarioOutcome:
    """Result of executing a scenario to completion."""

    name: str
    success: bool
    reason: str
    frames_elapsed: int
    metrics: dict[str, Any]
    trajectory: list[FrameRecord]
    wall_time_ms: float


# ---------------------------------------------------------------------------
# Reward (mirrors env.py _compute_reward)
# ---------------------------------------------------------------------------


def _compute_reward(
    sim: SimState,
    events: list,
    prev_max_x: float,
    step_count: int,
    max_steps: int,
) -> float:
    """Compute per-frame reward, same formula as SpeednikEnv._compute_reward."""
    reward = 0.0
    p = sim.player.physics

    # Progress delta
    progress_delta = (sim.max_x_reached - prev_max_x) / sim.level_width
    reward += progress_delta * 10.0

    # Speed bonus
    reward += abs(p.x_vel) / MAX_X_SPEED * 0.01

    # Goal bonus
    if sim.goal_reached:
        time_bonus = max(0.0, 1.0 - step_count / max_steps)
        reward += 10.0 + 5.0 * time_bonus

    # Death penalty
    if sim.player_dead:
        reward -= 5.0

    # Ring bonus
    for e in events:
        if isinstance(e, RingCollectedEvent):
            reward += 0.1

    # Time penalty
    reward -= 0.001

    return reward


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _metric_completion_time(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> int | None:
    return len(trajectory) if success else None


def _metric_max_x(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> float:
    if not trajectory:
        return 0.0
    return max(r.x for r in trajectory)


def _metric_rings_collected(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> int:
    return sim.rings_collected


def _metric_death_count(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> int:
    return sim.deaths


def _metric_total_reward(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> float:
    return sum(r.reward for r in trajectory)


def _metric_average_speed(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> float:
    if not trajectory:
        return 0.0
    return sum(abs(r.x_vel) for r in trajectory) / len(trajectory)


def _metric_peak_speed(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> float:
    if not trajectory:
        return 0.0
    return max(abs(r.x_vel) for r in trajectory)


def _metric_time_on_ground(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> float:
    if not trajectory:
        return 0.0
    return sum(1 for r in trajectory if r.on_ground) / len(trajectory)


def _metric_stuck_at(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> float | None:
    if not trajectory:
        return None
    # Check last 120 frames for being stuck (spread < 2.0)
    window = min(120, len(trajectory))
    recent = trajectory[-window:]
    xs = [r.x for r in recent]
    spread = max(xs) - min(xs)
    if spread < 2.0:
        return recent[-1].x
    return None


def _metric_velocity_profile(
    trajectory: list[FrameRecord], sim: SimState, success: bool,
) -> list[float]:
    return [r.x_vel for r in trajectory]


_METRIC_DISPATCH: dict[str, Any] = {
    "completion_time": _metric_completion_time,
    "max_x": _metric_max_x,
    "rings_collected": _metric_rings_collected,
    "death_count": _metric_death_count,
    "total_reward": _metric_total_reward,
    "average_speed": _metric_average_speed,
    "peak_speed": _metric_peak_speed,
    "time_on_ground": _metric_time_on_ground,
    "stuck_at": _metric_stuck_at,
    "velocity_profile": _metric_velocity_profile,
}


def compute_metrics(
    requested: list[str],
    trajectory: list[FrameRecord],
    sim: SimState,
    success: bool,
) -> dict[str, Any]:
    """Compute the requested metrics from trajectory and sim state."""
    result: dict[str, Any] = {}
    for name in requested:
        func = _METRIC_DISPATCH.get(name)
        if func is None:
            raise ValueError(
                f"Unknown metric: {name!r}. "
                f"Valid metrics: {sorted(_METRIC_DISPATCH)}"
            )
        result[name] = func(trajectory, sim, success)
    return result


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_scenario(scenario_def: ScenarioDef) -> ScenarioOutcome:
    """Execute a single scenario to completion.

    Creates a simulation, resolves the agent, runs the frame loop with
    condition checking, and returns a ScenarioOutcome with trajectory
    and metrics.
    """
    sim = create_sim(scenario_def.stage)

    # Apply start override
    if scenario_def.start_override:
        sim.player.physics.x = scenario_def.start_override.x
        sim.player.physics.y = scenario_def.start_override.y

    # Resolve and reset agent
    agent = resolve_agent(scenario_def.agent, scenario_def.agent_params)
    agent.reset()

    trajectory: list[FrameRecord] = []
    prev_jump_held = False
    prev_max_x = sim.player.physics.x
    sim.max_x_reached = sim.player.physics.x
    success: bool | None = None
    reason: str | None = None

    start_time = time.perf_counter()

    for frame in range(scenario_def.max_frames):
        obs = extract_observation(sim)
        action = agent.act(obs)
        inp, prev_jump_held = action_to_input(action, prev_jump_held)

        prev_max_x = sim.max_x_reached
        events = sim_step(sim, inp)
        reward = _compute_reward(
            sim, events, prev_max_x, frame + 1, scenario_def.max_frames,
        )

        trajectory.append(
            FrameRecord(
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
                events=[type(e).__name__ for e in events],
            )
        )

        success, reason = check_conditions(
            scenario_def.success,
            scenario_def.failure,
            sim,
            trajectory,
            frame,
            scenario_def.max_frames,
        )
        if success is not None:
            break

    wall_time = (time.perf_counter() - start_time) * 1000
    metrics = compute_metrics(
        scenario_def.metrics, trajectory, sim, success is True,
    )

    return ScenarioOutcome(
        name=scenario_def.name,
        success=success if success is not None else False,
        reason=reason or "timed_out",
        frames_elapsed=len(trajectory),
        metrics=metrics,
        trajectory=trajectory,
        wall_time_ms=wall_time,
    )

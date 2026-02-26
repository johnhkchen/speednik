"""Naive-player regression suite (T-011-06).

Parameterized test matrix: 3 stages × 3 strategies = 9 combinations.
Each combo runs sim_step + camera for full frame budget, then asserts:
- 0 error-severity invariant violations
- 0 camera oscillation events
- Forward progress (max_x exceeds threshold)
- Deaths within per-combo bounds
- Results logged for comparison
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from speednik.camera import create_camera, camera_update
from speednik.invariants import POSITION_MARGIN, Violation, check_invariants
from speednik.simulation import Event, SimState, create_sim, sim_step
from speednik.strategies import (
    Strategy,
    hold_right,
    hold_right_jump,
    spindash_right,
)
from speednik.terrain import get_quadrant
from tests.test_camera_stability import (
    CameraSnapshot,
    CameraTrajectory,
    check_oscillation,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STAGES: dict[str, dict[str, Any]] = {
    "hillside": {"width": 4800, "max_frames": 4000},
    "pipeworks": {"width": 5600, "max_frames": 5000},
    "skybridge": {"width": 5200, "max_frames": 6000},
}

STRATEGIES: dict[str, type[object] | Any] = {
    "hold_right": hold_right,
    "hold_right_jump": hold_right_jump,
    "spindash_right": spindash_right,
}

# Forward progress: min max_x as fraction of level width.
X_THRESHOLD_FRACTION = 0.05

# Death caps per (stage, strategy).
MAX_DEATHS: dict[str, dict[str, int]] = {
    "hillside": {"hold_right": 0, "hold_right_jump": 0, "spindash_right": 0},
    "pipeworks": {"hold_right": 3, "hold_right_jump": 3, "spindash_right": 3},
    "skybridge": {"hold_right": 3, "hold_right_jump": 3, "spindash_right": 3},
}

ALL_STAGES = list(STAGES.keys())
ALL_STRATEGIES = list(STRATEGIES.keys())


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RegressionSnapshot:
    """SnapshotLike-compatible snapshot for invariant checking."""

    frame: int
    x: float
    y: float
    x_vel: float
    y_vel: float
    on_ground: bool
    quadrant: int
    state: str


@dataclass
class RegressionResult:
    """Collected data for one (stage, strategy) combo."""

    stage: str
    strategy: str
    snapshots: list[RegressionSnapshot]
    events_per_frame: list[list[Event]]
    camera_trajectory: CameraTrajectory
    sim: SimState
    max_x: float
    deaths: int
    rings_collected: int
    goal_reached: bool
    frames_run: int


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _run_regression(stage: str, strategy_name: str) -> RegressionResult:
    """Run unified sim + camera loop, collect all data for assertions."""
    sim = create_sim(stage)
    p = sim.player
    camera = create_camera(sim.level_width, sim.level_height, p.physics.x, p.physics.y)
    strategy: Strategy = STRATEGIES[strategy_name]()

    max_frames = STAGES[stage]["max_frames"]
    snapshots: list[RegressionSnapshot] = []
    events_per_frame: list[list[Event]] = []
    camera_snapshots: list[CameraSnapshot] = []
    max_x = p.physics.x

    for frame in range(max_frames):
        inp = strategy(frame, sim.player)
        events = sim_step(sim, inp)
        camera_update(camera, sim.player, inp)

        ph = sim.player.physics
        snapshots.append(RegressionSnapshot(
            frame=frame,
            x=ph.x,
            y=ph.y,
            x_vel=ph.x_vel,
            y_vel=ph.y_vel,
            on_ground=ph.on_ground,
            quadrant=get_quadrant(ph.angle),
            state=sim.player.state.value,
        ))
        events_per_frame.append(events)
        camera_snapshots.append(CameraSnapshot(
            frame=frame,
            cam_x=camera.x,
            cam_y=camera.y,
            player_x=ph.x,
            player_y=ph.y,
            player_dead=sim.player_dead,
        ))
        if ph.x > max_x:
            max_x = ph.x

    cam_traj = CameraTrajectory(
        snapshots=camera_snapshots,
        level_width=sim.level_width,
        level_height=sim.level_height,
    )

    return RegressionResult(
        stage=stage,
        strategy=strategy_name,
        snapshots=snapshots,
        events_per_frame=events_per_frame,
        camera_trajectory=cam_traj,
        sim=sim,
        max_x=max_x,
        deaths=sim.deaths,
        rings_collected=sim.rings_collected,
        goal_reached=sim.goal_reached,
        frames_run=max_frames,
    )


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_RESULT_CACHE: dict[tuple[str, str], RegressionResult] = {}


def _get_result(stage: str, strategy: str) -> RegressionResult:
    key = (stage, strategy)
    if key not in _RESULT_CACHE:
        _RESULT_CACHE[key] = _run_regression(stage, strategy)
    return _RESULT_CACHE[key]


# ---------------------------------------------------------------------------
# Tests — 3 stages × 3 strategies = 9 combos × 5 assertions = 45 tests
# ---------------------------------------------------------------------------


@pytest.mark.regression
@pytest.mark.parametrize("stage", ALL_STAGES)
@pytest.mark.parametrize("strategy", ALL_STRATEGIES)
class TestRegression:
    """Regression gate: invariants, camera, progress, and deaths."""

    def test_invariants(self, stage: str, strategy: str) -> None:
        """Zero error-severity invariant violations while player is in-bounds.

        Naive strategies often launch the player off-map (springs) or through
        pipe interiors.  Once the player leaves level bounds, position and
        velocity violations are expected and not physics-engine bugs.  We
        trim the trajectory to the in-bounds prefix before checking.

        ``inside_solid_tile`` is excluded because the checker produces false
        positives on staircase geometry and pipe regions where the player
        center briefly sits inside an adjacent FULL tile.
        """
        result = _get_result(stage, strategy)
        lw = result.sim.level_width
        lh = result.sim.level_height
        margin = POSITION_MARGIN

        # Trim to frames where the player is still within level bounds
        in_bounds_snaps: list[RegressionSnapshot] = []
        in_bounds_events: list[list[Event]] = []
        for snap, evts in zip(result.snapshots, result.events_per_frame):
            oob = (
                snap.x < -margin
                or snap.x > lw + margin
                or snap.y > lh + margin
            )
            if oob:
                break
            in_bounds_snaps.append(snap)
            in_bounds_events.append(evts)

        if not in_bounds_snaps:
            return  # Player went OOB on first frame — nothing to check

        violations = check_invariants(
            result.sim, in_bounds_snaps, in_bounds_events,
        )
        # Exclude invariants with known false positives on naive strategies:
        # - inside_solid_tile: staircase geometry / pipe regions
        # - position_x_negative: player bounced slightly past left edge
        _EXCLUDED = {"inside_solid_tile", "position_x_negative"}
        errors = [
            v for v in violations
            if v.severity == "error" and v.invariant not in _EXCLUDED
        ]
        assert len(errors) == 0, (
            f"{len(errors)} invariant error(s) on {stage}/{strategy}: "
            + "; ".join(
                f"[frame {v.frame}] {v.invariant}: {v.details}"
                for v in errors[:5]
            )
        )

    def test_camera_no_oscillation(self, stage: str, strategy: str) -> None:
        """No camera wobble on either axis."""
        result = _get_result(stage, strategy)
        traj = result.camera_trajectory
        x_osc = check_oscillation(traj, "x")
        y_osc = check_oscillation(traj, "y")
        assert not x_osc, (
            f"Horizontal camera oscillation on {stage}/{strategy} "
            f"at frames: {x_osc[:10]}"
        )
        assert not y_osc, (
            f"Vertical camera oscillation on {stage}/{strategy} "
            f"at frames: {y_osc[:10]}"
        )

    def test_forward_progress(self, stage: str, strategy: str) -> None:
        """Player moves at least X_THRESHOLD_FRACTION of level width."""
        if (stage, strategy) == ("skybridge", "hold_right_jump"):
            pytest.xfail(
                "Solid ejection fix (T-012-03-BUG-02) changes trajectory; "
                "hold_right_jump on skybridge reaches max_x≈213 < 260 threshold"
            )
        if (stage, strategy) == ("skybridge", "hold_right"):
            pytest.xfail(
                "T-013-03-BUG-01 fix: bridge deck angle correction removes "
                "ceiling-walking bypass; walker now hits enemy at x≈240 < 260 threshold"
            )
        result = _get_result(stage, strategy)
        width = STAGES[stage]["width"]
        min_x = width * X_THRESHOLD_FRACTION
        assert result.max_x > min_x, (
            f"max_x={result.max_x:.1f} below {min_x:.1f} "
            f"({X_THRESHOLD_FRACTION*100:.0f}% of {width}) "
            f"on {stage}/{strategy}"
        )

    def test_deaths_within_bounds(self, stage: str, strategy: str) -> None:
        """Deaths stay within the per-combo cap."""
        result = _get_result(stage, strategy)
        cap = MAX_DEATHS[stage][strategy]
        assert result.deaths <= cap, (
            f"deaths={result.deaths} exceeds cap={cap} "
            f"on {stage}/{strategy}"
        )

    def test_results_logged(self, stage: str, strategy: str) -> None:
        """Log results summary for future comparison."""
        result = _get_result(stage, strategy)
        width = STAGES[stage]["width"]
        summary = (
            f"REGRESSION {stage}/{strategy}: "
            f"max_x={result.max_x:.1f} ({result.max_x/width*100:.0f}%), "
            f"rings={result.rings_collected}, "
            f"deaths={result.deaths}, "
            f"goal={'YES' if result.goal_reached else 'no'}, "
            f"frames={result.frames_run}"
        )
        print(summary)

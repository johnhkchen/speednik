"""Stage walkthrough smoke tests (T-011-01).

Run 3 strategies across 3 stages via the scenario runner and assert forward
progress, goal reachability, ring collection, death bounds, and frame budget.

Observed behavior matrix (max_frames per stage: hillside=4000, pipeworks=5000,
skybridge=6000):

| Stage     | hold_right         | hold_right_jump      | spindash_right       |
|-----------|--------------------|----------------------|----------------------|
| hillside  | stuck ~617 (17%)   | stuck ~3436 (73%)    | GOAL frame 728       |
| pipeworks | stuck ~2826 (55%)  | stuck ~518 (9%)      | timed out, off-map   |
| skybridge | off-map (springs)  | stuck ~566 (13%)     | off-map (springs)    |

Only hillside+spindash_right reaches the goal. Other combos get stuck or fly
off-map via springs. Deaths are 0 across all combos (no lethal hazards hit).
"""

from __future__ import annotations

import pytest

from speednik.scenarios import (
    FailureCondition,
    ScenarioDef,
    SuccessCondition,
    run_scenario,
)
from speednik.scenarios.runner import ScenarioOutcome

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STAGES = {
    "hillside": {"width": 4800, "max_frames": 4000},
    "pipeworks": {"width": 5600, "max_frames": 5000},
    "skybridge": {"width": 5200, "max_frames": 6000},
}

STRATEGIES = {
    "hold_right": {"agent": "hold_right", "agent_params": None},
    "hold_right_jump": {"agent": "jump_runner", "agent_params": None},
    "spindash_right": {
        "agent": "spindash",
        "agent_params": {"charge_frames": 3, "redash_speed": 0.15},
    },
}

# Minimum max_x (within level bounds) for "forward progress" assertion.
# Expressed as fraction of level width. Combos that fly off-map are excluded
# from this check since their max_x exceeds the level trivially.
PROGRESS_MIN_FRACTION = 0.05

# Maximum deaths allowed per stage.
DEATH_CAPS = {"hillside": 0, "pipeworks": 3, "skybridge": 3}

# Combos known to reach the goal.
GOAL_REACHING_COMBOS: set[tuple[str, str]] = {
    ("hillside", "spindash_right"),
}

ALL_STAGES = list(STAGES.keys())
ALL_STRATEGIES = list(STRATEGIES.keys())

# ---------------------------------------------------------------------------
# Outcome cache — each combo is run once, shared across all test methods
# ---------------------------------------------------------------------------

_OUTCOME_CACHE: dict[tuple[str, str], ScenarioOutcome] = {}


def _make_scenario(stage: str, strategy: str) -> ScenarioDef:
    sdata = STAGES[stage]
    adata = STRATEGIES[strategy]
    return ScenarioDef(
        name=f"{stage}_{strategy}",
        description=f"walkthrough: {strategy} on {stage}",
        stage=stage,
        agent=adata["agent"],
        agent_params=adata["agent_params"],
        max_frames=sdata["max_frames"],
        success=SuccessCondition(type="goal_reached"),
        failure=FailureCondition(
            type="any",
            conditions=[
                FailureCondition(type="player_dead"),
                FailureCondition(type="stuck", tolerance=2.0, window=120),
            ],
        ),
        metrics=[
            "max_x",
            "stuck_at",
            "rings_collected",
            "death_count",
            "completion_time",
        ],
        start_override=None,
    )


def _get_outcome(stage: str, strategy: str) -> ScenarioOutcome:
    key = (stage, strategy)
    if key not in _OUTCOME_CACHE:
        _OUTCOME_CACHE[key] = run_scenario(_make_scenario(stage, strategy))
    return _OUTCOME_CACHE[key]


# ---------------------------------------------------------------------------
# Tests — parameterized across 3 stages × 3 strategies = 9 combos
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.parametrize("stage", ALL_STAGES)
@pytest.mark.parametrize("strategy", ALL_STRATEGIES)
class TestWalkthrough:
    """Stage walkthrough smoke tests: 9 parameterized (stage, strategy) combos."""

    def test_forward_progress(self, stage: str, strategy: str) -> None:
        """Player moves meaningfully from the start position."""
        outcome = _get_outcome(stage, strategy)
        width = STAGES[stage]["width"]
        min_x = width * PROGRESS_MIN_FRACTION
        assert outcome.metrics["max_x"] > min_x, (
            f"max_x={outcome.metrics['max_x']:.1f} below {min_x:.1f} "
            f"({PROGRESS_MIN_FRACTION*100:.0f}% of {width})"
        )

    def test_rings_collected(self, stage: str, strategy: str) -> None:
        """Every moving strategy collects at least one ring."""
        outcome = _get_outcome(stage, strategy)
        assert outcome.metrics["rings_collected"] > 0, (
            f"rings_collected=0 for {strategy} on {stage}"
        )

    def test_deaths_within_cap(self, stage: str, strategy: str) -> None:
        """Deaths stay within the per-stage cap."""
        outcome = _get_outcome(stage, strategy)
        cap = DEATH_CAPS[stage]
        assert outcome.metrics["death_count"] <= cap, (
            f"deaths={outcome.metrics['death_count']} exceeds cap={cap} "
            f"for {strategy} on {stage}"
        )

    def test_frame_budget(self, stage: str, strategy: str) -> None:
        """No strategy exceeds 6000 frames to reach the goal."""
        outcome = _get_outcome(stage, strategy)
        if not outcome.success:
            pytest.skip("did not reach goal")
        assert outcome.frames_elapsed <= 6000, (
            f"took {outcome.frames_elapsed} frames (budget=6000)"
        )

    def test_no_softlock_on_goal_combos(self, stage: str, strategy: str) -> None:
        """Goal-reaching combos must not report stuck_at."""
        if (stage, strategy) not in GOAL_REACHING_COMBOS:
            pytest.skip("not a goal-reaching combo")
        outcome = _get_outcome(stage, strategy)
        assert outcome.metrics["stuck_at"] is None, (
            f"stuck at x={outcome.metrics['stuck_at']}"
        )


# ---------------------------------------------------------------------------
# Targeted tests for spindash goal reachability
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestSpindashReachesGoal:
    """spindash_right must reach the goal on hillside (the only reachable stage).

    Pipeworks and skybridge are not reachable with the current spindash agent
    due to off-map spring launches and complex pipe navigation respectively.
    These are documented as known limitations.
    """

    def test_hillside(self) -> None:
        outcome = _get_outcome("hillside", "spindash_right")
        assert outcome.success is True
        assert outcome.reason == "goal_reached"

    def test_pipeworks_documented(self) -> None:
        """Spindash on pipeworks: times out, player goes off-map."""
        outcome = _get_outcome("pipeworks", "spindash_right")
        assert outcome.success is False
        assert outcome.reason in ("timed_out", "stuck")

    def test_skybridge_documented(self) -> None:
        """Spindash on skybridge: reaches goal after T-012-07 angle smoothing."""
        outcome = _get_outcome("skybridge", "spindash_right")
        assert outcome.success is True


# ---------------------------------------------------------------------------
# Hillside-specific: all strategies should complete with 0 deaths
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.parametrize("strategy", ALL_STRATEGIES)
class TestHillsideNoDeath:
    """Hillside is the easiest stage — 0 deaths for all strategies."""

    def test_zero_deaths(self, strategy: str) -> None:
        outcome = _get_outcome("hillside", strategy)
        assert outcome.metrics["death_count"] == 0, (
            f"deaths={outcome.metrics['death_count']} on hillside/{strategy}"
        )

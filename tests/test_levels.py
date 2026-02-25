"""tests/test_levels.py — Level softlock detection via robotic player strategies.

Runs automated strategies against real stage data and verifies that each level is
completable with its design-intended difficulty. Detects structural blockages where
all strategies fail at the same point.

No Pyxel imports. Uses the physics-only harness from tests/harness.py.
"""

from __future__ import annotations

import pytest

from speednik.level import StageData, load_stage

from tests.harness import (
    ScenarioResult,
    hold_left,
    hold_right,
    hold_right_jump,
    idle,
    run_on_stage,
    spindash_right,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_cached_stages: dict[str, StageData] = {}


def _get_stage(name: str) -> StageData:
    """Load a stage once and cache for reuse across tests."""
    if name not in _cached_stages:
        _cached_stages[name] = load_stage(name)
    return _cached_stages[name]


def get_goal_x(stage_name: str) -> float:
    """Extract the goal X coordinate from a stage's entity list."""
    stage = _get_stage(stage_name)
    goals = [e for e in stage.entities if e.get("type") == "goal"]
    assert goals, f"No goal entity found in stage {stage_name!r}"
    return float(goals[0]["x"])


def _stall_info(result: ScenarioResult) -> str:
    """Format stall info for assertion messages."""
    stuck = result.stuck_at()
    if stuck is not None:
        return f"stuck at x={stuck:.1f}"
    return f"final x={result.final.x:.1f}"


STRATEGIES = {
    "idle": idle,
    "hold_right": hold_right,
    "hold_right_jump": hold_right_jump,
    "spindash_right": spindash_right,
}


# ---------------------------------------------------------------------------
# TestHillside — beginner level, hold_right should suffice
# ---------------------------------------------------------------------------


class TestHillside:
    def test_hold_right_reaches_goal(self):
        """Hillside should be completable by just holding right."""
        result = run_on_stage("hillside", hold_right(), frames=3600)
        goal_x = get_goal_x("hillside")
        assert result.max_x >= goal_x, (
            f"hold_right {_stall_info(result)}, goal at x={goal_x}"
        )

    def test_spindash_reaches_goal(self):
        """Spindash should reach the goal (wall angle threshold exempts loops)."""
        result = run_on_stage("hillside", spindash_right(), frames=3600)
        goal_x = get_goal_x("hillside")
        assert result.max_x >= goal_x, (
            f"spindash_right {_stall_info(result)}, goal at x={goal_x}"
        )

    def test_no_structural_blockage(self):
        """At least one strategy should reach the hillside goal."""
        goal_x = get_goal_x("hillside")
        best_x = 0.0
        best_name = "none"
        for name, factory in STRATEGIES.items():
            result = run_on_stage("hillside", factory(), frames=3600)
            if result.max_x > best_x:
                best_x = result.max_x
                best_name = name
        assert best_x >= goal_x, (
            f"No strategy reached goal (x={goal_x}), "
            f"best was {best_name} at x={best_x:.1f}"
        )


# ---------------------------------------------------------------------------
# TestPipeworks — requires jumping to clear gaps
# ---------------------------------------------------------------------------


class TestPipeworks:
    def test_hold_right_does_not_reach_goal(self):
        """Stage 2 has gaps that require jumping — hold_right alone should fail."""
        result = run_on_stage("pipeworks", hold_right(), frames=3600)
        goal_x = get_goal_x("pipeworks")
        assert result.max_x < goal_x, (
            f"hold_right unexpectedly reached goal at x={goal_x} "
            f"(max_x={result.max_x:.1f}) — expected to be blocked by gaps"
        )

    @pytest.mark.xfail(
        reason="Physics-only harness: pipeworks requires springs/pipes to complete"
    )
    def test_hold_right_jump_reaches_goal(self):
        """Stage 2 should be completable with hold_right + jump."""
        result = run_on_stage("pipeworks", hold_right_jump(), frames=3600)
        goal_x = get_goal_x("pipeworks")
        assert result.max_x >= goal_x, (
            f"hold_right_jump {_stall_info(result)}, goal at x={goal_x}"
        )

    def test_no_structural_blockage(self):
        """At least one strategy should reach the pipeworks goal."""
        goal_x = get_goal_x("pipeworks")
        best_x = 0.0
        best_name = "none"
        for name, factory in STRATEGIES.items():
            result = run_on_stage("pipeworks", factory(), frames=3600)
            if result.max_x > best_x:
                best_x = result.max_x
                best_name = name
        assert best_x >= goal_x, (
            f"No strategy reached goal (x={goal_x}), "
            f"best was {best_name} at x={best_x:.1f}"
        )


# ---------------------------------------------------------------------------
# TestSkybridge — requires spindash / advanced techniques
# ---------------------------------------------------------------------------


class TestSkybridge:
    @pytest.mark.xfail(
        reason="Physics-only harness: skybridge requires springs to complete"
    )
    def test_spindash_reaches_boss_area(self):
        """Spindash should reach the boss area / goal region."""
        result = run_on_stage("skybridge", spindash_right(), frames=5400)
        goal_x = get_goal_x("skybridge")
        assert result.max_x >= goal_x, (
            f"spindash_right {_stall_info(result)}, goal at x={goal_x}"
        )

    def test_no_structural_blockage(self):
        """At least one strategy should reach the skybridge goal."""
        goal_x = get_goal_x("skybridge")
        best_x = 0.0
        best_name = "none"
        for name, factory in STRATEGIES.items():
            result = run_on_stage("skybridge", factory(), frames=5400)
            if result.max_x > best_x:
                best_x = result.max_x
                best_name = name
        assert best_x >= goal_x, (
            f"No strategy reached goal (x={goal_x}), "
            f"best was {best_name} at x={best_x:.1f}"
        )


# ---------------------------------------------------------------------------
# TestStallDetection — progress tracking
# ---------------------------------------------------------------------------


class TestStallDetection:
    def test_hillside_no_stall_longer_than_3_seconds(self):
        """Player should not be stuck at any X for more than 180 frames (3s)."""
        result = run_on_stage("hillside", hold_right_jump(), frames=3600)
        # Scan for any 180-frame window where position barely changes
        stall_x = result.stuck_at(tolerance=2.0, window=180)
        assert stall_x is None, (
            f"hold_right_jump stuck at x={stall_x:.1f} for 3+ seconds (180 frames)"
        )


# ---------------------------------------------------------------------------
# TestBoundaryEscape — detect player escaping level boundaries
# ---------------------------------------------------------------------------

_STAGE_NAMES = ["hillside", "pipeworks", "skybridge"]

_RIGHT_STRATEGIES = {
    "hold_right": hold_right,
    "hold_right_jump": hold_right_jump,
    "spindash_right": spindash_right,
}


class TestBoundaryEscape:
    """Boundary escape detection: player should stay within level bounds.

    These tests are expected to fail (xfail) because no kill plane or position
    clamping exists yet. They document the known defect and serve as the
    regression gate for the eventual fix.
    """

    @pytest.mark.xfail(
        reason="No kill plane or position clamping exists yet",
        strict=False,
    )
    def test_right_edge_escape(self):
        """No right-moving strategy should send the player past level_width."""
        for stage_name in _STAGE_NAMES:
            stage = _get_stage(stage_name)
            w = stage.level_width
            for name, factory in _RIGHT_STRATEGIES.items():
                result = run_on_stage(stage_name, factory(), frames=3600)
                for snap in result.snapshots:
                    assert snap.x <= w, (
                        f"{stage_name}/{name}: escaped right at frame {snap.frame}, "
                        f"x={snap.x:.1f}, level_width={w}"
                    )

    @pytest.mark.xfail(
        reason="No kill plane or position clamping exists yet",
        strict=False,
    )
    def test_left_edge_escape(self):
        """hold_left should not send the player past x=0."""
        for stage_name in _STAGE_NAMES:
            result = run_on_stage(stage_name, hold_left(), frames=3600)
            for snap in result.snapshots:
                assert snap.x >= 0, (
                    f"{stage_name}/hold_left: escaped left at frame {snap.frame}, "
                    f"x={snap.x:.1f}"
                )

    @pytest.mark.xfail(
        reason="No kill plane or position clamping exists yet",
        strict=False,
    )
    def test_bottom_edge_escape(self):
        """No strategy should send the player far below level_height."""
        for stage_name in _STAGE_NAMES:
            stage = _get_stage(stage_name)
            h = stage.level_height
            for name, factory in STRATEGIES.items():
                result = run_on_stage(stage_name, factory(), frames=3600)
                for snap in result.snapshots:
                    assert snap.y <= h + 64, (
                        f"{stage_name}/{name}: fell off bottom at frame {snap.frame}, "
                        f"y={snap.y:.1f}, level_height={h}"
                    )

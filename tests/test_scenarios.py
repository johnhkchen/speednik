"""Tests for speednik.scenarios — YAML format, loader, conditions, and runner."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from speednik.scenarios import (
    VALID_FAILURE_TYPES,
    VALID_SUCCESS_TYPES,
    FailureCondition,
    FrameRecord,
    ScenarioDef,
    ScenarioOutcome,
    StartOverride,
    SuccessCondition,
    check_conditions,
    load_scenario,
    load_scenarios,
    run_scenario,
)

SCENARIOS_DIR = Path("scenarios")


# ---------------------------------------------------------------------------
# Helper: write a temporary YAML scenario
# ---------------------------------------------------------------------------

def _write_yaml(tmp_path: Path, name: str, data: dict) -> Path:
    p = tmp_path / f"{name}.yaml"
    p.write_text(yaml.dump(data))
    return p


def _minimal_scenario(**overrides) -> dict:
    """Return a minimal valid scenario dict, with optional overrides."""
    base = {
        "name": "test_scenario",
        "description": "A test scenario",
        "stage": "hillside",
        "agent": "hold_right",
        "max_frames": 600,
        "success": {"type": "goal_reached"},
        "failure": {"type": "player_dead"},
        "metrics": ["max_x"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Round-trip: load a real scenario file
# ---------------------------------------------------------------------------

class TestLoadRealScenarios:
    def test_load_hillside_complete(self):
        s = load_scenario(SCENARIOS_DIR / "hillside_complete.yaml")
        assert isinstance(s, ScenarioDef)
        assert s.name == "hillside_complete"
        assert s.stage == "hillside"
        assert s.agent == "spindash"
        assert s.agent_params == {"charge_frames": 3, "redash_speed": 0.15}
        assert s.max_frames == 3600
        assert s.success.type == "goal_reached"
        assert s.failure.type == "player_dead"
        assert "completion_time" in s.metrics
        assert s.start_override is None

    def test_load_hillside_loop_compound_failure(self):
        s = load_scenario(SCENARIOS_DIR / "hillside_loop.yaml")
        assert s.failure.type == "any"
        assert s.failure.conditions is not None
        assert len(s.failure.conditions) == 2
        types = {c.type for c in s.failure.conditions}
        assert types == {"player_dead", "stuck"}
        stuck = [c for c in s.failure.conditions if c.type == "stuck"][0]
        assert stuck.tolerance == 2.0
        assert stuck.window == 120

    def test_load_hillside_loop_start_override(self):
        s = load_scenario(SCENARIOS_DIR / "hillside_loop.yaml")
        assert s.start_override is not None
        assert s.start_override.x == 1200.0
        assert s.start_override.y == 610.0

    def test_load_gap_jump_scripted_agent(self):
        s = load_scenario(SCENARIOS_DIR / "gap_jump.yaml")
        assert s.agent == "scripted"
        assert s.agent_params is not None
        assert "timeline" in s.agent_params

    def test_load_scenarios_run_all(self):
        scenarios = load_scenarios(run_all=True, base=SCENARIOS_DIR)
        assert len(scenarios) >= 5
        names = {s.name for s in scenarios}
        assert "hillside_complete" in names
        assert "gap_jump" in names

    def test_load_scenarios_explicit_paths(self):
        paths = [
            SCENARIOS_DIR / "hillside_complete.yaml",
            SCENARIOS_DIR / "pipeworks_jump.yaml",
        ]
        scenarios = load_scenarios(paths=paths)
        assert len(scenarios) == 2
        assert scenarios[0].name == "hillside_complete"
        assert scenarios[1].name == "pipeworks_jump"

    def test_all_yaml_files_parse(self):
        """Every YAML file in scenarios/ should parse without error."""
        for path in sorted(SCENARIOS_DIR.glob("*.yaml")):
            s = load_scenario(path)
            assert isinstance(s, ScenarioDef), f"Failed to parse {path.name}"


# ---------------------------------------------------------------------------
# Success condition types
# ---------------------------------------------------------------------------

class TestSuccessConditions:
    def test_goal_reached(self, tmp_path):
        data = _minimal_scenario(success={"type": "goal_reached"})
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.success.type == "goal_reached"
        assert s.success.value is None

    def test_position_x_gte(self, tmp_path):
        data = _minimal_scenario(success={"type": "position_x_gte", "value": 2400})
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.success.type == "position_x_gte"
        assert s.success.value == 2400

    def test_position_x_gte_with_min_speed(self, tmp_path):
        data = _minimal_scenario(
            success={"type": "position_x_gte", "value": 2400, "min_speed": 4.0}
        )
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.success.min_speed == 4.0

    def test_position_y_lte(self, tmp_path):
        data = _minimal_scenario(success={"type": "position_y_lte", "value": 100})
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.success.type == "position_y_lte"
        assert s.success.value == 100

    def test_alive_at_end(self, tmp_path):
        data = _minimal_scenario(success={"type": "alive_at_end"})
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.success.type == "alive_at_end"

    def test_rings_gte(self, tmp_path):
        data = _minimal_scenario(success={"type": "rings_gte", "value": 50})
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.success.type == "rings_gte"
        assert s.success.value == 50


# ---------------------------------------------------------------------------
# Failure condition types
# ---------------------------------------------------------------------------

class TestFailureConditions:
    def test_player_dead(self, tmp_path):
        data = _minimal_scenario(failure={"type": "player_dead"})
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.failure.type == "player_dead"

    def test_stuck(self, tmp_path):
        data = _minimal_scenario(
            failure={"type": "stuck", "tolerance": 1.5, "window": 60}
        )
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.failure.type == "stuck"
        assert s.failure.tolerance == 1.5
        assert s.failure.window == 60

    def test_any_compound(self, tmp_path):
        data = _minimal_scenario(
            failure={
                "type": "any",
                "conditions": [
                    {"type": "player_dead"},
                    {"type": "stuck", "tolerance": 2.0, "window": 30},
                ],
            }
        )
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.failure.type == "any"
        assert len(s.failure.conditions) == 2
        assert s.failure.conditions[0].type == "player_dead"
        assert s.failure.conditions[1].type == "stuck"
        assert s.failure.conditions[1].tolerance == 2.0


# ---------------------------------------------------------------------------
# Optional fields
# ---------------------------------------------------------------------------

class TestOptionalFields:
    def test_start_override_present(self, tmp_path):
        data = _minimal_scenario(start_override={"x": 800, "y": 300})
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.start_override is not None
        assert s.start_override.x == 800.0
        assert s.start_override.y == 300.0

    def test_start_override_absent(self, tmp_path):
        data = _minimal_scenario()
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.start_override is None

    def test_agent_params_present(self, tmp_path):
        data = _minimal_scenario(
            agent="spindash",
            agent_params={"charge_frames": 5, "redash_speed": 0.2},
        )
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.agent_params == {"charge_frames": 5, "redash_speed": 0.2}

    def test_agent_params_absent(self, tmp_path):
        data = _minimal_scenario()
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.agent_params is None

    def test_description_defaults_to_empty(self, tmp_path):
        data = _minimal_scenario()
        del data["description"]
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.description == ""

    def test_metrics_defaults_to_empty(self, tmp_path):
        data = _minimal_scenario()
        del data["metrics"]
        s = load_scenario(_write_yaml(tmp_path, "sc", data))
        assert s.metrics == []


# ---------------------------------------------------------------------------
# Validation / error cases
# ---------------------------------------------------------------------------

class TestValidation:
    def test_invalid_success_type(self, tmp_path):
        data = _minimal_scenario(success={"type": "nonexistent"})
        with pytest.raises(ValueError, match="Unknown success condition type"):
            load_scenario(_write_yaml(tmp_path, "sc", data))

    def test_invalid_failure_type(self, tmp_path):
        data = _minimal_scenario(failure={"type": "nonexistent"})
        with pytest.raises(ValueError, match="Unknown failure condition type"):
            load_scenario(_write_yaml(tmp_path, "sc", data))

    def test_missing_name(self, tmp_path):
        data = _minimal_scenario()
        del data["name"]
        with pytest.raises(KeyError):
            load_scenario(_write_yaml(tmp_path, "sc", data))

    def test_missing_stage(self, tmp_path):
        data = _minimal_scenario()
        del data["stage"]
        with pytest.raises(KeyError):
            load_scenario(_write_yaml(tmp_path, "sc", data))

    def test_missing_success(self, tmp_path):
        data = _minimal_scenario()
        del data["success"]
        with pytest.raises(KeyError):
            load_scenario(_write_yaml(tmp_path, "sc", data))

    def test_invalid_nested_failure_type(self, tmp_path):
        data = _minimal_scenario(
            failure={
                "type": "any",
                "conditions": [{"type": "bogus"}],
            }
        )
        with pytest.raises(ValueError, match="Unknown failure condition type"):
            load_scenario(_write_yaml(tmp_path, "sc", data))


# ---------------------------------------------------------------------------
# Constant sets
# ---------------------------------------------------------------------------

class TestConstants:
    def test_success_types_complete(self):
        expected = {"goal_reached", "position_x_gte", "position_y_lte",
                    "alive_at_end", "rings_gte"}
        assert VALID_SUCCESS_TYPES == expected

    def test_failure_types_complete(self):
        expected = {"player_dead", "stuck", "any"}
        assert VALID_FAILURE_TYPES == expected


# ---------------------------------------------------------------------------
# No Pyxel imports
# ---------------------------------------------------------------------------

class TestNoPyxelImports:
    def test_scenarios_package_no_pyxel(self):
        import speednik.scenarios.conditions as cond_mod
        import speednik.scenarios.loader as loader_mod
        import speednik.scenarios.runner as runner_mod

        for mod in [cond_mod, loader_mod, runner_mod]:
            source = Path(mod.__file__).read_text()
            assert "import pyxel" not in source
            assert "from pyxel" not in source


# ---------------------------------------------------------------------------
# check_conditions: unit tests using real SimState
# ---------------------------------------------------------------------------


def _make_sim():
    """Create a hillside SimState for condition testing."""
    from speednik.simulation import create_sim

    return create_sim("hillside")


@dataclass
class _FakeRecord:
    """Minimal stand-in for FrameRecord with just an x attribute."""

    x: float


class TestCheckConditions:
    """Unit tests for each condition type."""

    def test_success_goal_reached_fires(self):
        sim = _make_sim()
        sim.goal_reached = True
        success = SuccessCondition(type="goal_reached")
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is True
        assert reason == "goal_reached"

    def test_success_goal_reached_not_yet(self):
        sim = _make_sim()
        success = SuccessCondition(type="goal_reached")
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is None
        assert reason is None

    def test_success_position_x_gte(self):
        sim = _make_sim()
        sim.player.physics.x = 2500.0
        success = SuccessCondition(type="position_x_gte", value=2400.0)
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is True
        assert reason == "position_x_gte"

    def test_success_position_x_gte_not_yet(self):
        sim = _make_sim()
        sim.player.physics.x = 100.0
        success = SuccessCondition(type="position_x_gte", value=2400.0)
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is None

    def test_success_position_x_gte_with_min_speed_pass(self):
        sim = _make_sim()
        sim.player.physics.x = 2500.0
        sim.player.physics.ground_speed = 5.0
        success = SuccessCondition(type="position_x_gte", value=2400.0, min_speed=4.0)
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is True

    def test_success_position_x_gte_with_min_speed_fail(self):
        sim = _make_sim()
        sim.player.physics.x = 2500.0
        sim.player.physics.ground_speed = 1.0
        success = SuccessCondition(type="position_x_gte", value=2400.0, min_speed=4.0)
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is None

    def test_success_position_y_lte(self):
        sim = _make_sim()
        sim.player.physics.y = 50.0
        success = SuccessCondition(type="position_y_lte", value=100.0)
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is True
        assert reason == "position_y_lte"

    def test_success_alive_at_end_fires(self):
        sim = _make_sim()
        success = SuccessCondition(type="alive_at_end")
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 599, 600)
        assert result is True
        assert reason == "alive_at_end"

    def test_success_alive_at_end_not_yet(self):
        sim = _make_sim()
        success = SuccessCondition(type="alive_at_end")
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 100, 600)
        assert result is None

    def test_success_rings_gte(self):
        sim = _make_sim()
        sim.rings_collected = 55
        success = SuccessCondition(type="rings_gte", value=50.0)
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is True
        assert reason == "rings_gte"

    def test_failure_player_dead(self):
        sim = _make_sim()
        sim.player_dead = True
        success = SuccessCondition(type="goal_reached")
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is False
        assert reason == "player_dead"

    def test_failure_player_dead_not_yet(self):
        sim = _make_sim()
        success = SuccessCondition(type="goal_reached")
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is None

    def test_failure_stuck(self):
        sim = _make_sim()
        # Build trajectory with same position for 30 frames
        trajectory = [_FakeRecord(x=100.0) for _ in range(30)]
        success = SuccessCondition(type="goal_reached")
        failure = FailureCondition(type="stuck", tolerance=2.0, window=30)
        result, reason = check_conditions(
            success, failure, sim, trajectory, 29, 600,
        )
        assert result is False
        assert reason == "stuck"

    def test_failure_stuck_not_enough_frames(self):
        sim = _make_sim()
        trajectory = [_FakeRecord(x=100.0) for _ in range(10)]
        success = SuccessCondition(type="goal_reached")
        failure = FailureCondition(type="stuck", tolerance=2.0, window=30)
        result, reason = check_conditions(
            success, failure, sim, trajectory, 9, 600,
        )
        assert result is None

    def test_failure_stuck_moving(self):
        sim = _make_sim()
        # Position varies enough to not be stuck
        trajectory = [_FakeRecord(x=100.0 + i * 0.5) for i in range(30)]
        success = SuccessCondition(type="goal_reached")
        failure = FailureCondition(type="stuck", tolerance=2.0, window=30)
        result, reason = check_conditions(
            success, failure, sim, trajectory, 29, 600,
        )
        assert result is None

    def test_failure_any_first_triggers(self):
        sim = _make_sim()
        sim.player_dead = True
        success = SuccessCondition(type="goal_reached")
        failure = FailureCondition(
            type="any",
            conditions=[
                FailureCondition(type="player_dead"),
                FailureCondition(type="stuck", tolerance=2.0, window=30),
            ],
        )
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is False
        assert reason == "player_dead"

    def test_failure_any_none_triggers(self):
        sim = _make_sim()
        success = SuccessCondition(type="goal_reached")
        failure = FailureCondition(
            type="any",
            conditions=[
                FailureCondition(type="player_dead"),
                FailureCondition(type="stuck", tolerance=2.0, window=30),
            ],
        )
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is None

    def test_success_takes_priority(self):
        """When both success and failure fire, success wins."""
        sim = _make_sim()
        sim.goal_reached = True
        sim.player_dead = True
        success = SuccessCondition(type="goal_reached")
        failure = FailureCondition(type="player_dead")
        result, reason = check_conditions(success, failure, sim, [], 0, 600)
        assert result is True
        assert reason == "goal_reached"


# ---------------------------------------------------------------------------
# FrameRecord / ScenarioOutcome dataclass sanity
# ---------------------------------------------------------------------------


class TestFrameRecord:
    def test_frame_record_fields(self):
        r = FrameRecord(
            frame=0,
            x=128.0,
            y=400.0,
            x_vel=1.5,
            y_vel=0.0,
            ground_speed=1.5,
            angle=0,
            on_ground=True,
            state="running",
            action=2,
            reward=0.01,
            rings=0,
            events=[],
        )
        assert r.frame == 0
        assert r.x == 128.0
        assert r.state == "running"
        assert r.events == []


class TestScenarioOutcome:
    def test_scenario_outcome_fields(self):
        o = ScenarioOutcome(
            name="test",
            success=True,
            reason="goal_reached",
            frames_elapsed=100,
            metrics={"max_x": 500.0},
            trajectory=[],
            wall_time_ms=10.5,
        )
        assert o.name == "test"
        assert o.success is True
        assert o.wall_time_ms == 10.5


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    def _make_trajectory(self, n=100):
        return [
            FrameRecord(
                frame=i,
                x=100.0 + i * 2.0,
                y=400.0,
                x_vel=2.0,
                y_vel=0.0,
                ground_speed=2.0,
                angle=0,
                on_ground=i % 3 != 0,
                state="running",
                action=2,
                reward=0.05,
                rings=i,
                events=[],
            )
            for i in range(n)
        ]

    def test_completion_time_success(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(50)
        sim = _make_sim()
        result = compute_metrics(["completion_time"], traj, sim, success=True)
        assert result["completion_time"] == 50

    def test_completion_time_failure(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(50)
        sim = _make_sim()
        result = compute_metrics(["completion_time"], traj, sim, success=False)
        assert result["completion_time"] is None

    def test_max_x(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(100)
        sim = _make_sim()
        result = compute_metrics(["max_x"], traj, sim, success=True)
        assert result["max_x"] == 100.0 + 99 * 2.0

    def test_rings_collected(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory()
        sim = _make_sim()
        sim.rings_collected = 42
        result = compute_metrics(["rings_collected"], traj, sim, success=True)
        assert result["rings_collected"] == 42

    def test_total_reward(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(10)
        sim = _make_sim()
        result = compute_metrics(["total_reward"], traj, sim, success=True)
        assert result["total_reward"] == pytest.approx(0.05 * 10)

    def test_average_speed(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(10)
        sim = _make_sim()
        result = compute_metrics(["average_speed"], traj, sim, success=True)
        assert result["average_speed"] == pytest.approx(2.0)

    def test_peak_speed(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(10)
        sim = _make_sim()
        result = compute_metrics(["peak_speed"], traj, sim, success=True)
        assert result["peak_speed"] == pytest.approx(2.0)

    def test_time_on_ground(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(9)
        sim = _make_sim()
        result = compute_metrics(["time_on_ground"], traj, sim, success=True)
        # Pattern: on_ground = (i % 3 != 0) -> off at 0,3,6 -> 6 on, 3 off
        expected = 6 / 9
        assert result["time_on_ground"] == pytest.approx(expected)

    def test_death_count(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(10)
        sim = _make_sim()
        sim.deaths = 3
        result = compute_metrics(["death_count"], traj, sim, success=True)
        assert result["death_count"] == 3

    def test_stuck_at_stuck(self):
        from speednik.scenarios.runner import compute_metrics

        # All frames at the same x position
        traj = [
            FrameRecord(
                frame=i, x=100.0, y=400.0, x_vel=0.0, y_vel=0.0,
                ground_speed=0.0, angle=0, on_ground=True, state="idle",
                action=0, reward=0.0, rings=0, events=[],
            )
            for i in range(120)
        ]
        sim = _make_sim()
        result = compute_metrics(["stuck_at"], traj, sim, success=False)
        assert result["stuck_at"] == 100.0

    def test_stuck_at_not_stuck(self):
        from speednik.scenarios.runner import compute_metrics

        # x increases enough to avoid stuck detection
        traj = [
            FrameRecord(
                frame=i, x=100.0 + i * 0.1, y=400.0, x_vel=0.1, y_vel=0.0,
                ground_speed=0.1, angle=0, on_ground=True, state="running",
                action=2, reward=0.0, rings=0, events=[],
            )
            for i in range(120)
        ]
        sim = _make_sim()
        result = compute_metrics(["stuck_at"], traj, sim, success=False)
        assert result["stuck_at"] is None

    def test_stuck_at_short_trajectory(self):
        from speednik.scenarios.runner import compute_metrics

        # Only 10 frames at constant x — window clamps to 10
        traj = [
            FrameRecord(
                frame=i, x=100.0, y=400.0, x_vel=0.0, y_vel=0.0,
                ground_speed=0.0, angle=0, on_ground=True, state="idle",
                action=0, reward=0.0, rings=0, events=[],
            )
            for i in range(10)
        ]
        sim = _make_sim()
        result = compute_metrics(["stuck_at"], traj, sim, success=False)
        assert result["stuck_at"] == 100.0

    def test_velocity_profile(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(5)
        sim = _make_sim()
        result = compute_metrics(["velocity_profile"], traj, sim, success=True)
        assert result["velocity_profile"] == [2.0, 2.0, 2.0, 2.0, 2.0]

    def test_unknown_metric_raises_valueerror(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(10)
        sim = _make_sim()
        with pytest.raises(ValueError, match="Unknown metric.*'nonexistent'"):
            compute_metrics(["nonexistent"], traj, sim, success=True)

    def test_empty_trajectory_metrics(self):
        from speednik.scenarios.runner import compute_metrics

        sim = _make_sim()
        result = compute_metrics(
            ["max_x", "average_speed", "peak_speed", "time_on_ground",
             "stuck_at", "velocity_profile", "total_reward"],
            [], sim, success=False,
        )
        assert result["max_x"] == 0.0
        assert result["average_speed"] == 0.0
        assert result["peak_speed"] == 0.0
        assert result["time_on_ground"] == 0.0
        assert result["stuck_at"] is None
        assert result["velocity_profile"] == []
        assert result["total_reward"] == 0.0

    def test_only_requested_metrics_computed(self):
        from speednik.scenarios.runner import compute_metrics

        traj = self._make_trajectory(10)
        sim = _make_sim()
        result = compute_metrics(["max_x"], traj, sim, success=True)
        assert list(result.keys()) == ["max_x"]


# ---------------------------------------------------------------------------
# run_scenario: integration tests
# ---------------------------------------------------------------------------


class TestRunScenario:
    def test_run_scenario_hold_right_hillside(self):
        sd = load_scenario(SCENARIOS_DIR / "hillside_hold_right.yaml")
        outcome = run_scenario(sd)
        assert isinstance(outcome, ScenarioOutcome)
        assert outcome.name == "hillside_hold_right"
        assert outcome.frames_elapsed > 0
        assert len(outcome.trajectory) == outcome.frames_elapsed
        assert outcome.reason in ("goal_reached", "player_dead", "timed_out")

    def test_run_scenario_start_override(self):
        sd = load_scenario(SCENARIOS_DIR / "hillside_loop.yaml")
        outcome = run_scenario(sd)
        # The first frame should be near the start_override position
        first = outcome.trajectory[0]
        assert first.x == pytest.approx(sd.start_override.x, abs=50)

    def test_run_scenario_wall_time_measured(self):
        sd = load_scenario(SCENARIOS_DIR / "hillside_hold_right.yaml")
        sd = ScenarioDef(
            name=sd.name,
            description=sd.description,
            stage=sd.stage,
            agent=sd.agent,
            agent_params=sd.agent_params,
            max_frames=60,
            success=sd.success,
            failure=sd.failure,
            metrics=sd.metrics,
            start_override=sd.start_override,
        )
        outcome = run_scenario(sd)
        assert outcome.wall_time_ms > 0.0

    def test_run_scenario_agent_resolved(self):
        """Spindash agent is resolved from YAML and runs correctly."""
        sd = load_scenario(SCENARIOS_DIR / "hillside_complete.yaml")
        sd = ScenarioDef(
            name=sd.name,
            description=sd.description,
            stage=sd.stage,
            agent=sd.agent,
            agent_params=sd.agent_params,
            max_frames=120,
            success=sd.success,
            failure=sd.failure,
            metrics=sd.metrics,
            start_override=sd.start_override,
        )
        outcome = run_scenario(sd)
        assert outcome.frames_elapsed == 120 or outcome.reason != "timed_out"

    def test_run_scenario_trajectory_has_frame_records(self):
        sd = load_scenario(SCENARIOS_DIR / "hillside_hold_right.yaml")
        sd = ScenarioDef(
            name=sd.name,
            description=sd.description,
            stage=sd.stage,
            agent=sd.agent,
            agent_params=sd.agent_params,
            max_frames=30,
            success=sd.success,
            failure=sd.failure,
            metrics=sd.metrics,
            start_override=sd.start_override,
        )
        outcome = run_scenario(sd)
        assert len(outcome.trajectory) > 0
        r = outcome.trajectory[0]
        assert isinstance(r, FrameRecord)
        assert r.frame == 0
        assert isinstance(r.state, str)
        assert isinstance(r.events, list)

    def test_run_scenario_metrics_computed(self):
        sd = load_scenario(SCENARIOS_DIR / "hillside_complete.yaml")
        sd = ScenarioDef(
            name=sd.name,
            description=sd.description,
            stage=sd.stage,
            agent=sd.agent,
            agent_params=sd.agent_params,
            max_frames=120,
            success=sd.success,
            failure=sd.failure,
            metrics=["max_x", "average_speed"],
            start_override=sd.start_override,
        )
        outcome = run_scenario(sd)
        assert "max_x" in outcome.metrics
        assert "average_speed" in outcome.metrics
        assert outcome.metrics["max_x"] > 0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_two_runs_identical_trajectory(self):
        """Same scenario run twice must produce identical trajectories."""
        sd = load_scenario(SCENARIOS_DIR / "hillside_hold_right.yaml")
        sd = ScenarioDef(
            name=sd.name,
            description=sd.description,
            stage=sd.stage,
            agent=sd.agent,
            agent_params=sd.agent_params,
            max_frames=300,
            success=sd.success,
            failure=sd.failure,
            metrics=sd.metrics,
            start_override=sd.start_override,
        )
        o1 = run_scenario(sd)
        o2 = run_scenario(sd)

        assert o1.frames_elapsed == o2.frames_elapsed
        assert o1.success == o2.success
        assert o1.reason == o2.reason
        assert len(o1.trajectory) == len(o2.trajectory)

        for i, (r1, r2) in enumerate(zip(o1.trajectory, o2.trajectory)):
            assert r1.frame == r2.frame, f"frame mismatch at {i}"
            assert r1.x == r2.x, f"x mismatch at frame {i}"
            assert r1.y == r2.y, f"y mismatch at frame {i}"
            assert r1.x_vel == r2.x_vel, f"x_vel mismatch at frame {i}"
            assert r1.y_vel == r2.y_vel, f"y_vel mismatch at frame {i}"
            assert r1.ground_speed == r2.ground_speed, f"ground_speed mismatch at {i}"
            assert r1.angle == r2.angle, f"angle mismatch at frame {i}"
            assert r1.on_ground == r2.on_ground, f"on_ground mismatch at frame {i}"
            assert r1.state == r2.state, f"state mismatch at frame {i}"
            assert r1.action == r2.action, f"action mismatch at frame {i}"
            assert r1.reward == r2.reward, f"reward mismatch at frame {i}"
            assert r1.rings == r2.rings, f"rings mismatch at frame {i}"
            assert r1.events == r2.events, f"events mismatch at frame {i}"


# ---------------------------------------------------------------------------
# hillside_complete.yaml runs without errors
# ---------------------------------------------------------------------------


class TestHillsideComplete:
    def test_hillside_complete_runs_without_errors(self):
        sd = load_scenario(SCENARIOS_DIR / "hillside_complete.yaml")
        outcome = run_scenario(sd)
        assert isinstance(outcome, ScenarioOutcome)
        assert outcome.frames_elapsed > 0
        assert outcome.wall_time_ms > 0


# ---------------------------------------------------------------------------
# CLI: output.py — print_outcome, save_results, compare_results
# ---------------------------------------------------------------------------


def _make_outcome(
    name: str = "test_scenario",
    success: bool = True,
    reason: str = "goal_reached",
    frames_elapsed: int = 100,
    metrics: dict | None = None,
    wall_time_ms: float = 42.3,
) -> ScenarioOutcome:
    """Create a minimal ScenarioOutcome for testing output functions."""
    return ScenarioOutcome(
        name=name,
        success=success,
        reason=reason,
        frames_elapsed=frames_elapsed,
        metrics=metrics or {"max_x": 1500.0},
        trajectory=[],
        wall_time_ms=wall_time_ms,
    )


class TestPrintOutcome:
    def test_print_pass(self, capsys):
        from speednik.scenarios.output import print_outcome

        outcome = _make_outcome(success=True)
        print_outcome(outcome)
        captured = capsys.readouterr().out
        assert "PASS" in captured
        assert "test_scenario" in captured

    def test_print_fail(self, capsys):
        from speednik.scenarios.output import print_outcome

        outcome = _make_outcome(success=False, reason="player_dead")
        print_outcome(outcome)
        captured = capsys.readouterr().out
        assert "FAIL" in captured
        assert "test_scenario" in captured

    def test_print_includes_metrics(self, capsys):
        from speednik.scenarios.output import print_outcome

        outcome = _make_outcome(metrics={"max_x": 2500.0})
        print_outcome(outcome)
        captured = capsys.readouterr().out
        assert "max_x=2500.0" in captured

    def test_print_includes_stuck_at(self, capsys):
        from speednik.scenarios.output import print_outcome

        outcome = _make_outcome(
            success=False,
            metrics={"max_x": 1200.0, "stuck_at": 1200.0},
        )
        print_outcome(outcome)
        captured = capsys.readouterr().out
        assert "stuck_at=1200.0" in captured

    def test_print_frames_and_wall_time(self, capsys):
        from speednik.scenarios.output import print_outcome

        outcome = _make_outcome(frames_elapsed=1847, wall_time_ms=42.3)
        print_outcome(outcome)
        captured = capsys.readouterr().out
        assert "1847 frames" in captured
        assert "42.3ms" in captured


class TestPrintSummary:
    def test_summary_all_pass(self, capsys):
        from speednik.scenarios.output import print_summary

        results = [_make_outcome(success=True) for _ in range(3)]
        print_summary(results)
        captured = capsys.readouterr().out
        assert "3 scenarios" in captured
        assert "3 passed" in captured
        assert "0 failed" in captured

    def test_summary_mixed(self, capsys):
        from speednik.scenarios.output import print_summary

        results = [
            _make_outcome(success=True),
            _make_outcome(success=False),
            _make_outcome(success=True),
        ]
        print_summary(results)
        captured = capsys.readouterr().out
        assert "3 scenarios" in captured
        assert "2 passed" in captured
        assert "1 failed" in captured


class TestSaveResults:
    def test_save_basic(self, tmp_path):
        import json

        from speednik.scenarios.output import save_results

        results = [_make_outcome(name="sc1"), _make_outcome(name="sc2")]
        out_path = tmp_path / "results.json"
        save_results(results, out_path)
        data = json.loads(out_path.read_text())
        assert len(data) == 2
        assert data[0]["name"] == "sc1"
        assert data[1]["name"] == "sc2"
        assert data[0]["success"] is True

    def test_save_without_trajectory(self, tmp_path):
        import json

        from speednik.scenarios.output import save_results

        results = [_make_outcome()]
        out_path = tmp_path / "results.json"
        save_results(results, out_path, include_trajectory=False)
        data = json.loads(out_path.read_text())
        assert "trajectory" not in data[0]

    def test_save_with_trajectory(self, tmp_path):
        import json

        from speednik.scenarios.output import save_results

        outcome = _make_outcome()
        outcome.trajectory = [
            FrameRecord(
                frame=0, x=100.0, y=400.0, x_vel=1.0, y_vel=0.0,
                ground_speed=1.0, angle=0, on_ground=True, state="running",
                action=2, reward=0.01, rings=0, events=[],
            )
        ]
        save_results([outcome], tmp_path / "results.json", include_trajectory=True)
        data = json.loads((tmp_path / "results.json").read_text())
        assert "trajectory" in data[0]
        assert len(data[0]["trajectory"]) == 1
        assert data[0]["trajectory"][0]["x"] == 100.0

    def test_save_creates_parent_dirs(self, tmp_path):
        from speednik.scenarios.output import save_results

        out_path = tmp_path / "nested" / "dir" / "results.json"
        save_results([_make_outcome()], out_path)
        assert out_path.exists()

    def test_save_metrics_serialized(self, tmp_path):
        import json

        from speednik.scenarios.output import save_results

        results = [_make_outcome(metrics={"max_x": 3200.5, "stuck_at": None})]
        out_path = tmp_path / "results.json"
        save_results(results, out_path)
        data = json.loads(out_path.read_text())
        assert data[0]["metrics"]["max_x"] == 3200.5
        assert data[0]["metrics"]["stuck_at"] is None


class TestMetricDirection:
    def test_all_dispatch_metrics_have_direction(self):
        from speednik.scenarios.compare import METRIC_DIRECTION
        from speednik.scenarios.runner import _METRIC_DISPATCH

        # Every non-profile metric should have a direction entry
        for key in _METRIC_DISPATCH:
            if key == "velocity_profile":
                continue
            assert key in METRIC_DIRECTION, f"{key} missing from METRIC_DIRECTION"

    def test_direction_values_valid(self):
        from speednik.scenarios.compare import METRIC_DIRECTION

        for key, val in METRIC_DIRECTION.items():
            assert val in ("higher", "lower", "neutral"), f"{key}: {val}"


class TestIsRegression:
    def test_higher_is_better_decrease_beyond_threshold(self):
        from speednik.scenarios.compare import is_regression

        # max_x is "higher" — a 10% decrease is a regression
        assert is_regression("max_x", 1000.0, 890.0) is True

    def test_higher_is_better_decrease_within_threshold(self):
        from speednik.scenarios.compare import is_regression

        # max_x drops 3% — within 5% threshold
        assert is_regression("max_x", 1000.0, 970.0) is False

    def test_higher_is_better_increase(self):
        from speednik.scenarios.compare import is_regression

        assert is_regression("max_x", 1000.0, 1100.0) is False

    def test_lower_is_better_increase_beyond_threshold(self):
        from speednik.scenarios.compare import is_regression

        # completion_time is "lower" — a 10% increase is a regression
        assert is_regression("completion_time", 1000, 1100) is True

    def test_lower_is_better_decrease(self):
        from speednik.scenarios.compare import is_regression

        assert is_regression("completion_time", 1000, 900) is False

    def test_lower_is_better_increase_within_threshold(self):
        from speednik.scenarios.compare import is_regression

        assert is_regression("completion_time", 1000, 1040) is False

    def test_neutral_metric_never_regresses(self):
        from speednik.scenarios.compare import is_regression

        assert is_regression("time_on_ground", 0.5, 0.1) is False
        assert is_regression("stuck_at", 100.0, 200.0) is False

    def test_unknown_metric_never_regresses(self):
        from speednik.scenarios.compare import is_regression

        assert is_regression("unknown_metric", 100.0, 0.0) is False

    def test_zero_old_val_no_crash(self):
        from speednik.scenarios.compare import is_regression

        assert is_regression("max_x", 0.0, 100.0) is False

    def test_custom_threshold(self):
        from speednik.scenarios.compare import is_regression

        # 8% decrease with 10% threshold → not a regression
        assert is_regression("max_x", 1000.0, 920.0, threshold=0.10) is False
        # 8% decrease with 5% threshold → regression
        assert is_regression("max_x", 1000.0, 920.0, threshold=0.05) is True


class TestCompareResults:
    def _write_baseline(self, tmp_path, data):
        import json
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps(data))
        return baseline_path

    def test_compare_prints_deltas(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "sc1", "success": True, "reason": "goal_reached",
             "metrics": {"max_x": 1000.0, "average_speed": 4.0}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)

        current = [_make_outcome(name="sc1", metrics={"max_x": 1100.0, "average_speed": 4.5})]
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "sc1:" in captured
        assert "max_x" in captured
        assert "average_speed" in captured
        assert "+" in captured
        assert exit_code == 0  # improvements, no regressions

    def test_compare_new_scenario(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline_path = self._write_baseline(tmp_path, [])
        current = [_make_outcome(name="sc1")]
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "NEW" in captured
        assert exit_code == 0

    def test_compare_missing_scenario(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "old_scenario", "success": True, "reason": "goal_reached",
             "metrics": {"max_x": 1000.0}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)
        current = []  # no scenarios in current run
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "MISSING" in captured
        assert exit_code == 0

    def test_status_flip_pass_to_fail_exit_1(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "sc1", "success": True, "reason": "goal_reached",
             "metrics": {"max_x": 1000.0}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)
        current = [_make_outcome(name="sc1", success=False, reason="player_dead",
                                 metrics={"max_x": 500.0})]
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "STATUS CHANGES" in captured
        assert "REGRESSION" in captured
        assert "PASS" in captured
        assert "FAIL" in captured
        assert exit_code == 1

    def test_status_flip_fail_to_pass(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "sc1", "success": False, "reason": "player_dead",
             "metrics": {"max_x": 500.0}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)
        current = [_make_outcome(name="sc1", success=True, reason="goal_reached",
                                 metrics={"max_x": 1000.0})]
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "fixed!" in captured
        assert exit_code == 0  # FAIL→PASS is not a regression

    def test_metric_regression_exit_2(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "sc1", "success": True, "reason": "goal_reached",
             "metrics": {"average_speed": 4.0}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)
        # average_speed dropped 20% — significant regression
        current = [_make_outcome(name="sc1", success=True, reason="goal_reached",
                                 metrics={"average_speed": 3.2})]
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "⚠" in captured
        assert "regression" in captured
        assert exit_code == 2

    def test_no_regression_exit_0(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "sc1", "success": True, "reason": "goal_reached",
             "metrics": {"max_x": 1000.0, "completion_time": 1847}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)
        # Same or better values
        current = [_make_outcome(name="sc1", success=True, reason="goal_reached",
                                 metrics={"max_x": 1050.0, "completion_time": 1800})]
        exit_code = compare_results(current, baseline_path)
        assert exit_code == 0

    def test_change_below_threshold_not_flagged(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "sc1", "success": True, "reason": "goal_reached",
             "metrics": {"average_speed": 4.0}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)
        # 2% decrease — within threshold, shown but not flagged
        current = [_make_outcome(name="sc1", metrics={"average_speed": 3.92})]
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "average_speed" in captured
        assert "⚠" not in captured
        assert exit_code == 0

    def test_none_metric_values(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "sc1", "success": False, "reason": "player_dead",
             "metrics": {"completion_time": None, "max_x": 500.0}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)
        current = [_make_outcome(name="sc1", success=False, reason="player_dead",
                                 metrics={"completion_time": None, "max_x": 600.0})]
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "None" in captured
        assert exit_code == 0

    def test_improvement_annotation(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "sc1", "success": True, "reason": "goal_reached",
             "metrics": {"completion_time": 2000}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)
        # completion_time is lower-is-better; 20% decrease is good
        current = [_make_outcome(name="sc1", metrics={"completion_time": 1600})]
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "✓" in captured
        assert "faster" in captured
        assert exit_code == 0

    def test_list_metrics_skipped(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "sc1", "success": True, "reason": "goal_reached",
             "metrics": {"velocity_profile": [1.0, 2.0], "max_x": 1000.0}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)
        current = [_make_outcome(name="sc1", metrics={"velocity_profile": [1.5, 2.5], "max_x": 1000.0})]
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "velocity_profile" not in captured
        assert "max_x" in captured

    def test_multiple_scenarios_mixed(self, tmp_path, capsys):
        from speednik.scenarios.compare import compare_results

        baseline = [
            {"name": "sc1", "success": True, "reason": "goal_reached",
             "metrics": {"max_x": 1000.0}},
            {"name": "sc2", "success": True, "reason": "goal_reached",
             "metrics": {"average_speed": 5.0}},
        ]
        baseline_path = self._write_baseline(tmp_path, baseline)
        current = [
            _make_outcome(name="sc1", metrics={"max_x": 1100.0}),
            _make_outcome(name="sc2", metrics={"average_speed": 4.0}),  # 20% regression
        ]
        exit_code = compare_results(current, baseline_path)
        captured = capsys.readouterr().out
        assert "sc1:" in captured
        assert "sc2:" in captured
        assert exit_code == 2  # metric regression in sc2


# ---------------------------------------------------------------------------
# Round-trip serialization
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_round_trip_basic(self, tmp_path):
        import json

        from speednik.scenarios.output import save_results

        outcomes = [
            _make_outcome(
                name="sc1", success=True, reason="goal_reached",
                frames_elapsed=1847, wall_time_ms=42.3,
                metrics={"max_x": 3200.5, "completion_time": 1847, "average_speed": 4.2},
            ),
            _make_outcome(
                name="sc2", success=False, reason="player_dead",
                frames_elapsed=500, wall_time_ms=12.1,
                metrics={"max_x": 800.0, "completion_time": None},
            ),
        ]
        out_path = tmp_path / "results.json"
        save_results(outcomes, out_path)
        data = json.loads(out_path.read_text())

        assert len(data) == 2
        d1, d2 = data[0], data[1]

        assert d1["name"] == "sc1"
        assert d1["success"] is True
        assert d1["reason"] == "goal_reached"
        assert d1["frames_elapsed"] == 1847
        assert d1["wall_time_ms"] == pytest.approx(42.3)
        assert d1["metrics"]["max_x"] == pytest.approx(3200.5)
        assert d1["metrics"]["completion_time"] == 1847
        assert d1["metrics"]["average_speed"] == pytest.approx(4.2)

        assert d2["name"] == "sc2"
        assert d2["success"] is False
        assert d2["reason"] == "player_dead"
        assert d2["metrics"]["completion_time"] is None

    def test_round_trip_with_trajectory(self, tmp_path):
        import json

        from speednik.scenarios.output import save_results

        outcome = _make_outcome()
        outcome.trajectory = [
            FrameRecord(
                frame=0, x=128.0, y=400.0, x_vel=1.5, y_vel=-0.5,
                ground_speed=1.5, angle=32, on_ground=True, state="running",
                action=2, reward=0.05, rings=3, events=["RingCollectedEvent"],
            ),
            FrameRecord(
                frame=1, x=129.5, y=399.5, x_vel=1.6, y_vel=-0.3,
                ground_speed=1.6, angle=32, on_ground=True, state="running",
                action=2, reward=0.04, rings=3, events=[],
            ),
        ]
        out_path = tmp_path / "results.json"
        save_results([outcome], out_path, include_trajectory=True)
        data = json.loads(out_path.read_text())

        traj = data[0]["trajectory"]
        assert len(traj) == 2
        r0 = traj[0]
        assert r0["frame"] == 0
        assert r0["x"] == pytest.approx(128.0)
        assert r0["y"] == pytest.approx(400.0)
        assert r0["x_vel"] == pytest.approx(1.5)
        assert r0["y_vel"] == pytest.approx(-0.5)
        assert r0["ground_speed"] == pytest.approx(1.5)
        assert r0["angle"] == 32
        assert r0["on_ground"] is True
        assert r0["state"] == "running"
        assert r0["action"] == 2
        assert r0["reward"] == pytest.approx(0.05)
        assert r0["rings"] == 3
        assert r0["events"] == ["RingCollectedEvent"]

    def test_round_trip_null_metrics(self, tmp_path):
        import json

        from speednik.scenarios.output import save_results

        outcome = _make_outcome(
            metrics={"completion_time": None, "stuck_at": None, "max_x": 500.0},
        )
        out_path = tmp_path / "results.json"
        save_results([outcome], out_path)
        data = json.loads(out_path.read_text())
        m = data[0]["metrics"]
        assert m["completion_time"] is None
        assert m["stuck_at"] is None
        assert m["max_x"] == pytest.approx(500.0)


# ---------------------------------------------------------------------------
# CLI: cli.py — main() integration tests
# ---------------------------------------------------------------------------


class TestCliMain:
    def test_cli_no_args_exit_2(self):
        from speednik.scenarios.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 2

    def test_cli_help(self):
        from speednik.scenarios.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_cli_run_single_scenario(self):
        from speednik.scenarios.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["scenarios/gap_jump.yaml"])
        # gap_jump is a short scripted scenario — may pass or fail
        assert exc_info.value.code in (0, 1)

    def test_cli_all_flag(self, capsys):
        from speednik.scenarios.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--all"])
        assert exc_info.value.code in (0, 1)
        captured = capsys.readouterr().out
        assert "scenarios:" in captured  # summary line

    def test_cli_agent_override(self, capsys):
        from speednik.scenarios.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["scenarios/gap_jump.yaml", "--agent", "hold_right"])
        assert exc_info.value.code in (0, 1)

    def test_cli_output_json(self, tmp_path):
        import json

        from speednik.scenarios.cli import main

        out_path = tmp_path / "results.json"
        with pytest.raises(SystemExit):
            main(["scenarios/gap_jump.yaml", "-o", str(out_path)])
        assert out_path.exists()
        data = json.loads(out_path.read_text())
        assert len(data) == 1
        assert data[0]["name"] == "gap_jump"

    def test_cli_trajectory_flag(self, tmp_path):
        import json

        from speednik.scenarios.cli import main

        out_path = tmp_path / "results.json"
        with pytest.raises(SystemExit):
            main(["scenarios/gap_jump.yaml", "-o", str(out_path), "--trajectory"])
        data = json.loads(out_path.read_text())
        assert "trajectory" in data[0]
        assert len(data[0]["trajectory"]) > 0


# ---------------------------------------------------------------------------
# CLI: No Pyxel imports in new modules
# ---------------------------------------------------------------------------


class TestCliNoPyxel:
    def test_cli_modules_no_pyxel(self):
        import speednik.scenarios.cli as cli_mod
        import speednik.scenarios.compare as compare_mod
        import speednik.scenarios.output as output_mod

        for mod in [cli_mod, output_mod, compare_mod]:
            source = Path(mod.__file__).read_text()
            assert "import pyxel" not in source
            assert "from pyxel" not in source

    def test_main_entry_no_pyxel(self):
        main_path = Path("speednik/scenarios/__main__.py")
        source = main_path.read_text()
        assert "import pyxel" not in source
        assert "from pyxel" not in source

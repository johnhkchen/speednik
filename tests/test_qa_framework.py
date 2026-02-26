"""tests/test_qa_framework.py — Unit tests for the QA audit framework.

Tests archetypes, expectation framework, and format_findings using
synthetic grids only. No real stage tests (those belong in T-012-02+).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from speednik.grids import build_flat, build_gap
from speednik.physics import InputState
from speednik.simulation import SimState, create_sim_from_lookup, sim_step
from speednik.terrain import TILE_SIZE

from speednik.qa import (
    AuditFinding,
    AuditResult,
    Archetype,
    BehaviorExpectation,
    _build_findings,
    _capture_snapshot,
    format_findings,
    make_cautious,
    make_chaos,
    make_jumper,
    make_speed_demon,
    make_walker,
    make_wall_hugger,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GROUND_ROW = 30


def _make_flat_sim(width_tiles: int = 60) -> SimState:
    """Create a sim on flat ground. Player starts on surface."""
    _, lookup = build_flat(width_tiles, GROUND_ROW)
    start_y = float(GROUND_ROW * TILE_SIZE - 20)  # feet on surface
    return create_sim_from_lookup(lookup, 32.0, start_y, level_width=width_tiles * TILE_SIZE)


def _make_gap_sim(
    approach: int = 20, gap: int = 3, landing: int = 20,
) -> SimState:
    """Create a sim with a gap in the ground."""
    _, lookup = build_gap(approach, gap, landing, GROUND_ROW)
    total_width = (approach + gap + landing) * TILE_SIZE
    start_y = float(GROUND_ROW * TILE_SIZE - 20)
    return create_sim_from_lookup(lookup, 32.0, start_y, level_width=total_width)


def _run_archetype_on_flat(
    archetype: Archetype,
    frames: int = 300,
    width_tiles: int = 60,
) -> tuple[SimState, list]:
    """Run an archetype on flat ground and return (final_sim, snapshots)."""
    sim = _make_flat_sim(width_tiles)
    snapshots = []
    for frame in range(frames):
        if sim.player_dead:
            break
        inp = archetype(frame, sim)
        sim_step(sim, inp)
        snapshots.append(_capture_snapshot(sim, frame + 1))
    return sim, snapshots


# ---------------------------------------------------------------------------
# Archetype tests
# ---------------------------------------------------------------------------

class TestArchetypes:
    def test_walker_moves_right_on_flat(self):
        """Walker should move rightward on flat ground."""
        sim, snaps = _run_archetype_on_flat(make_walker(), frames=120)
        assert sim.player.physics.x > 100.0, "Walker should move right"
        assert sim.player.physics.on_ground, "Walker should stay on ground"

    def test_jumper_leaves_ground_on_flat(self):
        """Jumper should become airborne at some point."""
        sim, snaps = _run_archetype_on_flat(make_jumper(), frames=120)
        was_airborne = any(not s.on_ground for s in snaps)
        assert was_airborne, "Jumper should leave the ground"
        assert sim.player.physics.x > 100.0, "Jumper should also move right"

    def test_speed_demon_reaches_high_speed(self):
        """Speed demon should reach a higher peak speed than walker."""
        _, snaps_demon = _run_archetype_on_flat(
            make_speed_demon(), frames=300, width_tiles=100,
        )
        _, snaps_walker = _run_archetype_on_flat(make_walker(), frames=300, width_tiles=100)
        peak_demon = max(abs(s.ground_speed) for s in snaps_demon)
        peak_walker = max(abs(s.ground_speed) for s in snaps_walker)
        assert peak_demon > peak_walker, (
            f"Speed demon peak={peak_demon:.1f} should exceed "
            f"walker peak={peak_walker:.1f}"
        )

    def test_cautious_moves_slower_than_walker(self):
        """Cautious should move right but slower than walker."""
        sim_cautious, _ = _run_archetype_on_flat(make_cautious(), frames=300)
        sim_walker, _ = _run_archetype_on_flat(make_walker(), frames=300)
        assert sim_cautious.player.physics.x > 32.0, "Cautious should move right"
        assert sim_cautious.max_x_reached < sim_walker.max_x_reached, (
            "Cautious should be slower than walker"
        )

    def test_wall_hugger_jumps_at_wall(self):
        """Wall hugger on flat ground: should move right. On a wall it would jump."""
        sim, snaps = _run_archetype_on_flat(make_wall_hugger(), frames=120)
        assert sim.player.physics.x > 100.0, "Wall hugger should move right on flat ground"

    def test_chaos_deterministic(self):
        """Same seed should produce identical trajectories."""
        sim1, snaps1 = _run_archetype_on_flat(make_chaos(42), frames=200)
        sim2, snaps2 = _run_archetype_on_flat(make_chaos(42), frames=200)
        assert len(snaps1) == len(snaps2)
        for s1, s2 in zip(snaps1, snaps2):
            assert s1.x == s2.x, f"Frame {s1.frame}: x mismatch {s1.x} != {s2.x}"
            assert s1.y == s2.y, f"Frame {s1.frame}: y mismatch {s1.y} != {s2.y}"

    def test_chaos_different_seeds_differ(self):
        """Different seeds should produce different trajectories."""
        _, snaps1 = _run_archetype_on_flat(make_chaos(42), frames=200)
        _, snaps2 = _run_archetype_on_flat(make_chaos(99), frames=200)
        xs1 = [s.x for s in snaps1]
        xs2 = [s.x for s in snaps2]
        assert xs1 != xs2, "Different seeds should diverge"

    def test_all_archetypes_return_valid_input(self):
        """Every archetype should return InputState on every frame."""
        sim = _make_flat_sim()
        archetypes = [
            make_walker(), make_jumper(), make_speed_demon(),
            make_cautious(), make_wall_hugger(), make_chaos(7),
        ]
        for arch in archetypes:
            for frame in range(10):
                result = arch(frame, sim)
                assert isinstance(result, InputState), (
                    f"Archetype returned {type(result)}, expected InputState"
                )


# ---------------------------------------------------------------------------
# Expectation framework tests
# ---------------------------------------------------------------------------

class TestExpectationFramework:
    def _clean_expectation(self, **overrides) -> BehaviorExpectation:
        defaults = dict(
            name="test",
            stage="synthetic",
            archetype="walker",
            min_x_progress=0.0,
            max_deaths=0,
            require_goal=False,
            max_frames=300,
            invariant_errors_ok=0,
        )
        defaults.update(overrides)
        return BehaviorExpectation(**defaults)

    def test_clean_flat_no_findings(self):
        """Walker on flat ground with lenient expectations → 0 findings."""
        sim, snaps = _run_archetype_on_flat(make_walker(), frames=120)
        from speednik.invariants import check_invariants
        violations = check_invariants(sim, snaps, [[] for _ in snaps])
        exp = self._clean_expectation(min_x_progress=0.0)
        findings = _build_findings(sim, snaps, violations, exp)
        bugs = [f for f in findings if f.severity == "bug"]
        assert len(bugs) == 0, format_findings(findings)

    def test_min_x_not_met_generates_finding(self):
        """If player doesn't reach min_x_progress, a bug finding is generated."""
        sim, snaps = _run_archetype_on_flat(make_walker(), frames=60)
        from speednik.invariants import check_invariants
        violations = check_invariants(sim, snaps, [[] for _ in snaps])
        # Set impossibly high x progress requirement
        exp = self._clean_expectation(min_x_progress=99999.0)
        findings = _build_findings(sim, snaps, violations, exp)
        bugs = [f for f in findings if f.severity == "bug"]
        assert any("min_x_progress" in f.expectation or "Reach at least" in f.expectation
                    for f in bugs), format_findings(findings)

    def test_death_exceeds_max_generates_finding(self):
        """If deaths exceed max_deaths, a bug finding is generated."""
        sim = _make_flat_sim()
        sim.deaths = 3
        snaps = [_capture_snapshot(sim, 0)]
        exp = self._clean_expectation(max_deaths=1)
        findings = _build_findings(sim, snaps, [], exp)
        bugs = [f for f in findings if f.severity == "bug"]
        assert any("deaths" in f.details.lower() for f in bugs), format_findings(findings)

    def test_goal_not_reached_generates_finding(self):
        """If goal is required but not reached, a bug finding is generated."""
        sim = _make_flat_sim()
        sim.goal_reached = False
        snaps = [_capture_snapshot(sim, 0)]
        exp = self._clean_expectation(require_goal=True)
        findings = _build_findings(sim, snaps, [], exp)
        bugs = [f for f in findings if f.severity == "bug"]
        assert any("goal" in f.details.lower() for f in bugs), format_findings(findings)

    def test_invariant_violation_becomes_finding(self):
        """Invariant violations should become findings."""
        from speednik.invariants import Violation
        sim = _make_flat_sim()
        snaps = [_capture_snapshot(sim, 0)]
        violations = [Violation(frame=0, invariant="test_inv", details="test detail", severity="error")]
        exp = self._clean_expectation(invariant_errors_ok=10)
        findings = _build_findings(sim, snaps, violations, exp)
        assert any(f.details == "test detail" for f in findings)

    def test_invariant_error_budget_exceeded(self):
        """Too many invariant errors should produce a budget-exceeded finding."""
        from speednik.invariants import Violation
        sim = _make_flat_sim()
        snaps = [_capture_snapshot(sim, 0)]
        violations = [
            Violation(frame=0, invariant="a", details="a", severity="error"),
            Violation(frame=0, invariant="b", details="b", severity="error"),
        ]
        exp = self._clean_expectation(invariant_errors_ok=0)
        findings = _build_findings(sim, snaps, violations, exp)
        bugs = [f for f in findings if f.severity == "bug"]
        assert any("budget" in f.details.lower() or "exceeds" in f.details.lower()
                    for f in bugs), format_findings(findings)

    def test_warnings_not_counted_as_errors(self):
        """Warning-severity violations should not count against invariant error budget."""
        from speednik.invariants import Violation
        sim = _make_flat_sim()
        snaps = [_capture_snapshot(sim, 0)]
        violations = [
            Violation(frame=0, invariant="w", details="warn", severity="warning"),
        ]
        exp = self._clean_expectation(invariant_errors_ok=0)
        findings = _build_findings(sim, snaps, violations, exp)
        bugs = [f for f in findings if f.severity == "bug"]
        # Warning should not trigger budget-exceeded bug
        assert not any("budget" in f.details.lower() or "exceeds" in f.details.lower()
                       for f in bugs)


# ---------------------------------------------------------------------------
# format_findings tests
# ---------------------------------------------------------------------------

class TestFormatFindings:
    def test_empty_findings(self):
        result = format_findings([])
        assert "0 bugs" in result

    def test_single_bug(self):
        f = AuditFinding(
            expectation="forward progress",
            actual="stuck at x=100",
            frame=50,
            x=100.0,
            y=300.0,
            severity="bug",
            details="Player stuck at x=100",
        )
        result = format_findings([f])
        assert "1 bugs" in result
        assert "frame 50" in result
        assert "x=100.0" in result
        assert "Expected: forward progress" in result
        assert "Actual: stuck at x=100" in result

    def test_multiple_findings(self):
        findings = [
            AuditFinding("a", "b", 10, 50.0, 60.0, "bug", "first"),
            AuditFinding("c", "d", 20, 70.0, 80.0, "warning", "second"),
            AuditFinding("e", "f", 30, 90.0, 100.0, "bug", "third"),
        ]
        result = format_findings(findings)
        assert "2 bugs" in result
        assert "first" in result
        assert "second" in result
        assert "third" in result

    def test_format_includes_all_fields(self):
        f = AuditFinding(
            expectation="my expectation",
            actual="my actual",
            frame=99,
            x=123.4,
            y=567.8,
            severity="bug",
            details="detailed description",
        )
        result = format_findings([f])
        assert "Expected: my expectation" in result
        assert "Actual: my actual" in result
        assert "detailed description" in result


# ---------------------------------------------------------------------------
# Audit respawn tests (T-013-03-BUG-02)
# ---------------------------------------------------------------------------

class TestAuditRespawn:
    """Tests for respawn-after-death behavior in run_audit()."""

    # Wide gap and low level_height ensure the walker falls far enough
    # for pit death to trigger within a reasonable number of frames.
    GAP_APPROACH = 20
    GAP_WIDTH = 30
    GAP_LANDING = 20
    GAP_LEVEL_HEIGHT_ROWS = GROUND_ROW + 3  # 3 tile rows below ground = short fall

    def _make_pit_sim(self):
        """Create a sim with a wide gap that causes pit death."""
        _, lookup = build_gap(
            self.GAP_APPROACH, self.GAP_WIDTH, self.GAP_LANDING, GROUND_ROW,
        )
        total_width = (self.GAP_APPROACH + self.GAP_WIDTH + self.GAP_LANDING) * TILE_SIZE
        level_height = self.GAP_LEVEL_HEIGHT_ROWS * TILE_SIZE
        start_y = float(GROUND_ROW * TILE_SIZE - 20)
        return create_sim_from_lookup(
            lookup, 32.0, start_y,
            level_width=total_width, level_height=level_height,
        )

    def test_respawn_after_pit_death(self):
        """Player should respawn after falling into a gap (within death budget)."""
        from speednik.player import PlayerState
        from speednik.qa import _respawn_player
        from speednik.simulation import DeathEvent

        sim = self._make_pit_sim()
        walker = make_walker()
        died = False

        for frame in range(600):
            if sim.player_dead:
                break
            inp = walker(frame, sim)
            events = sim_step(sim, inp)
            if any(isinstance(e, DeathEvent) for e in events):
                died = True
                assert sim.deaths == 1
                _respawn_player(sim)
                break

        assert died, "Player should have died falling into the gap"
        assert sim.player.state == PlayerState.STANDING
        assert sim.player.physics.x == sim.player.respawn_x
        assert sim.player.physics.y == sim.player.respawn_y
        assert sim.player.physics.on_ground is True
        assert sim.player.physics.x_vel == 0.0
        assert sim.player.physics.y_vel == 0.0

    def test_death_budget_exceeded_terminates(self):
        """When deaths exceed max_deaths, player_dead should be set."""
        from speednik.simulation import DeathEvent

        sim = self._make_pit_sim()
        walker = make_walker()

        for frame in range(600):
            if sim.player_dead:
                break
            inp = walker(frame, sim)
            events = sim_step(sim, inp)
            if any(isinstance(e, DeathEvent) for e in events):
                # max_deaths=0 means first death exceeds budget
                if sim.deaths > 0:
                    sim.player_dead = True

        assert sim.deaths >= 1, "Player should have died"
        assert sim.player_dead is True, "player_dead should be set when budget exceeded"

    def test_respawn_resets_player_state(self):
        """After respawn, player should be in clean STANDING state."""
        from speednik.player import PlayerState
        from speednik.qa import _respawn_player

        _, lookup = build_flat(20, GROUND_ROW)
        start_y = float(GROUND_ROW * TILE_SIZE - 20)
        sim = create_sim_from_lookup(lookup, 32.0, start_y)

        # Dirty the player state
        sim.player.state = PlayerState.DEAD
        sim.player.physics.x = 999.0
        sim.player.physics.y = 999.0
        sim.player.physics.x_vel = 5.0
        sim.player.physics.y_vel = 10.0
        sim.player.physics.ground_speed = 5.0
        sim.player.physics.on_ground = False
        sim.player.physics.is_rolling = True
        sim.player.rings = 50
        sim.player.invulnerability_timer = 100

        _respawn_player(sim)

        assert sim.player.state == PlayerState.STANDING
        assert sim.player.physics.x == 32.0  # respawn_x = start_x
        assert sim.player.physics.y == start_y  # respawn_y = start_y
        assert sim.player.physics.x_vel == 0.0
        assert sim.player.physics.y_vel == 0.0
        assert sim.player.physics.ground_speed == 0.0
        assert sim.player.physics.on_ground is True
        assert sim.player.physics.is_rolling is False
        assert sim.player.rings == 0  # respawn_rings defaults to 0
        assert sim.player.invulnerability_timer == 0

    def test_max_x_tracks_across_respawns(self):
        """max_x_reached should reflect best progress, not just current life."""
        from speednik.qa import _respawn_player
        from speednik.simulation import DeathEvent

        sim = self._make_pit_sim()
        walker = make_walker()
        pre_death_max_x = 0.0

        for frame in range(600):
            if sim.player_dead:
                break
            inp = walker(frame, sim)
            events = sim_step(sim, inp)
            if any(isinstance(e, DeathEvent) for e in events):
                pre_death_max_x = sim.max_x_reached
                _respawn_player(sim)
                break

        assert pre_death_max_x > 100.0, "Player should have made progress before death"
        assert sim.max_x_reached >= pre_death_max_x, (
            f"max_x_reached ({sim.max_x_reached}) should preserve "
            f"pre-death progress ({pre_death_max_x})"
        )


# ---------------------------------------------------------------------------
# No Pyxel import
# ---------------------------------------------------------------------------

class TestNoPyxelImport:
    def test_no_pyxel_import(self):
        import speednik.qa as mod
        source = Path(inspect.getfile(mod)).read_text()
        assert "import pyxel" not in source
        assert "from pyxel" not in source

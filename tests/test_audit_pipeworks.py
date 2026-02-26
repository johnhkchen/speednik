"""tests/test_audit_pipeworks.py — Pipeworks behavior audit.

Runs all 6 player archetypes through Pipeworks and asserts against
aspirational expectations from T-012-03. Findings document bugs, not
weakened thresholds.

Pipeworks is harder than Hillside: gaps, pipes, liquid zones, more
vertical terrain. Some archetypes are expected to die at gaps — that's
game design, not a bug. BUG-01 (slope wall) and BUG-02 (solid clipping)
are fixed. Remaining issues: narrow wall clipping BUG-03, steep slope
difficulty for jumping archetypes.
"""

from __future__ import annotations

import pytest

from speednik.qa import (
    BehaviorExpectation,
    format_findings,
    make_cautious,
    make_chaos,
    make_jumper,
    make_speed_demon,
    make_walker,
    make_wall_hugger,
    run_audit,
)

# ---------------------------------------------------------------------------
# Expectations — from ticket T-012-03 table, not adjusted to match bugs
# ---------------------------------------------------------------------------

PIPEWORKS_WALKER = BehaviorExpectation(
    name="pipeworks_walker",
    stage="pipeworks",
    archetype="walker",
    min_x_progress=3000,
    max_deaths=2,
    require_goal=False,
    max_frames=3600,
    invariant_errors_ok=0,
)

PIPEWORKS_JUMPER = BehaviorExpectation(
    name="pipeworks_jumper",
    stage="pipeworks",
    archetype="jumper",
    min_x_progress=5400,
    max_deaths=1,
    require_goal=True,
    max_frames=3600,
    invariant_errors_ok=0,
)

PIPEWORKS_SPEED_DEMON = BehaviorExpectation(
    name="pipeworks_speed_demon",
    stage="pipeworks",
    archetype="speed_demon",
    min_x_progress=5400,
    max_deaths=1,
    require_goal=True,
    max_frames=3600,
    invariant_errors_ok=0,
)

PIPEWORKS_CAUTIOUS = BehaviorExpectation(
    name="pipeworks_cautious",
    stage="pipeworks",
    archetype="cautious",
    min_x_progress=1500,
    max_deaths=1,
    require_goal=False,
    max_frames=3600,
    invariant_errors_ok=0,
)

PIPEWORKS_WALL_HUGGER = BehaviorExpectation(
    name="pipeworks_wall_hugger",
    stage="pipeworks",
    archetype="wall_hugger",
    min_x_progress=2000,
    max_deaths=2,
    require_goal=False,
    max_frames=3600,
    invariant_errors_ok=0,
)

PIPEWORKS_CHAOS = BehaviorExpectation(
    name="pipeworks_chaos",
    stage="pipeworks",
    archetype="chaos",
    min_x_progress=800,
    max_deaths=3,
    require_goal=False,
    max_frames=3600,
    invariant_errors_ok=0,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pipeworks_walker():
    # BUG-01 (slope wall), BUG-02 (solid clipping), and T-013-04 (solid
    # ejection) all fixed. Walker completes Pipeworks cleanly.
    findings, result = run_audit("pipeworks", make_walker(), PIPEWORKS_WALKER)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    strict=True,
    reason="Jumper bounces on 45-degree slope, max_x≈505 far below 5400 target",
)
def test_pipeworks_jumper():
    # BUG-01 (slope wall) is fixed. Jumper no longer hits the wall but bounces
    # repeatedly on the 45-degree slope (angle=32), unable to build enough
    # ground speed to climb over. Reaches max_x≈505 vs target 5400.
    findings, result = run_audit("pipeworks", make_jumper(), PIPEWORKS_JUMPER)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    strict=True,
    reason="Speed demon stalls on 45-degree slope, max_x≈449 far below 5400 target",
)
def test_pipeworks_speed_demon():
    # BUG-01 (slope wall) is fixed. Speed Demon struggles with the steep
    # 45-degree slope approach, reaching max_x≈449 vs target 5400.
    findings, result = run_audit(
        "pipeworks", make_speed_demon(), PIPEWORKS_SPEED_DEMON,
    )
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    strict=True,
    reason="Cautious stalls on 45-degree slope, max_x≈447 below 1500 target",
)
def test_pipeworks_cautious():
    # BUG-01 (slope wall) is fixed. Cautious cannot climb the steep 45-degree
    # slope approach, reaching max_x≈447 vs target 1500.
    findings, result = run_audit(
        "pipeworks", make_cautious(), PIPEWORKS_CAUTIOUS,
    )
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


def test_pipeworks_wall_hugger():
    # BUG-01 (slope wall), BUG-02 (solid clipping), and T-013-04 (solid
    # ejection) all fixed. Wall Hugger completes Pipeworks cleanly.
    findings, result = run_audit(
        "pipeworks", make_wall_hugger(), PIPEWORKS_WALL_HUGGER,
    )
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    strict=True,
    reason="Chaos max_x≈429 below 800 target (BUG-03 clipping fixed, progress shortfall remains)",
)
def test_pipeworks_chaos():
    # BUG-03 (narrow wall clipping at x≈100) is fixed. Chaos (seed=42) now has
    # zero invariant errors. However, max_x≈429 is still below the 800 target.
    findings, result = run_audit(
        "pipeworks", make_chaos(42), PIPEWORKS_CHAOS,
    )
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)

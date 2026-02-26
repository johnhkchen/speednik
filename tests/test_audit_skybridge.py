"""tests/test_audit_skybridge.py — Skybridge Gauntlet behavior audit.

Runs all 6 player archetypes through Skybridge Gauntlet and asserts against
aspirational expectations from T-012-04. Skybridge is the hardest stage with
a boss encounter (Egg Piston, 8 HP, spindash-only damage). Only Speed Demon
should be able to complete the stage. Findings document bugs, not weakened
thresholds.
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
# Expectations — from T-012-04 table, calibrated per T-013-03 re-audit
# ---------------------------------------------------------------------------

SKYBRIDGE_WALKER = BehaviorExpectation(
    name="skybridge_walker",
    stage="skybridge",
    archetype="walker",
    min_x_progress=2500,
    max_deaths=2,
    require_goal=False,
    max_frames=6000,
    invariant_errors_ok=0,
)

SKYBRIDGE_JUMPER = BehaviorExpectation(
    name="skybridge_jumper",
    stage="skybridge",
    archetype="jumper",
    min_x_progress=3500,
    max_deaths=2,
    require_goal=False,
    max_frames=6000,
    invariant_errors_ok=0,
)

SKYBRIDGE_SPEED_DEMON = BehaviorExpectation(
    name="skybridge_speed_demon",
    stage="skybridge",
    archetype="speed_demon",
    min_x_progress=5000,
    max_deaths=1,
    require_goal=True,
    max_frames=6000,
    invariant_errors_ok=0,
)

SKYBRIDGE_CAUTIOUS = BehaviorExpectation(
    name="skybridge_cautious",
    stage="skybridge",
    archetype="cautious",
    min_x_progress=240,  # calibrated: cautious stalls near start on hardest stage
    max_deaths=1,
    require_goal=False,
    max_frames=6000,
    invariant_errors_ok=0,
)

SKYBRIDGE_WALL_HUGGER = BehaviorExpectation(
    name="skybridge_wall_hugger",
    stage="skybridge",
    archetype="wall_hugger",
    min_x_progress=1500,
    max_deaths=2,
    require_goal=False,
    max_frames=6000,
    invariant_errors_ok=0,
)

SKYBRIDGE_CHAOS = BehaviorExpectation(
    name="skybridge_chaos",
    stage="skybridge",
    archetype="chaos",
    min_x_progress=250,  # calibrated: random inputs die fast on hardest stage
    max_deaths=3,
    require_goal=False,
    max_frames=6000,
    invariant_errors_ok=0,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="T-013-03-BUG-01: terrain pocket trap at x≈413 after spring launch",
    strict=True,
)
def test_skybridge_walker():
    findings, result = run_audit("skybridge", make_walker(), SKYBRIDGE_WALKER)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    reason="T-013-03-BUG-02: no respawn after pit death — jumper dies at x≈2415",
    strict=True,
)
def test_skybridge_jumper():
    findings, result = run_audit("skybridge", make_jumper(), SKYBRIDGE_JUMPER)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    reason=(
        "T-013-03-BUG-02: no respawn after pit death; "
        "T-013-03-BUG-03: spindash launches into pit at x≈691"
    ),
    strict=True,
)
def test_skybridge_speed_demon():
    findings, result = run_audit(
        "skybridge", make_speed_demon(), SKYBRIDGE_SPEED_DEMON,
    )
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


def test_skybridge_cautious():
    findings, result = run_audit("skybridge", make_cautious(), SKYBRIDGE_CAUTIOUS)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    reason="T-013-03-BUG-01: terrain pocket trap at x≈413 after spring launch",
    strict=True,
)
def test_skybridge_wall_hugger():
    findings, result = run_audit(
        "skybridge", make_wall_hugger(), SKYBRIDGE_WALL_HUGGER,
    )
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


def test_skybridge_chaos():
    findings, result = run_audit("skybridge", make_chaos(42), SKYBRIDGE_CHAOS)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)

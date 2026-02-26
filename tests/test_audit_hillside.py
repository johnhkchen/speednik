"""tests/test_audit_hillside.py — Hillside Rush behavior audit.

Runs all 6 player archetypes through Hillside Rush and asserts against
aspirational expectations from T-012-02. Findings document bugs, not
weakened thresholds.
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
# Expectations — from ticket T-012-02 table, not adjusted to match bugs
# ---------------------------------------------------------------------------

HILLSIDE_WALKER = BehaviorExpectation(
    name="hillside_walker",
    stage="hillside",
    archetype="walker",
    min_x_progress=4700,
    max_deaths=0,
    require_goal=True,
    max_frames=3600,
    invariant_errors_ok=0,
)

HILLSIDE_JUMPER = BehaviorExpectation(
    name="hillside_jumper",
    stage="hillside",
    archetype="jumper",
    min_x_progress=4700,
    max_deaths=0,
    require_goal=True,
    max_frames=3600,
    invariant_errors_ok=0,
)

HILLSIDE_SPEED_DEMON = BehaviorExpectation(
    name="hillside_speed_demon",
    stage="hillside",
    archetype="speed_demon",
    min_x_progress=4700,
    max_deaths=0,
    require_goal=True,
    max_frames=3600,
    invariant_errors_ok=0,
)

HILLSIDE_CAUTIOUS = BehaviorExpectation(
    name="hillside_cautious",
    stage="hillside",
    archetype="cautious",
    min_x_progress=2400,
    max_deaths=0,
    require_goal=False,
    max_frames=3600,
    invariant_errors_ok=0,
)

HILLSIDE_WALL_HUGGER = BehaviorExpectation(
    name="hillside_wall_hugger",
    stage="hillside",
    archetype="wall_hugger",
    min_x_progress=2400,
    max_deaths=0,
    require_goal=False,
    max_frames=3600,
    invariant_errors_ok=0,
)

HILLSIDE_CHAOS = BehaviorExpectation(
    name="hillside_chaos",
    stage="hillside",
    archetype="chaos",
    min_x_progress=1200,
    max_deaths=2,
    require_goal=False,
    max_frames=3600,
    invariant_errors_ok=0,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="BUG-01 wall fixed (past x≈601), but walker stalls at x≈880 — separate terrain issue",
)
def test_hillside_walker():
    findings, result = run_audit("hillside", make_walker(), HILLSIDE_WALKER)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    strict=True,
    reason="Jumper falls off right edge at x=4800 — no kill zone at level boundary",
)
def test_hillside_jumper():
    findings, result = run_audit("hillside", make_jumper(), HILLSIDE_JUMPER)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    strict=True,
    reason="Speed demon gets stuck at loop area (max_x≈3647 < 4700) — solid ejection prevents clipping-based traversal",
)
def test_hillside_speed_demon():
    findings, result = run_audit(
        "hillside", make_speed_demon(), HILLSIDE_SPEED_DEMON,
    )
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    strict=True,
    reason="BUG-01 wall fixed (past x≈601), but cautious stalls at x≈846 — separate terrain issue",
)
def test_hillside_cautious():
    findings, result = run_audit("hillside", make_cautious(), HILLSIDE_CAUTIOUS)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


@pytest.mark.xfail(
    strict=True,
    reason="BUG-01 wall fixed (past x≈601), but wall hugger stalls at x≈880 — separate terrain issue",
)
def test_hillside_wall_hugger():
    findings, result = run_audit(
        "hillside", make_wall_hugger(), HILLSIDE_WALL_HUGGER,
    )
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)


def test_hillside_chaos():
    findings, result = run_audit("hillside", make_chaos(42), HILLSIDE_CHAOS)
    bugs = [f for f in findings if f.severity == "bug"]
    assert len(bugs) == 0, format_findings(findings)

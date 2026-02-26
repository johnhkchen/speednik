"""speednik/qa.py — Player archetype library and QA audit framework.

Provides 6 player archetype strategies that model real player behaviors,
plus an expectation-based audit runner that treats failures as findings
(not broken tests). No Pyxel imports.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from speednik.invariants import Violation, check_invariants
from speednik.physics import InputState
from speednik.player import PlayerState
from speednik.simulation import (
    DeathEvent,
    Event,
    GoalReachedEvent,
    SimState,
    create_sim,
    sim_step,
)
from speednik.strategies import FrameSnapshot
from speednik.terrain import get_quadrant

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

Archetype = Callable[[int, SimState], InputState]

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class BehaviorExpectation:
    """What a player archetype should experience on a given stage."""

    name: str
    stage: str
    archetype: str
    min_x_progress: float
    max_deaths: int
    require_goal: bool
    max_frames: int
    invariant_errors_ok: int


@dataclass
class AuditFinding:
    """A single finding from an audit run."""

    expectation: str
    actual: str
    frame: int
    x: float
    y: float
    severity: str  # "bug" | "warning"
    details: str


@dataclass
class AuditResult:
    """Full audit run output — trajectory, violations, and final sim state."""

    snapshots: list[FrameSnapshot]
    events_per_frame: list[list[Event]]
    violations: list[Violation]
    sim: SimState


# ---------------------------------------------------------------------------
# Snapshot capture
# ---------------------------------------------------------------------------


def _capture_snapshot(sim: SimState, frame: int) -> FrameSnapshot:
    p = sim.player.physics
    return FrameSnapshot(
        frame=frame,
        x=p.x,
        y=p.y,
        x_vel=p.x_vel,
        y_vel=p.y_vel,
        ground_speed=p.ground_speed,
        angle=p.angle,
        on_ground=p.on_ground,
        quadrant=get_quadrant(p.angle),
        state=sim.player.state.value,
    )


# ---------------------------------------------------------------------------
# Archetype factories
# ---------------------------------------------------------------------------


def make_walker() -> Archetype:
    """Hold right every frame. The most basic human input."""

    def strategy(frame: int, sim: SimState) -> InputState:
        return InputState(right=True)

    return strategy


def make_jumper() -> Archetype:
    """Hold right + press jump whenever grounded."""
    prev_jump = False

    def strategy(frame: int, sim: SimState) -> InputState:
        nonlocal prev_jump
        want_jump = sim.player.physics.on_ground
        pressed = want_jump and not prev_jump
        prev_jump = want_jump
        return InputState(
            right=True,
            jump_pressed=pressed,
            jump_held=want_jump,
        )

    return strategy


def make_speed_demon() -> Archetype:
    """Spindash, release, hold right, re-spindash when slow."""
    APPROACH, CROUCH, CHARGE, RELEASE, RUN = 0, 1, 2, 3, 4
    phase = APPROACH
    counter = 0
    charge_frames = 3
    redash_threshold = 2.0
    prev_jump = False

    def strategy(frame: int, sim: SimState) -> InputState:
        nonlocal phase, counter, prev_jump

        p = sim.player.physics

        if phase == APPROACH:
            counter += 1
            if counter >= 10:
                phase = CROUCH
            return InputState(right=True)

        if phase == CROUCH:
            phase = CHARGE
            counter = 0
            prev_jump = False
            return InputState(down_held=True)

        if phase == CHARGE:
            counter += 1
            pressed = not prev_jump
            prev_jump = True
            if counter >= charge_frames:
                phase = RELEASE
            return InputState(down_held=True, jump_pressed=pressed, jump_held=True)

        if phase == RELEASE:
            phase = RUN
            prev_jump = False
            return InputState(right=True)

        # RUN phase
        if (
            p.on_ground
            and abs(p.ground_speed) < redash_threshold
            and sim.player.state != PlayerState.SPINDASH
            and frame > 20
        ):
            phase = CROUCH
            return InputState(down_held=True)

        return InputState(right=True)

    return strategy


def make_cautious() -> Archetype:
    """Walk right slowly (tap right, release, repeat). Occasionally walk left."""
    counter = 0

    def strategy(frame: int, sim: SimState) -> InputState:
        nonlocal counter
        counter += 1
        cycle = counter % 135

        # Every ~135 frames: walk left for 15 frames
        if cycle >= 120:
            return InputState(left=True)

        # Tap-walk: right for 10, nothing for 5
        tap_phase = cycle % 15
        if tap_phase < 10:
            return InputState(right=True)

        return InputState()

    return strategy


def make_wall_hugger() -> Archetype:
    """Hold right until wall detected (near-zero speed), then jump."""
    stall_frames = 0
    stall_threshold = 5
    prev_jump = False

    def strategy(frame: int, sim: SimState) -> InputState:
        nonlocal stall_frames, prev_jump
        p = sim.player.physics

        if p.on_ground and abs(p.ground_speed) < 0.1 and frame > 5:
            stall_frames += 1
        else:
            stall_frames = 0

        if stall_frames >= stall_threshold and p.on_ground:
            want_jump = True
            pressed = want_jump and not prev_jump
            prev_jump = want_jump
            stall_frames = 0
            return InputState(right=True, jump_pressed=pressed, jump_held=True)

        prev_jump = False
        return InputState(right=True)

    return strategy


def make_chaos(seed: int) -> Archetype:
    """Deterministic pseudo-random inputs. Reproducible via seeded RNG."""
    rng = random.Random(seed)
    next_change = 0
    current = InputState()

    def strategy(frame: int, sim: SimState) -> InputState:
        nonlocal next_change, current
        if frame >= next_change:
            next_change = frame + rng.randint(5, 15)
            current = InputState(
                left=rng.choice([True, False]),
                right=rng.choice([True, False]),
                jump_pressed=rng.choice([True, False]),
                jump_held=rng.choice([True, False]),
                down_held=rng.choice([True, False]),
            )
        return current

    return strategy


# ---------------------------------------------------------------------------
# Finding builder
# ---------------------------------------------------------------------------


def _build_findings(
    sim: SimState,
    snapshots: list[FrameSnapshot],
    violations: list[Violation],
    expectation: BehaviorExpectation,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    # Invariant violations → findings
    for v in violations:
        snap = _find_snapshot_at_frame(snapshots, v.frame)
        severity = "bug" if v.severity == "error" else "warning"
        findings.append(AuditFinding(
            expectation=f"No {v.invariant} violations",
            actual=v.details,
            frame=v.frame,
            x=snap.x if snap else 0.0,
            y=snap.y if snap else 0.0,
            severity=severity,
            details=v.details,
        ))

    # Check invariant error count against budget
    error_count = sum(1 for v in violations if v.severity == "error")
    if error_count > expectation.invariant_errors_ok:
        last_frame = snapshots[-1].frame if snapshots else 0
        last_x = snapshots[-1].x if snapshots else 0.0
        last_y = snapshots[-1].y if snapshots else 0.0
        findings.append(AuditFinding(
            expectation=f"At most {expectation.invariant_errors_ok} invariant errors",
            actual=f"{error_count} invariant errors",
            frame=last_frame,
            x=last_x,
            y=last_y,
            severity="bug",
            details=(
                f"Invariant error count {error_count} exceeds "
                f"budget {expectation.invariant_errors_ok}"
            ),
        ))

    # Check min_x_progress
    max_x = sim.max_x_reached
    if max_x < expectation.min_x_progress:
        last_frame = snapshots[-1].frame if snapshots else 0
        last_x = snapshots[-1].x if snapshots else 0.0
        last_y = snapshots[-1].y if snapshots else 0.0
        findings.append(AuditFinding(
            expectation=f"Reach at least x={expectation.min_x_progress:.1f}",
            actual=f"max_x={max_x:.1f}",
            frame=last_frame,
            x=last_x,
            y=last_y,
            severity="bug",
            details=(
                f"Player reached x={max_x:.1f}, "
                f"expected at least x={expectation.min_x_progress:.1f}"
            ),
        ))

    # Check max_deaths
    if sim.deaths > expectation.max_deaths:
        last_frame = snapshots[-1].frame if snapshots else 0
        last_x = snapshots[-1].x if snapshots else 0.0
        last_y = snapshots[-1].y if snapshots else 0.0
        findings.append(AuditFinding(
            expectation=f"At most {expectation.max_deaths} deaths",
            actual=f"{sim.deaths} deaths",
            frame=last_frame,
            x=last_x,
            y=last_y,
            severity="bug",
            details=(
                f"{sim.deaths} deaths exceeds maximum {expectation.max_deaths}"
            ),
        ))

    # Check require_goal
    if expectation.require_goal and not sim.goal_reached:
        last_frame = snapshots[-1].frame if snapshots else 0
        last_x = snapshots[-1].x if snapshots else 0.0
        last_y = snapshots[-1].y if snapshots else 0.0
        findings.append(AuditFinding(
            expectation="Reach the goal",
            actual="Goal not reached",
            frame=last_frame,
            x=last_x,
            y=last_y,
            severity="bug",
            details=f"Player did not reach goal (max_x={max_x:.1f})",
        ))

    return findings


def _find_snapshot_at_frame(
    snapshots: list[FrameSnapshot], frame: int
) -> FrameSnapshot | None:
    for s in snapshots:
        if s.frame == frame:
            return s
    return snapshots[-1] if snapshots else None


# ---------------------------------------------------------------------------
# Respawn helper
# ---------------------------------------------------------------------------


def _respawn_player(sim: SimState) -> None:
    """Reset the player to checkpoint/start position after death."""
    p = sim.player
    p.state = PlayerState.STANDING
    p.physics.x = p.respawn_x
    p.physics.y = p.respawn_y
    p.physics.x_vel = 0.0
    p.physics.y_vel = 0.0
    p.physics.ground_speed = 0.0
    p.physics.on_ground = True
    p.physics.is_rolling = False
    p.physics.is_charging_spindash = False
    p.rings = p.respawn_rings
    p.invulnerability_timer = 0
    p.scattered_rings = []
    p.in_pipe = False


# ---------------------------------------------------------------------------
# Audit runner
# ---------------------------------------------------------------------------


def run_audit(
    stage: str,
    archetype_fn: Archetype,
    expectation: BehaviorExpectation,
) -> tuple[list[AuditFinding], AuditResult]:
    """Run an archetype on a stage and compare against expectations.

    Returns (findings, result) where findings are expectation mismatches
    and invariant violations, and result contains the full trajectory.
    """
    sim = create_sim(stage)

    snapshots: list[FrameSnapshot] = []
    events_per_frame: list[list[Event]] = []

    for frame in range(expectation.max_frames):
        if sim.goal_reached or sim.player_dead:
            break

        inp = archetype_fn(frame, sim)
        events = sim_step(sim, inp)
        snapshots.append(_capture_snapshot(sim, frame + 1))
        events_per_frame.append(events)

        # Respawn after death or terminate if budget exceeded
        if any(isinstance(e, DeathEvent) for e in events):
            if sim.deaths > expectation.max_deaths:
                sim.player_dead = True
            else:
                _respawn_player(sim)

    violations = check_invariants(sim, snapshots, events_per_frame)
    findings = _build_findings(sim, snapshots, violations, expectation)
    result = AuditResult(
        snapshots=snapshots,
        events_per_frame=events_per_frame,
        violations=violations,
        sim=sim,
    )
    return findings, result


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_findings(findings: list[AuditFinding]) -> str:
    """Format findings into a human-readable string for assertion messages."""
    bugs = [f for f in findings if f.severity == "bug"]
    lines = [f"FINDINGS ({len(bugs)} bugs):"]

    for f in findings:
        lines.append(f"  [frame {f.frame}, x={f.x:.1f}] {f.details}")
        lines.append(f"    Expected: {f.expectation}")
        lines.append(f"    Actual: {f.actual}")

    return "\n".join(lines)

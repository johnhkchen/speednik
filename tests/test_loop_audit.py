"""Loop traversal QA audit (T-012-08).

Tests that loop-de-loops are fully traversable — the player stays on the loop
surface through all 4 quadrants {0, 1, 2, 3} while on_ground. Visiting quadrants
while airborne does not count.

Audit Probes:
┌──────────────────────────┬───────────────────────────────────────────────────┐
│ Probe                    │ What it tests                                     │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Synthetic traversal      │ build_loop() loops: grounded quadrants {0,1,2,3}  │
│ Synthetic exit           │ Player exits with positive speed, on_ground       │
│ Speed sweep              │ Minimum speed for full traversal at r=48          │
│ Hillside traversal       │ Real stage loop: grounded quadrants {0,1,2,3}    │
│ Hillside exit            │ Real stage loop: player clears loop region        │
└──────────────────────────┴───────────────────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from speednik.grids import build_loop
from speednik.physics import InputState
from speednik.player import PlayerState
from speednik.simulation import (
    SimState,
    create_sim,
    create_sim_from_lookup,
    sim_step,
)
from speednik.terrain import TILE_SIZE, get_quadrant


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GROUND_ROW = 20
GROUND_Y = GROUND_ROW * TILE_SIZE - 20


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LoopAuditSnap:
    """Per-frame snapshot for loop audit assertions."""

    frame: int
    x: float
    y: float
    ground_speed: float
    on_ground: bool
    quadrant: int
    angle: int
    state: str


@dataclass
class LoopAuditResult:
    """Result of running a loop audit probe."""

    snaps: list[LoopAuditSnap]

    @property
    def grounded_quadrants(self) -> set[int]:
        return {s.quadrant for s in self.snaps if s.on_ground}

    @property
    def all_quadrants(self) -> set[int]:
        return {s.quadrant for s in self.snaps}

    @property
    def max_x(self) -> float:
        return max(s.x for s in self.snaps)

    @property
    def final(self) -> LoopAuditSnap:
        return self.snaps[-1]

    def loop_region_snaps(
        self, loop_start_x: float, loop_end_x: float,
    ) -> list[LoopAuditSnap]:
        return [s for s in self.snaps if loop_start_x <= s.x <= loop_end_x]

    def ground_loss_frame(self, after_x: float) -> int | None:
        """First frame after after_x where on_ground drops from True to False."""
        prev_on_ground = False
        for s in self.snaps:
            if s.x < after_x:
                prev_on_ground = s.on_ground
                continue
            if prev_on_ground and not s.on_ground:
                return s.frame
            prev_on_ground = s.on_ground
        return None

    def post_loop_grounded(self, loop_exit_x: float) -> list[LoopAuditSnap]:
        return [s for s in self.snaps if s.x > loop_exit_x and s.on_ground]


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def _format_diagnostic(
    result: LoopAuditResult,
    loop_start_x: float,
    loop_end_x: float,
    *,
    radius: int | None = None,
    entry_speed: float | None = None,
    label: str = "",
) -> str:
    """Format rich diagnostic output for a failed loop audit."""
    parts: list[str] = []

    header = "LOOP AUDIT FAILED"
    details = []
    if label:
        details.append(label)
    if radius is not None:
        details.append(f"radius={radius}")
    if entry_speed is not None:
        details.append(f"entry_speed={entry_speed:.1f}")
    if details:
        header += f" ({', '.join(details)})"
    parts.append(f"{header}:")

    parts.append(
        f"  Grounded quadrants: {result.grounded_quadrants}  "
        f"(expected {{0, 1, 2, 3}})"
    )
    parts.append(
        f"  All quadrants (incl. airborne): {result.all_quadrants}"
    )
    parts.append("")

    # Trajectory through loop region (max 30 frames)
    region = result.loop_region_snaps(loop_start_x - 20, loop_end_x + 20)
    if region:
        parts.append(
            f"  Trajectory through loop region "
            f"(x={loop_start_x:.0f}..{loop_end_x:.0f}):"
        )
        for s in region[:30]:
            og = "True " if s.on_ground else "False"
            parts.append(
                f"    f={s.frame:>3d}: x={s.x:>7.0f} y={s.y:>6.0f} "
                f"gs={s.ground_speed:>5.1f} og={og} q={s.quadrant}  "
                f"state={s.state}"
            )
        if len(region) > 30:
            parts.append(f"    ... ({len(region)} total frames in loop region)")
    parts.append("")

    # Ground loss analysis
    loss_frame = result.ground_loss_frame(loop_start_x)
    if loss_frame is not None:
        loss_snap = next(
            (s for s in result.snaps if s.frame == loss_frame), None,
        )
        if loss_snap:
            parts.append(
                f"  Ground contact lost at frame {loss_frame} "
                f"(x={loss_snap.x:.0f})."
            )
    else:
        # Check if player just never reaches higher quadrants
        max_q = max(result.grounded_quadrants) if result.grounded_quadrants else -1
        if max_q < 2:
            parts.append(
                "  Player never reached Q2 (ceiling). "
                "Stuck on lower quadrants."
            )
    parts.append("")

    # Probable causes
    parts.append("  Probable causes:")
    if result.grounded_quadrants <= {0, 1}:
        parts.append(
            "    - Player pops off surface at Q1→Q2 transition"
        )
        parts.append(
            "    - Loop tile angles may have discontinuous jumps"
        )
    if result.grounded_quadrants <= {0}:
        parts.append(
            "    - Player never enters loop (ramp geometry issue)"
        )
    if entry_speed is not None and entry_speed < 5.0:
        parts.append(
            "    - Entry speed too low to maintain adhesion through ceiling"
        )
    if entry_speed is not None and entry_speed > 10.0:
        parts.append(
            "    - Entry speed too high — player overshoots sensor snap range"
        )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def _spindash_strategy():
    """Spindash then hold right; re-dash if speed drops below 2.0."""
    CROUCH, CHARGE, RELEASE, RUN = 0, 1, 2, 3
    state = {"phase": CROUCH, "counter": 0}

    def strategy(frame: int, sim: SimState) -> InputState:
        phase = state["phase"]

        if phase == CROUCH:
            state["phase"] = CHARGE
            state["counter"] = 0
            return InputState(down_held=True)

        if phase == CHARGE:
            state["counter"] += 1
            if state["counter"] >= 3:
                state["phase"] = RELEASE
            return InputState(down_held=True, jump_pressed=True, jump_held=True)

        if phase == RELEASE:
            state["phase"] = RUN
            return InputState(right=True)

        # RUN phase
        if (
            sim.player.physics.on_ground
            and abs(sim.player.physics.ground_speed) < 2.0
            and sim.player.state != PlayerState.SPINDASH
        ):
            state["phase"] = CROUCH
            return InputState(down_held=True)

        return InputState(right=True)

    return strategy


def _hold_right(_frame: int, _sim: SimState) -> InputState:
    return InputState(right=True)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _run_loop_audit(
    sim: SimState,
    strategy,
    frames: int = 600,
) -> LoopAuditResult:
    """Run a loop audit probe."""
    snaps: list[LoopAuditSnap] = []
    for frame in range(frames):
        inp = strategy(frame, sim)
        sim_step(sim, inp)
        p = sim.player.physics
        snaps.append(
            LoopAuditSnap(
                frame=frame,
                x=p.x,
                y=p.y,
                ground_speed=p.ground_speed,
                on_ground=p.on_ground,
                quadrant=get_quadrant(p.angle),
                angle=p.angle,
                state=sim.player.state.value,
            )
        )
    return LoopAuditResult(snaps=snaps)


# ---------------------------------------------------------------------------
# Test: Synthetic loop traversal (Phase 1)
# ---------------------------------------------------------------------------


class TestSyntheticLoopTraversal:
    """Audit: spindash through synthetic loops of varying radii.

    A full traversal means the player visits all 4 quadrants {0, 1, 2, 3}
    while on_ground. Visiting quadrants while airborne does not count.
    """

    @staticmethod
    def _build_and_run(radius: int) -> tuple[LoopAuditResult, float, float]:
        """Build a synthetic loop and run the audit.

        Returns (result, loop_start_x, loop_end_x) for diagnostic formatting.
        """
        ramp_radius = max(16, radius // 2)
        _, lookup = build_loop(
            approach_tiles=15, radius=radius,
            ground_row=GROUND_ROW, ramp_radius=ramp_radius,
        )
        approach_px = 15 * TILE_SIZE
        loop_start_x = float(approach_px + ramp_radius)
        loop_end_x = float(loop_start_x + 2 * radius)

        sim = create_sim_from_lookup(lookup, 48.0, float(GROUND_Y))
        result = _run_loop_audit(sim, _spindash_strategy(), frames=600)
        return result, loop_start_x, loop_end_x

    @pytest.mark.parametrize("radius", [
        pytest.param(32, marks=pytest.mark.xfail(strict=True,
            reason="r=32 too small for full grounded traversal (only 4 tiles wide)",
        ), id="r32"),
        pytest.param(48, id="r48"),
        pytest.param(64, id="r64"),
        pytest.param(96, id="r96"),
    ])
    def test_all_quadrants_grounded(self, radius: int) -> None:
        """Loop must be fully traversed on_ground at spindash speed."""
        result, loop_start, loop_end = self._build_and_run(radius)
        grounded = result.grounded_quadrants
        assert grounded == {0, 1, 2, 3}, _format_diagnostic(
            result, loop_start, loop_end, radius=radius,
        )

    @pytest.mark.parametrize("radius", [
        pytest.param(32, marks=pytest.mark.xfail(strict=True,
            reason="r=32 too small — player overshoots exit",
        ), id="r32"),
        pytest.param(48, marks=pytest.mark.xfail(strict=True,
            reason="r=48 exit ramp geometry: player goes airborne before grounding past exit",
        ), id="r48"),
        pytest.param(64, id="r64"),
        pytest.param(96, id="r96"),
    ])
    def test_exit_positive_speed(self, radius: int) -> None:
        """After loop, player should have positive ground_speed."""
        result, loop_start, loop_end = self._build_and_run(radius)
        ramp_radius = max(16, radius // 2)
        loop_exit_x = loop_end + ramp_radius
        post_loop = result.post_loop_grounded(loop_exit_x)
        assert len(post_loop) > 0, _format_diagnostic(
            result, loop_start, loop_end, radius=radius,
            label="no on-ground frames past loop exit",
        )
        assert post_loop[0].ground_speed > 0, (
            f"radius={radius}: exit ground_speed="
            f"{post_loop[0].ground_speed:.2f}"
        )

    @pytest.mark.parametrize("radius", [
        pytest.param(32, marks=pytest.mark.xfail(strict=True,
            reason="r=32 too small — player overshoots exit",
        ), id="r32"),
        pytest.param(48, marks=pytest.mark.xfail(strict=True,
            reason="r=48 exit ramp geometry: player goes airborne before grounding past exit",
        ), id="r48"),
        pytest.param(64, id="r64"),
        pytest.param(96, id="r96"),
    ])
    def test_exit_on_ground(self, radius: int) -> None:
        """After loop, player should return to ground."""
        result, loop_start, loop_end = self._build_and_run(radius)
        ramp_radius = max(16, radius // 2)
        loop_exit_x = loop_end + ramp_radius
        post_loop = [s for s in result.snaps if s.x > loop_exit_x]
        any_on_ground = any(s.on_ground for s in post_loop)
        assert any_on_ground, _format_diagnostic(
            result, loop_start, loop_end, radius=radius,
            label="player never on_ground past loop exit",
        )


# ---------------------------------------------------------------------------
# Test: Speed sweep (Phase 1 extension)
# ---------------------------------------------------------------------------


class TestSyntheticLoopSpeedSweep:
    """Audit: minimum speed to complete a radius-48 loop.

    Injects speed directly (no spindash) to isolate the speed threshold.
    Documents which speeds achieve full grounded traversal.
    """

    RADIUS = 48
    RAMP_RADIUS = 24  # max(16, 48 // 2)

    @classmethod
    def _run_at_speed(cls, speed: float) -> tuple[LoopAuditResult, float, float]:
        _, lookup = build_loop(
            approach_tiles=15, radius=cls.RADIUS,
            ground_row=GROUND_ROW, ramp_radius=cls.RAMP_RADIUS,
        )
        approach_px = 15 * TILE_SIZE
        loop_start_x = float(approach_px + cls.RAMP_RADIUS)
        loop_end_x = float(loop_start_x + 2 * cls.RADIUS)

        sim = create_sim_from_lookup(lookup, 48.0, float(GROUND_Y))
        sim.player.physics.ground_speed = speed
        sim.player.physics.x_vel = speed
        result = _run_loop_audit(sim, _hold_right, frames=600)
        return result, loop_start_x, loop_end_x

    @pytest.mark.parametrize("speed", [
        pytest.param(4.0, marks=pytest.mark.xfail(strict=True,
            reason="speed=4.0 too slow for r=48 loop traversal",
        ), id="s4"),
        pytest.param(5.0, id="s5"),
        pytest.param(6.0, marks=pytest.mark.xfail(strict=True,
            reason="speed=6.0 does not complete r=48 loop "
            "(speed sensitivity — narrow traversal windows)",
        ), id="s6"),
        pytest.param(7.0, marks=pytest.mark.xfail(strict=True,
            reason="speed=7.0 does not complete r=48 loop",
        ), id="s7"),
        pytest.param(8.0, id="s8"),
        pytest.param(9.0, marks=pytest.mark.xfail(strict=True,
            reason="speed=9.0 overshoots sensor snap range at r=48",
        ), id="s9"),
        pytest.param(10.0, marks=pytest.mark.xfail(strict=True,
            reason="speed=10.0 overshoots sensor snap range at r=48",
        ), id="s10"),
        pytest.param(11.0, marks=pytest.mark.xfail(strict=True,
            reason="speed=11.0 overshoots sensor snap range at r=48",
        ), id="s11"),
        pytest.param(12.0, marks=pytest.mark.xfail(strict=True,
            reason="speed=12.0 overshoots sensor snap range at r=48",
        ), id="s12"),
    ])
    def test_traversal_at_speed(self, speed: float) -> None:
        """Full grounded traversal at the given entry speed."""
        result, loop_start, loop_end = self._run_at_speed(speed)
        grounded = result.grounded_quadrants
        assert grounded == {0, 1, 2, 3}, _format_diagnostic(
            result, loop_start, loop_end,
            radius=self.RADIUS, entry_speed=speed,
        )


# ---------------------------------------------------------------------------
# Test: Hillside real stage loop (Phase 2)
# ---------------------------------------------------------------------------

# Hillside loop region: tiles tx=217–233, px 3472–3744, ground≈610
_HILLSIDE_LOOP_START_X = 3472.0
_HILLSIDE_LOOP_END_X = 3744.0
_HILLSIDE_SPINDASH_X = 3100.0
_HILLSIDE_SPINDASH_Y = 610.0


class TestHillsideLoopTraversal:
    """Audit: spindash through the hillside stage loop.

    The hillside loop uses hand-placed tiles with different geometry from
    build_loop(). Tests whether the real stage loop is fully traversable.
    """

    @staticmethod
    def _build_and_run() -> LoopAuditResult:
        sim = create_sim("hillside")
        sim.player.physics.x = _HILLSIDE_SPINDASH_X
        sim.player.physics.y = _HILLSIDE_SPINDASH_Y
        return _run_loop_audit(sim, _spindash_strategy(), frames=600)

    @pytest.mark.xfail(strict=True,
        reason="Hillside loop hand-placed tiles lack Q3 grounded coverage "
        "(player goes airborne over loop, lands on exit downslope at Q3→Q0)",
    )
    def test_all_quadrants_grounded(self) -> None:
        """Hillside loop must be fully traversed on_ground."""
        result = self._build_and_run()
        grounded = result.grounded_quadrants
        assert grounded == {0, 1, 2, 3}, _format_diagnostic(
            result, _HILLSIDE_LOOP_START_X, _HILLSIDE_LOOP_END_X,
            label="hillside",
        )

    def test_exits_loop_region(self) -> None:
        """Player should clear the loop region (x > 3744)."""
        result = self._build_and_run()
        assert result.max_x > _HILLSIDE_LOOP_END_X, _format_diagnostic(
            result, _HILLSIDE_LOOP_START_X, _HILLSIDE_LOOP_END_X,
            label="hillside — didn't exit loop region",
        )

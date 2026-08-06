"""Loop traversal QA audit (T-012-08).

Tests that loop-de-loops are fully traversable — the player enters the loop,
stays on the surface through all 4 quadrants {0, 1, 2, 3} while on_ground,
AND exits the loop region. A player that visits all quadrants but remains
trapped inside the loop is a failure.

Audit Probes:
┌──────────────────────────┬───────────────────────────────────────────────────┐
│ Probe                    │ What it tests                                     │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Synthetic traversal      │ build_loop(): grounded {0,1,2,3} AND exits loop  │
│ Speed sweep              │ Which speeds achieve full traversal + exit        │
│ Hillside traversal       │ Real stage loop: full traversal + exits           │
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

    def player_exits_loop(self, loop_exit_x: float) -> bool:
        """True if the player's max_x exceeds loop_exit_x."""
        return self.max_x > loop_exit_x


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
    parts.append(f"  Max x reached: {result.max_x:.0f}")
    parts.append(f"  Final x: {result.final.x:.0f}")

    # Check for stuck-in-loop condition
    ramp_r = radius // 2 if radius else 0
    exit_x = loop_end_x + ramp_r
    if not result.player_exits_loop(exit_x):
        parts.append(
            f"  ** STUCK IN LOOP ** — max_x={result.max_x:.0f} < "
            f"loop_exit_x={exit_x:.0f}"
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

    A correct traversal requires BOTH:
    1. The player visits all 4 quadrants {0, 1, 2, 3} while on_ground
    2. The player exits the loop (max_x > loop_exit_x)

    A player that visits all quadrants but stays trapped in the loop is a failure.
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
        pytest.param(32, id="r32"),
        pytest.param(48, id="r48"),
        pytest.param(64, id="r64"),
        pytest.param(96, id="r96"),
    ])
    def test_player_exits_loop(self, radius: int) -> None:
        """Player must exit the loop region (not get stuck orbiting)."""
        result, loop_start, loop_end = self._build_and_run(radius)
        ramp_radius = max(16, radius // 2)
        loop_exit_x = loop_end + ramp_radius
        assert result.player_exits_loop(loop_exit_x), _format_diagnostic(
            result, loop_start, loop_end, radius=radius,
            label="player stuck in loop — never exits",
        )


# ---------------------------------------------------------------------------
# Test: Speed sweep (Phase 1 extension)
# ---------------------------------------------------------------------------


class TestSyntheticLoopSpeedSweep:
    """Audit: loop behavior across entry speeds at r=48.

    Injects speed directly (no spindash) to isolate the speed threshold.
    Tests both quadrant coverage AND loop exit — a speed that achieves
    all 4 grounded quadrants but traps the player is a failure.
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
        pytest.param(4.0, id="s4"),
        pytest.param(5.0, marks=pytest.mark.xfail(strict=True,
            reason="speed=5.0 gets stuck in loop (visits all quads but never exits)",
        ), id="s5"),
        pytest.param(6.0, id="s6"),
        pytest.param(7.0, id="s7"),
        pytest.param(8.0, id="s8"),
        pytest.param(9.0, id="s9"),
        pytest.param(10.0, marks=pytest.mark.xfail(strict=True,
            reason="speed=10.0 gets stuck in loop",
        ), id="s10"),
        pytest.param(11.0, id="s11"),
        pytest.param(12.0, id="s12"),
    ])
    def test_player_exits_loop(self, speed: float) -> None:
        """Player must exit the loop at the given speed."""
        result, loop_start, loop_end = self._run_at_speed(speed)
        loop_exit_x = loop_end + self.RAMP_RADIUS
        assert result.player_exits_loop(loop_exit_x), _format_diagnostic(
            result, loop_start, loop_end,
            radius=self.RADIUS, entry_speed=speed,
            label="player stuck in loop",
        )

    @pytest.mark.parametrize("speed", [
        pytest.param(8.0, id="s8"),
    ])
    def test_full_traversal_and_exit(self, speed: float) -> None:
        """The gold standard: all 4 grounded quadrants AND exits the loop."""
        result, loop_start, loop_end = self._run_at_speed(speed)
        loop_exit_x = loop_end + self.RAMP_RADIUS

        grounded = result.grounded_quadrants
        assert grounded == {0, 1, 2, 3}, _format_diagnostic(
            result, loop_start, loop_end,
            radius=self.RADIUS, entry_speed=speed,
            label="incomplete quadrant coverage",
        )
        assert result.player_exits_loop(loop_exit_x), _format_diagnostic(
            result, loop_start, loop_end,
            radius=self.RADIUS, entry_speed=speed,
            label="all quads visited but player stuck in loop",
        )


# ---------------------------------------------------------------------------
# Test: Hillside real stage loop (Phase 2)
# ---------------------------------------------------------------------------

# Hillside loop region (synthetic build_loop, r=64, ramp_radius=32, cx=3584):
# Entry ramp: px 3488–3520, Loop circle: px 3520–3648, Exit ramp: px 3648–3680
_HILLSIDE_LOOP_START_X = 3488.0
_HILLSIDE_LOOP_END_X = 3680.0
_HILLSIDE_SPINDASH_X = 3100.0
_HILLSIDE_SPINDASH_Y = 610.0


class TestHillsideLoopTraversal:
    """Audit: spindash through the hillside stage loop.

    The hillside loop uses synthetic build_loop() geometry.
    Tests whether the stage loop is fully traversable.
    """

    @staticmethod
    def _build_and_run() -> LoopAuditResult:
        sim = create_sim("hillside")
        sim.player.physics.x = _HILLSIDE_SPINDASH_X
        sim.player.physics.y = _HILLSIDE_SPINDASH_Y
        return _run_loop_audit(sim, _spindash_strategy(), frames=600)

    @pytest.mark.xfail(strict=True,
        reason="Hillside terrain launches player high over loop — lands at low "
        "speed and gets stuck orbiting (pre-existing physics/level issue)",
    )
    def test_all_quadrants_grounded(self) -> None:
        """Hillside loop must be fully traversed on_ground AND player must exit."""
        result = self._build_and_run()
        grounded = result.grounded_quadrants
        assert grounded == {0, 1, 2, 3}, _format_diagnostic(
            result, _HILLSIDE_LOOP_START_X, _HILLSIDE_LOOP_END_X,
            label="hillside — incomplete quadrant coverage",
        )
        assert result.player_exits_loop(_HILLSIDE_LOOP_END_X), _format_diagnostic(
            result, _HILLSIDE_LOOP_START_X, _HILLSIDE_LOOP_END_X,
            label="hillside — player stuck in loop",
        )

    @pytest.mark.xfail(strict=True,
        reason="Hillside terrain launches player high over loop — lands at low "
        "speed and gets stuck orbiting (pre-existing physics/level issue)",
    )
    def test_exits_loop_region(self) -> None:
        """Player should clear the loop region."""
        result = self._build_and_run()
        assert result.max_x > _HILLSIDE_LOOP_END_X, _format_diagnostic(
            result, _HILLSIDE_LOOP_START_X, _HILLSIDE_LOOP_END_X,
            label="hillside — didn't exit loop region",
        )

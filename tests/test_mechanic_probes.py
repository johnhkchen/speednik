"""Composable mechanic probe tests (T-012-06).

Tests game mechanics in isolation using synthetic grids from speednik/grids.py.
Each probe asks: "given ideal conditions, does this element work?"
Failures here are engine/physics bugs, not level design issues.

Mechanic Probes:
┌──────────────────┬──────────────────────────────────────────────────────┐
│ Probe            │ What it tests                                        │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Loop entry       │ Spindash through loop, all quadrants visited          │
│ Loop exit        │ Positive speed and on_ground after loop               │
│ Ramp entry       │ No wall-slam velocity zeroing on slope transitions    │
│ Gap clearable    │ Running jump clears N-tile gap                        │
│ Spring launch    │ Spring impulse, height gain, landing                  │
│ Slope adhesion   │ Player stays on_ground on angled surfaces             │
└──────────────────┴──────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from speednik.constants import GRAVITY, SPRING_UP_VELOCITY
from speednik.grids import build_flat, build_gap, build_loop, build_ramp, build_slope
from speednik.objects import Spring
from speednik.physics import InputState
from speednik.player import PlayerState
from speednik.simulation import (
    Event,
    SimState,
    SpringEvent,
    create_sim_from_lookup,
    sim_step,
)
from speednik.terrain import TILE_SIZE, TileLookup, get_quadrant


# ---------------------------------------------------------------------------
# Probe infrastructure
# ---------------------------------------------------------------------------

GROUND_ROW = 20
# Player center y for standing on GROUND_ROW surface.
# Ground surface top is at GROUND_ROW * TILE_SIZE. Collision resolution snaps the
# player so their bottom (center + height_radius) aligns with the surface.
# Using surface_y - 20 ensures the player starts on_ground after the first step.
GROUND_Y = GROUND_ROW * TILE_SIZE - 20


@dataclass
class FrameSnap:
    """Lightweight per-frame snapshot for probe assertions."""

    frame: int
    x: float
    y: float
    x_vel: float
    y_vel: float
    ground_speed: float
    angle: int
    on_ground: bool
    quadrant: int
    state: str


@dataclass
class ProbeResult:
    """Result of running a mechanic probe."""

    snaps: list[FrameSnap]
    events_per_frame: list[list[Event]]
    sim: SimState

    @property
    def all_events(self) -> list[Event]:
        return [e for frame_evts in self.events_per_frame for e in frame_evts]

    @property
    def quadrants_visited(self) -> set[int]:
        return {s.quadrant for s in self.snaps}

    @property
    def min_y(self) -> float:
        return min(s.y for s in self.snaps)

    @property
    def final(self) -> FrameSnap:
        return self.snaps[-1]


def _run_mechanic_probe(
    tile_lookup: TileLookup,
    start_x: float,
    start_y: float,
    strategy,
    frames: int = 300,
    *,
    springs: list[Spring] | None = None,
    level_width: int = 10000,
    level_height: int = 10000,
) -> ProbeResult:
    """Run a mechanic probe on a synthetic grid.

    Args:
        tile_lookup: TileLookup from a grid builder.
        start_x: Player starting X (pixels).
        start_y: Player starting Y (pixels).
        strategy: Callable (frame: int, sim: SimState) -> InputState.
        frames: Number of frames to simulate.
        springs: Optional list of Spring entities to inject.
        level_width: Level width in pixels.
        level_height: Level height in pixels.
    """
    sim = create_sim_from_lookup(
        tile_lookup, start_x, start_y,
        level_width=level_width, level_height=level_height,
    )
    if springs:
        sim.springs = list(springs)

    snaps: list[FrameSnap] = []
    events_per_frame: list[list[Event]] = []

    for frame in range(frames):
        inp = strategy(frame, sim)
        events = sim_step(sim, inp)
        p = sim.player.physics
        snaps.append(
            FrameSnap(
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
        )
        events_per_frame.append(events)

    return ProbeResult(snaps=snaps, events_per_frame=events_per_frame, sim=sim)


# ---------------------------------------------------------------------------
# Strategy helpers
# ---------------------------------------------------------------------------


def _hold_right(_frame: int, _sim: SimState) -> InputState:
    return InputState(right=True)


def _make_spindash_strategy():
    """Spindash then hold right; re-dash if speed drops."""
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


def _make_jump_right_strategy():
    """Hold right + jump on landing (not first frame — build speed first)."""
    state = {"was_airborne": False, "has_jumped": False}

    def strategy(frame: int, sim: SimState) -> InputState:
        on_ground = sim.player.physics.on_ground
        just_landed = state["was_airborne"] and on_ground
        state["was_airborne"] = not on_ground
        # Only jump after landing (not on frame 0 — need to build speed first)
        press = just_landed
        return InputState(right=True, jump_pressed=press, jump_held=True)

    return strategy


def _make_gap_jump_strategy(gap_edge_x: float):
    """Hold right to build speed, jump once near the gap edge.

    Releases jump_held after the initial press so JUMP_RELEASE_CAP applies,
    preventing the player from overflying the landing zone.
    """
    state = {"jumped": False}

    def strategy(frame: int, sim: SimState) -> InputState:
        p = sim.player.physics
        # Jump when approaching the gap edge and on ground
        if not state["jumped"] and p.on_ground and p.x > gap_edge_x - 30:
            state["jumped"] = True
            return InputState(right=True, jump_pressed=True, jump_held=True)
        # After jumping, just hold right (release jump for shorter arc)
        return InputState(right=True)

    return strategy


# ---------------------------------------------------------------------------
# Test: Loop entry and traversal
# ---------------------------------------------------------------------------


class TestLoopEntry:
    """Probe: spindash through a synthetic loop.

    Tests whether loops of varying radii can be entered and fully traversed
    at spindash speed. A full traversal visits all 4 quadrants (0-3).
    """

    @staticmethod
    def _build_and_run(radius: int) -> ProbeResult:
        ramp_radius = max(16, radius // 2)
        _, lookup = build_loop(
            approach_tiles=15, radius=radius,
            ground_row=GROUND_ROW, ramp_radius=ramp_radius,
        )
        start_x = 48.0  # a few tiles into the approach
        start_y = float(GROUND_Y)
        return _run_mechanic_probe(
            lookup, start_x, start_y,
            strategy=_make_spindash_strategy(), frames=600,
        )

    @pytest.mark.parametrize("radius", [
        pytest.param(32, marks=pytest.mark.xfail(strict=True,
            reason="r=32 too small for full grounded traversal (only 4 tiles wide)",
        ), id="r32"),
        pytest.param(48, id="r48"),
        pytest.param(64, id="r64"),
        pytest.param(96, id="r96"),
    ])
    def test_loop_traverses_all_quadrants(self, radius: int) -> None:
        """Loop should be fully traversable at spindash speed."""
        result = self._build_and_run(radius)
        visited = result.quadrants_visited
        assert visited == {0, 1, 2, 3}, (
            f"radius={radius}: visited quadrants {visited}, expected {{0,1,2,3}}"
        )

    @pytest.mark.parametrize("radius", [
        pytest.param(32, id="r32"),
        pytest.param(48, id="r48"),
        pytest.param(64, id="r64"),
        pytest.param(96, id="r96"),
    ])
    def test_loop_exit_positive_speed(self, radius: int) -> None:
        """After loop, player should have positive ground_speed."""
        result = self._build_and_run(radius)
        # Find frames past the loop region
        loop_end_x = float(15 * TILE_SIZE + max(16, radius // 2) + 2 * radius)
        post_loop = [s for s in result.snaps if s.x > loop_end_x and s.on_ground]
        assert len(post_loop) > 0, (
            f"radius={radius}: no on-ground frames past loop end x={loop_end_x:.0f}"
        )
        assert post_loop[0].ground_speed > 0, (
            f"radius={radius}: exit ground_speed={post_loop[0].ground_speed:.2f}"
        )

    @pytest.mark.parametrize("radius", [
        pytest.param(32, id="r32"),
        pytest.param(48, id="r48"),
        pytest.param(64, id="r64"),
        pytest.param(96, id="r96"),
    ])
    def test_loop_exit_on_ground(self, radius: int) -> None:
        """After loop, player should return to ground."""
        result = self._build_and_run(radius)
        loop_end_x = float(15 * TILE_SIZE + max(16, radius // 2) + 2 * radius)
        post_loop = [s for s in result.snaps if s.x > loop_end_x]
        any_on_ground = any(s.on_ground for s in post_loop)
        assert any_on_ground, (
            f"radius={radius}: player never on_ground past loop end x={loop_end_x:.0f}"
        )


# ---------------------------------------------------------------------------
# Test: Ramp entry
# ---------------------------------------------------------------------------


class TestRampEntry:
    """Probe: running onto a ramp should not zero velocity.

    Distinguishes 'slowed by slope physics' (gradual) from 'wall slam'
    (velocity drops from >1 to ~0 in a single frame).
    """

    @staticmethod
    def _build_and_run(end_angle: int) -> ProbeResult:
        _, lookup = build_ramp(
            approach_tiles=10, ramp_tiles=10,
            start_angle=0, end_angle=end_angle,
            ground_row=GROUND_ROW,
        )
        start_x = 48.0
        start_y = float(GROUND_Y)
        return _run_mechanic_probe(
            lookup, start_x, start_y,
            strategy=_make_spindash_strategy(), frames=300,
        )

    @pytest.mark.parametrize("end_angle", [10, 20, 30, 40, 50])
    def test_ramp_no_wall_slam(self, end_angle: int) -> None:
        """Running onto a ramp should not zero velocity in a single frame."""
        result = self._build_and_run(end_angle)
        ramp_start_x = 10 * TILE_SIZE
        ramp_end_x = 20 * TILE_SIZE
        ramp_snaps = [
            s for s in result.snaps
            if ramp_start_x < s.x < ramp_end_x and s.on_ground
        ]
        for i in range(1, len(ramp_snaps)):
            prev = ramp_snaps[i - 1]
            curr = ramp_snaps[i]
            if prev.ground_speed > 1.0 and abs(curr.ground_speed) < 0.01:
                pytest.fail(
                    f"end_angle={end_angle}: wall slam at frame {curr.frame} "
                    f"(x={curr.x:.1f}): {prev.ground_speed:.2f} -> "
                    f"{curr.ground_speed:.2f}"
                )

    @pytest.mark.parametrize("end_angle", [10, 20, 30, 40, 50])
    def test_ramp_player_advances(self, end_angle: int) -> None:
        """Player should advance past the ramp region."""
        result = self._build_and_run(end_angle)
        max_x = max(s.x for s in result.snaps)
        ramp_end_x = 20 * TILE_SIZE
        assert max_x > ramp_end_x, (
            f"end_angle={end_angle}: max_x={max_x:.1f}, "
            f"expected past ramp end at {ramp_end_x}"
        )


# ---------------------------------------------------------------------------
# Test: Gap clearable
# ---------------------------------------------------------------------------


class TestGapClearable:
    """Probe: a running jump should clear a gap of N tiles.

    Documents the maximum clearable gap. Small gaps (2-3) should always work.
    Larger gaps test the jump arc limits.
    """

    @staticmethod
    def _build_and_run(gap_tiles: int) -> ProbeResult:
        approach = 15
        landing = 30  # generous landing zone
        _, lookup = build_gap(
            approach_tiles=approach, gap_tiles=gap_tiles,
            landing_tiles=landing, ground_row=GROUND_ROW,
        )
        start_x = 48.0
        start_y = float(GROUND_Y)
        gap_edge_x = float(approach * TILE_SIZE)
        total_width = (approach + gap_tiles + landing) * TILE_SIZE + 100
        return _run_mechanic_probe(
            lookup, start_x, start_y,
            strategy=_make_gap_jump_strategy(gap_edge_x), frames=400,
            level_width=total_width, level_height=GROUND_ROW * TILE_SIZE + 200,
        )

    @pytest.mark.parametrize("gap_tiles", [2, 3, 4, 5])
    def test_gap_clearable_with_jump(self, gap_tiles: int) -> None:
        """A running jump should clear this gap and land on the other side."""
        result = self._build_and_run(gap_tiles)
        gap_end_x = float((15 + gap_tiles) * TILE_SIZE)
        # Check if player lands on ground past the gap
        landed_past_gap = any(
            s.on_ground and s.x > gap_end_x
            for s in result.snaps
        )
        assert landed_past_gap, (
            f"{gap_tiles}-tile gap: player never landed past gap end "
            f"at x={gap_end_x:.0f}"
        )


# ---------------------------------------------------------------------------
# Test: Spring launch
# ---------------------------------------------------------------------------


class TestSpringLaunch:
    """Probe: spring impulse, height gain, and landing.

    Places a spring on a flat synthetic grid and walks into it.
    Expected height gain: v^2 / (2*g) = 10^2 / (2*0.21875) = 228.6 px.
    """

    GRID_WIDTH = 200  # wide enough for player to land after spring arc
    SPRING_TX = 15  # tile column for spring

    @classmethod
    def _build_and_run(cls) -> ProbeResult:
        _, lookup = build_flat(cls.GRID_WIDTH, GROUND_ROW)
        spring_x = float(cls.SPRING_TX * TILE_SIZE + TILE_SIZE // 2)
        spring_y = float(GROUND_ROW * TILE_SIZE)
        spring = Spring(x=spring_x, y=spring_y, direction="up")
        start_x = 48.0
        start_y = float(GROUND_Y)
        return _run_mechanic_probe(
            lookup, start_x, start_y,
            strategy=_hold_right, frames=400,
            springs=[spring],
            level_width=cls.GRID_WIDTH * TILE_SIZE,
        )

    def test_spring_event_fires(self) -> None:
        """SpringEvent fires when player contacts the spring."""
        result = self._build_and_run()
        spring_events = [e for e in result.all_events if isinstance(e, SpringEvent)]
        assert len(spring_events) > 0, "No SpringEvent fired"

    def test_spring_reaches_expected_height(self) -> None:
        """Player reaches height consistent with SPRING_UP_VELOCITY impulse."""
        result = self._build_and_run()
        start_y = result.snaps[0].y
        # Expected: v^2/(2g) = 10^2 / (2*0.21875) ≈ 228.6 px
        expected_height = (SPRING_UP_VELOCITY ** 2) / (2 * GRAVITY)
        # Use generous tolerance (frame discretization + collision)
        assert result.min_y < start_y - expected_height * 0.7, (
            f"min_y={result.min_y:.1f}, start_y={start_y:.1f}, "
            f"expected at least {expected_height * 0.7:.0f}px height gain"
        )

    def test_spring_lands_on_ground(self) -> None:
        """Player lands back on ground after spring launch."""
        result = self._build_and_run()
        # Find frame where spring fires
        spring_frame = None
        for i, frame_events in enumerate(result.events_per_frame):
            if any(isinstance(e, SpringEvent) for e in frame_events):
                spring_frame = i
                break
        assert spring_frame is not None, "No SpringEvent to anchor landing check"
        # Check landing within 120 frames
        landed = False
        for s in result.snaps[spring_frame + 5 : spring_frame + 120]:
            if s.on_ground:
                landed = True
                break
        assert landed, (
            f"Player did not land within 120 frames of spring (frame {spring_frame})"
        )


# ---------------------------------------------------------------------------
# Test: Slope adhesion
# ---------------------------------------------------------------------------


class TestSlopeAdhesion:
    """Probe: player walking on a slope should stay on_ground.

    Sweeps through byte angles 0-45. Documents the angle where adhesion fails.
    """

    @staticmethod
    def _build_and_run(angle: int) -> ProbeResult:
        _, lookup = build_slope(
            approach_tiles=5, slope_tiles=15,
            angle=angle, ground_row=GROUND_ROW,
        )
        start_x = 48.0
        start_y = float(GROUND_Y)
        return _run_mechanic_probe(
            lookup, start_x, start_y,
            strategy=_hold_right, frames=300,
        )

    @pytest.mark.parametrize("angle", [
        pytest.param(a, id=f"a{a}")
        for a in range(0, 50, 5)
    ])
    def test_slope_stays_on_ground(self, angle: int) -> None:
        """Player should maintain ground contact while on the slope."""
        result = self._build_and_run(angle)
        slope_start_x = 5 * TILE_SIZE
        slope_end_x = 20 * TILE_SIZE
        slope_snaps = [
            s for s in result.snaps
            if slope_start_x < s.x < slope_end_x
        ]
        if not slope_snaps:
            pytest.skip(f"angle={angle}: player never reached slope region")
        # Count frames on ground in slope region
        on_ground_count = sum(1 for s in slope_snaps if s.on_ground)
        total = len(slope_snaps)
        ratio = on_ground_count / total if total > 0 else 0
        # At least 80% of frames in slope region should be on_ground
        assert ratio >= 0.8, (
            f"angle={angle}: on_ground {on_ground_count}/{total} "
            f"({ratio:.0%}) in slope region (expected >=80%)"
        )

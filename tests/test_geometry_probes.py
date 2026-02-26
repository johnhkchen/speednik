"""Geometric feature probe tests (T-011-03).

Targeted tests against specific geometric features in real stages.
Each probe places the player at known coordinates and asserts specific
physics outcomes for individual features.

Coordinate Reference (from stage entities.json and tile_map.json):
┌─────────────┬──────────────┬───────────────────────────────────────────┐
│ Feature     │ Stage        │ Coordinates (px)                          │
├─────────────┼──────────────┼───────────────────────────────────────────┤
│ Loop        │ hillside     │ tiles tx=217–233, px 3472–3744, ground≈610│
│ Spring (up) │ hillside     │ x=2380 y=612                              │
│ Checkpoint  │ hillside     │ x=1620 y=610                              │
│ Gap (2-tile)│ skybridge    │ tiles 27–28, px 432–464, y≈490            │
│ Ramp region │ hillside     │ x=1700–2100, rolling hills, angles 0–248  │
└─────────────┴──────────────┴───────────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from speednik.physics import InputState
from speednik.player import PlayerState
from speednik.simulation import (
    CheckpointEvent,
    Event,
    SimState,
    SpringEvent,
    create_sim,
    sim_step,
)
from speednik.terrain import get_quadrant


# ---------------------------------------------------------------------------
# Probe infrastructure
# ---------------------------------------------------------------------------


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
    """Result of running a geometry probe."""

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


def _run_probe(
    stage: str,
    start_x: float,
    start_y: float,
    strategy,
    frames: int = 300,
) -> ProbeResult:
    """Run a geometry probe: create sim, override position, step, collect data.

    Args:
        stage: Stage name ("hillside", "pipeworks", "skybridge").
        start_x: Override player X position.
        start_y: Override player Y position.
        strategy: Callable (frame: int, sim: SimState) -> InputState.
        frames: Number of frames to simulate.
    """
    sim = create_sim(stage)
    sim.player.physics.x = start_x
    sim.player.physics.y = start_y

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
# Strategy factories
# ---------------------------------------------------------------------------


def _hold_right(frame: int, sim: SimState) -> InputState:
    return InputState(right=True)


def _make_spindash_strategy():
    """Create a fresh spindash strategy with its own state."""
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


def _make_hold_right_jump_strategy():
    """Create a fresh hold-right-jump strategy with its own state."""
    state = {"was_airborne": False}

    def strategy(frame: int, sim: SimState) -> InputState:
        on_ground = sim.player.physics.on_ground
        just_landed = state["was_airborne"] and on_ground
        state["was_airborne"] = not on_ground
        press = (frame == 0 and on_ground) or just_landed
        return InputState(right=True, jump_pressed=press, jump_held=True)

    return strategy


# ---------------------------------------------------------------------------
# Test: Loop traversal (hillside)
# ---------------------------------------------------------------------------


class TestLoopTraversal:
    """Probe: spindash through the hillside loop region.

    Loop location: tiles tx=217–233 (px 3472–3744), with loop-type surface
    tiles spanning quadrants 0–3 in angle data. The loop entry ramp starts
    at ~px 3400 with increasing angles (0→35 byte-angle).

    At spindash speed, the player enters the loop ramp and hits quadrant 1
    (right-wall angles 33–96) before launching airborne over the loop.
    The player then lands past the loop exit and continues forward.
    """

    def _run(self) -> ProbeResult:
        # Hillside loop: tiles tx=217–233, px 3472–3744
        # Place player at x=3100 for longer spindash approach — player needs
        # multiple spindash cycles to build enough speed/momentum to clear
        # the loop ramp (the initial spindash gets deflected by the steep entry).
        return _run_probe(
            "hillside",
            start_x=3100.0,
            start_y=610.0,
            strategy=_make_spindash_strategy(),
            frames=600,
        )

    def test_enters_loop_quadrant(self) -> None:
        """Player reaches quadrant 1 (right-wall angle) on the loop entry ramp.

        The loop entry ramp has tiles with angles 34–47+ (quadrant 1).
        A spindash player should hit these surfaces before going airborne.
        """
        result = self._run()
        visited = result.quadrants_visited
        assert 1 in visited, (
            f"Expected quadrant 1 (loop ramp), visited {visited}"
        )

    def test_crosses_loop_region(self) -> None:
        """Player X crosses past the entire loop region (px 3744)."""
        result = self._run()
        max_x = max(s.x for s in result.snaps)
        # Loop ends at px 3744 (tile 233 * 16 + 16)
        assert max_x > 3744, (
            f"max_x={max_x:.1f}, expected to cross past loop exit at px 3744"
        )

    def test_exits_with_positive_speed(self) -> None:
        """Player exits the loop region moving right with positive x_vel."""
        result = self._run()
        # Find frames past the loop exit
        post_loop = [s for s in result.snaps if s.x > 3744]
        assert len(post_loop) > 0, "No frames past loop exit"
        assert post_loop[0].x_vel > 0, (
            f"x_vel={post_loop[0].x_vel:.2f} past loop exit (expected positive)"
        )

    def test_returns_to_ground_level(self) -> None:
        """Player Y after loop exit is approximately equal to Y before entry."""
        result = self._run()
        entry_y = result.snaps[0].y
        # Find first on-ground frame past loop exit
        post_loop = [s for s in result.snaps if s.x > 3744 and s.on_ground]
        assert len(post_loop) > 0, "Player never on ground past loop exit"
        exit_y = post_loop[0].y
        assert abs(exit_y - entry_y) < 40, (
            f"entry_y={entry_y:.1f}, exit_y={exit_y:.1f}, "
            f"diff={abs(exit_y - entry_y):.1f} (expected <40)"
        )


# ---------------------------------------------------------------------------
# Test: Spring launch (hillside)
# ---------------------------------------------------------------------------


class TestSpringLaunch:
    """Probe: spring launch on hillside.

    Spring location: spring_up at x=2380, y=612.
    Place player at x=2350, run right to trigger spring.
    """

    def _run(self) -> ProbeResult:
        # Hillside spring_up at x=2380, y=612
        # Start just left of spring
        return _run_probe(
            "hillside",
            start_x=2350.0,
            start_y=610.0,
            strategy=_hold_right,
            frames=200,
        )

    def test_spring_event_fires(self) -> None:
        """SpringEvent fires when player hits the spring."""
        result = self._run()
        spring_events = [e for e in result.all_events if isinstance(e, SpringEvent)]
        assert len(spring_events) > 0, "No SpringEvent fired"

    def test_gains_height(self) -> None:
        """Player gains significant height after spring launch."""
        result = self._run()
        start_y = result.snaps[0].y
        # Player should reach at least 50px above start (spring impulse is -10.0)
        assert result.min_y < start_y - 50, (
            f"min_y={result.min_y:.1f}, start_y={start_y:.1f}, "
            f"expected at least 50px height gain"
        )

    def test_lands_on_ground(self) -> None:
        """Player lands back on solid ground after spring launch."""
        result = self._run()
        # Find the frame where spring event fires
        spring_frame = None
        for i, frame_events in enumerate(result.events_per_frame):
            if any(isinstance(e, SpringEvent) for e in frame_events):
                spring_frame = i
                break
        assert spring_frame is not None, "No SpringEvent to anchor landing check"

        # Check that player lands within 120 frames of spring event
        landed = False
        for s in result.snaps[spring_frame:spring_frame + 120]:
            if s.on_ground and s.frame > spring_frame + 5:  # skip initial frames
                landed = True
                break
        assert landed, (
            f"Player did not land within 120 frames of spring event (frame {spring_frame})"
        )


# ---------------------------------------------------------------------------
# Test: Gap clearing (skybridge)
# ---------------------------------------------------------------------------


class TestGapClearing:
    """Probe: clear gaps in skybridge using hold_right_jump.

    Gap location: 2-tile gap at tiles 27–28 (px 432–464), platform y≈490.
    Player starts before the gap and jumps across.
    """

    def _run(self) -> ProbeResult:
        # Skybridge 2-tile gap at px 432–464, platform y≈490
        # Start at x=350 for approach run
        return _run_probe(
            "skybridge",
            start_x=350.0,
            start_y=490.0,
            strategy=_make_hold_right_jump_strategy(),
            frames=300,
        )

    def test_crosses_gap(self) -> None:
        """Player X crosses past the gap without dying."""
        result = self._run()
        # Gap ends at px 464 (tile 28 * 16 + 16)
        max_x = max(s.x for s in result.snaps)
        assert max_x > 480, (
            f"max_x={max_x:.1f}, expected to cross past gap at px 464"
        )
        assert not result.sim.player_dead, "Player died while crossing gap"

    def test_stays_above_death_threshold(self) -> None:
        """Player Y stays above the stage bottom (no falling to death)."""
        result = self._run()
        level_height = result.sim.level_height  # 896 for skybridge
        for s in result.snaps:
            assert s.y < level_height, (
                f"Player y={s.y:.1f} reached death threshold {level_height} "
                f"at frame {s.frame}"
            )


# ---------------------------------------------------------------------------
# Test: Ramp transitions (hillside)
# ---------------------------------------------------------------------------


class TestRampTransition:
    """Probe: ramp/slope transitions in hillside.

    Ramp region: the rolling hills between x=1700–2100 contain multiple
    slope transitions through angles 0, 8, 19, 27, 32, 224, 229, 240, 248.
    Player spindashes from x=1650 through this undulating terrain.
    """

    def _run(self) -> ProbeResult:
        # Hillside rolling hills: x=1700–2100 has varied slope angles
        # Spindash from x=1650 to have enough speed to power through
        return _run_probe(
            "hillside",
            start_x=1650.0,
            start_y=610.0,
            strategy=_make_spindash_strategy(),
            frames=200,
        )

    def test_no_velocity_zeroing(self) -> None:
        """Ground speed doesn't drop to zero on slope transitions (no wall slam)."""
        result = self._run()
        # Check on-ground frames in the ramp region (x=1700–2100)
        ramp_snaps = [s for s in result.snaps if 1700 < s.x < 2100 and s.on_ground]
        assert len(ramp_snaps) > 0, "No on-ground frames in ramp region"

        for i in range(1, len(ramp_snaps)):
            prev = ramp_snaps[i - 1]
            curr = ramp_snaps[i]
            # If player had meaningful speed and it dropped to 0, that's a wall slam
            if prev.ground_speed > 1.0 and abs(curr.ground_speed) < 0.01:
                assert False, (
                    f"Velocity zeroed at frame {curr.frame} (x={curr.x:.1f}): "
                    f"prev_speed={prev.ground_speed:.2f} -> "
                    f"curr_speed={curr.ground_speed:.2f}"
                )

    def test_smooth_angle_changes(self) -> None:
        """Angle changes between consecutive on-ground frames are gradual."""
        result = self._run()
        ramp_snaps = [s for s in result.snaps if 1700 < s.x < 2100 and s.on_ground]
        assert len(ramp_snaps) > 1, "Not enough on-ground frames in ramp region"

        max_angle_delta = 0
        for i in range(1, len(ramp_snaps)):
            prev = ramp_snaps[i - 1]
            curr = ramp_snaps[i]
            # Compute smallest angle difference (handle wraparound at 256)
            diff = abs(curr.angle - prev.angle)
            diff = min(diff, 256 - diff)
            max_angle_delta = max(max_angle_delta, diff)

        # 30 byte-angles ~= 42 degrees per frame — generous but catches major jumps
        assert max_angle_delta <= 30, (
            f"Max angle change between frames: {max_angle_delta} byte-angles "
            f"(expected <=30)"
        )


# ---------------------------------------------------------------------------
# Test: Checkpoint activation (hillside)
# ---------------------------------------------------------------------------


class TestCheckpointActivation:
    """Probe: checkpoint activation in hillside.

    Checkpoint location: x=1620, y=610.
    Player starts at x=1550 and runs right through the checkpoint.
    """

    def _run(self) -> ProbeResult:
        # Hillside checkpoint at x=1620, y=610
        # Start at x=1400 with spindash to reach checkpoint with enough speed
        # (terrain between 1550-1620 has slight uphill that stalls hold_right)
        return _run_probe(
            "hillside",
            start_x=1400.0,
            start_y=610.0,
            strategy=_make_spindash_strategy(),
            frames=200,
        )

    def test_checkpoint_event_fires(self) -> None:
        """CheckpointEvent fires when player reaches the checkpoint."""
        result = self._run()
        checkpoint_events = [
            e for e in result.all_events if isinstance(e, CheckpointEvent)
        ]
        assert len(checkpoint_events) > 0, "No CheckpointEvent fired"

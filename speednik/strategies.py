"""speednik/strategies.py — Strategy primitives and scenario runner.

Provides a Pyxel-free simulation loop that feeds inputs frame-by-frame via a strategy
function and returns a trajectory log. Used by the test suite and dev park visualization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from speednik.level import load_stage
from speednik.physics import InputState
from speednik.player import Player, PlayerState, create_player, player_update
from speednik.terrain import TileLookup, get_quadrant


# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

Strategy = Callable[[int, Player], InputState]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FrameSnapshot:
    frame: int
    x: float
    y: float
    x_vel: float
    y_vel: float
    ground_speed: float
    angle: int
    on_ground: bool
    quadrant: int
    state: str  # PlayerState value


@dataclass
class ScenarioResult:
    snapshots: list[FrameSnapshot]
    player: Player  # final player object

    @property
    def final(self) -> FrameSnapshot:
        return self.snapshots[-1]

    @property
    def max_x(self) -> float:
        return max(s.x for s in self.snapshots)

    @property
    def quadrants_visited(self) -> set[int]:
        return {s.quadrant for s in self.snapshots}

    def stuck_at(self, tolerance: float = 2.0, window: int = 30) -> float | None:
        """Return X where player was stuck, or None if they kept moving.

        Scans with a sliding window. If max(x) - min(x) < tolerance within any
        window of frames, returns the average X of that window.
        """
        if len(self.snapshots) < window:
            return None
        for i in range(len(self.snapshots) - window + 1):
            xs = [s.x for s in self.snapshots[i : i + window]]
            if max(xs) - min(xs) < tolerance:
                return sum(xs) / len(xs)
        return None


# ---------------------------------------------------------------------------
# Snapshot capture
# ---------------------------------------------------------------------------

def _capture_snapshot(frame: int, player: Player) -> FrameSnapshot:
    p = player.physics
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
        state=player.state.value,
    )


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------

def run_scenario(
    tile_lookup: TileLookup,
    start_x: float,
    start_y: float,
    strategy: Strategy,
    frames: int = 600,
    *,
    on_ground: bool = True,
) -> ScenarioResult:
    """Run a scenario: place player, feed inputs, return trajectory.

    Args:
        tile_lookup: Collision lookup function.
        start_x: Player starting X position (pixels).
        start_y: Player starting Y position (pixels).
        strategy: Callable (frame, player) -> InputState.
        frames: Number of frames to simulate.
        on_ground: Whether player starts on ground (default True).

    Returns:
        ScenarioResult with per-frame snapshots and final Player.
    """
    player = create_player(start_x, start_y)
    if not on_ground:
        player.physics.on_ground = False

    snapshots: list[FrameSnapshot] = []
    for frame in range(frames):
        inp = strategy(frame, player)
        player_update(player, inp, tile_lookup)
        snapshots.append(_capture_snapshot(frame, player))

    return ScenarioResult(snapshots=snapshots, player=player)


def run_on_stage(
    stage_name: str,
    strategy: Strategy,
    frames: int = 600,
) -> ScenarioResult:
    """Load a real stage and run from player_start.

    Args:
        stage_name: One of "hillside", "pipeworks", "skybridge".
        strategy: Callable (frame, player) -> InputState.
        frames: Number of frames to simulate.

    Returns:
        ScenarioResult with per-frame snapshots and final Player.
    """
    stage = load_stage(stage_name)
    sx, sy = stage.player_start
    return run_scenario(stage.tile_lookup, sx, sy, strategy, frames)


# ---------------------------------------------------------------------------
# Strategy factories
# ---------------------------------------------------------------------------

def idle() -> Strategy:
    """Strategy: do nothing every frame. Tests ground adhesion."""
    def strategy(frame: int, player: Player) -> InputState:
        return InputState()
    return strategy


def hold_right() -> Strategy:
    """Strategy: hold right every frame. The baseline 'beginner player'."""
    def strategy(frame: int, player: Player) -> InputState:
        return InputState(right=True)
    return strategy


def hold_left() -> Strategy:
    """Strategy: hold left every frame. Tests left-edge boundary escape."""
    def strategy(frame: int, player: Player) -> InputState:
        return InputState(left=True)
    return strategy


def hold_right_jump() -> Strategy:
    """Strategy: hold right + jump. Press jump on first frame and re-press after landing.

    Models the 'spam jump' player: jump is pressed once, held indefinitely,
    and re-pressed after each landing.
    """
    was_airborne = [False]

    def strategy(frame: int, player: Player) -> InputState:
        on_ground = player.physics.on_ground
        just_landed = was_airborne[0] and on_ground
        was_airborne[0] = not on_ground

        # Press jump on first frame or after landing
        press = (frame == 0 and on_ground) or just_landed
        return InputState(
            right=True,
            jump_pressed=press,
            jump_held=True,
        )

    return strategy


def spindash_right(
    charge_frames: int = 3,
    redash_threshold: float = 2.0,
) -> Strategy:
    """Strategy: charge spindash, release, hold right, re-dash when slow.

    State machine: CROUCH -> CHARGE -> RELEASE -> RUN -> (repeat).
    Models the 'power player' who spindashes through obstacles.
    """
    CROUCH, CHARGE, RELEASE, RUN = 0, 1, 2, 3
    phase = [CROUCH]
    counter = [0]

    def strategy(frame: int, player: Player) -> InputState:
        p = phase[0]

        if p == CROUCH:
            # Hold down for 1 frame to enter SPINDASH state
            phase[0] = CHARGE
            counter[0] = 0
            return InputState(down_held=True)

        if p == CHARGE:
            counter[0] += 1
            if counter[0] >= charge_frames:
                phase[0] = RELEASE
            return InputState(down_held=True, jump_pressed=True, jump_held=True)

        if p == RELEASE:
            # Release down to launch spindash
            phase[0] = RUN
            return InputState(right=True)

        # RUN phase
        if (
            player.physics.on_ground
            and abs(player.physics.ground_speed) < redash_threshold
            and player.state != PlayerState.SPINDASH
        ):
            # Speed dropped — re-spindash
            phase[0] = CROUCH
            return InputState(down_held=True)

        return InputState(right=True)

    return strategy


def scripted(
    timeline: list[tuple[int, int, InputState]],
) -> Strategy:
    """Strategy: frame-windowed input playback.

    Args:
        timeline: List of (start_frame, end_frame, InputState) tuples.
            Returns the InputState for the first matching window.
            Frames outside any window get empty InputState.

    Returns:
        Strategy callable.
    """
    def strategy(frame: int, player: Player) -> InputState:
        for start, end, inp in timeline:
            if start <= frame < end:
                return inp
        return InputState()

    return strategy

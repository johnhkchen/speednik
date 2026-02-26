"""Camera stability integration tests (T-011-04).

Run real stages with strategies, track camera alongside simulation, and assert
smooth, bounded camera behavior: no oscillation, no extreme jumps, level bounds
respected, and player always visible on screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest

from speednik.camera import Camera, camera_update, create_camera
from speednik.constants import (
    CAMERA_H_SCROLL_CAP,
    CAMERA_V_SCROLL_AIR,
    CAMERA_V_SCROLL_GROUND_FAST,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from speednik.physics import InputState
from speednik.simulation import create_sim, sim_step
from tests.harness import Strategy, hold_right, spindash_right


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CameraSnapshot:
    frame: int
    cam_x: float
    cam_y: float
    player_x: float
    player_y: float
    player_dead: bool


@dataclass
class CameraTrajectory:
    snapshots: list[CameraSnapshot]
    level_width: int
    level_height: int


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_with_camera(
    stage: str,
    strategy_factory: Callable[[], Strategy],
    frames: int,
) -> CameraTrajectory:
    """Run a full sim + camera loop and record trajectory."""
    sim = create_sim(stage)
    p = sim.player
    camera = create_camera(sim.level_width, sim.level_height, p.physics.x, p.physics.y)
    strategy = strategy_factory()

    snapshots: list[CameraSnapshot] = []
    for frame in range(frames):
        inp = strategy(frame, sim.player)
        sim_step(sim, inp)
        camera_update(camera, sim.player, inp)
        snapshots.append(CameraSnapshot(
            frame=frame,
            cam_x=camera.x,
            cam_y=camera.y,
            player_x=sim.player.physics.x,
            player_y=sim.player.physics.y,
            player_dead=sim.player_dead,
        ))

    return CameraTrajectory(
        snapshots=snapshots,
        level_width=sim.level_width,
        level_height=sim.level_height,
    )


# ---------------------------------------------------------------------------
# Trajectory cache
# ---------------------------------------------------------------------------

_TRAJECTORY_CACHE: dict[tuple[str, str], CameraTrajectory] = {}

STAGES = {
    "hillside": {"frames": 4000},
    "pipeworks": {"frames": 5000},
    "skybridge": {"frames": 6000},
}

STRATEGIES: dict[str, Callable[[], Strategy]] = {
    "hold_right": hold_right,
    "spindash_right": spindash_right,
}


def get_trajectory(stage: str, strategy_name: str) -> CameraTrajectory:
    key = (stage, strategy_name)
    if key not in _TRAJECTORY_CACHE:
        factory = STRATEGIES[strategy_name]
        frames = STAGES[stage]["frames"]
        _TRAJECTORY_CACHE[key] = run_with_camera(stage, factory, frames)
    return _TRAJECTORY_CACHE[key]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OSCILLATION_WINDOW = 10
OSCILLATION_MAX_FLIPS = 5
DELTA_MARGIN = 1.0

ALL_STAGES = list(STAGES.keys())
ALL_STRATEGIES = list(STRATEGIES.keys())


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------

def _sign_flips_in_window(signs: list[int | None]) -> int:
    """Count sign changes in a window, ignoring None (stationary) entries."""
    flips = 0
    prev_sign = None
    for s in signs:
        if s is None:
            continue
        if prev_sign is not None and s != prev_sign:
            flips += 1
        prev_sign = s
    return flips


def _compute_signs(deltas: list[float]) -> list[int | None]:
    """Map deltas to +1/-1/None (positive/negative/zero)."""
    signs: list[int | None] = []
    for d in deltas:
        if d > 0:
            signs.append(1)
        elif d < 0:
            signs.append(-1)
        else:
            signs.append(None)
    return signs


def check_oscillation(
    traj: CameraTrajectory,
    axis: str,
) -> list[int]:
    """Return frames where camera oscillation is detected (sign-flip counting).

    Scans a sliding window of OSCILLATION_WINDOW frames. If the sign of the
    camera delta flips more than OSCILLATION_MAX_FLIPS times within any window,
    returns the starting frame of that window.

    Zero-delta frames are skipped (camera stationary in dead zone).

    Windows where the player position itself is oscillating on the same axis
    are excluded — when the camera faithfully tracks a physically bouncing
    player, that is expected behavior, not a camera bug.
    """
    snaps = traj.snapshots
    if len(snaps) < 2:
        return []

    # Compute camera deltas and player deltas
    cam_deltas: list[float] = []
    player_deltas: list[float] = []
    for i in range(1, len(snaps)):
        if axis == "x":
            cam_deltas.append(snaps[i].cam_x - snaps[i - 1].cam_x)
            player_deltas.append(snaps[i].player_x - snaps[i - 1].player_x)
        else:
            cam_deltas.append(snaps[i].cam_y - snaps[i - 1].cam_y)
            player_deltas.append(snaps[i].player_y - snaps[i - 1].player_y)

    cam_signs = _compute_signs(cam_deltas)
    player_signs = _compute_signs(player_deltas)

    violations: list[int] = []
    w = OSCILLATION_WINDOW
    for start in range(len(cam_signs) - w + 1):
        cam_window = cam_signs[start : start + w]
        cam_flips = _sign_flips_in_window(cam_window)
        if cam_flips > OSCILLATION_MAX_FLIPS:
            # Check if player is also oscillating — if so, camera is just tracking
            player_window = player_signs[start : start + w]
            player_flips = _sign_flips_in_window(player_window)
            if player_flips > OSCILLATION_MAX_FLIPS:
                continue  # player-induced oscillation, not a camera bug
            violations.append(start + 1)  # +1 because deltas are offset by 1

    return violations


def check_delta_bounds(
    traj: CameraTrajectory,
) -> list[tuple[int, str, float]]:
    """Return (frame, axis, delta) for any frame exceeding scroll caps."""
    snaps = traj.snapshots
    max_dx = CAMERA_H_SCROLL_CAP + DELTA_MARGIN
    max_dy = max(CAMERA_V_SCROLL_GROUND_FAST, CAMERA_V_SCROLL_AIR) + DELTA_MARGIN
    violations: list[tuple[int, str, float]] = []

    for i in range(1, len(snaps)):
        dx = abs(snaps[i].cam_x - snaps[i - 1].cam_x)
        dy = abs(snaps[i].cam_y - snaps[i - 1].cam_y)
        if dx > max_dx:
            violations.append((snaps[i].frame, "x", dx))
        if dy > max_dy:
            violations.append((snaps[i].frame, "y", dy))

    return violations


def check_level_bounds(
    traj: CameraTrajectory,
) -> list[tuple[int, str, float]]:
    """Return (frame, axis, value) for any frame where camera exceeds level bounds."""
    max_x = traj.level_width - SCREEN_WIDTH
    max_y = traj.level_height - SCREEN_HEIGHT
    violations: list[tuple[int, str, float]] = []

    for snap in traj.snapshots:
        if snap.cam_x < -0.01:
            violations.append((snap.frame, "x_min", snap.cam_x))
        if snap.cam_x > max_x + 0.01:
            violations.append((snap.frame, "x_max", snap.cam_x))
        if snap.cam_y < -0.01:
            violations.append((snap.frame, "y_min", snap.cam_y))
        if snap.cam_y > max_y + 0.01:
            violations.append((snap.frame, "y_max", snap.cam_y))

    return violations


def check_player_visible(
    traj: CameraTrajectory,
) -> list[tuple[int, str]]:
    """Return (frame, axis) for any frame where the player is off-screen.

    Skips frames where:
    - player_dead is True (death animation may move player off-screen)
    - player is outside the level bounds (falling off-map before death triggers)
    """
    violations: list[tuple[int, str]] = []

    for snap in traj.snapshots:
        if snap.player_dead:
            continue
        # Player outside level bounds — about to die, camera can't follow
        if (
            snap.player_x < 0
            or snap.player_x > traj.level_width
            or snap.player_y < 0
            or snap.player_y > traj.level_height
        ):
            continue
        if snap.player_x < snap.cam_x or snap.player_x > snap.cam_x + SCREEN_WIDTH:
            violations.append((snap.frame, "x"))
        if snap.player_y < snap.cam_y or snap.player_y > snap.cam_y + SCREEN_HEIGHT:
            violations.append((snap.frame, "y"))

    return violations


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stage", ALL_STAGES)
@pytest.mark.parametrize("strategy", ALL_STRATEGIES)
class TestNoOscillation:
    """Camera should not wobble (rapid direction reversals) on any stage."""

    def test_no_horizontal_oscillation(self, stage: str, strategy: str) -> None:
        traj = get_trajectory(stage, strategy)
        violations = check_oscillation(traj, "x")
        assert not violations, (
            f"Horizontal oscillation on {stage}/{strategy} at frames: "
            f"{violations[:10]}"
        )

    def test_no_vertical_oscillation(self, stage: str, strategy: str) -> None:
        traj = get_trajectory(stage, strategy)
        violations = check_oscillation(traj, "y")
        assert not violations, (
            f"Vertical oscillation on {stage}/{strategy} at frames: "
            f"{violations[:10]}"
        )


@pytest.mark.parametrize("stage", ALL_STAGES)
@pytest.mark.parametrize("strategy", ALL_STRATEGIES)
class TestNoDeltaSpike:
    """No single-frame camera delta should exceed the max scroll speed + margin."""

    def test_no_extreme_camera_jumps(self, stage: str, strategy: str) -> None:
        traj = get_trajectory(stage, strategy)
        violations = check_delta_bounds(traj)
        assert not violations, (
            f"Delta spike on {stage}/{strategy}: "
            f"{violations[:10]}"
        )


@pytest.mark.parametrize("stage", ALL_STAGES)
@pytest.mark.parametrize("strategy", ALL_STRATEGIES)
class TestBoundsRespected:
    """Camera should never exceed level boundaries."""

    def test_camera_within_level_bounds(self, stage: str, strategy: str) -> None:
        traj = get_trajectory(stage, strategy)
        violations = check_level_bounds(traj)
        assert not violations, (
            f"Bounds violation on {stage}/{strategy}: "
            f"{violations[:10]}"
        )


@pytest.mark.parametrize("stage", ALL_STAGES)
@pytest.mark.parametrize("strategy", ALL_STRATEGIES)
class TestPlayerVisible:
    """Player should always be visible on screen (except during death)."""

    def test_player_on_screen(self, stage: str, strategy: str) -> None:
        traj = get_trajectory(stage, strategy)
        violations = check_player_visible(traj)
        assert not violations, (
            f"Player off-screen on {stage}/{strategy}: "
            f"{violations[:10]}"
        )

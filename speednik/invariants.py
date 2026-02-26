"""speednik/invariants.py — Physics invariant checker for simulation trajectories.

Scans a recorded trajectory (list of snapshots + events) and flags impossible
physics states. This is a library module — tests import it and assert on results.
No Pyxel imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, Sequence, runtime_checkable

from speednik.simulation import SimState, SpringEvent
from speednik.terrain import FULL, SURFACE_LOOP, TILE_SIZE

if TYPE_CHECKING:
    from speednik.simulation import Event

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_VEL = 20.0
"""Sane maximum for |x_vel| or |y_vel| — well beyond spindash top speed."""

SPIKE_THRESHOLD = 12.0
"""Max per-axis velocity change in one frame without excusal."""

POSITION_MARGIN = 64
"""Pixels beyond level boundary before flagging out-of-bounds."""

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SnapshotLike(Protocol):
    """Minimal interface for frame snapshots accepted by the checker."""

    frame: int
    x: float
    y: float
    x_vel: float
    y_vel: float
    on_ground: bool
    quadrant: int
    state: str


# ---------------------------------------------------------------------------
# Violation
# ---------------------------------------------------------------------------


@dataclass
class Violation:
    """A single physics invariant violation."""

    frame: int
    invariant: str
    details: str
    severity: str  # "error" or "warning"


# ---------------------------------------------------------------------------
# Individual checkers
# ---------------------------------------------------------------------------


def _check_position_bounds(
    sim: SimState,
    snapshots: Sequence[SnapshotLike],
) -> list[Violation]:
    violations: list[Violation] = []
    for snap in snapshots:
        if snap.x < 0:
            violations.append(Violation(
                frame=snap.frame,
                invariant="position_x_negative",
                details=f"Player X={snap.x:.1f} is negative",
                severity="error",
            ))
        if snap.y > sim.level_height + POSITION_MARGIN:
            violations.append(Violation(
                frame=snap.frame,
                invariant="position_y_below_world",
                details=(
                    f"Player Y={snap.y:.1f} exceeds "
                    f"level_height+{POSITION_MARGIN} "
                    f"({sim.level_height + POSITION_MARGIN})"
                ),
                severity="error",
            ))
        if snap.x > sim.level_width + POSITION_MARGIN:
            violations.append(Violation(
                frame=snap.frame,
                invariant="position_x_beyond_right",
                details=(
                    f"Player X={snap.x:.1f} exceeds "
                    f"level_width+{POSITION_MARGIN} "
                    f"({sim.level_width + POSITION_MARGIN})"
                ),
                severity="error",
            ))
    return violations


def _check_inside_solid(
    sim: SimState,
    snapshots: Sequence[SnapshotLike],
) -> list[Violation]:
    violations: list[Violation] = []
    for snap in snapshots:
        tx = int(snap.x) // TILE_SIZE
        ty = int(snap.y) // TILE_SIZE
        col = int(snap.x) % TILE_SIZE
        tile = sim.tile_lookup(tx, ty)
        if tile is not None and tile.solidity == FULL and tile.tile_type != SURFACE_LOOP:
            height = tile.height_array[col]
            solid_top = (ty + 1) * TILE_SIZE - height
            if snap.y >= solid_top:
                violations.append(Violation(
                    frame=snap.frame,
                    invariant="inside_solid_tile",
                    details=(
                        f"Player center ({snap.x:.1f}, {snap.y:.1f}) "
                        f"is inside solid tile at ({tx}, {ty})"
                    ),
                    severity="error",
                ))
    return violations


def _check_velocity_limits(
    snapshots: Sequence[SnapshotLike],
) -> list[Violation]:
    violations: list[Violation] = []
    for snap in snapshots:
        if abs(snap.x_vel) > MAX_VEL:
            violations.append(Violation(
                frame=snap.frame,
                invariant="velocity_x_exceeds_max",
                details=f"|x_vel|={abs(snap.x_vel):.1f} exceeds {MAX_VEL}",
                severity="error",
            ))
        if abs(snap.y_vel) > MAX_VEL:
            violations.append(Violation(
                frame=snap.frame,
                invariant="velocity_y_exceeds_max",
                details=f"|y_vel|={abs(snap.y_vel):.1f} exceeds {MAX_VEL}",
                severity="error",
            ))
    return violations


def _check_velocity_spikes(
    snapshots: Sequence[SnapshotLike],
    events_per_frame: Sequence[Sequence[Event]],
) -> list[Violation]:
    violations: list[Violation] = []
    for i in range(1, len(snapshots)):
        prev = snapshots[i - 1]
        curr = snapshots[i]
        dx = abs(curr.x_vel - prev.x_vel)
        dy = abs(curr.y_vel - prev.y_vel)

        if dx <= SPIKE_THRESHOLD and dy <= SPIKE_THRESHOLD:
            continue

        # Check excusals: SpringEvent this frame
        frame_events = events_per_frame[i] if i < len(events_per_frame) else []
        has_spring = any(isinstance(e, SpringEvent) for e in frame_events)
        if has_spring:
            continue

        # Excusal: spindash release (prev was spindash, curr is not)
        if prev.state == "spindash" and curr.state != "spindash":
            continue

        axis = "x" if dx > SPIKE_THRESHOLD else "y"
        delta = dx if dx > SPIKE_THRESHOLD else dy
        violations.append(Violation(
            frame=curr.frame,
            invariant="velocity_spike",
            details=(
                f"|delta_{axis}_vel|={delta:.1f} exceeds "
                f"{SPIKE_THRESHOLD} without excusal"
            ),
            severity="warning",
        ))
    return violations


def _check_ground_consistency(
    sim: SimState,
    snapshots: Sequence[SnapshotLike],
) -> list[Violation]:
    from speednik.constants import STANDING_HEIGHT_RADIUS

    violations: list[Violation] = []
    for snap in snapshots:
        if not snap.on_ground:
            continue
        # Check tile at player's feet (below center by height radius)
        feet_y = snap.y + STANDING_HEIGHT_RADIUS
        tx = int(snap.x) // TILE_SIZE
        ty = int(feet_y) // TILE_SIZE
        tile = sim.tile_lookup(tx, ty)
        if tile is None:
            violations.append(Violation(
                frame=snap.frame,
                invariant="on_ground_no_surface",
                details=(
                    f"on_ground=True but no tile at feet "
                    f"({snap.x:.1f}, {feet_y:.1f}) -> tile ({tx}, {ty})"
                ),
                severity="warning",
            ))
    return violations


def _check_quadrant_jumps(
    snapshots: Sequence[SnapshotLike],
) -> list[Violation]:
    violations: list[Violation] = []
    for i in range(1, len(snapshots)):
        prev_q = snapshots[i - 1].quadrant
        curr_q = snapshots[i].quadrant
        if prev_q == curr_q:
            continue
        # Compute shortest distance on the cyclic 0-1-2-3-0 ring
        diff = abs(curr_q - prev_q)
        if diff == 2:
            violations.append(Violation(
                frame=snapshots[i].frame,
                invariant="quadrant_diagonal_jump",
                details=(
                    f"Quadrant jumped from {prev_q} to {curr_q} "
                    f"(skipped intermediate)"
                ),
                severity="warning",
            ))
    return violations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_invariants(
    sim: SimState,
    snapshots: Sequence[SnapshotLike],
    events_per_frame: Sequence[Sequence[Event]],
) -> list[Violation]:
    """Scan a trajectory for physics invariant violations.

    Args:
        sim: The simulation state (for tile_lookup, level dimensions).
        snapshots: Per-frame snapshot list.
        events_per_frame: Per-frame event lists (parallel to snapshots).

    Returns:
        List of Violation objects, sorted by frame number.
    """
    violations: list[Violation] = []
    violations.extend(_check_position_bounds(sim, snapshots))
    violations.extend(_check_inside_solid(sim, snapshots))
    violations.extend(_check_velocity_limits(snapshots))
    violations.extend(_check_velocity_spikes(snapshots, events_per_frame))
    violations.extend(_check_ground_consistency(sim, snapshots))
    violations.extend(_check_quadrant_jumps(snapshots))
    violations.sort(key=lambda v: v.frame)
    return violations

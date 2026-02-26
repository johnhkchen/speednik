"""speednik/scenarios/conditions — Condition dataclasses and runtime checker."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from speednik.simulation import SimState

VALID_SUCCESS_TYPES: frozenset[str] = frozenset(
    {
        "goal_reached",
        "position_x_gte",
        "position_y_lte",
        "alive_at_end",
        "rings_gte",
    }
)

VALID_FAILURE_TYPES: frozenset[str] = frozenset(
    {
        "player_dead",
        "stuck",
        "any",
    }
)


@dataclass
class SuccessCondition:
    type: str
    value: float | None = None
    min_speed: float | None = None


@dataclass
class FailureCondition:
    type: str
    tolerance: float | None = None
    window: int | None = None
    conditions: list[FailureCondition] | None = None


@dataclass
class StartOverride:
    x: float
    y: float


# ---------------------------------------------------------------------------
# Runtime condition checking
# ---------------------------------------------------------------------------


def _check_success(
    cond: SuccessCondition,
    sim: SimState,
    trajectory: list,
    frame: int,
    max_frames: int,
) -> tuple[bool | None, str | None]:
    """Evaluate a single success condition.

    Returns ``(True, reason)`` if the condition fires, ``(None, None)`` otherwise.
    """
    if cond.type == "goal_reached":
        if sim.goal_reached:
            return True, "goal_reached"

    elif cond.type == "position_x_gte":
        if sim.player.physics.x >= cond.value:
            if cond.min_speed is not None:
                if abs(sim.player.physics.ground_speed) < cond.min_speed:
                    return None, None
            return True, "position_x_gte"

    elif cond.type == "position_y_lte":
        if sim.player.physics.y <= cond.value:
            return True, "position_y_lte"

    elif cond.type == "alive_at_end":
        if frame >= max_frames - 1 and not sim.player_dead:
            return True, "alive_at_end"

    elif cond.type == "rings_gte":
        if sim.rings_collected >= cond.value:
            return True, "rings_gte"

    return None, None


def _check_failure(
    cond: FailureCondition,
    sim: SimState,
    trajectory: list,
    frame: int,
) -> tuple[bool | None, str | None]:
    """Evaluate a single failure condition.

    Returns ``(False, reason)`` if the condition fires, ``(None, None)`` otherwise.
    """
    if cond.type == "player_dead":
        if sim.player_dead:
            return False, "player_dead"

    elif cond.type == "stuck":
        window = cond.window or 120
        tolerance = cond.tolerance or 2.0
        if len(trajectory) >= window:
            recent = trajectory[-window:]
            xs = [r.x for r in recent]
            spread = max(xs) - min(xs)
            if spread < tolerance:
                return False, "stuck"

    elif cond.type == "any":
        if cond.conditions:
            for sub in cond.conditions:
                result, reason = _check_failure(sub, sim, trajectory, frame)
                if result is not None:
                    return result, reason

    return None, None


def check_conditions(
    success: SuccessCondition,
    failure: FailureCondition,
    sim: SimState,
    trajectory: list,
    frame: int,
    max_frames: int,
) -> tuple[bool | None, str | None]:
    """Check success and failure conditions for the current frame.

    Returns ``(True, reason)`` for success, ``(False, reason)`` for failure,
    or ``(None, None)`` if neither condition has triggered yet.
    """
    result, reason = _check_success(success, sim, trajectory, frame, max_frames)
    if result is not None:
        return result, reason

    result, reason = _check_failure(failure, sim, trajectory, frame)
    if result is not None:
        return result, reason

    return None, None

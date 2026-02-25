"""Elemental terrain tests — micro-scenarios on synthetic grids.

Each test isolates one mechanic, uses a single strategy, and makes a sharp
assertion. Together they define the mechanical boundaries of the physics engine.
"""

from __future__ import annotations

import pytest

from speednik.constants import STANDING_HEIGHT_RADIUS
from speednik.terrain import TILE_SIZE

from tests.grids import build_flat, build_gap, build_loop, build_slope
from tests.harness import (
    ScenarioResult,
    hold_right,
    hold_right_jump,
    idle,
    run_scenario,
    spindash_right,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GROUND_ROW = 10
LOOP_GROUND_ROW = 40
START_X = 48.0
FRAMES = 600

# Walkability boundary: the engine's slip threshold is byte angle 33 (~46°).
# Angles below this are walkable; angles at or above stall due to slope slip.
# WALKABLE_CEILING: guaranteed walkable (degrees).
# UNWALKABLE_FLOOR: guaranteed unwalkable (degrees).
WALKABLE_CEILING = 45
UNWALKABLE_FLOOR = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deg_to_byte(deg: float) -> int:
    """Convert degrees to byte angle (0-255)."""
    return round(deg * 256 / 360) % 256


def _start_y(ground_row: int) -> float:
    """Player start Y on a ground row (center of player above surface)."""
    return float(ground_row * TILE_SIZE) - STANDING_HEIGHT_RADIUS


def _diag(result: ScenarioResult, label: str) -> str:
    """Build a diagnostic string for assertion messages."""
    f = result.final
    stuck = result.stuck_at()
    return (
        f"{label} | x={f.x:.1f} y={f.y:.1f} gspd={f.ground_speed:.2f} "
        f"angle={f.angle} on_ground={f.on_ground} q={f.quadrant} "
        f"stuck_at={stuck}"
    )


# ===================================================================
# Ground Adhesion
# ===================================================================

def test_idle_on_flat():
    """Player on flat ground stays put for 600 frames."""
    _, lookup = build_flat(20, GROUND_ROW)
    sy = _start_y(GROUND_ROW)
    result = run_scenario(lookup, START_X, sy, idle(), FRAMES)

    assert all(s.on_ground for s in result.snapshots), _diag(result, "lost ground")
    assert result.final.y == pytest.approx(result.snapshots[0].y, abs=0.5), (
        _diag(result, "Y drift on flat")
    )


def test_idle_on_slope():
    """Player on a 20-degree slope stays on_ground (may slide, but no fall-through)."""
    angle = _deg_to_byte(20)
    _, lookup = build_slope(5, 15, angle, GROUND_ROW)
    sy = _start_y(GROUND_ROW)
    result = run_scenario(lookup, START_X, sy, idle(), FRAMES)

    assert all(s.on_ground for s in result.snapshots), _diag(result, "lost ground on slope")


def test_idle_on_tile_boundary():
    """Player exactly on a tile boundary stays grounded."""
    _, lookup = build_flat(20, GROUND_ROW)
    boundary_x = 5.0 * TILE_SIZE  # exactly on tile edge
    sy = _start_y(GROUND_ROW)
    result = run_scenario(lookup, boundary_x, sy, idle(), FRAMES)

    assert all(s.on_ground for s in result.snapshots), (
        _diag(result, "lost ground at boundary")
    )
    assert result.final.y == pytest.approx(result.snapshots[0].y, abs=0.5), (
        _diag(result, "Y drift at boundary")
    )


# ===================================================================
# Walkability Threshold
# ===================================================================

def test_walk_climbs_gentle_slope():
    """hold_right should climb a 20-degree slope without stalling."""
    angle = _deg_to_byte(20)
    _, lookup = build_slope(3, 40, angle, GROUND_ROW)
    sy = _start_y(GROUND_ROW)
    result = run_scenario(lookup, 24.0, sy, hold_right(), 400)

    assert result.stuck_at(tolerance=2.0, window=60) is None, (
        _diag(result, "stalled on 20° slope")
    )


def test_walk_stalls_on_steep_slope():
    """hold_right should stall on a 70-degree slope."""
    angle = _deg_to_byte(70)
    _, lookup = build_slope(3, 40, angle, GROUND_ROW)
    sy = _start_y(GROUND_ROW)
    result = run_scenario(lookup, 24.0, sy, hold_right(), 400)

    assert result.stuck_at(tolerance=2.0, window=60) is not None, (
        _diag(result, "did not stall on 70° slope")
    )


@pytest.mark.parametrize("angle_deg", range(0, 86, 5))
def test_walkability_sweep(angle_deg: int):
    """Sweep angles 0-85 to map the walkability threshold.

    The engine's walkability boundary is at byte angle 33 (~46°), which
    corresponds to SLIP_ANGLE_THRESHOLD. Below this, hold_right progresses;
    at or above, the player stalls due to slope slip.

    Angles <= WALKABLE_CEILING (45°) must be walkable.
    Angles >= UNWALKABLE_FLOOR (50°) must stall.
    Stops at 85° because 90° (byte 64) enters wall quadrant (Q1) where
    floor sensor behavior is fundamentally different.
    """
    angle = _deg_to_byte(angle_deg)
    _, lookup = build_slope(2, 50, angle, GROUND_ROW)
    sy = _start_y(GROUND_ROW)
    result = run_scenario(lookup, 16.0, sy, hold_right(), 600)

    stuck = result.stuck_at(tolerance=2.0, window=60)

    if angle_deg <= WALKABLE_CEILING:
        assert stuck is None, (
            _diag(result, f"should walk {angle_deg}° (byte {angle})")
        )
    elif angle_deg >= UNWALKABLE_FLOOR:
        assert stuck is not None, (
            _diag(result, f"should stall {angle_deg}° (byte {angle})")
        )
    # Transition zone (46-49°): no assertion — engine defines the boundary


# ===================================================================
# Speed Gates
# ===================================================================

def test_spindash_clears_steep_slope():
    """Spindash should clear a slope that walking cannot."""
    angle = _deg_to_byte(55)
    _, lookup = build_slope(5, 30, angle, GROUND_ROW)
    sy = _start_y(GROUND_ROW)
    result = run_scenario(lookup, START_X, sy, spindash_right(), FRAMES)

    slope_end_x = (5 + 30) * TILE_SIZE  # 560 px
    assert result.max_x > slope_end_x, _diag(result, "spindash didn't clear slope")


def test_walk_blocked_by_steep_slope():
    """Walking should not clear a steep slope that spindash can."""
    angle = _deg_to_byte(55)
    _, lookup = build_slope(5, 30, angle, GROUND_ROW)
    sy = _start_y(GROUND_ROW)
    result = run_scenario(lookup, START_X, sy, hold_right(), FRAMES)

    assert result.stuck_at(tolerance=2.0, window=60) is not None, (
        _diag(result, "walk should stall on 55° slope")
    )


# ===================================================================
# Loop Traversal
# ===================================================================

# Loop geometry constants (approach=10, radius=128, ramp_radius=128)
_LOOP_APPROACH = 10
_LOOP_RADIUS = 128
_LOOP_RAMP_RADIUS = 128
_LOOP_APPROACH_PX = _LOOP_APPROACH * TILE_SIZE         # 160
_LOOP_START_PX = _LOOP_APPROACH_PX + _LOOP_RAMP_RADIUS  # 288
_LOOP_END_PX = _LOOP_START_PX + 2 * _LOOP_RADIUS       # 544
_LOOP_EXIT_PX = _LOOP_END_PX + _LOOP_RAMP_RADIUS        # 672


def test_loop_ramps_provide_angle_transition():
    """Loop with entry ramps: spindash should enter the ramp angle range.

    The entry ramp generates tiles with angles in Q3 (161-223 byte range),
    providing the angle transition needed for loop traversal. This confirms
    that build_loop's ramp geometry creates a valid angle ramp.
    """
    _, lookup = build_loop(_LOOP_APPROACH, _LOOP_RADIUS, LOOP_GROUND_ROW,
                        ramp_radius=_LOOP_RAMP_RADIUS)
    sy = _start_y(LOOP_GROUND_ROW)
    result = run_scenario(lookup, START_X, sy, spindash_right(), FRAMES)

    assert 3 in result.quadrants_visited, (
        _diag(result, f"ramp should produce Q3 angles: {result.quadrants_visited}")
    )
    assert result.final.x > _LOOP_EXIT_PX, (
        _diag(result, "didn't exit loop area")
    )


def test_loop_no_ramps_no_angle_transition():
    """Loop without ramps: player never enters Q3 (no angle transition).

    This is the core S-007 bug: without entry ramps, the player's angle stays
    at 0 (Q0) and floor sensors never pick up the ascending loop surface.
    """
    _, lookup = build_loop(_LOOP_APPROACH, _LOOP_RADIUS, LOOP_GROUND_ROW,
                        ramp_radius=None)
    sy = _start_y(LOOP_GROUND_ROW)
    result = run_scenario(lookup, START_X, sy, spindash_right(), FRAMES)

    assert result.quadrants_visited == {0}, (
        _diag(result, f"expected Q0 only without ramps: {result.quadrants_visited}")
    )


def test_loop_walk_speed_less_progress():
    """Walking makes less progress through the loop area than spindash.

    Both strategies pass through on synthetic grids (no physical blocking),
    but spindash covers more distance, confirming speed matters.
    """
    _, lookup = build_loop(_LOOP_APPROACH, _LOOP_RADIUS, LOOP_GROUND_ROW,
                        ramp_radius=_LOOP_RAMP_RADIUS)
    sy = _start_y(LOOP_GROUND_ROW)

    spin_result = run_scenario(lookup, START_X, sy, spindash_right(), FRAMES)
    walk_result = run_scenario(lookup, START_X, sy, hold_right(), FRAMES)

    assert spin_result.final.x > walk_result.final.x, (
        _diag(walk_result, "walk should cover less distance than spindash")
    )


# ===================================================================
# Gap Clearing
# ===================================================================

@pytest.mark.parametrize(
    "gap_tiles,strategy_factory,should_clear",
    [
        (3, hold_right_jump, True),    # small gap (48px), jump clears
        (8, hold_right_jump, True),    # medium gap (128px), jump clears
        (25, hold_right_jump, False),  # huge gap (400px), too far for jump
        (4, spindash_right, True),     # small gap (64px), spindash rolls across
    ],
    ids=["small-jump", "medium-jump", "huge-jump-fail", "small-spindash"],
)
def test_gap_clearing(gap_tiles: int, strategy_factory, should_clear: bool):
    """Test gap clearing with different gap sizes and strategies."""
    approach = 30
    landing = 10
    _, lookup = build_gap(approach, gap_tiles, landing, GROUND_ROW)
    sy = _start_y(GROUND_ROW)
    strategy = strategy_factory()
    result = run_scenario(lookup, START_X, sy, strategy, FRAMES)

    landing_start_x = float((approach + gap_tiles) * TILE_SIZE)
    # "Cleared" means the player landed on the far side (on_ground past gap)
    landed_on_far_side = any(
        s.on_ground and s.x >= landing_start_x for s in result.snapshots
    )

    if should_clear:
        assert landed_on_far_side, (
            _diag(result, f"should clear {gap_tiles}-tile gap")
        )
    else:
        assert not landed_on_far_side, (
            _diag(result, f"should NOT clear {gap_tiles}-tile gap")
        )

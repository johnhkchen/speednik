"""tests/test_invariants.py — Unit tests for the physics invariant checker."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from speednik.invariants import Violation, check_invariants
from speednik.simulation import SimState, SpringEvent, create_sim_from_lookup
from speednik.terrain import FULL, NOT_SOLID, TILE_SIZE, Tile
from tests.harness import FrameSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flat_tile() -> Tile:
    return Tile(height_array=[TILE_SIZE] * TILE_SIZE, angle=0, solidity=FULL)


def _empty_lookup(tx: int, ty: int) -> Tile | None:
    return None


def _ground_at_row(ground_row: int):
    """Return a tile_lookup that has flat FULL tiles at ground_row and below."""
    def lookup(tx: int, ty: int) -> Tile | None:
        if ty >= ground_row:
            return _flat_tile()
        return None
    return lookup


def make_snap(
    frame: int = 0,
    x: float = 100.0,
    y: float = 400.0,
    x_vel: float = 0.0,
    y_vel: float = 0.0,
    ground_speed: float = 0.0,
    angle: int = 0,
    on_ground: bool = True,
    quadrant: int = 0,
    state: str = "standing",
) -> FrameSnapshot:
    return FrameSnapshot(
        frame=frame, x=x, y=y, x_vel=x_vel, y_vel=y_vel,
        ground_speed=ground_speed, angle=angle, on_ground=on_ground,
        quadrant=quadrant, state=state,
    )


def make_sim(
    tile_lookup=None,
    level_width: int = 10000,
    level_height: int = 10000,
) -> SimState:
    if tile_lookup is None:
        tile_lookup = _ground_at_row(level_height // TILE_SIZE)
    return create_sim_from_lookup(
        tile_lookup, 100.0, 400.0,
        level_width=level_width, level_height=level_height,
    )


# ---------------------------------------------------------------------------
# Violation dataclass
# ---------------------------------------------------------------------------

class TestViolationDataclass:
    def test_violation_fields(self):
        v = Violation(frame=5, invariant="test", details="details", severity="error")
        assert v.frame == 5
        assert v.invariant == "test"
        assert v.details == "details"
        assert v.severity == "error"


# ---------------------------------------------------------------------------
# Position invariants
# ---------------------------------------------------------------------------

class TestPositionInvariants:
    def test_x_negative_flagged(self):
        sim = make_sim()
        snaps = [make_snap(frame=0, x=-1.0)]
        vs = check_invariants(sim, snaps, [[]])
        assert any(v.invariant == "position_x_negative" for v in vs)
        assert all(v.severity == "error" for v in vs if v.invariant == "position_x_negative")

    def test_y_fell_through_world(self):
        sim = make_sim(level_height=1000)
        snaps = [make_snap(frame=0, y=1065.0)]  # > 1000 + 64
        vs = check_invariants(sim, snaps, [[]])
        assert any(v.invariant == "position_y_below_world" for v in vs)

    def test_x_escaped_right(self):
        sim = make_sim(level_width=500)
        snaps = [make_snap(frame=0, x=565.0)]  # > 500 + 64
        vs = check_invariants(sim, snaps, [[]])
        assert any(v.invariant == "position_x_beyond_right" for v in vs)

    def test_clean_position_no_violations(self):
        sim = make_sim()
        snaps = [make_snap(frame=0, x=100.0, y=400.0)]
        vs = check_invariants(sim, snaps, [[]])
        pos_violations = [v for v in vs if v.invariant.startswith("position_")]
        assert len(pos_violations) == 0


# ---------------------------------------------------------------------------
# Solid tile invariant
# ---------------------------------------------------------------------------

class TestSolidTileInvariant:
    def test_inside_solid_flagged(self):
        # Place a FULL tile at tile (6, 25). Tile covers y=400..416 with full height.
        # Player at (100, 408) -> tx=6, ty=25, col=4
        # Solid top = (25+1)*16 - 16 = 400. y=408 >= 400 → inside.
        def lookup(tx: int, ty: int) -> Tile | None:
            if tx == 6 and ty == 25:
                return _flat_tile()
            return None
        sim = make_sim(tile_lookup=lookup)
        snaps = [make_snap(frame=0, x=100.0, y=408.0)]
        vs = check_invariants(sim, snaps, [[]])
        assert any(v.invariant == "inside_solid_tile" for v in vs)

    def test_above_solid_clean(self):
        # Player at y=399, tile at row 25 covers y=400..416. Player above solid.
        def lookup(tx: int, ty: int) -> Tile | None:
            if ty == 25:
                return _flat_tile()
            return None
        sim = make_sim(tile_lookup=lookup)
        snaps = [make_snap(frame=0, x=100.0, y=399.0)]
        vs = check_invariants(sim, snaps, [[]])
        assert not any(v.invariant == "inside_solid_tile" for v in vs)


# ---------------------------------------------------------------------------
# Velocity invariants
# ---------------------------------------------------------------------------

class TestVelocityInvariants:
    def test_x_vel_exceeds_max(self):
        sim = make_sim()
        snaps = [make_snap(frame=0, x_vel=25.0)]
        vs = check_invariants(sim, snaps, [[]])
        assert any(v.invariant == "velocity_x_exceeds_max" for v in vs)

    def test_y_vel_exceeds_max(self):
        sim = make_sim()
        snaps = [make_snap(frame=0, y_vel=-21.0)]
        vs = check_invariants(sim, snaps, [[]])
        assert any(v.invariant == "velocity_y_exceeds_max" for v in vs)

    def test_normal_velocity_clean(self):
        sim = make_sim()
        snaps = [make_snap(frame=0, x_vel=6.0, y_vel=-6.5)]
        vs = check_invariants(sim, snaps, [[]])
        assert not any(v.invariant.startswith("velocity_") for v in vs)


# ---------------------------------------------------------------------------
# Velocity spike invariant
# ---------------------------------------------------------------------------

class TestVelocitySpikes:
    def test_spike_without_excuse_flagged(self):
        sim = make_sim()
        snaps = [
            make_snap(frame=0, x_vel=0.0, y_vel=0.0),
            make_snap(frame=1, x_vel=15.0, y_vel=0.0),  # delta=15 > 12
        ]
        vs = check_invariants(sim, snaps, [[], []])
        assert any(v.invariant == "velocity_spike" for v in vs)

    def test_spike_with_spring_excused(self):
        sim = make_sim()
        snaps = [
            make_snap(frame=0, x_vel=0.0, y_vel=0.0),
            make_snap(frame=1, x_vel=0.0, y_vel=-15.0),  # delta=15 but spring
        ]
        vs = check_invariants(sim, snaps, [[], [SpringEvent()]])
        spike_vs = [v for v in vs if v.invariant == "velocity_spike"]
        assert len(spike_vs) == 0

    def test_spike_with_spindash_excused(self):
        sim = make_sim()
        snaps = [
            make_snap(frame=0, x_vel=0.0, state="spindash"),
            make_snap(frame=1, x_vel=12.5, state="rolling"),  # spindash release
        ]
        vs = check_invariants(sim, snaps, [[], []])
        spike_vs = [v for v in vs if v.invariant == "velocity_spike"]
        assert len(spike_vs) == 0

    def test_gradual_acceleration_clean(self):
        sim = make_sim()
        snaps = [
            make_snap(frame=0, x_vel=0.0),
            make_snap(frame=1, x_vel=0.5),
            make_snap(frame=2, x_vel=1.0),
        ]
        vs = check_invariants(sim, snaps, [[], [], []])
        spike_vs = [v for v in vs if v.invariant == "velocity_spike"]
        assert len(spike_vs) == 0


# ---------------------------------------------------------------------------
# Ground consistency
# ---------------------------------------------------------------------------

class TestGroundConsistency:
    def test_on_ground_no_tile_flagged(self):
        sim = make_sim(tile_lookup=_empty_lookup)
        snaps = [make_snap(frame=0, on_ground=True)]
        vs = check_invariants(sim, snaps, [[]])
        assert any(v.invariant == "on_ground_no_surface" for v in vs)

    def test_on_ground_with_tile_clean(self):
        # Player at y=384, feet at y=384+20=404, tile row = 404//16 = 25
        sim = make_sim(tile_lookup=_ground_at_row(25))
        snaps = [make_snap(frame=0, x=100.0, y=384.0, on_ground=True)]
        vs = check_invariants(sim, snaps, [[]])
        assert not any(v.invariant == "on_ground_no_surface" for v in vs)


# ---------------------------------------------------------------------------
# Quadrant jumps
# ---------------------------------------------------------------------------

class TestQuadrantJumps:
    def test_diagonal_quadrant_jump_flagged(self):
        sim = make_sim()
        snaps = [
            make_snap(frame=0, quadrant=0),
            make_snap(frame=1, quadrant=2),  # 0→2 skip
        ]
        vs = check_invariants(sim, snaps, [[], []])
        assert any(v.invariant == "quadrant_diagonal_jump" for v in vs)

    def test_opposite_quadrant_jump_1_to_3(self):
        sim = make_sim()
        snaps = [
            make_snap(frame=0, quadrant=1),
            make_snap(frame=1, quadrant=3),  # 1→3 skip
        ]
        vs = check_invariants(sim, snaps, [[], []])
        assert any(v.invariant == "quadrant_diagonal_jump" for v in vs)

    def test_adjacent_quadrant_transition_clean(self):
        sim = make_sim()
        snaps = [
            make_snap(frame=0, quadrant=0),
            make_snap(frame=1, quadrant=1),  # 0→1 adjacent
        ]
        vs = check_invariants(sim, snaps, [[], []])
        assert not any(v.invariant == "quadrant_diagonal_jump" for v in vs)

    def test_same_quadrant_clean(self):
        sim = make_sim()
        snaps = [
            make_snap(frame=0, quadrant=2),
            make_snap(frame=1, quadrant=2),
        ]
        vs = check_invariants(sim, snaps, [[], []])
        assert not any(v.invariant == "quadrant_diagonal_jump" for v in vs)


# ---------------------------------------------------------------------------
# Clean trajectory (integration)
# ---------------------------------------------------------------------------

class TestCleanTrajectory:
    def test_full_clean_trajectory_zero_violations(self):
        """Multi-frame clean trajectory should produce 0 violations."""
        ground_row = 25
        sim = make_sim(tile_lookup=_ground_at_row(ground_row))
        y = ground_row * TILE_SIZE - 20  # feet land on ground_row
        snaps = [
            make_snap(frame=i, x=100.0 + i * 2.0, y=float(y),
                      x_vel=2.0, on_ground=True)
            for i in range(60)
        ]
        events = [[] for _ in range(60)]
        vs = check_invariants(sim, snaps, events)
        assert len(vs) == 0


# ---------------------------------------------------------------------------
# No Pyxel import
# ---------------------------------------------------------------------------

class TestNoPyxelImport:
    def test_no_pyxel_import(self):
        import speednik.invariants as mod
        source = Path(inspect.getfile(mod)).read_text()
        assert "import pyxel" not in source
        assert "from pyxel" not in source

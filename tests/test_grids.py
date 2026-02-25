"""Tests for tests/grids.py — synthetic tile-grid builders."""

from __future__ import annotations

from speednik.terrain import FULL, SURFACE_LOOP, TILE_SIZE, TOP_ONLY, Tile

from tests.grids import (
    FILL_DEPTH,
    build_flat,
    build_gap,
    build_loop,
    build_ramp,
    build_slope,
)


# ---------------------------------------------------------------------------
# TestBuildFlat
# ---------------------------------------------------------------------------

class TestBuildFlat:
    def test_surface_tiles_present(self):
        _, lookup = build_flat(width_tiles=5, ground_row=10)
        for tx in range(5):
            tile = lookup(tx, 10)
            assert tile is not None, f"Missing surface tile at ({tx}, 10)"

    def test_surface_tile_properties(self):
        _, lookup = build_flat(width_tiles=3, ground_row=10)
        for tx in range(3):
            tile = lookup(tx, 10)
            assert tile.height_array == [16] * 16
            assert tile.angle == 0
            assert tile.solidity == FULL

    def test_fill_below_exists(self):
        _, lookup = build_flat(width_tiles=3, ground_row=10)
        for tx in range(3):
            for ty in range(11, 11 + FILL_DEPTH):
                tile = lookup(tx, ty)
                assert tile is not None, f"Missing fill tile at ({tx}, {ty})"
                assert tile.height_array == [16] * 16
                assert tile.solidity == FULL

    def test_outside_returns_none(self):
        _, lookup = build_flat(width_tiles=3, ground_row=10)
        assert lookup(-1, 10) is None
        assert lookup(3, 10) is None
        assert lookup(0, 9) is None
        assert lookup(0, 11 + FILL_DEPTH) is None

    def test_single_tile_width(self):
        _, lookup = build_flat(width_tiles=1, ground_row=5)
        assert lookup(0, 5) is not None
        assert lookup(1, 5) is None


# ---------------------------------------------------------------------------
# TestBuildGap
# ---------------------------------------------------------------------------

class TestBuildGap:
    def test_approach_tiles_present(self):
        _, lookup = build_gap(approach_tiles=3, gap_tiles=2, landing_tiles=3, ground_row=10)
        for tx in range(3):
            tile = lookup(tx, 10)
            assert tile is not None
            assert tile.height_array == [16] * 16
            assert tile.angle == 0

    def test_gap_is_empty(self):
        _, lookup = build_gap(approach_tiles=3, gap_tiles=2, landing_tiles=3, ground_row=10)
        for tx in range(3, 5):  # gap columns
            assert lookup(tx, 10) is None
            for ty in range(11, 11 + FILL_DEPTH):
                assert lookup(tx, ty) is None

    def test_landing_tiles_present(self):
        _, lookup = build_gap(approach_tiles=3, gap_tiles=2, landing_tiles=3, ground_row=10)
        for tx in range(5, 8):  # landing columns
            tile = lookup(tx, 10)
            assert tile is not None
            assert tile.height_array == [16] * 16

    def test_fill_below_approach_and_landing(self):
        _, lookup = build_gap(approach_tiles=2, gap_tiles=1, landing_tiles=2, ground_row=10)
        # Approach fill
        for tx in range(2):
            assert lookup(tx, 11) is not None
        # Landing fill
        for tx in range(3, 5):
            assert lookup(tx, 11) is not None


# ---------------------------------------------------------------------------
# TestBuildSlope
# ---------------------------------------------------------------------------

class TestBuildSlope:
    def test_approach_is_flat(self):
        _, lookup = build_slope(approach_tiles=3, slope_tiles=4, angle=10, ground_row=10)
        for tx in range(3):
            tile = lookup(tx, 10)
            assert tile is not None
            assert tile.angle == 0
            assert tile.height_array == [16] * 16

    def test_slope_tiles_have_correct_angle(self):
        angle = 10
        _, lookup = build_slope(approach_tiles=2, slope_tiles=3, angle=angle, ground_row=10)
        for tx in range(2, 5):
            tile = lookup(tx, 10)
            assert tile is not None
            assert tile.angle == angle

    def test_slope_heights_in_range(self):
        _, lookup = build_slope(approach_tiles=2, slope_tiles=3, angle=10, ground_row=10)
        for tx in range(2, 5):
            tile = lookup(tx, 10)
            assert tile is not None
            for h in tile.height_array:
                assert 0 <= h <= 16

    def test_fill_below_slope(self):
        _, lookup = build_slope(approach_tiles=2, slope_tiles=3, angle=10, ground_row=10)
        for tx in range(5):
            assert lookup(tx, 11) is not None

    def test_zero_angle_is_flat(self):
        _, lookup = build_slope(approach_tiles=0, slope_tiles=3, angle=0, ground_row=10)
        for tx in range(3):
            tile = lookup(tx, 10)
            assert tile is not None
            # angle=0 means flat, heights should all be near 8 or uniform
            assert tile.angle == 0


# ---------------------------------------------------------------------------
# TestBuildRamp
# ---------------------------------------------------------------------------

class TestBuildRamp:
    def test_approach_is_flat(self):
        _, lookup = build_ramp(
            approach_tiles=3, ramp_tiles=4,
            start_angle=0, end_angle=20, ground_row=10,
        )
        for tx in range(3):
            tile = lookup(tx, 10)
            assert tile is not None
            assert tile.angle == 0

    def test_ramp_angles_progress(self):
        _, lookup = build_ramp(
            approach_tiles=2, ramp_tiles=5,
            start_angle=0, end_angle=20, ground_row=10,
        )
        angles = []
        for tx in range(2, 7):
            tile = lookup(tx, 10)
            assert tile is not None
            angles.append(tile.angle)
        # Angles should progress from start toward end
        assert angles[0] == 0  # start_angle
        assert angles[-1] == 20  # end_angle

    def test_ramp_heights_in_range(self):
        _, lookup = build_ramp(
            approach_tiles=1, ramp_tiles=4,
            start_angle=0, end_angle=15, ground_row=10,
        )
        for tx in range(1, 5):
            tile = lookup(tx, 10)
            assert tile is not None
            for h in tile.height_array:
                assert 0 <= h <= 16

    def test_single_ramp_tile(self):
        _, lookup = build_ramp(
            approach_tiles=2, ramp_tiles=1,
            start_angle=5, end_angle=15, ground_row=10,
        )
        tile = lookup(2, 10)
        assert tile is not None
        # Single tile gets midpoint angle
        assert tile.angle == round((5 + 15) / 2) % 256

    def test_fill_below_ramp(self):
        _, lookup = build_ramp(
            approach_tiles=2, ramp_tiles=3,
            start_angle=0, end_angle=10, ground_row=10,
        )
        for tx in range(5):
            assert lookup(tx, 11) is not None


# ---------------------------------------------------------------------------
# TestBuildLoop
# ---------------------------------------------------------------------------

class TestBuildLoop:
    def test_approach_is_flat(self):
        _, lookup = build_loop(approach_tiles=3, radius=64, ground_row=10)
        for tx in range(3):
            tile = lookup(tx, 10)
            assert tile is not None
            assert tile.angle == 0
            assert tile.height_array == [16] * 16

    def test_loop_tiles_have_loop_type(self):
        _, lookup = build_loop(approach_tiles=2, radius=64, ground_row=10)
        # The loop starts at pixel 2*16=32, loop_start=32, loop_end=32+128=160
        # Tile columns in loop: 32//16=2 to 159//16=9
        found_loop = False
        for tx in range(2, 12):
            for ty in range(0, 20):
                tile = lookup(tx, ty)
                if tile is not None and tile.tile_type == SURFACE_LOOP:
                    found_loop = True
                    break
            if found_loop:
                break
        assert found_loop, "No loop tiles found"

    def test_upper_arc_top_only(self):
        _, lookup = build_loop(approach_tiles=2, radius=64, ground_row=10)
        found_top_only = False
        for tx in range(20):
            for ty in range(20):
                tile = lookup(tx, ty)
                if (tile is not None and tile.tile_type == SURFACE_LOOP
                        and tile.solidity == TOP_ONLY):
                    found_top_only = True
                    break
            if found_top_only:
                break
        assert found_top_only, "No TOP_ONLY loop tiles found (upper arc)"

    def test_lower_arc_full(self):
        _, lookup = build_loop(approach_tiles=2, radius=64, ground_row=10)
        found_full_loop = False
        for tx in range(20):
            for ty in range(20):
                tile = lookup(tx, ty)
                if (tile is not None and tile.tile_type == SURFACE_LOOP
                        and tile.solidity == FULL):
                    found_full_loop = True
                    break
            if found_full_loop:
                break
        assert found_full_loop, "No FULL loop tiles found (lower arc)"

    def test_interior_hollow(self):
        """Interior tiles between upper and lower arcs should be None."""
        radius = 64
        _, lookup = build_loop(approach_tiles=2, radius=radius, ground_row=10)

        ground_y = 10 * TILE_SIZE
        cy = ground_y - radius
        # Check center column of loop
        center_px = 2 * TILE_SIZE + radius
        center_tx = center_px // TILE_SIZE

        # Find upper and lower tile rows at the center
        upper_ty = int((cy - radius)) // TILE_SIZE
        lower_ty = int((cy + radius)) // TILE_SIZE

        # Interior rows between upper and lower should be None (or at least
        # not all filled)
        interior_none_count = 0
        for ty in range(upper_ty + 1, lower_ty):
            tile = lookup(center_tx, ty)
            if tile is None:
                interior_none_count += 1
        # With radius=64 (4 tiles), there should be at least some hollow interior
        assert interior_none_count > 0, "Loop interior is not hollow"

    def test_fill_below_loop(self):
        _, lookup = build_loop(approach_tiles=2, radius=64, ground_row=10)
        # Fill should exist below ground_row for approach tiles
        for tx in range(2):
            assert lookup(tx, 11) is not None

    def test_with_ramp_radius(self):
        """With ramp_radius, transition ramp tiles should exist."""
        _, lookup = build_loop(
            approach_tiles=2, radius=64, ground_row=10, ramp_radius=32,
        )
        # Approach still flat
        tile = lookup(0, 10)
        assert tile is not None

        # Ramp tiles should exist in the transition zone
        # Ramp starts at pixel 32 (approach=2 tiles), ramp is 32px = 2 tiles
        # So tiles at tx=2 should have ramp data
        ramp_tile = lookup(2, 10)
        assert ramp_tile is not None

    def test_angle_coverage(self):
        """Loop should produce tiles with angles spanning multiple quadrants."""
        _, lookup = build_loop(approach_tiles=2, radius=96, ground_row=12)
        angles = set()
        for tx in range(30):
            for ty in range(30):
                tile = lookup(tx, ty)
                if tile is not None and tile.tile_type == SURFACE_LOOP:
                    angles.add(tile.angle)
        # A full loop should have angles across a wide range
        assert len(angles) > 10, f"Too few distinct angles: {len(angles)}"

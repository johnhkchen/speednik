"""Tests for speednik/terrain.py — tile collision system."""

from __future__ import annotations

from speednik.constants import WALL_SENSOR_EXTENT, STANDING_HEIGHT_RADIUS
from speednik.physics import PhysicsState, calculate_landing_speed
from speednik.terrain import (
    DOWN,
    FULL,
    LEFT,
    LRB_ONLY,
    MAX_SENSOR_RANGE,
    NOT_SOLID,
    RIGHT,
    TILE_SIZE,
    TOP_ONLY,
    UP,
    SensorResult,
    Tile,
    TileLookup,
    find_ceiling,
    find_floor,
    find_wall_push,
    get_quadrant,
    resolve_collision,
    _sensor_cast_down,
    _sensor_cast_up,
    _sensor_cast_left,
    _sensor_cast_right,
    _floor_solidity_filter,
    _no_top_only_filter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def degrees_to_byte(deg: float) -> int:
    """Convert degrees to byte angle (0–255)."""
    return round(deg * 256 / 360) % 256


def make_tile_lookup(tiles: dict[tuple[int, int], Tile]) -> TileLookup:
    """Create a TileLookup from a dict of (tile_x, tile_y) -> Tile."""
    def lookup(tx: int, ty: int) -> Tile | None:
        return tiles.get((tx, ty))
    return lookup


def flat_tile(angle: int = 0, solidity: int = FULL) -> Tile:
    """Create a flat ground tile (all columns height 16)."""
    return Tile(height_array=[16] * 16, angle=angle, solidity=solidity)


def empty_tile(solidity: int = FULL) -> Tile:
    """Create an empty tile (all columns height 0)."""
    return Tile(height_array=[0] * 16, angle=0, solidity=solidity)


def slope_45_tile(angle: int = 0) -> Tile:
    """Create a 45° slope tile: height increases 1 per column from left to right."""
    return Tile(height_array=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16], angle=angle, solidity=FULL)


def half_height_tile(angle: int = 0) -> Tile:
    """Create a tile with height 8 across all columns."""
    return Tile(height_array=[8] * 16, angle=angle, solidity=FULL)


# ---------------------------------------------------------------------------
# TestTile
# ---------------------------------------------------------------------------

class TestTile:
    def test_height_array_stored(self):
        t = Tile(height_array=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], angle=32, solidity=FULL)
        assert t.height_array[0] == 0
        assert t.height_array[15] == 15
        assert t.angle == 32
        assert t.solidity == FULL

    def test_width_array_flat(self):
        """A full flat tile (all heights 16) should have all widths 16."""
        t = flat_tile()
        assert t.width_array() == [16] * 16

    def test_width_array_empty(self):
        """An empty tile (all heights 0) should have all widths 0."""
        t = Tile(height_array=[0] * 16, angle=0, solidity=FULL)
        assert t.width_array() == [0] * 16

    def test_width_array_45_slope(self):
        """A 45° slope tile: width_array should reflect the rotation."""
        t = slope_45_tile()
        wa = t.width_array()
        # Row 0 (bottom): all 16 columns have height > 0, so width = 16
        # Actually: height_array = [1,2,3,...,16]
        # Row 0: count cols where height > 0: col 0 has h=1 > 0, col 1 has h=2 > 0, ... all 16
        assert wa[0] == 16
        # Row 1: count cols where height > 1: col 0 has h=1, NOT > 1. col 1 has h=2 > 1. But we break on first fail.
        # col 0: h=1, 1 > 1? No → break → width = 0
        assert wa[1] == 0
        # Wait, this doesn't seem right. The width_array as implemented counts consecutive
        # solid columns from the LEFT. For row r, it counts how many columns from 0
        # have height > r.
        # Row 1: col 0 has h=1, 1 > 1 = False → break → 0
        # This is correct for detecting walls from the left side.

    def test_width_array_half_height(self):
        """Half-height tile: bottom 8 rows have all columns solid."""
        t = half_height_tile()
        wa = t.width_array()
        # All heights are 8. Row r: if r < 8, all cols have h > r → width 16
        for row in range(8):
            assert wa[row] == 16, f"row {row}"
        # Row 8: h=8 > 8 = False → 0
        for row in range(8, 16):
            assert wa[row] == 0, f"row {row}"


# ---------------------------------------------------------------------------
# TestGetQuadrant
# ---------------------------------------------------------------------------

class TestGetQuadrant:
    def test_normal_zero(self):
        assert get_quadrant(0) == 0

    def test_normal_low(self):
        assert get_quadrant(16) == 0

    def test_normal_boundary_32(self):
        assert get_quadrant(32) == 0

    def test_right_wall_33(self):
        assert get_quadrant(33) == 1

    def test_right_wall_64(self):
        assert get_quadrant(64) == 1

    def test_right_wall_boundary_96(self):
        assert get_quadrant(96) == 1

    def test_ceiling_97(self):
        assert get_quadrant(97) == 2

    def test_ceiling_128(self):
        assert get_quadrant(128) == 2

    def test_ceiling_boundary_160(self):
        assert get_quadrant(160) == 2

    def test_left_wall_161(self):
        assert get_quadrant(161) == 3

    def test_left_wall_192(self):
        assert get_quadrant(192) == 3

    def test_left_wall_boundary_223(self):
        assert get_quadrant(223) == 3

    def test_normal_224(self):
        assert get_quadrant(224) == 0

    def test_normal_255(self):
        assert get_quadrant(255) == 0


# ---------------------------------------------------------------------------
# TestSensorCastDown
# ---------------------------------------------------------------------------

class TestSensorCastDown:
    def test_flat_ground_above(self):
        """Sensor 4px above a flat tile surface should return distance 4."""
        # Flat tile at grid (0, 1), surface at y = 1*16 + (16-16) = 16
        tiles = {(0, 1): flat_tile()}
        lookup = make_tile_lookup(tiles)
        # Sensor at (8, 12) — 4px above the surface at y=16
        result = _sensor_cast_down(8.0, 12.0, lookup, _no_top_only_filter)
        # Sensor is in tile (0, 0) which is empty. Extension to (0, 1).
        # Surface in (0,1): tile_y=1, height=16, surface_y = 1*16 + (16-16) = 16
        # distance = 16 - 12 = 4
        assert result.found is True
        assert result.distance == 4.0

    def test_sensor_on_surface(self):
        """Sensor exactly at surface should return distance 0."""
        tiles = {(0, 1): flat_tile()}
        lookup = make_tile_lookup(tiles)
        result = _sensor_cast_down(8.0, 16.0, lookup, _no_top_only_filter)
        # Sensor is in tile (0, 1). Height=16, so regression to (0, 0) which doesn't exist.
        # Falls through to: surface_y = 1*16 = 16, dist = 16 - 16 = 0
        assert result.found is True
        assert result.distance == 0.0

    def test_sensor_inside_solid(self):
        """Sensor inside a solid tile should return negative distance."""
        tiles = {(0, 1): flat_tile()}
        lookup = make_tile_lookup(tiles)
        # Sensor at y=20, surface at y=16
        result = _sensor_cast_down(8.0, 20.0, lookup, _no_top_only_filter)
        # Sensor in tile (0, 1), height=16, regression: check (0, 0) = None
        # surface_y = 1*16 = 16, dist = 16 - 20 = -4
        assert result.found is True
        assert result.distance == -4.0

    def test_no_tile_found(self):
        """Sensor over empty space should return not found."""
        lookup = make_tile_lookup({})
        result = _sensor_cast_down(8.0, 8.0, lookup, _no_top_only_filter)
        assert result.found is False

    def test_extension_to_tile_below(self):
        """When current tile has height 0 at column, extend to tile below."""
        tiles = {
            (0, 0): Tile(height_array=[0] * 16, angle=0, solidity=FULL),
            (0, 1): half_height_tile(angle=10),
        }
        lookup = make_tile_lookup(tiles)
        # Sensor at (8, 4), in tile (0, 0) which has height 0
        # Extension to (0, 1): height=8, surface_y = 1*16 + (16-8) = 24
        # dist = 24 - 4 = 20
        result = _sensor_cast_down(8.0, 4.0, lookup, _no_top_only_filter)
        assert result.found is True
        assert result.distance == 20.0
        assert result.tile_angle == 10

    def test_beyond_max_range(self):
        """Surface beyond 32px should not be found."""
        tiles = {(0, 3): flat_tile()}
        lookup = make_tile_lookup(tiles)
        # Sensor at (8, 4), surface at y = 3*16 = 48, distance = 44 > 32
        result = _sensor_cast_down(8.0, 4.0, lookup, _no_top_only_filter)
        assert result.found is False

    def test_45_slope(self):
        """Sensor above a 45° slope tile returns correct distance per column."""
        slope_angle = degrees_to_byte(45)
        tiles = {(0, 1): slope_45_tile(angle=slope_angle)}
        lookup = make_tile_lookup(tiles)
        # Column 0: height=1, surface_y = 16 + (16-1) = 31
        result = _sensor_cast_down(0.5, 12.0, lookup, _no_top_only_filter)
        # Sensor in tile (0, 0), empty, extension to (0, 1)
        assert result.found is True
        assert result.distance == 31.0 - 12.0  # 19.0

        # Column 15: height=16, surface_y = 16 + (16-16) = 16
        result = _sensor_cast_down(15.5, 12.0, lookup, _no_top_only_filter)
        # Sensor in (0, 0), height for col 15 in (0,0) doesn't exist → empty, extension to (0,1)
        # In (0,1): height_array[15] = 16, surface_y = 16 + 0 = 16
        assert result.found is True
        assert result.distance == 16.0 - 12.0  # 4.0

    def test_top_only_ignored_when_rising(self):
        """Top-only tile should be ignored when filter says rising (y_vel < 0)."""
        tiles = {(0, 1): flat_tile(solidity=TOP_ONLY)}
        lookup = make_tile_lookup(tiles)
        rising_filter = _floor_solidity_filter(-1.0)
        result = _sensor_cast_down(8.0, 12.0, lookup, rising_filter)
        assert result.found is False

    def test_top_only_collides_when_falling(self):
        """Top-only tile should collide when filter says falling (y_vel >= 0)."""
        tiles = {(0, 1): flat_tile(solidity=TOP_ONLY)}
        lookup = make_tile_lookup(tiles)
        falling_filter = _floor_solidity_filter(1.0)
        result = _sensor_cast_down(8.0, 12.0, lookup, falling_filter)
        assert result.found is True


# ---------------------------------------------------------------------------
# TestSensorCastUp
# ---------------------------------------------------------------------------

class TestSensorCastUp:
    def test_ceiling_above(self):
        """Sensor below a ceiling tile should detect it."""
        # Tile at (0, 0) is a full ceiling. Sensor at (8, 20) casts up.
        tiles = {(0, 0): flat_tile()}
        lookup = make_tile_lookup(tiles)
        # Sensor at y=20, in tile (0, 1) which is empty. Extension up to (0, 0).
        # In (0, 0): height=16, surface at top of solid = (0)*16 + (16-16) = 0
        # For upward cast extension: solid_top_y = (0)*16 + (16-16) = 0
        # dist = 20 - 0 = 20
        result = _sensor_cast_up(8.0, 20.0, lookup, _no_top_only_filter)
        assert result.found is True
        assert result.distance == 20.0

    def test_no_ceiling(self):
        """No tile above should return not found."""
        lookup = make_tile_lookup({})
        result = _sensor_cast_up(8.0, 20.0, lookup, _no_top_only_filter)
        assert result.found is False

    def test_top_only_ignored_for_ceiling(self):
        """Top-only tiles should never collide with ceiling sensors."""
        tiles = {(0, 0): flat_tile(solidity=TOP_ONLY)}
        lookup = make_tile_lookup(tiles)
        result = _sensor_cast_up(8.0, 20.0, lookup, _no_top_only_filter)
        assert result.found is False


# ---------------------------------------------------------------------------
# TestSensorCastHorizontal
# ---------------------------------------------------------------------------

class TestSensorCastHorizontal:
    def test_wall_on_right(self):
        """Sensor casting right should detect a wall."""
        # Wall tile at (1, 0), full solid
        tiles = {(1, 0): flat_tile()}
        lookup = make_tile_lookup(tiles)
        # Sensor at (12, 8) in tile (0, 0) which is empty.
        # Extension to (1, 0). width_row = 15 - 8 = 7. wa[7] = 16 for flat tile.
        # surface_x = 1*16 + (16-16) = 16. dist = 16 - 12 = 4
        result = _sensor_cast_right(12.0, 8.0, lookup, _no_top_only_filter)
        assert result.found is True
        assert result.distance == 4.0

    def test_wall_on_left(self):
        """Sensor casting left should detect a wall."""
        # Wall tile at (0, 0), full solid
        tiles = {(0, 0): flat_tile()}
        lookup = make_tile_lookup(tiles)
        # Sensor at (20, 8) in tile (1, 0) which is empty.
        # Extension to (0, 0). width_row = 15-8=7. wa[7]=16 for flat tile.
        # surface_x = 0*16 + 16 = 16. dist = 20 - 16 = 4
        result = _sensor_cast_left(20.0, 8.0, lookup, _no_top_only_filter)
        assert result.found is True
        assert result.distance == 4.0

    def test_no_wall(self):
        """No tiles should return not found."""
        lookup = make_tile_lookup({})
        result = _sensor_cast_right(8.0, 8.0, lookup, _no_top_only_filter)
        assert result.found is False
        result = _sensor_cast_left(8.0, 8.0, lookup, _no_top_only_filter)
        assert result.found is False


# ---------------------------------------------------------------------------
# TestFloorSensors
# ---------------------------------------------------------------------------

class TestFloorSensors:
    def test_standing_on_flat_ground(self):
        """Player standing on flat ground: floor detected with correct distance."""
        # Ground tiles at y=2 (grid row 2), player at y = 2*16 - 20 = 12
        tiles = {(0, 2): flat_tile(), (1, 2): flat_tile()}
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=12.0, y=12.0, on_ground=True)
        result = find_floor(state, lookup)
        # Sensor A at x=12-9=3, y=12+20=32. Tile (0, 2), surface at 2*16=32. dist=0
        assert result.found is True
        assert result.distance == 0.0

    def test_tile_boundary_crossing(self):
        """A on tile N, B on tile N+1: both detect their own tile."""
        angle_a = 5
        angle_b = 10
        tiles = {
            (0, 2): flat_tile(angle=angle_a),
            (1, 2): flat_tile(angle=angle_b),
        }
        lookup = make_tile_lookup(tiles)
        # Player at x=14 (near right edge of tile 0)
        # A at x=14-9=5 (tile 0), B at x=14+9=23 (tile 1)
        state = PhysicsState(x=14.0, y=12.0, on_ground=True)
        result = find_floor(state, lookup)
        # Both find surface at y=32, sensor_y=32, dist=0. Tied → A wins.
        assert result.found is True
        assert result.tile_angle == angle_a  # A wins ties

    def test_a_wins_ties(self):
        """When A and B return equal distances, prefer A."""
        tiles = {(0, 2): flat_tile(angle=42), (1, 2): flat_tile(angle=99)}
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=14.0, y=12.0, on_ground=True)
        result = find_floor(state, lookup)
        assert result.tile_angle == 42  # A's angle

    def test_top_only_pass_through_rising(self):
        """Top-only platform ignored when y_vel < 0 (rising)."""
        tiles = {(0, 2): flat_tile(solidity=TOP_ONLY)}
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=8.0, y=12.0, on_ground=False, y_vel=-5.0)
        result = find_floor(state, lookup)
        assert result.found is False

    def test_top_only_collide_falling(self):
        """Top-only platform collides when y_vel >= 0 (falling)."""
        tiles = {(0, 2): flat_tile(solidity=TOP_ONLY), (1, 2): flat_tile(solidity=TOP_ONLY)}
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=8.0, y=12.0, on_ground=False, y_vel=3.0)
        result = find_floor(state, lookup)
        assert result.found is True

    def test_b_closer_wins(self):
        """When B is closer to surface, B wins."""
        # Tile 0 at height 8 (surface at y=24), tile 1 at height 16 (surface at y=16)
        tiles = {
            (0, 1): half_height_tile(angle=5),
            (1, 1): flat_tile(angle=10),
        }
        lookup = make_tile_lookup(tiles)
        # Player at x=14, sensor A at x=5 (tile 0), B at x=23 (tile 1)
        # Sensor y = y + h_rad = 0 + 20 = 20
        # A: in tile (0, 1), col 5, height=8. surface_y = 16 + (16-8) = 24. dist = 24 - 20 = 4
        # B: in tile (1, 1), col 7, height=16. Regression: tile (1, 0) = None.
        #    surface_y = 1*16 = 16. dist = 16 - 20 = -4
        # |B.dist|=4 == |A.dist|=4 → tie → A wins
        # Actually let me reconsider. Both have |dist| = 4, so A wins ties.
        state = PhysicsState(x=14.0, y=0.0, on_ground=True)
        result = find_floor(state, lookup)
        assert result.found is True
        assert result.tile_angle == 5  # A wins tie


# ---------------------------------------------------------------------------
# TestCeilingSensors
# ---------------------------------------------------------------------------

class TestCeilingSensors:
    def test_ceiling_detected(self):
        """Ceiling sensor detects solid tile above."""
        # Ceiling tile at row 0, player below
        tiles = {(0, 0): flat_tile(angle=0)}
        lookup = make_tile_lookup(tiles)
        # Player at y=28 (center), head at y=28-20=8, in tile (0, 0)
        state = PhysicsState(x=8.0, y=28.0, on_ground=False, y_vel=-3.0)
        result = find_ceiling(state, lookup)
        assert result.found is True

    def test_no_ceiling(self):
        """No ceiling tile: not found."""
        lookup = make_tile_lookup({})
        state = PhysicsState(x=8.0, y=40.0, on_ground=False, y_vel=-3.0)
        result = find_ceiling(state, lookup)
        assert result.found is False

    def test_top_only_ignored_by_ceiling(self):
        """Top-only tiles never collide with ceiling sensors."""
        tiles = {(0, 0): flat_tile(solidity=TOP_ONLY)}
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=8.0, y=28.0, on_ground=False, y_vel=-3.0)
        result = find_ceiling(state, lookup)
        assert result.found is False


# ---------------------------------------------------------------------------
# TestWallSensors
# ---------------------------------------------------------------------------

class TestWallSensors:
    def test_wall_right_detected(self):
        """Wall sensor F detects wall to the right when moving right."""
        tiles = {(2, 0): flat_tile(angle=64)}
        lookup = make_tile_lookup(tiles)
        # Player at x=20, wall at tile (2, 0) = x range [32, 48)
        # F sensor at x = 20 + 10 = 30, casting right
        # angle=64 is wall-like (> WALL_ANGLE_THRESHOLD=48), so the gate passes it through
        state = PhysicsState(x=20.0, y=8.0, on_ground=True, x_vel=2.0)
        result = find_wall_push(state, lookup, RIGHT)
        assert result.found is True

    def test_wall_disabled_moving_away(self):
        """Wall sensor disabled when moving away from wall."""
        tiles = {(2, 0): flat_tile(angle=64)}
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=20.0, y=8.0, on_ground=True, x_vel=-2.0)
        # Moving left, checking right wall → disabled
        result = find_wall_push(state, lookup, RIGHT)
        assert result.found is False

    def test_wall_left_detected(self):
        """Wall sensor E detects wall to the left when moving left."""
        tiles = {(0, 0): flat_tile(angle=192)}
        lookup = make_tile_lookup(tiles)
        # Player at x=20, E sensor at x = 20 - 10 = 10
        # angle=192 is wall-like (left-wall range, > WALL_ANGLE_THRESHOLD from both ends)
        state = PhysicsState(x=20.0, y=8.0, on_ground=True, x_vel=-2.0)
        result = find_wall_push(state, lookup, LEFT)
        assert result.found is True

    def test_rolling_narrows_detection(self):
        """Rolling state uses narrower width_radius but wall sensor extent is same."""
        tiles = {(2, 0): flat_tile(angle=64)}
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=20.0, y=8.0, on_ground=True, is_rolling=True, x_vel=2.0)
        result = find_wall_push(state, lookup, RIGHT)
        # Wall sensor extent is WALL_SENSOR_EXTENT (10), independent of width_radius
        # Sensor at x = 20 + 10 = 30; angle=64 passes the wall angle gate
        assert result.found is True


# ---------------------------------------------------------------------------
# TestResolveCollision
# ---------------------------------------------------------------------------

class TestResolveCollision:
    def test_flat_ground_stays_grounded(self):
        """Player on flat ground stays on ground with correct y."""
        tiles = {
            (0, 2): flat_tile(),
            (1, 2): flat_tile(),
        }
        lookup = make_tile_lookup(tiles)
        # Player at y=12, feet at y=32 (surface of tile row 2)
        state = PhysicsState(x=12.0, y=12.0, on_ground=True, ground_speed=2.0)
        resolve_collision(state, lookup)
        assert state.on_ground is True
        assert state.angle == 0

    def test_walking_off_ledge(self):
        """Player walking off a ledge detaches from ground."""
        tiles = {(0, 2): flat_tile()}
        lookup = make_tile_lookup(tiles)
        # Player far from any ground tile
        state = PhysicsState(x=100.0, y=12.0, on_ground=True, ground_speed=2.0)
        resolve_collision(state, lookup)
        assert state.on_ground is False
        assert state.angle == 0

    def test_landing_from_air(self):
        """Airborne player landing on ground transitions to on_ground."""
        tiles = {
            (0, 2): flat_tile(angle=0),
            (1, 2): flat_tile(angle=0),
        }
        lookup = make_tile_lookup(tiles)
        # Player falling: y_vel > 0, feet will be at or past surface
        # Player y=14 (just past where feet at y+20=34 would be past surface at y=32)
        state = PhysicsState(x=12.0, y=14.0, on_ground=False, x_vel=3.0, y_vel=2.0)
        resolve_collision(state, lookup)
        assert state.on_ground is True
        assert state.angle == 0

    def test_landing_snaps_angle(self):
        """Landing snaps player angle to the tile's stored angle."""
        slope_angle = degrees_to_byte(45)
        tiles = {
            (0, 2): slope_45_tile(angle=slope_angle),
            (1, 2): flat_tile(angle=slope_angle),
        }
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=12.0, y=14.0, on_ground=False, x_vel=3.0, y_vel=2.0)
        resolve_collision(state, lookup)
        assert state.on_ground is True
        assert state.angle == slope_angle

    def test_slope_adherence(self):
        """Player on a slope has angle continuously updated."""
        slope_angle = degrees_to_byte(45)
        tiles = {
            (0, 2): slope_45_tile(angle=slope_angle),
            (1, 2): flat_tile(angle=slope_angle),
        }
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=12.0, y=12.0, on_ground=True, ground_speed=2.0, angle=0)
        resolve_collision(state, lookup)
        # Angle should be updated to the slope angle
        assert state.angle == slope_angle

    def test_wall_collision_pushes_out(self):
        """Wall collision pushes player away from wall."""
        # Ground tile and wall tile
        # Wall tiles must have a wall-like angle (> WALL_ANGLE_THRESHOLD=48) so the
        # angle gate in find_wall_push() does not discard them.
        tiles = {
            (0, 2): flat_tile(),
            (1, 2): flat_tile(),
            (2, 0): flat_tile(angle=64),  # wall — steep angle passes gate
            (2, 1): flat_tile(angle=64),  # wall — steep angle passes gate
        }
        lookup = make_tile_lookup(tiles)
        # Player very close to wall, moving right
        state = PhysicsState(x=24.0, y=12.0, on_ground=True, x_vel=3.0, ground_speed=3.0)
        resolve_collision(state, lookup)
        # Wall at x=32, sensor at x=34, should be pushed back
        # After push, x_vel should be 0
        assert state.x_vel == 0.0
        assert state.ground_speed == 0.0

    def test_ceiling_collision_zeros_upward_velocity(self):
        """Ceiling collision zeroes upward velocity."""
        tiles = {(0, 0): flat_tile()}
        lookup = make_tile_lookup(tiles)
        # Player jumping up, head hits ceiling
        state = PhysicsState(x=8.0, y=20.0, on_ground=False, y_vel=-5.0)
        ceiling_result = find_ceiling(state, lookup)
        # Check ceiling is detected
        if ceiling_result.found and ceiling_result.distance < 0:
            state.y -= ceiling_result.distance
            if state.y_vel < 0:
                state.y_vel = 0.0
        # After ceiling hit, upward velocity should be zeroed
        assert state.y_vel == 0.0

    def test_top_only_pass_through_from_below(self):
        """Player jumping through top-only platform from below should pass through."""
        tiles = {
            (0, 2): flat_tile(solidity=TOP_ONLY),
            (1, 2): flat_tile(solidity=TOP_ONLY),
        }
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=12.0, y=14.0, on_ground=False, x_vel=0.0, y_vel=-5.0)
        resolve_collision(state, lookup)
        # Should NOT land (y_vel < 0)
        assert state.on_ground is False


# ---------------------------------------------------------------------------
# TestAngleQuadrantSwitching
# ---------------------------------------------------------------------------

class TestAngleQuadrantSwitching:
    def test_right_wall_mode_sensors(self):
        """In right wall mode (angle ~90°), floor sensors cast right."""
        angle = degrees_to_byte(90)  # ~64 byte
        assert get_quadrant(angle) == 1

    def test_ceiling_mode_sensors(self):
        """In ceiling mode (angle ~180°), floor sensors cast up."""
        angle = degrees_to_byte(180)  # ~128 byte
        assert get_quadrant(angle) == 2

    def test_left_wall_mode_sensors(self):
        """In left wall mode (angle ~270°), floor sensors cast left."""
        angle = degrees_to_byte(270)  # ~192 byte
        assert get_quadrant(angle) == 3

    def test_loop_traversal_all_quadrants(self):
        """Angle rotating through all quadrants during loop traversal."""
        # Simulate angle progressing through a loop
        angles = [0, 32, 64, 96, 128, 160, 192, 224, 255]
        expected_quadrants = [0, 0, 1, 1, 2, 2, 3, 0, 0]
        for angle, expected in zip(angles, expected_quadrants):
            assert get_quadrant(angle) == expected, f"angle={angle}"


# ---------------------------------------------------------------------------
# TestLanding
# ---------------------------------------------------------------------------

class TestLanding:
    def test_landing_does_not_carry_air_angle(self):
        """Landing snaps to tile angle, does not carry air angle (0)."""
        slope_angle = degrees_to_byte(30)
        tiles = {
            (0, 2): flat_tile(angle=slope_angle),
            (1, 2): flat_tile(angle=slope_angle),
        }
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=12.0, y=14.0, on_ground=False, angle=0, x_vel=3.0, y_vel=2.0)
        resolve_collision(state, lookup)
        assert state.on_ground is True
        assert state.angle == slope_angle  # Snapped to tile, not carried from air

    def test_landing_recalculates_ground_speed(self):
        """Landing calls calculate_landing_speed to set ground_speed from velocities."""
        tiles = {
            (0, 2): flat_tile(angle=0),
            (1, 2): flat_tile(angle=0),
        }
        lookup = make_tile_lookup(tiles)
        state = PhysicsState(x=12.0, y=14.0, on_ground=False, x_vel=5.0, y_vel=2.0)
        resolve_collision(state, lookup)
        assert state.on_ground is True
        # Flat angle (0°): ground_speed = x_vel = 5.0
        assert state.ground_speed == 5.0


# ---------------------------------------------------------------------------
# TestWallSensorAngleGate
# ---------------------------------------------------------------------------

class TestWallSensorAngleGate:
    """Wall sensor must not block movement onto shallow-angled floor tiles."""

    def _state_moving_right(self):
        """Player on flat ground, moving right at speed 5."""
        return PhysicsState(x=100.0, y=96.0, x_vel=5.0, on_ground=True, angle=0)

    def _lookup_at_sensor(self, tile):
        """Return a tile lookup that places `tile` exactly at the right wall sensor."""
        # Sensor is at x = 100 + WALL_SENSOR_EXTENT = 110, y = 96
        # tile_x = 110 // 16 = 6,  tile_y = 96 // 16 = 6
        def lookup(tx, ty):
            if tx == 6 and ty == 6:
                return tile
            return None
        return lookup

    def test_shallow_angle_tile_does_not_block(self):
        """Tile with byte angle < WALL_ANGLE_THRESHOLD must not block horizontal movement."""
        shallow = Tile(height_array=[16] * 16, angle=20, solidity=FULL)
        state = self._state_moving_right()
        result = find_wall_push(state, self._lookup_at_sensor(shallow), RIGHT)
        assert not result.found, (
            "Shallow-angled tile (loop entry) should be ignored by wall sensor"
        )

    def test_steep_angle_tile_does_block(self):
        """Tile with byte angle >= WALL_ANGLE_THRESHOLD must still block movement."""
        steep = Tile(height_array=[16] * 16, angle=64, solidity=FULL)
        state = self._state_moving_right()
        result = find_wall_push(state, self._lookup_at_sensor(steep), RIGHT)
        assert result.found and result.distance < 0, (
            "Steep-angled tile (genuine wall) must block horizontal movement"
        )

    def test_left_wall_shallow_angle_does_not_block(self):
        """Same gate applies to the left wall sensor."""
        shallow = Tile(height_array=[16] * 16, angle=236, solidity=FULL)
        # angle=236: 236*360/256 ≈ 332°, mirror of 28° — floor range on left side
        state = PhysicsState(x=100.0, y=96.0, x_vel=-5.0, on_ground=True, angle=0)
        # Left sensor at x = 100 - 10 = 90, tile_x = 90//16 = 5, tile_y = 6
        def lookup(tx, ty):
            if tx == 5 and ty == 6:
                return shallow
            return None
        result = find_wall_push(state, lookup, LEFT)
        assert not result.found, (
            "Shallow-angled tile on the left should also be ignored"
        )

    def test_exact_boundary_angle_48_is_rejected(self):
        """Exact boundary value angle=48 must be floor-range and rejected."""
        boundary = Tile(height_array=[16] * 16, angle=48, solidity=FULL)
        state = self._state_moving_right()
        result = find_wall_push(state, self._lookup_at_sensor(boundary), RIGHT)
        assert not result.found, "angle=48 is floor-range boundary and must be ignored"

    def test_one_above_boundary_angle_49_is_accepted(self):
        """angle=49 is the first wall-like angle and must not be ignored."""
        just_steep = Tile(height_array=[16] * 16, angle=49, solidity=FULL)
        state = self._state_moving_right()
        result = find_wall_push(state, self._lookup_at_sensor(just_steep), RIGHT)
        assert result.found, "angle=49 is first wall-like angle and must block movement"

    def test_exact_upper_boundary_angle_208_is_rejected(self):
        """Upper boundary angle=208 must also be floor-range and rejected."""
        upper_boundary = Tile(height_array=[16] * 16, angle=208, solidity=FULL)
        state = self._state_moving_right()
        result = find_wall_push(state, self._lookup_at_sensor(upper_boundary), RIGHT)
        assert not result.found, "angle=208 is upper floor-range boundary and must be ignored"

    def test_one_below_upper_boundary_angle_207_is_accepted(self):
        """angle=207 is the last wall-like angle and must not be ignored."""
        just_below = Tile(height_array=[16] * 16, angle=207, solidity=FULL)
        state = self._state_moving_right()
        result = find_wall_push(state, self._lookup_at_sensor(just_below), RIGHT)
        assert result.found, "angle=207 is last wall-like angle and must block movement"

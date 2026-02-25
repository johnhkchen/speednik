"""speednik/terrain.py — Tile collision: height arrays, angles, sensors.

Implements specification §3: tile format, sensor layout, sensor casts,
floor/ceiling/wall resolution, and quadrant-based mode switching.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

from speednik.constants import (
    ANGLE_STEPS,
    ROLLING_HEIGHT_RADIUS,
    ROLLING_WIDTH_RADIUS,
    STANDING_HEIGHT_RADIUS,
    STANDING_WIDTH_RADIUS,
    WALL_ANGLE_THRESHOLD,
    WALL_SENSOR_EXTENT,
)
from speednik.physics import PhysicsState, byte_angle_to_rad, calculate_landing_speed

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Solidity flags
NOT_SOLID = 0
TOP_ONLY = 1
FULL = 2
LRB_ONLY = 3

# Cast directions
DOWN = 0
RIGHT = 1
UP = 2
LEFT = 3

TILE_SIZE = 16
MAX_SENSOR_RANGE = 32

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

TileLookup = Callable[[int, int], Optional["Tile"]]
"""Callable that returns the Tile at grid position (tile_x, tile_y), or None."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Tile:
    """A 16x16 collision tile with height profile, angle, and solidity."""

    height_array: list[int]  # 16 values, 0–16
    angle: int  # byte angle 0–255
    solidity: int  # NOT_SOLID / TOP_ONLY / FULL / LRB_ONLY

    def width_array(self) -> list[int]:
        """Compute the width array (height_array rotated 90° for wall detection).

        For each row (0 = bottom, 15 = top), the width is how many columns
        from the left are solid at that row. A column is solid at row r if
        height_array[col] > r.
        """
        result = [0] * TILE_SIZE
        for row in range(TILE_SIZE):
            count = 0
            for col in range(TILE_SIZE):
                if self.height_array[col] > row:
                    count += 1
                else:
                    break
            result[row] = count
        return result


@dataclass
class SensorResult:
    """Result of a single sensor cast."""

    found: bool  # whether a surface was detected
    distance: float  # distance from sensor to surface (negative = inside solid)
    tile_angle: int  # angle of the hit tile


# ---------------------------------------------------------------------------
# Quadrant mapping
# ---------------------------------------------------------------------------

def get_quadrant(angle: int) -> int:
    """Map byte angle (0–255) to quadrant 0–3.

    0: normal (0–32, 224–255) — floor sensors point down
    1: right wall (33–96) — floor sensors point right
    2: ceiling (97–160) — floor sensors point up
    3: left wall (161–223) — floor sensors point left
    """
    if angle <= 32 or angle >= 224:
        return 0
    elif angle <= 96:
        return 1
    elif angle <= 160:
        return 2
    else:
        return 3


# ---------------------------------------------------------------------------
# Sensor radii helpers
# ---------------------------------------------------------------------------

def _get_radii(state: PhysicsState) -> tuple[int, int]:
    """Return (width_radius, height_radius) based on rolling state."""
    if state.is_rolling or not state.on_ground:
        return ROLLING_WIDTH_RADIUS, ROLLING_HEIGHT_RADIUS
    return STANDING_WIDTH_RADIUS, STANDING_HEIGHT_RADIUS


# ---------------------------------------------------------------------------
# Vertical sensor casts
# ---------------------------------------------------------------------------

def _sensor_cast_down(
    sensor_x: float,
    sensor_y: float,
    tile_lookup: TileLookup,
    solidity_filter: Callable[[int], bool],
) -> SensorResult:
    """Cast a sensor downward from (sensor_x, sensor_y).

    Returns distance to the first solid surface found below.
    Positive distance = surface is below sensor (gap).
    Negative distance = sensor is inside solid (overlap).
    """
    # Determine which tile column the sensor is in
    tile_x = int(sensor_x) // TILE_SIZE
    col = int(sensor_x) % TILE_SIZE

    # Check the tile the sensor is currently in
    tile_y = int(sensor_y) // TILE_SIZE
    tile = tile_lookup(tile_x, tile_y)

    if tile is not None and tile.solidity != NOT_SOLID and solidity_filter(tile.solidity):
        height = tile.height_array[col]
        if height == 0:
            # Extension: check tile below
            tile_below = tile_lookup(tile_x, tile_y + 1)
            if tile_below is not None and tile_below.solidity != NOT_SOLID and solidity_filter(tile_below.solidity):
                height_below = tile_below.height_array[col]
                if height_below > 0:
                    # Surface is in the tile below
                    surface_y = (tile_y + 1) * TILE_SIZE + (TILE_SIZE - height_below)
                    dist = surface_y - sensor_y
                    if abs(dist) <= MAX_SENSOR_RANGE:
                        return SensorResult(found=True, distance=dist, tile_angle=tile_below.angle)
            # No surface found even with extension
            return SensorResult(found=False, distance=0.0, tile_angle=0)
        elif height == TILE_SIZE:
            # Regression: check tile above
            tile_above = tile_lookup(tile_x, tile_y - 1)
            if tile_above is not None and tile_above.solidity != NOT_SOLID and solidity_filter(tile_above.solidity):
                height_above = tile_above.height_array[col]
                if height_above < TILE_SIZE:
                    # Surface is in the tile above
                    surface_y = (tile_y - 1) * TILE_SIZE + (TILE_SIZE - height_above)
                    dist = surface_y - sensor_y
                    if abs(dist) <= MAX_SENSOR_RANGE:
                        return SensorResult(found=True, distance=dist, tile_angle=tile_above.angle)
                else:
                    # Tile above is also full — surface is at top of tile above
                    surface_y = (tile_y - 1) * TILE_SIZE
                    dist = surface_y - sensor_y
                    if abs(dist) <= MAX_SENSOR_RANGE:
                        return SensorResult(found=True, distance=dist, tile_angle=tile_above.angle)
            # No regression target — surface is at top of current tile
            surface_y = tile_y * TILE_SIZE
            dist = surface_y - sensor_y
            if abs(dist) <= MAX_SENSOR_RANGE:
                return SensorResult(found=True, distance=dist, tile_angle=tile.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
        else:
            # Normal case: surface is within this tile
            surface_y = tile_y * TILE_SIZE + (TILE_SIZE - height)
            dist = surface_y - sensor_y
            if abs(dist) <= MAX_SENSOR_RANGE:
                return SensorResult(found=True, distance=dist, tile_angle=tile.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
    else:
        # No solid tile at sensor position — check tile below (extension)
        tile_below = tile_lookup(tile_x, tile_y + 1)
        if tile_below is not None and tile_below.solidity != NOT_SOLID and solidity_filter(tile_below.solidity):
            height_below = tile_below.height_array[col]
            if height_below > 0:
                surface_y = (tile_y + 1) * TILE_SIZE + (TILE_SIZE - height_below)
                dist = surface_y - sensor_y
                if abs(dist) <= MAX_SENSOR_RANGE:
                    return SensorResult(found=True, distance=dist, tile_angle=tile_below.angle)
        return SensorResult(found=False, distance=0.0, tile_angle=0)


def _sensor_cast_up(
    sensor_x: float,
    sensor_y: float,
    tile_lookup: TileLookup,
    solidity_filter: Callable[[int], bool],
) -> SensorResult:
    """Cast a sensor upward from (sensor_x, sensor_y).

    Returns distance to the first solid surface found above.
    Positive distance = surface is above sensor (gap).
    Negative distance = sensor is inside solid (overlap).
    """
    tile_x = int(sensor_x) // TILE_SIZE
    col = int(sensor_x) % TILE_SIZE

    tile_y = int(sensor_y) // TILE_SIZE
    tile = tile_lookup(tile_x, tile_y)

    if tile is not None and tile.solidity != NOT_SOLID and solidity_filter(tile.solidity):
        height = tile.height_array[col]
        if height == 0:
            # Extension: check tile above
            tile_above = tile_lookup(tile_x, tile_y - 1)
            if tile_above is not None and tile_above.solidity != NOT_SOLID and solidity_filter(tile_above.solidity):
                height_above = tile_above.height_array[col]
                if height_above > 0:
                    # Surface (bottom of solid region) in tile above
                    surface_y = tile_y * TILE_SIZE  # bottom of current tile = top of... no
                    # For upward cast, the "surface" is the bottom of the solid part
                    surface_y = (tile_y - 1) * TILE_SIZE + height_above
                    dist = sensor_y - surface_y
                    if abs(dist) <= MAX_SENSOR_RANGE:
                        return SensorResult(found=True, distance=dist, tile_angle=tile_above.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
        elif height == TILE_SIZE:
            # Regression: check tile below
            tile_below = tile_lookup(tile_x, tile_y + 1)
            if tile_below is not None and tile_below.solidity != NOT_SOLID and solidity_filter(tile_below.solidity):
                height_below = tile_below.height_array[col]
                if height_below < TILE_SIZE:
                    surface_y = (tile_y + 1) * TILE_SIZE + height_below
                    dist = sensor_y - surface_y
                    if abs(dist) <= MAX_SENSOR_RANGE:
                        return SensorResult(found=True, distance=dist, tile_angle=tile_below.angle)
            # Surface is at bottom of current full tile
            surface_y = (tile_y + 1) * TILE_SIZE
            dist = sensor_y - surface_y
            if abs(dist) <= MAX_SENSOR_RANGE:
                return SensorResult(found=True, distance=dist, tile_angle=tile.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
        else:
            # Normal case: bottom of solid region within this tile
            surface_y = tile_y * TILE_SIZE + (TILE_SIZE - height)
            # For ceiling, the surface the player hits is the bottom of the solid part
            # Height from bottom means solid occupies [tile_top + (16 - height), tile_bottom]
            # The bottom of solid = tile_top + (16 - height) ... no, solid is from bottom.
            # height_array[col] = N means N pixels of solid from the bottom of the tile.
            # Bottom of tile = (tile_y + 1) * TILE_SIZE
            # Solid spans from (tile_y+1)*16 - N  to  (tile_y+1)*16
            # The "ceiling surface" (bottom of solid from above perspective) is at
            # (tile_y+1)*16 - height ... wait, that's the top of the solid.
            # For an upward cast, we hit the BOTTOM of solid = (tile_y + 1) * TILE_SIZE
            # No — height_array measures from the bottom. So solid region is:
            #   bottom: (tile_y + 1) * TILE_SIZE - height ... no.
            # tile occupies y range [tile_y * 16, (tile_y+1) * 16)
            # height_array[col] = h means h pixels are solid from the bottom
            # solid region: y from (tile_y+1)*16 - h  to  (tile_y+1)*16 - 1
            # actually solid from bottom: y = (tile_y * 16 + 16 - h) to (tile_y * 16 + 15)
            # so the TOP of the solid is at y = tile_y * 16 + (16 - h)
            # the BOTTOM of the solid is at y = tile_y * 16 + 15 (bottom of tile)
            # Wait, that's confusing. Let me think in screen coords (y increases downward).
            # Tile top = tile_y * 16, tile bottom = (tile_y + 1) * 16
            # Solid fills from the bottom up: solid from y = (tile_y+1)*16 - h to (tile_y+1)*16
            # Top of solid surface = (tile_y + 1) * TILE_SIZE - height
            # For upward cast, we hit the bottom of the solid block from below
            # The lowest point of the solid = (tile_y + 1) * TILE_SIZE (bottom of tile) ... no
            # (tile_y+1)*16 - h is the top of solid, (tile_y+1)*16 is the bottom
            # In screen coords (y-down), "bottom" = higher y value
            # Upward cast = decreasing y. We hit the part with highest y = bottom of solid
            # Bottom of solid = (tile_y + 1) * TILE_SIZE
            # But that's the bottom edge of the tile, which is the start of solid.
            # Actually for ceiling detection, the sensor is BELOW the tile, casting UP.
            # It hits the bottom edge of the solid, which is at (tile_y+1)*16 - h?
            # No! Solid fills from bottom (high y) up (low y).
            # Top surface (low y) = tile_y*16 + (16 - h)
            # Bottom of tile (high y) = (tile_y+1)*16
            # A sensor below the tile casting up hits... the bottom of the tile.
            # But we're checking the tile the sensor IS in, so sensor_y is within this tile.
            # For ceiling: we want the underside of the solid part.
            # The solid occupies y: [tile_y*16 + 16 - h, (tile_y+1)*16)
            # The underside (highest y of solid, i.e., bottom in screen coords) is (tile_y+1)*16
            # The topside (lowest y, closest to 0) is tile_y*16 + 16 - h
            # For upward cast (sensor below solid), we're looking for the bottom face
            # which is at y = (tile_y + 1) * TILE_SIZE.
            # But the sensor is IN this tile... if it's below the solid region, it can see
            # the underside at y = tile_y*16 + (16 - h)
            # If it's inside the solid, distance is negative.

            solid_top_y = tile_y * TILE_SIZE + (TILE_SIZE - height)
            dist = sensor_y - solid_top_y
            if abs(dist) <= MAX_SENSOR_RANGE:
                return SensorResult(found=True, distance=dist, tile_angle=tile.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
    else:
        # No solid tile — check tile above (extension)
        tile_above = tile_lookup(tile_x, tile_y - 1)
        if tile_above is not None and tile_above.solidity != NOT_SOLID and solidity_filter(tile_above.solidity):
            height_above = tile_above.height_array[col]
            if height_above > 0:
                # For upward extension, the surface we hit is the bottom of the solid
                # Solid in tile_above spans y: [ty*16 + 16 - h, (ty+1)*16)
                solid_top_y = (tile_y - 1) * TILE_SIZE + (TILE_SIZE - height_above)
                dist = sensor_y - solid_top_y
                if abs(dist) <= MAX_SENSOR_RANGE:
                    return SensorResult(found=True, distance=dist, tile_angle=tile_above.angle)
        return SensorResult(found=False, distance=0.0, tile_angle=0)


# ---------------------------------------------------------------------------
# Horizontal sensor casts
# ---------------------------------------------------------------------------

def _sensor_cast_right(
    sensor_x: float,
    sensor_y: float,
    tile_lookup: TileLookup,
    solidity_filter: Callable[[int], bool],
) -> SensorResult:
    """Cast a sensor rightward from (sensor_x, sensor_y)."""
    tile_y = int(sensor_y) // TILE_SIZE
    row = int(sensor_y) % TILE_SIZE
    # For width_array, row 0 = bottom of tile. Convert screen row.
    # In screen coords, row within tile = int(sensor_y) % 16
    # But width_array is indexed from bottom (row 0 = bottom).
    # Screen row 0 in tile = tile_y * 16, which is the TOP of the tile.
    # Bottom of tile = row 15 in screen space.
    # width_array[0] = bottom row, width_array[15] = top row.
    # So we need: width_row = TILE_SIZE - 1 - row
    width_row = TILE_SIZE - 1 - row

    tile_x = int(sensor_x) // TILE_SIZE
    tile = tile_lookup(tile_x, tile_y)

    if tile is not None and tile.solidity != NOT_SOLID and solidity_filter(tile.solidity):
        wa = tile.width_array()
        width = wa[width_row]
        if width == 0:
            # Extension: check tile to the right
            tile_right = tile_lookup(tile_x + 1, tile_y)
            if tile_right is not None and tile_right.solidity != NOT_SOLID and solidity_filter(tile_right.solidity):
                wa_right = tile_right.width_array()
                width_right = wa_right[width_row]
                if width_right > 0:
                    # Surface is left edge of solid in right tile
                    surface_x = (tile_x + 1) * TILE_SIZE + (TILE_SIZE - width_right)
                    dist = surface_x - sensor_x
                    if abs(dist) <= MAX_SENSOR_RANGE:
                        return SensorResult(found=True, distance=dist, tile_angle=tile_right.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
        elif width == TILE_SIZE:
            # Regression: check tile to the left
            tile_left = tile_lookup(tile_x - 1, tile_y)
            if tile_left is not None and tile_left.solidity != NOT_SOLID and solidity_filter(tile_left.solidity):
                wa_left = tile_left.width_array()
                width_left = wa_left[width_row]
                if width_left < TILE_SIZE:
                    surface_x = (tile_x - 1) * TILE_SIZE + (TILE_SIZE - width_left)
                    dist = surface_x - sensor_x
                    if abs(dist) <= MAX_SENSOR_RANGE:
                        return SensorResult(found=True, distance=dist, tile_angle=tile_left.angle)
            surface_x = tile_x * TILE_SIZE
            dist = surface_x - sensor_x
            if abs(dist) <= MAX_SENSOR_RANGE:
                return SensorResult(found=True, distance=dist, tile_angle=tile.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
        else:
            # Width from the left edge of the tile
            surface_x = tile_x * TILE_SIZE + (TILE_SIZE - width)
            dist = surface_x - sensor_x
            if abs(dist) <= MAX_SENSOR_RANGE:
                return SensorResult(found=True, distance=dist, tile_angle=tile.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
    else:
        # Check tile to the right
        tile_right = tile_lookup(tile_x + 1, tile_y)
        if tile_right is not None and tile_right.solidity != NOT_SOLID and solidity_filter(tile_right.solidity):
            wa_right = tile_right.width_array()
            width_right = wa_right[width_row]
            if width_right > 0:
                surface_x = (tile_x + 1) * TILE_SIZE + (TILE_SIZE - width_right)
                dist = surface_x - sensor_x
                if abs(dist) <= MAX_SENSOR_RANGE:
                    return SensorResult(found=True, distance=dist, tile_angle=tile_right.angle)
        return SensorResult(found=False, distance=0.0, tile_angle=0)


def _sensor_cast_left(
    sensor_x: float,
    sensor_y: float,
    tile_lookup: TileLookup,
    solidity_filter: Callable[[int], bool],
) -> SensorResult:
    """Cast a sensor leftward from (sensor_x, sensor_y)."""
    tile_y = int(sensor_y) // TILE_SIZE
    row = int(sensor_y) % TILE_SIZE
    width_row = TILE_SIZE - 1 - row

    tile_x = int(sensor_x) // TILE_SIZE
    tile = tile_lookup(tile_x, tile_y)

    if tile is not None and tile.solidity != NOT_SOLID and solidity_filter(tile.solidity):
        wa = tile.width_array()
        width = wa[width_row]
        if width == 0:
            # Extension: check tile to the left
            tile_left = tile_lookup(tile_x - 1, tile_y)
            if tile_left is not None and tile_left.solidity != NOT_SOLID and solidity_filter(tile_left.solidity):
                wa_left = tile_left.width_array()
                width_left = wa_left[width_row]
                if width_left > 0:
                    surface_x = (tile_x - 1) * TILE_SIZE + width_left
                    dist = sensor_x - surface_x
                    if abs(dist) <= MAX_SENSOR_RANGE:
                        return SensorResult(found=True, distance=dist, tile_angle=tile_left.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
        elif width == TILE_SIZE:
            # Regression: check tile to the right
            tile_right = tile_lookup(tile_x + 1, tile_y)
            if tile_right is not None and tile_right.solidity != NOT_SOLID and solidity_filter(tile_right.solidity):
                wa_right = tile_right.width_array()
                width_right = wa_right[width_row]
                if width_right < TILE_SIZE:
                    surface_x = (tile_x + 1) * TILE_SIZE + width_right
                    dist = sensor_x - surface_x
                    if abs(dist) <= MAX_SENSOR_RANGE:
                        return SensorResult(found=True, distance=dist, tile_angle=tile_right.angle)
            surface_x = (tile_x + 1) * TILE_SIZE
            dist = sensor_x - surface_x
            if abs(dist) <= MAX_SENSOR_RANGE:
                return SensorResult(found=True, distance=dist, tile_angle=tile.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
        else:
            # Width from left: solid occupies columns 0..width-1
            # Right edge of solid = tile_x * TILE_SIZE + width
            surface_x = tile_x * TILE_SIZE + width
            dist = sensor_x - surface_x
            if abs(dist) <= MAX_SENSOR_RANGE:
                return SensorResult(found=True, distance=dist, tile_angle=tile.angle)
            return SensorResult(found=False, distance=0.0, tile_angle=0)
    else:
        # Check tile to the left
        tile_left = tile_lookup(tile_x - 1, tile_y)
        if tile_left is not None and tile_left.solidity != NOT_SOLID and solidity_filter(tile_left.solidity):
            wa_left = tile_left.width_array()
            width_left = wa_left[width_row]
            if width_left > 0:
                surface_x = (tile_x - 1) * TILE_SIZE + width_left
                dist = sensor_x - surface_x
                if abs(dist) <= MAX_SENSOR_RANGE:
                    return SensorResult(found=True, distance=dist, tile_angle=tile_left.angle)
        return SensorResult(found=False, distance=0.0, tile_angle=0)


# ---------------------------------------------------------------------------
# Sensor cast dispatcher
# ---------------------------------------------------------------------------

_CAST_FUNCS = {
    DOWN: _sensor_cast_down,
    UP: _sensor_cast_up,
    RIGHT: _sensor_cast_right,
    LEFT: _sensor_cast_left,
}


def _sensor_cast(
    sensor_x: float,
    sensor_y: float,
    direction: int,
    tile_lookup: TileLookup,
    solidity_filter: Callable[[int], bool],
) -> SensorResult:
    """Dispatch a sensor cast in the given direction."""
    return _CAST_FUNCS[direction](sensor_x, sensor_y, tile_lookup, solidity_filter)


# ---------------------------------------------------------------------------
# Solidity filters
# ---------------------------------------------------------------------------

def _floor_solidity_filter(y_vel: float) -> Callable[[int], bool]:
    """Return a filter for floor sensors. Top-only tiles collide only when y_vel >= 0."""
    def _filter(solidity: int) -> bool:
        if solidity == TOP_ONLY:
            return y_vel >= 0
        return solidity != NOT_SOLID
    return _filter


def _no_top_only_filter(solidity: int) -> bool:
    """Filter that rejects top-only tiles (for ceiling and wall sensors)."""
    return solidity not in (NOT_SOLID, TOP_ONLY)


# ---------------------------------------------------------------------------
# Quadrant direction tables
# ---------------------------------------------------------------------------

# (floor_direction, ceiling_direction)
_QUADRANT_FLOOR_CEILING = {
    0: (DOWN, UP),
    1: (RIGHT, LEFT),
    2: (UP, DOWN),
    3: (LEFT, RIGHT),
}


# ---------------------------------------------------------------------------
# Floor sensors (A/B)
# ---------------------------------------------------------------------------

def find_floor(state: PhysicsState, tile_lookup: TileLookup) -> SensorResult:
    """Run floor sensors A and B, return the winning result.

    A wins ties. Returns the sensor with shorter distance to surface.
    """
    quadrant = get_quadrant(state.angle)
    floor_dir = _QUADRANT_FLOOR_CEILING[quadrant][0]
    w_rad, h_rad = _get_radii(state)

    sol_filter = _floor_solidity_filter(state.y_vel)

    # Compute sensor A and B positions based on quadrant
    if quadrant == 0:  # normal: A/B at feet, spread by width_radius
        a_x = state.x - w_rad
        a_y = state.y + h_rad
        b_x = state.x + w_rad
        b_y = state.y + h_rad
    elif quadrant == 1:  # right wall: A/B to the right, spread vertically
        a_x = state.x + h_rad
        a_y = state.y + w_rad
        b_x = state.x + h_rad
        b_y = state.y - w_rad
    elif quadrant == 2:  # ceiling: A/B at head, spread by width_radius
        a_x = state.x + w_rad
        a_y = state.y - h_rad
        b_x = state.x - w_rad
        b_y = state.y - h_rad
    else:  # left wall: A/B to the left, spread vertically
        a_x = state.x - h_rad
        a_y = state.y - w_rad
        b_x = state.x - h_rad
        b_y = state.y + w_rad

    result_a = _sensor_cast(a_x, a_y, floor_dir, tile_lookup, sol_filter)
    result_b = _sensor_cast(b_x, b_y, floor_dir, tile_lookup, sol_filter)

    if not result_a.found and not result_b.found:
        return SensorResult(found=False, distance=0.0, tile_angle=0)
    if not result_b.found:
        return result_a
    if not result_a.found:
        return result_b

    # Both found: use shorter distance (closer to sensor). A wins ties.
    if abs(result_a.distance) <= abs(result_b.distance):
        return result_a
    return result_b


# ---------------------------------------------------------------------------
# Ceiling sensors (C/D)
# ---------------------------------------------------------------------------

def find_ceiling(state: PhysicsState, tile_lookup: TileLookup) -> SensorResult:
    """Run ceiling sensors C and D, return the winning result."""
    quadrant = get_quadrant(state.angle)
    ceiling_dir = _QUADRANT_FLOOR_CEILING[quadrant][1]
    w_rad, h_rad = _get_radii(state)

    # Compute sensor C and D positions (opposite side of floor sensors)
    if quadrant == 0:  # normal: C/D at head
        c_x = state.x - w_rad
        c_y = state.y - h_rad
        d_x = state.x + w_rad
        d_y = state.y - h_rad
    elif quadrant == 1:  # right wall: C/D to the left
        c_x = state.x - h_rad
        c_y = state.y + w_rad
        d_x = state.x - h_rad
        d_y = state.y - w_rad
    elif quadrant == 2:  # ceiling: C/D at feet
        c_x = state.x + w_rad
        c_y = state.y + h_rad
        d_x = state.x - w_rad
        d_y = state.y + h_rad
    else:  # left wall: C/D to the right
        c_x = state.x + h_rad
        c_y = state.y - w_rad
        d_x = state.x + h_rad
        d_y = state.y + w_rad

    result_c = _sensor_cast(c_x, c_y, ceiling_dir, tile_lookup, _no_top_only_filter)
    result_d = _sensor_cast(d_x, d_y, ceiling_dir, tile_lookup, _no_top_only_filter)

    if not result_c.found and not result_d.found:
        return SensorResult(found=False, distance=0.0, tile_angle=0)
    if not result_d.found:
        return result_c
    if not result_c.found:
        return result_d

    if abs(result_c.distance) <= abs(result_d.distance):
        return result_c
    return result_d


# ---------------------------------------------------------------------------
# Wall sensors (E/F)
# ---------------------------------------------------------------------------

def find_wall_push(
    state: PhysicsState, tile_lookup: TileLookup, wall_direction: int
) -> SensorResult:
    """Run wall sensor E (left) or F (right).

    wall_direction: LEFT for E sensor, RIGHT for F sensor (in normal quadrant).
    Disabled when moving away from the wall.
    """
    quadrant = get_quadrant(state.angle)
    w_rad, h_rad = _get_radii(state)

    # Check if moving away from wall (disable sensor)
    if quadrant in (0, 2):  # horizontal walls
        if wall_direction == LEFT and state.x_vel > 0:
            return SensorResult(found=False, distance=0.0, tile_angle=0)
        if wall_direction == RIGHT and state.x_vel < 0:
            return SensorResult(found=False, distance=0.0, tile_angle=0)
    else:  # vertical walls (quadrants 1, 3)
        if wall_direction == UP and state.y_vel > 0:
            return SensorResult(found=False, distance=0.0, tile_angle=0)
        if wall_direction == DOWN and state.y_vel < 0:
            return SensorResult(found=False, distance=0.0, tile_angle=0)

    # Wall sensor direction depends on quadrant
    if quadrant in (0, 2):  # horizontal wall sensors
        cast_dir = wall_direction  # LEFT or RIGHT
        sensor_x = state.x + (WALL_SENSOR_EXTENT if wall_direction == RIGHT else -WALL_SENSOR_EXTENT)
        sensor_y = state.y
    else:  # vertical wall sensors (quadrants 1, 3)
        # In wall mode, wall sensors cast vertically
        cast_dir = wall_direction
        sensor_x = state.x
        sensor_y = state.y + (WALL_SENSOR_EXTENT if wall_direction == DOWN else -WALL_SENSOR_EXTENT)

    result = _sensor_cast(sensor_x, sensor_y, cast_dir, tile_lookup, _no_top_only_filter)

    # Angle gate: ignore hits on floor-range tiles (loop entry ramps, gentle slopes).
    # Only tiles whose angle is genuinely wall-like (steeper than ~67°) should block.
    if result.found:
        a = result.tile_angle
        if a <= WALL_ANGLE_THRESHOLD or a >= ANGLE_STEPS - WALL_ANGLE_THRESHOLD:
            return SensorResult(found=False, distance=0.0, tile_angle=0)

    return result


# ---------------------------------------------------------------------------
# Top-level collision resolution
# ---------------------------------------------------------------------------

# Ground snap tolerance: how far below the surface the player can be and still snap
_GROUND_SNAP_DISTANCE = 14.0
# Air landing threshold: sensor must detect surface within this distance
_AIR_LAND_DISTANCE = 16.0


def resolve_collision(state: PhysicsState, tile_lookup: TileLookup) -> None:
    """Run all sensors and resolve collision. Steps 5–7 of the frame update.

    Modifies state in place: x, y, angle, on_ground, x_vel, y_vel.
    """
    quadrant = get_quadrant(state.angle)

    # --- Floor sensors ---
    floor_result = find_floor(state, tile_lookup)

    if state.on_ground:
        if floor_result.found and abs(floor_result.distance) <= _GROUND_SNAP_DISTANCE:
            # Snap to surface
            _snap_to_floor(state, floor_result, quadrant)
            # Two-pass: if snapping changed the active quadrant, re-run the floor
            # sensor immediately with the new quadrant so the position is fully
            # corrected this frame instead of one frame later.
            new_quadrant = get_quadrant(state.angle)
            if new_quadrant != quadrant:
                floor_result2 = find_floor(state, tile_lookup)
                if floor_result2.found and abs(floor_result2.distance) <= _GROUND_SNAP_DISTANCE:
                    _snap_to_floor(state, floor_result2, new_quadrant)
        else:
            # No floor — detach
            state.on_ground = False
            state.angle = 0
    else:
        # Airborne: check for landing
        if floor_result.found and state.y_vel >= 0:
            # Land when surface is within snap range (at or slightly past feet)
            if floor_result.distance <= _AIR_LAND_DISTANCE:
                _snap_to_floor(state, floor_result, quadrant)
                state.on_ground = True
                state.angle = floor_result.tile_angle
                calculate_landing_speed(state)

    # --- Wall sensors ---
    wall_left = find_wall_push(state, tile_lookup, LEFT)
    wall_right = find_wall_push(state, tile_lookup, RIGHT)

    if wall_left.found and wall_left.distance < 0:
        # Push right (away from left wall)
        if quadrant in (0, 2):
            state.x -= wall_left.distance  # distance is negative, so this pushes right
            if state.x_vel < 0:
                state.x_vel = 0.0
                if state.on_ground:
                    state.ground_speed = 0.0
        else:
            state.y -= wall_left.distance
            if state.y_vel < 0:
                state.y_vel = 0.0

    if wall_right.found and wall_right.distance < 0:
        # Push left (away from right wall)
        if quadrant in (0, 2):
            state.x += wall_right.distance  # distance is negative, so this pushes left
            if state.x_vel > 0:
                state.x_vel = 0.0
                if state.on_ground:
                    state.ground_speed = 0.0
        else:
            state.y += wall_right.distance
            if state.y_vel > 0:
                state.y_vel = 0.0

    # --- Ceiling sensors (only when airborne or in ceiling/wall quadrant) ---
    if not state.on_ground or quadrant != 0:
        ceiling_result = find_ceiling(state, tile_lookup)
        if ceiling_result.found and ceiling_result.distance < 0:
            if quadrant == 0:
                # Normal mode: push down, zero upward velocity
                state.y -= ceiling_result.distance  # distance is negative
                if state.y_vel < 0:
                    state.y_vel = 0.0
            elif quadrant == 2:
                # Ceiling mode: push up
                state.y += ceiling_result.distance
                if state.y_vel > 0:
                    state.y_vel = 0.0


def _snap_to_floor(state: PhysicsState, result: SensorResult, quadrant: int) -> None:
    """Snap player position to the detected floor surface."""
    if quadrant == 0:
        state.y += result.distance
    elif quadrant == 1:
        state.x += result.distance
    elif quadrant == 2:
        state.y -= result.distance
    else:
        state.x -= result.distance
    state.angle = result.tile_angle

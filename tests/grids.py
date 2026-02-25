"""Synthetic tile-grid builders for physics tests.

Each builder returns a TileLookup callable that maps (tx, ty) -> Tile | None.
No Pyxel imports. No stage files on disk.
"""

from __future__ import annotations

import math
from typing import Optional

from speednik.terrain import FULL, SURFACE_LOOP, TILE_SIZE, TOP_ONLY, Tile, TileLookup

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FILL_DEPTH = 4  # rows of solid fill below the surface


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _wrap(tiles: dict[tuple[int, int], Tile]) -> TileLookup:
    """Wrap a tile dict as a TileLookup callable."""
    def lookup(tx: int, ty: int) -> Optional[Tile]:
        return tiles.get((tx, ty))
    return lookup


def _flat_tile(angle: int = 0, solidity: int = FULL, tile_type: int = 0) -> Tile:
    """Create a flat full tile."""
    return Tile(height_array=[TILE_SIZE] * TILE_SIZE, angle=angle, solidity=solidity,
                tile_type=tile_type)


def _fill_below(tiles: dict[tuple[int, int], Tile], tx: int, ground_row: int) -> None:
    """Add FILL_DEPTH rows of solid fill below ground_row at column tx."""
    for ty in range(ground_row + 1, ground_row + 1 + FILL_DEPTH):
        if (tx, ty) not in tiles:
            tiles[(tx, ty)] = _flat_tile()


def _slope_height_array(angle_byte: int, col_offset: float = 0.0) -> list[int]:
    """Compute a 16-element height array for a tile at the given byte angle.

    angle_byte: surface angle in byte-angle format (0-255).
    col_offset: pixel offset from the slope origin (shifts the baseline).

    The height array represents solid height from the bottom of the tile at
    each of the 16 pixel columns. A positive slope (angle < 128) rises from
    left to right.
    """
    rad = angle_byte * (2.0 * math.pi / 256)
    # slope = -tan(rad) because positive byte angles = surface tilting right
    # which means height increases left-to-right
    slope = -math.tan(rad)

    heights: list[int] = []
    for col in range(TILE_SIZE):
        # Height at this column: base height + slope contribution
        # Base height is 8 (middle of tile) + offset from col_offset
        h = 8.0 + (col_offset + col - 7.5) * slope
        h_clamped = max(0, min(TILE_SIZE, round(h)))
        heights.append(h_clamped)
    return heights


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def build_flat(width_tiles: int, ground_row: int) -> tuple[dict[tuple[int, int], Tile], TileLookup]:
    """Flat ground spanning width_tiles columns at ground_row.

    All surface tiles: height_array=[16]*16, angle=0, solidity=FULL.
    Fill tiles below ground_row to prevent sensor fall-through.

    Returns (tiles_dict, tile_lookup).
    """
    tiles: dict[tuple[int, int], Tile] = {}
    for tx in range(width_tiles):
        tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)
    return tiles, _wrap(tiles)


def build_gap(
    approach_tiles: int,
    gap_tiles: int,
    landing_tiles: int,
    ground_row: int,
) -> tuple[dict[tuple[int, int], Tile], TileLookup]:
    """Flat approach, gap (no tiles), flat landing.

    Fill below approach and landing but not the gap.

    Returns (tiles_dict, tile_lookup).
    """
    tiles: dict[tuple[int, int], Tile] = {}

    # Approach
    for tx in range(approach_tiles):
        tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    # Gap: no tiles at all (approach_tiles .. approach_tiles + gap_tiles - 1)

    # Landing
    landing_start = approach_tiles + gap_tiles
    for i in range(landing_tiles):
        tx = landing_start + i
        tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    return tiles, _wrap(tiles)


def build_slope(
    approach_tiles: int,
    slope_tiles: int,
    angle: int,
    ground_row: int,
) -> tuple[dict[tuple[int, int], Tile], TileLookup]:
    """Flat approach, then a constant-angle slope.

    angle: byte angle (0-255). The slope tiles all have this angle.
    Height arrays computed from the slope geometry.

    Returns (tiles_dict, tile_lookup).
    """
    tiles: dict[tuple[int, int], Tile] = {}

    # Flat approach
    for tx in range(approach_tiles):
        tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    # Slope tiles
    for i in range(slope_tiles):
        tx = approach_tiles + i
        # col_offset shifts the height profile for continuity across tiles
        col_offset = i * TILE_SIZE
        ha = _slope_height_array(angle, col_offset)
        tiles[(tx, ground_row)] = Tile(
            height_array=ha, angle=angle, solidity=FULL
        )
        _fill_below(tiles, tx, ground_row)

    return tiles, _wrap(tiles)


def build_ramp(
    approach_tiles: int,
    ramp_tiles: int,
    start_angle: int,
    end_angle: int,
    ground_row: int,
) -> tuple[dict[tuple[int, int], Tile], TileLookup]:
    """Flat approach, then a ramp with linearly interpolated angles.

    Angles transition from start_angle to end_angle across ramp_tiles.
    Each ramp tile gets an interpolated angle and a matching height array.

    Returns (tiles_dict, tile_lookup).
    """
    tiles: dict[tuple[int, int], Tile] = {}

    # Flat approach
    for tx in range(approach_tiles):
        tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    # Ramp tiles
    for i in range(ramp_tiles):
        tx = approach_tiles + i
        # Interpolate angle (handle wraparound for small ranges)
        if ramp_tiles == 1:
            t = 0.5
        else:
            t = i / (ramp_tiles - 1)

        # Linear interpolation in byte-angle space
        # For small angle ranges this is fine; large ranges could wrap
        angle = round(start_angle + t * (end_angle - start_angle)) % 256

        col_offset = i * TILE_SIZE
        ha = _slope_height_array(angle, col_offset)
        tiles[(tx, ground_row)] = Tile(
            height_array=ha, angle=angle, solidity=FULL
        )
        _fill_below(tiles, tx, ground_row)

    return tiles, _wrap(tiles)


def build_loop(
    approach_tiles: int,
    radius: int,
    ground_row: int,
    ramp_radius: int | None = None,
) -> tuple[dict[tuple[int, int], Tile], TileLookup]:
    """Flat approach, full 360-degree loop, flat exit.

    radius: loop radius in pixels.
    ground_row: tile row of the ground surface.
    ramp_radius: if given, includes entry/exit quarter-circle ramps.

    Loop tiles: tile_type=SURFACE_LOOP, upper arc solidity=TOP_ONLY,
    lower arc solidity=FULL. Interior is hollow.

    Returns (tiles_dict, tile_lookup).
    """
    tiles: dict[tuple[int, int], Tile] = {}
    two_pi = 2.0 * math.pi

    # Ground y in pixels (bottom of ground_row tile = top of surface)
    ground_y = ground_row * TILE_SIZE  # top edge of ground_row

    # Circle center
    # The ground surface is at the top of ground_row tiles.
    # The bottom of the loop touches the ground, so cy = ground_y - radius.
    cy = ground_y - radius
    r_ramp = ramp_radius if ramp_radius is not None else 0

    # Pixel x layout
    approach_px = approach_tiles * TILE_SIZE
    ramp_entry_start = approach_px
    loop_start = approach_px + r_ramp
    loop_end = loop_start + 2 * radius
    ramp_exit_end = loop_end + r_ramp
    cx = loop_start + radius

    # --- Flat approach ---
    for tx in range(approach_tiles):
        tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    # --- Entry ramp (quarter-circle arc) ---
    if r_ramp > 0:
        entry_arc_cx = float(loop_start)
        for px in range(ramp_entry_start, loop_start):
            dx = px - entry_arc_cx
            val = max(0.0, r_ramp * r_ramp - dx * dx)
            sy = cy + math.sqrt(val)
            sy = min(sy, float(ground_y))

            # Angle from finite difference
            dx1 = (px + 1) - entry_arc_cx
            val1 = max(0.0, r_ramp * r_ramp - dx1 * dx1)
            sy1 = cy + math.sqrt(val1)
            sy1 = min(sy1, float(ground_y))
            slope = sy1 - sy
            angle = round(-math.atan2(slope, 1.0) * 256 / two_pi) % 256

            tx = px // TILE_SIZE
            local_x = px % TILE_SIZE

            if (tx, ground_row) not in tiles:
                tiles[(tx, ground_row)] = Tile(
                    height_array=[0] * TILE_SIZE, angle=angle, solidity=FULL
                )
            tile = tiles[(tx, ground_row)]
            # Height from bottom of tile
            tile_bottom_y = (ground_row + 1) * TILE_SIZE
            h = max(0, min(TILE_SIZE, round(tile_bottom_y - sy)))
            tile.height_array[local_x] = max(tile.height_array[local_x], h)
            tile.angle = angle

            _fill_below(tiles, tx, ground_row)

    # --- Loop circle ---
    # Track which tile positions are upper vs lower arc
    upper_tiles: set[tuple[int, int]] = set()
    lower_tiles: set[tuple[int, int]] = set()

    for px in range(loop_start, loop_end):
        dx = px - cx + 0.5  # pixel center
        if abs(dx) > radius:
            continue

        dy = math.sqrt(radius * radius - dx * dx)
        y_bottom = cy + dy
        y_top = cy - dy

        # Bottom arc
        angle_bottom = round(-math.atan2(dx, dy) * 256 / two_pi) % 256
        tx_b = px // TILE_SIZE
        local_x = px % TILE_SIZE
        ty_b = int(y_bottom) // TILE_SIZE

        key_b = (tx_b, ty_b)
        if key_b not in tiles:
            tiles[key_b] = Tile(
                height_array=[0] * TILE_SIZE,
                angle=angle_bottom,
                solidity=FULL,
                tile_type=SURFACE_LOOP,
            )
        tiles[key_b].height_array[local_x] = TILE_SIZE
        tiles[key_b].angle = angle_bottom
        tiles[key_b].tile_type = SURFACE_LOOP
        lower_tiles.add(key_b)

        # Top arc
        angle_top = round(-math.atan2(-dx, -dy) * 256 / two_pi) % 256
        ty_t = int(y_top) // TILE_SIZE

        key_t = (tx_b, ty_t)
        if key_t not in tiles:
            tiles[key_t] = Tile(
                height_array=[0] * TILE_SIZE,
                angle=angle_top,
                solidity=TOP_ONLY,
                tile_type=SURFACE_LOOP,
            )
        tiles[key_t].height_array[local_x] = TILE_SIZE
        tiles[key_t].angle = angle_top
        tiles[key_t].tile_type = SURFACE_LOOP
        upper_tiles.add(key_t)

        # Fill below bottom arc
        for fill_ty in range(ty_b + 1, ty_b + 1 + FILL_DEPTH):
            if (tx_b, fill_ty) not in tiles:
                tiles[(tx_b, fill_ty)] = _flat_tile()

    # Fix solidity: tiles that are ONLY upper get TOP_ONLY,
    # tiles that are lower (or both) get FULL
    for key in upper_tiles:
        if key not in lower_tiles:
            tiles[key].solidity = TOP_ONLY
        else:
            tiles[key].solidity = FULL

    for key in lower_tiles:
        tiles[key].solidity = FULL

    # --- Exit ramp (quarter-circle arc) ---
    if r_ramp > 0:
        exit_arc_cx = float(loop_end)
        for px in range(loop_end, ramp_exit_end):
            dx = px - exit_arc_cx
            val = max(0.0, r_ramp * r_ramp - dx * dx)
            sy = cy + math.sqrt(val)
            sy = min(sy, float(ground_y))

            dx1 = (px + 1) - exit_arc_cx
            val1 = max(0.0, r_ramp * r_ramp - dx1 * dx1)
            sy1 = cy + math.sqrt(val1)
            sy1 = min(sy1, float(ground_y))
            slope = sy1 - sy
            angle = round(-math.atan2(slope, 1.0) * 256 / two_pi) % 256

            tx = px // TILE_SIZE
            local_x = px % TILE_SIZE

            if (tx, ground_row) not in tiles:
                tiles[(tx, ground_row)] = Tile(
                    height_array=[0] * TILE_SIZE, angle=angle, solidity=FULL
                )
            tile = tiles[(tx, ground_row)]
            tile_bottom_y = (ground_row + 1) * TILE_SIZE
            h = max(0, min(TILE_SIZE, round(tile_bottom_y - sy)))
            tile.height_array[local_x] = max(tile.height_array[local_x], h)
            tile.angle = angle

            _fill_below(tiles, tx, ground_row)

    # --- Flat exit (1 tile after ramp/loop) ---
    exit_start_px = ramp_exit_end
    exit_tx_start = (exit_start_px + TILE_SIZE - 1) // TILE_SIZE
    # Add a few flat exit tiles
    for i in range(approach_tiles):
        tx = exit_tx_start + i
        tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    return tiles, _wrap(tiles)

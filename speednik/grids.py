"""Synthetic tile-grid builders for physics scenarios and dev park.

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
    Surface traced pixel-by-pixel and placed in the correct tile rows,
    supporting slopes steeper than 45°.

    Returns (tiles_dict, tile_lookup).
    """
    tiles: dict[tuple[int, int], Tile] = {}

    # Flat approach
    for tx in range(approach_tiles):
        tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    # Slope surface: trace each pixel column
    angle_rad = angle * (2.0 * math.pi / 256)
    slope = math.tan(angle_rad)  # rise per horizontal pixel
    # Baseline: top of the ground surface (bottom of ground_row tile area)
    base_y = float((ground_row + 1) * TILE_SIZE)
    slope_start_px = approach_tiles * TILE_SIZE

    for i in range(slope_tiles * TILE_SIZE):
        px = slope_start_px + i
        # Surface rises as we move right (y decreases in screen coords)
        surface_y = base_y - i * slope

        tx = px // TILE_SIZE
        ty = int(surface_y) // TILE_SIZE
        local_x = px % TILE_SIZE
        tile_bottom_y = (ty + 1) * TILE_SIZE

        # Create tile if it doesn't exist yet
        if (tx, ty) not in tiles:
            tiles[(tx, ty)] = Tile(
                height_array=[0] * TILE_SIZE, angle=angle, solidity=FULL
            )

        # Height from bottom of tile to the surface
        h = max(0, min(TILE_SIZE, round(tile_bottom_y - surface_y)))
        tiles[(tx, ty)].height_array[local_x] = max(
            tiles[(tx, ty)].height_array[local_x], h
        )

        _fill_below(tiles, tx, ty)

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
    # The entry ramp places tiles at ground_row with progressive angles that
    # rotate the player's sensor quadrant from Q0 to Q1, guiding it onto the
    # loop's right wall. The tiles use full height at ground_row; the angles
    # (not the heights) are what drive the player upward into the loop.
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
            tile_bottom_y = (ground_row + 1) * TILE_SIZE
            h = max(0, min(TILE_SIZE, round(tile_bottom_y - sy)))
            tile.height_array[local_x] = max(tile.height_array[local_x], h)
            tile.angle = angle

            _fill_below(tiles, tx, ground_row)

    # --- Loop circle ---
    # Iterate the full circumference, sampling at sub-pixel angular resolution.
    # For each sample point, compute the tile it falls in and record the surface
    # position + traversal angle. The traversal angle follows a continuous
    # clockwise progression (0=bottom, 64=right wall, 128=ceiling, 192=left wall).
    #
    # This produces tiles for the full circle including the bottom arc,
    # ensuring the player can smoothly transition through all four quadrants.
    arc_data: dict[tuple[int, int], list[tuple[int, float, int]]] = {}
    fill_rows: set[tuple[int, int]] = set()

    # Number of angular samples — at least 4 samples per pixel around circumference
    circumference = int(two_pi * radius)
    num_samples = max(circumference * 4, 512)

    for i in range(num_samples):
        # Polar angle theta: 0 = bottom, increases clockwise (in screen coords)
        theta = i * two_pi / num_samples
        # Circle point (screen coords: y increases downward)
        px_f = cx + radius * math.sin(theta)
        py_f = cy + radius * math.cos(theta)

        px = int(px_f)
        py = int(py_f)
        if px < loop_start or px >= loop_end:
            continue

        tx = px // TILE_SIZE
        ty = py // TILE_SIZE
        local_x = px % TILE_SIZE

        # Traversal angle: byte angle = theta * 256 / (2*pi)
        # This is the surface angle the player should see when traversing
        # the loop clockwise. 0=flat bottom, 64=right wall going up,
        # 128=ceiling, 192=left wall going down.
        traversal_angle = round(theta * 256 / two_pi) % 256

        key = (tx, ty)
        arc_data.setdefault(key, []).append((local_x, py_f, traversal_angle))

        # Fill below bottom arc (bottom half only: theta < pi)
        if theta < math.pi * 0.1 or theta > math.pi * 1.9:
            for fill_ty in range(ty + 1, ty + 1 + FILL_DEPTH):
                fill_rows.add((tx, fill_ty))

    # Build tiles from collected per-pixel data
    for key, pixels in arc_data.items():
        tx, ty = key
        tile_bottom_y = (ty + 1) * TILE_SIZE
        if key not in tiles:
            tiles[key] = Tile(
                height_array=[0] * TILE_SIZE, angle=0,
                solidity=FULL, tile_type=SURFACE_LOOP,
            )
        tile = tiles[key]
        tile.solidity = FULL
        tile.tile_type = SURFACE_LOOP
        for local_x, surface_y, _angle in pixels:
            h = max(0, min(TILE_SIZE, round(tile_bottom_y - surface_y)))
            tile.height_array[local_x] = max(tile.height_array[local_x], h)
        # Tile angle: use midpoint sample's angle
        mid = pixels[len(pixels) // 2]
        tile.angle = mid[2]

    for key in fill_rows:
        if key not in tiles:
            tiles[key] = _flat_tile()

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

    # --- Flat exit ---
    # Larger loops launch the player higher, so the ballistic arc covers more
    # horizontal distance before landing. Scale exit tiles accordingly.
    exit_start_px = ramp_exit_end
    exit_tx_start = (exit_start_px + TILE_SIZE - 1) // TILE_SIZE
    exit_tile_count = approach_tiles + 2 * ((radius + TILE_SIZE - 1) // TILE_SIZE)
    for i in range(exit_tile_count):
        tx = exit_tx_start + i
        tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    return tiles, _wrap(tiles)

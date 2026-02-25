#!/usr/bin/env python3
"""SVG-to-stage pipeline CLI.

Converts designer-drawn SVG files into tile map, collision data, and entity
placement that the speednik engine loads.

Usage:
    python tools/svg2stage.py input.svg output_dir/

Reference: docs/specification.md section 4.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TILE_SIZE = 16

# Surface types (stored in tile_map.json "type" field)
SURFACE_EMPTY = 0
SURFACE_SOLID = 1
SURFACE_TOP_ONLY = 2
SURFACE_SLOPE = 3
SURFACE_HAZARD = 4
SURFACE_LOOP = 5

# Solidity flags (matching speednik/terrain.py)
NOT_SOLID = 0
TOP_ONLY = 1
FULL = 2

# Stroke color → surface type
STROKE_COLOR_MAP: dict[str, int] = {
    "#00aa00": SURFACE_SOLID,
    "#0000ff": SURFACE_TOP_ONLY,
    "#ff8800": SURFACE_SLOPE,
    "#ff0000": SURFACE_HAZARD,
}

# Surface type → solidity
SOLIDITY_MAP: dict[int, int] = {
    SURFACE_EMPTY: NOT_SOLID,
    SURFACE_SOLID: FULL,
    SURFACE_TOP_ONLY: TOP_ONLY,
    SURFACE_SLOPE: FULL,
    SURFACE_HAZARD: FULL,
    SURFACE_LOOP: FULL,
}

# Known entity types (ordered longest-first for prefix matching)
ENTITY_TYPES: list[str] = sorted(
    [
        "player_start",
        "liquid_trigger",
        "enemy_buzzer",
        "enemy_chopper",
        "spring_right",
        "enemy_crab",
        "checkpoint",
        "spring_up",
        "pipe_h",
        "pipe_v",
        "ring",
        "goal",
    ],
    key=len,
    reverse=True,
)

# SVG namespace
SVG_NS = "http://www.w3.org/2000/svg"

# Angle consistency threshold in byte-angle units (~30°)
ANGLE_CONSISTENCY_THRESHOLD = 21

# Minimum gap size in pixels to not flag as impassable
MIN_GAP_PX = 18

# Maximum consecutive steep tiles without loop flag
MAX_STEEP_RUN = 3

# Steep angle range in byte angles (> 45°)
STEEP_LOW = 32   # ~45° clockwise from flat
STEEP_HIGH = 224  # ~45° counter-clockwise from flat


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Point:
    x: float
    y: float


@dataclass
class PathSegment:
    kind: str  # 'line', 'cubic', 'quad'
    points: list[Point]  # For line: [start, end]; cubic: [p0,p1,p2,p3]; quad: [p0,p1,p2]


@dataclass
class TerrainShape:
    segments: list[PathSegment]
    surface_type: int
    is_loop: bool = False
    center: Point | None = None


@dataclass
class Entity:
    entity_type: str
    x: float
    y: float


@dataclass
class TileData:
    surface_type: int = SURFACE_SOLID
    height_array: list[int] = field(default_factory=lambda: [0] * 16)
    angle: int = 0
    is_loop_upper: bool = False


class TileGrid:
    """2D grid of tile data."""

    def __init__(self, cols: int, rows: int) -> None:
        self.cols = cols
        self.rows = rows
        self._tiles: list[list[TileData | None]] = [
            [None for _ in range(cols)] for _ in range(rows)
        ]

    def set_tile(self, tx: int, ty: int, data: TileData) -> None:
        if 0 <= tx < self.cols and 0 <= ty < self.rows:
            self._tiles[ty][tx] = data

    def get_tile(self, tx: int, ty: int) -> TileData | None:
        if 0 <= tx < self.cols and 0 <= ty < self.rows:
            return self._tiles[ty][tx]
        return None


# ---------------------------------------------------------------------------
# SVG path 'd' attribute parser
# ---------------------------------------------------------------------------

_PATH_CMD_RE = re.compile(r"([MmLlHhVvCcQqZz])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)")


def parse_path_d(d: str) -> list[PathSegment]:
    """Parse SVG path 'd' attribute into a list of PathSegments."""
    tokens = _PATH_CMD_RE.findall(d)
    segments: list[PathSegment] = []
    current = Point(0.0, 0.0)
    start = Point(0.0, 0.0)

    i = 0

    def _next_num() -> float:
        nonlocal i
        while i < len(tokens) and tokens[i][0]:
            i += 1  # skip command tokens
        if i >= len(tokens):
            raise ValueError("Unexpected end of path data")
        val = float(tokens[i][1])
        i += 1
        return val

    while i < len(tokens):
        cmd_str, num_str = tokens[i]
        if cmd_str:
            cmd = cmd_str
            i += 1
        elif num_str:
            # Implicit repeat of previous command
            pass
        else:
            i += 1
            continue

        if cmd in ("M", "m"):
            x, y = _next_num(), _next_num()
            if cmd == "m":
                x += current.x
                y += current.y
            current = Point(x, y)
            start = Point(x, y)
            # Implicit L/l after first M coordinate pair
            while i < len(tokens) and not tokens[i][0]:
                x, y = _next_num(), _next_num()
                if cmd == "m":
                    x += current.x
                    y += current.y
                p_end = Point(x, y)
                segments.append(PathSegment("line", [Point(current.x, current.y), p_end]))
                current = p_end

        elif cmd in ("L", "l"):
            while i < len(tokens) and not tokens[i][0]:
                x, y = _next_num(), _next_num()
                if cmd == "l":
                    x += current.x
                    y += current.y
                p_end = Point(x, y)
                segments.append(PathSegment("line", [Point(current.x, current.y), p_end]))
                current = p_end

        elif cmd in ("H", "h"):
            while i < len(tokens) and not tokens[i][0]:
                x = _next_num()
                if cmd == "h":
                    x += current.x
                p_end = Point(x, current.y)
                segments.append(PathSegment("line", [Point(current.x, current.y), p_end]))
                current = p_end

        elif cmd in ("V", "v"):
            while i < len(tokens) and not tokens[i][0]:
                y = _next_num()
                if cmd == "v":
                    y += current.y
                p_end = Point(current.x, y)
                segments.append(PathSegment("line", [Point(current.x, current.y), p_end]))
                current = p_end

        elif cmd in ("C", "c"):
            while i < len(tokens) and not tokens[i][0]:
                x1, y1 = _next_num(), _next_num()
                x2, y2 = _next_num(), _next_num()
                x, y = _next_num(), _next_num()
                if cmd == "c":
                    x1 += current.x; y1 += current.y
                    x2 += current.x; y2 += current.y
                    x += current.x; y += current.y
                seg = PathSegment("cubic", [
                    Point(current.x, current.y),
                    Point(x1, y1),
                    Point(x2, y2),
                    Point(x, y),
                ])
                segments.append(seg)
                current = Point(x, y)

        elif cmd in ("Q", "q"):
            while i < len(tokens) and not tokens[i][0]:
                x1, y1 = _next_num(), _next_num()
                x, y = _next_num(), _next_num()
                if cmd == "q":
                    x1 += current.x; y1 += current.y
                    x += current.x; y += current.y
                seg = PathSegment("quad", [
                    Point(current.x, current.y),
                    Point(x1, y1),
                    Point(x, y),
                ])
                segments.append(seg)
                current = Point(x, y)

        elif cmd in ("Z", "z"):
            if current.x != start.x or current.y != start.y:
                segments.append(PathSegment("line", [Point(current.x, current.y), Point(start.x, start.y)]))
            current = Point(start.x, start.y)

    return segments


# ---------------------------------------------------------------------------
# Transform utilities
# ---------------------------------------------------------------------------

def _identity_matrix() -> list[list[float]]:
    return [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def _multiply_matrices(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    result = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                result[i][j] += a[i][k] * b[k][j]
    return result


def _parse_transform(attr: str) -> list[list[float]]:
    """Parse an SVG transform attribute into a 3x3 matrix."""
    result = _identity_matrix()
    for match in re.finditer(r"(\w+)\s*\(([^)]*)\)", attr):
        name = match.group(1)
        args = [float(x) for x in re.split(r"[\s,]+", match.group(2).strip())]
        m = _identity_matrix()
        if name == "translate":
            m[0][2] = args[0]
            m[1][2] = args[1] if len(args) > 1 else 0
        elif name == "scale":
            m[0][0] = args[0]
            m[1][1] = args[1] if len(args) > 1 else args[0]
        elif name == "rotate":
            angle_rad = math.radians(args[0])
            c, s = math.cos(angle_rad), math.sin(angle_rad)
            m[0][0] = c; m[0][1] = -s
            m[1][0] = s; m[1][1] = c
            if len(args) == 3:
                # rotate(angle, cx, cy)
                cx, cy = args[1], args[2]
                pre = _identity_matrix()
                pre[0][2] = cx; pre[1][2] = cy
                post = _identity_matrix()
                post[0][2] = -cx; post[1][2] = -cy
                m = _multiply_matrices(pre, _multiply_matrices(m, post))
        elif name == "matrix":
            m[0][0] = args[0]; m[0][1] = args[2]; m[0][2] = args[4]
            m[1][0] = args[1]; m[1][1] = args[3]; m[1][2] = args[5]
        result = _multiply_matrices(result, m)
    return result


def _apply_transform(point: Point, matrix: list[list[float]]) -> Point:
    x = matrix[0][0] * point.x + matrix[0][1] * point.y + matrix[0][2]
    y = matrix[1][0] * point.x + matrix[1][1] * point.y + matrix[1][2]
    return Point(x, y)


# ---------------------------------------------------------------------------
# SVG Parser
# ---------------------------------------------------------------------------

def _normalize_color(color: str) -> str:
    """Normalize a hex color to lowercase 6-digit form."""
    color = color.strip().lower()
    if color.startswith("#") and len(color) == 4:
        # Expand shorthand: #abc → #aabbcc
        color = "#" + color[1] * 2 + color[2] * 2 + color[3] * 2
    return color


def _get_stroke_color(element: ET.Element) -> str | None:
    """Extract stroke color from an SVG element."""
    # Check style attribute first
    style = element.get("style", "")
    for part in style.split(";"):
        part = part.strip()
        if part.startswith("stroke:"):
            val = part[len("stroke:"):].strip()
            if val and val != "none":
                return _normalize_color(val)
    # Check stroke attribute
    stroke = element.get("stroke")
    if stroke and stroke != "none":
        return _normalize_color(stroke)
    return None


def _match_entity_id(element: ET.Element) -> str | None:
    """Match element id against known entity types (prefix match, longest first)."""
    eid = element.get("id", "")
    if not eid:
        return None
    for etype in ENTITY_TYPES:
        if eid == etype or eid.startswith(etype + "_"):
            return etype
    return None


def _parse_points(points_str: str) -> list[Point]:
    """Parse SVG polygon/polyline 'points' attribute."""
    nums = re.findall(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?", points_str)
    points = []
    for j in range(0, len(nums) - 1, 2):
        points.append(Point(float(nums[j]), float(nums[j + 1])))
    return points


def _element_center(element: ET.Element) -> Point:
    """Compute center point of a circle, ellipse, or rect element."""
    tag = _local_tag(element.tag)
    if tag == "circle":
        return Point(float(element.get("cx", "0")), float(element.get("cy", "0")))
    elif tag == "ellipse":
        return Point(float(element.get("cx", "0")), float(element.get("cy", "0")))
    elif tag == "rect":
        x = float(element.get("x", "0"))
        y = float(element.get("y", "0"))
        w = float(element.get("width", "0"))
        h = float(element.get("height", "0"))
        return Point(x + w / 2, y + h / 2)
    return Point(0, 0)


def _local_tag(tag: str) -> str:
    """Strip namespace from an element tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _points_to_segments(points: list[Point], closed: bool) -> list[PathSegment]:
    """Convert a point list to line segments, optionally closing."""
    segments = []
    for j in range(len(points) - 1):
        segments.append(PathSegment("line", [points[j], points[j + 1]]))
    if closed and len(points) > 2:
        segments.append(PathSegment("line", [points[-1], points[0]]))
    return segments


def _ellipse_perimeter_segments(
    cx: float, cy: float, rx: float, ry: float, interval: float = 16.0
) -> tuple[list[PathSegment], list[Point]]:
    """Walk an ellipse perimeter at approximately `interval`-px steps.

    Returns (segments, sample_points) where each segment connects consecutive
    sample points and sample_points includes all samples around the loop.
    """
    # Estimate perimeter using Ramanujan's approximation
    h = ((rx - ry) / (rx + ry)) ** 2
    perimeter = math.pi * (rx + ry) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))
    n_samples = max(8, round(perimeter / interval))
    points = []
    for i in range(n_samples):
        t = 2 * math.pi * i / n_samples
        px = cx + rx * math.cos(t)
        py = cy + ry * math.sin(t)
        points.append(Point(px, py))
    segments = _points_to_segments(points, closed=True)
    return segments, points


class SVGParser:
    """Parses an SVG document into terrain shapes and entities."""

    def __init__(self, svg_path: str) -> None:
        self.tree = ET.parse(svg_path)
        self.root = self.tree.getroot()
        self.width: int = 0
        self.height: int = 0

    def parse(self) -> tuple[list[TerrainShape], list[Entity]]:
        self._resolve_viewbox()
        shapes: list[TerrainShape] = []
        entities: list[Entity] = []
        self._parse_element(self.root, _identity_matrix(), shapes, entities)
        return shapes, entities

    def _resolve_viewbox(self) -> None:
        vb = self.root.get("viewBox")
        if vb:
            parts = re.split(r"[\s,]+", vb.strip())
            self.width = int(float(parts[2]))
            self.height = int(float(parts[3]))
        else:
            self.width = int(float(self.root.get("width", "0")))
            self.height = int(float(self.root.get("height", "0")))

    def _parse_element(
        self,
        element: ET.Element,
        parent_transform: list[list[float]],
        shapes: list[TerrainShape],
        entities: list[Entity],
    ) -> None:
        transform = parent_transform
        local_tf = element.get("transform")
        if local_tf:
            transform = _multiply_matrices(parent_transform, _parse_transform(local_tf))

        tag = _local_tag(element.tag)

        if tag in ("polygon", "polyline"):
            self._parse_polygon_like(element, transform, tag == "polygon", shapes, entities)
        elif tag == "path":
            self._parse_path(element, transform, shapes)
        elif tag == "circle":
            self._parse_circle(element, transform, shapes, entities)
        elif tag == "ellipse":
            self._parse_ellipse(element, transform, shapes, entities)
        elif tag == "rect":
            self._parse_rect(element, transform, entities)

        for child in element:
            self._parse_element(child, transform, shapes, entities)

    def _parse_polygon_like(
        self,
        element: ET.Element,
        transform: list[list[float]],
        closed: bool,
        shapes: list[TerrainShape],
        entities: list[Entity],
    ) -> None:
        points_str = element.get("points", "")
        if not points_str:
            return
        points = [_apply_transform(p, transform) for p in _parse_points(points_str)]
        stroke = _get_stroke_color(element)
        if stroke and stroke in STROKE_COLOR_MAP:
            segments = _points_to_segments(points, closed)
            shapes.append(TerrainShape(segments, STROKE_COLOR_MAP[stroke]))
        entity_type = _match_entity_id(element)
        if entity_type and points:
            cx = sum(p.x for p in points) / len(points)
            cy = sum(p.y for p in points) / len(points)
            entities.append(Entity(entity_type, cx, cy))

    def _parse_path(
        self,
        element: ET.Element,
        transform: list[list[float]],
        shapes: list[TerrainShape],
    ) -> None:
        d = element.get("d", "")
        if not d:
            return
        stroke = _get_stroke_color(element)
        if not stroke or stroke not in STROKE_COLOR_MAP:
            return
        raw_segments = parse_path_d(d)
        # Apply transform to all segment points
        transformed = []
        for seg in raw_segments:
            new_points = [_apply_transform(p, transform) for p in seg.points]
            transformed.append(PathSegment(seg.kind, new_points))
        shapes.append(TerrainShape(transformed, STROKE_COLOR_MAP[stroke]))

    def _parse_circle(
        self,
        element: ET.Element,
        transform: list[list[float]],
        shapes: list[TerrainShape],
        entities: list[Entity],
    ) -> None:
        center = _apply_transform(_element_center(element), transform)
        entity_type = _match_entity_id(element)
        if entity_type:
            entities.append(Entity(entity_type, center.x, center.y))
            return
        stroke = _get_stroke_color(element)
        if stroke and stroke in STROKE_COLOR_MAP:
            r = float(element.get("r", "0"))
            # Scale radius by transform (approximate: use x-scale)
            scale = math.sqrt(transform[0][0] ** 2 + transform[1][0] ** 2)
            r *= scale
            segs, _ = _ellipse_perimeter_segments(center.x, center.y, r, r)
            shapes.append(TerrainShape(
                segs, STROKE_COLOR_MAP[stroke], is_loop=True, center=center
            ))

    def _parse_ellipse(
        self,
        element: ET.Element,
        transform: list[list[float]],
        shapes: list[TerrainShape],
        entities: list[Entity],
    ) -> None:
        center = _apply_transform(_element_center(element), transform)
        entity_type = _match_entity_id(element)
        if entity_type:
            entities.append(Entity(entity_type, center.x, center.y))
            return
        stroke = _get_stroke_color(element)
        if stroke and stroke in STROKE_COLOR_MAP:
            rx = float(element.get("rx", "0"))
            ry = float(element.get("ry", "0"))
            scale_x = math.sqrt(transform[0][0] ** 2 + transform[1][0] ** 2)
            scale_y = math.sqrt(transform[0][1] ** 2 + transform[1][1] ** 2)
            rx *= scale_x
            ry *= scale_y
            segs, _ = _ellipse_perimeter_segments(center.x, center.y, rx, ry)
            shapes.append(TerrainShape(
                segs, STROKE_COLOR_MAP[stroke], is_loop=True, center=center
            ))

    def _parse_rect(
        self,
        element: ET.Element,
        transform: list[list[float]],
        entities: list[Entity],
    ) -> None:
        entity_type = _match_entity_id(element)
        if entity_type:
            center = _apply_transform(_element_center(element), transform)
            entities.append(Entity(entity_type, center.x, center.y))


# ---------------------------------------------------------------------------
# Rasterizer
# ---------------------------------------------------------------------------

def _compute_segment_angle(p1: Point, p2: Point) -> int:
    """Compute byte angle (0–255) from a line segment direction.

    Convention: 0 = flat rightward, 64 = down (right wall),
    128 = leftward (ceiling), 192 = up (left wall).
    """
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    if dx == 0 and dy == 0:
        return 0
    # atan2 with screen coords (y down): angle clockwise from right
    rad = math.atan2(dy, dx)
    # Convert to byte angle: 0..2π → 0..256
    # Negate because engine byte angles go counter-clockwise from right
    # Engine: 0=flat, 64=right-wall(up on screen), 128=ceiling, 192=left-wall(down on screen)
    # atan2 gives: 0=right, π/2=down, π=left, -π/2=up
    # Mapping: engine_angle = -atan2_angle (mod 256)
    byte_angle = round(-rad * 256 / (2 * math.pi)) % 256
    return byte_angle


def _sample_cubic(p0: Point, p1: Point, p2: Point, p3: Point, interval: float = 16.0) -> list[Point]:
    """Sample a cubic bezier at approximately `interval`-px arc-length intervals."""
    # Estimate length by chord
    chord = math.hypot(p3.x - p0.x, p3.y - p0.y)
    ctrl = (
        math.hypot(p1.x - p0.x, p1.y - p0.y)
        + math.hypot(p2.x - p1.x, p2.y - p1.y)
        + math.hypot(p3.x - p2.x, p3.y - p2.y)
    )
    est_length = (chord + ctrl) / 2
    n_samples = max(2, round(est_length / interval))
    points = []
    for i in range(n_samples + 1):
        t = i / n_samples
        u = 1 - t
        x = u**3 * p0.x + 3 * u**2 * t * p1.x + 3 * u * t**2 * p2.x + t**3 * p3.x
        y = u**3 * p0.y + 3 * u**2 * t * p1.y + 3 * u * t**2 * p2.y + t**3 * p3.y
        points.append(Point(x, y))
    return points


def _sample_quad(p0: Point, p1: Point, p2: Point, interval: float = 16.0) -> list[Point]:
    """Sample a quadratic bezier at approximately `interval`-px arc-length intervals."""
    chord = math.hypot(p2.x - p0.x, p2.y - p0.y)
    ctrl = math.hypot(p1.x - p0.x, p1.y - p0.y) + math.hypot(p2.x - p1.x, p2.y - p1.y)
    est_length = (chord + ctrl) / 2
    n_samples = max(2, round(est_length / interval))
    points = []
    for i in range(n_samples + 1):
        t = i / n_samples
        u = 1 - t
        x = u**2 * p0.x + 2 * u * t * p1.x + t**2 * p2.x
        y = u**2 * p0.y + 2 * u * t * p1.y + t**2 * p2.y
        points.append(Point(x, y))
    return points


class Rasterizer:
    """Converts terrain shapes into a tile grid."""

    def __init__(self, width_px: int, height_px: int) -> None:
        self.width_px = width_px
        self.height_px = height_px
        self.cols = (width_px + TILE_SIZE - 1) // TILE_SIZE
        self.rows = (height_px + TILE_SIZE - 1) // TILE_SIZE
        self.grid = TileGrid(self.cols, self.rows)
        self.shape_source: dict[tuple[int, int], int] = {}

    def rasterize(self, shapes: list[TerrainShape]) -> TileGrid:
        for idx, shape in enumerate(shapes):
            self._current_shape_idx = idx
            self._rasterize_shape(shape)
        return self.grid

    def _rasterize_shape(self, shape: TerrainShape) -> None:
        if shape.is_loop and shape.center:
            self._rasterize_loop(shape)
        else:
            self._rasterize_edges(shape)
            self._fill_interior(shape)

    def _rasterize_edges(self, shape: TerrainShape) -> None:
        for seg in shape.segments:
            if seg.kind == "line":
                self._rasterize_line_segment(seg.points[0], seg.points[1], shape.surface_type)
            elif seg.kind == "cubic":
                samples = _sample_cubic(seg.points[0], seg.points[1], seg.points[2], seg.points[3])
                for j in range(len(samples) - 1):
                    self._rasterize_line_segment(samples[j], samples[j + 1], shape.surface_type)
            elif seg.kind == "quad":
                samples = _sample_quad(seg.points[0], seg.points[1], seg.points[2])
                for j in range(len(samples) - 1):
                    self._rasterize_line_segment(samples[j], samples[j + 1], shape.surface_type)

    def _rasterize_line_segment(self, p1: Point, p2: Point, surface_type: int) -> None:
        """Rasterize a single line segment into the tile grid."""
        angle = _compute_segment_angle(p1, p2)

        # Walk the segment at sub-tile resolution
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        length = math.hypot(dx, dy)
        if length < 0.5:
            return

        # Sample at 1px intervals along the segment
        n_steps = max(1, int(length))
        for step in range(n_steps + 1):
            t = step / n_steps
            sx = p1.x + dx * t
            sy = p1.y + dy * t

            tx = int(sx) // TILE_SIZE
            ty = int(sy) // TILE_SIZE
            col = int(sx) % TILE_SIZE
            if col < 0:
                col += TILE_SIZE
                tx -= 1

            if tx < 0 or tx >= self.cols or ty < 0 or ty >= self.rows:
                continue

            # Height = distance from sample point to tile bottom
            tile_bottom_y = (ty + 1) * TILE_SIZE
            height = max(0, min(16, math.ceil(tile_bottom_y - sy)))

            tile = self.grid.get_tile(tx, ty)
            if tile is None:
                tile = TileData(
                    surface_type=surface_type,
                    height_array=[0] * 16,
                    angle=angle,
                )
                self.grid.set_tile(tx, ty, tile)

            # Update the column height (take the max to handle overlapping segments)
            col = max(0, min(15, col))
            tile.height_array[col] = max(tile.height_array[col], height)
            tile.angle = angle
            tile.surface_type = surface_type
            self.shape_source[(tx, ty)] = self._current_shape_idx

    def _rasterize_loop(self, shape: TerrainShape) -> None:
        """Rasterize a loop (circle/ellipse) terrain shape."""
        assert shape.center is not None
        cx, cy = shape.center.x, shape.center.y

        # Compute loop radius from the first segment point
        p0 = shape.segments[0].points[0]
        r = math.hypot(p0.x - cx, p0.y - cy)
        r_ramp = r  # ramp radius matches loop radius

        # Generate entry/exit ramps BEFORE the loop circle so that any
        # overlapping tiles at tangent points are overwritten by loop tiles.
        self._rasterize_ramps(cx, cy, r, r_ramp)

        for seg in shape.segments:
            if seg.kind == "line":
                p1, p2 = seg.points[0], seg.points[1]
                angle = _compute_segment_angle(p1, p2)

                # Walk the segment
                dx = p2.x - p1.x
                dy = p2.y - p1.y
                length = math.hypot(dx, dy)
                if length < 0.5:
                    continue

                n_steps = max(1, int(length))
                for step in range(n_steps + 1):
                    t = step / n_steps
                    sx = p1.x + dx * t
                    sy = p1.y + dy * t

                    tx = int(sx) // TILE_SIZE
                    ty = int(sy) // TILE_SIZE
                    col = int(sx) % TILE_SIZE
                    if col < 0:
                        col += TILE_SIZE
                        tx -= 1

                    if tx < 0 or tx >= self.cols or ty < 0 or ty >= self.rows:
                        continue

                    tile_bottom_y = (ty + 1) * TILE_SIZE
                    height = max(0, min(16, math.ceil(tile_bottom_y - sy)))

                    tile = self.grid.get_tile(tx, ty)
                    if tile is None:
                        tile = TileData(
                            surface_type=SURFACE_LOOP,
                            height_array=[0] * 16,
                            angle=angle,
                            is_loop_upper=(sy < cy),
                        )
                        self.grid.set_tile(tx, ty, tile)

                    col = max(0, min(15, col))
                    tile.height_array[col] = max(tile.height_array[col], height)
                    tile.angle = angle
                    tile.is_loop_upper = tile.is_loop_upper or (sy < cy)
                    tile.surface_type = SURFACE_LOOP
                    self.shape_source[(tx, ty)] = self._current_shape_idx

    def _rasterize_ramps(
        self, cx: float, cy: float, r: float, r_ramp: float
    ) -> None:
        """Generate quarter-circle entry/exit ramp tiles for a loop.

        Entry ramp: arc from ground level up to the loop's left tangent point.
        Exit ramp: arc from the loop's right tangent point down to ground level.
        Ramp tiles are SURFACE_SOLID (not SURFACE_LOOP) with analytically
        computed height arrays and tangent angles.
        """
        ground_y = cy + r  # bottom of loop circle = ground level

        # --- Helper: compute surface y from arc equation ---
        def _arc_surface_y(px: float, arc_cx: float) -> float | None:
            """Return surface y for pixel x on a quarter-circle arc.

            Arc center is at (arc_cx, cy). Surface is the bottom half of
            the circle: surface_y = cy + sqrt(r_ramp² - dx²).

            Entry ramp: center at (cx - r - r_ramp, cy), dx ranges 0..r_ramp
              → surface goes from ground_y (flat) up to cy (tangent point)
            Exit ramp: center at (cx + r + r_ramp, cy), dx ranges -r_ramp..0
              → surface goes from cy (tangent point) down to ground_y (flat)
            """
            dx = px - arc_cx
            val = r_ramp * r_ramp - dx * dx
            if val < 0:
                return None
            return cy + math.sqrt(val)

        # --- Helper: compute angle between two surface points ---
        def _angle_from_neighbors(
            x: float, arc_cx: float
        ) -> int:
            """Compute byte angle from arc tangent at pixel x."""
            y0 = _arc_surface_y(x, arc_cx)
            y1 = _arc_surface_y(x + 1, arc_cx)
            if y0 is None or y1 is None:
                return 0
            return _compute_segment_angle(Point(x, y0), Point(x + 1, y1))

        # --- Helper: place a ramp pixel into the tile grid ---
        def _place_ramp_pixel(
            px: float, surface_y: float, angle: int
        ) -> None:
            tx = int(px) // TILE_SIZE
            ty = int(surface_y) // TILE_SIZE
            col = int(px) % TILE_SIZE
            if col < 0:
                col += TILE_SIZE
                tx -= 1
            if tx < 0 or tx >= self.cols or ty < 0 or ty >= self.rows:
                return

            tile_bottom_y = (ty + 1) * TILE_SIZE
            height = max(0, min(16, math.ceil(tile_bottom_y - surface_y)))

            tile = self.grid.get_tile(tx, ty)
            if tile is None:
                tile = TileData(
                    surface_type=SURFACE_SOLID,
                    height_array=[0] * 16,
                    angle=angle,
                )
                self.grid.set_tile(tx, ty, tile)

            col = max(0, min(15, col))
            tile.height_array[col] = max(tile.height_array[col], height)
            tile.angle = angle
            tile.surface_type = SURFACE_SOLID
            self.shape_source[(tx, ty)] = self._current_shape_idx

        # --- Entry ramp (left side) ---
        # Arc center at (cx - r - r_ramp, cy): bottom-right quarter sweeps
        # from ground_y (flat, at x = cx-r-r_ramp) to cy (vertical, at x = cx-r).
        entry_arc_cx = cx - r - r_ramp
        entry_x_start = int(cx - r - r_ramp)
        entry_x_end = int(cx - r)

        for px in range(entry_x_start, entry_x_end):
            sy = _arc_surface_y(float(px), entry_arc_cx)
            if sy is None:
                continue
            # Clamp surface to ground level (shouldn't exceed, but safety)
            sy = min(sy, ground_y)
            angle = _angle_from_neighbors(float(px), entry_arc_cx)
            _place_ramp_pixel(float(px), sy, angle)

        # --- Exit ramp (right side) ---
        # Arc center at (cx + r + r_ramp, cy): bottom-left quarter sweeps
        # from cy (vertical, at x = cx+r) to ground_y (flat, at x = cx+r+r_ramp).
        exit_arc_cx = cx + r + r_ramp
        exit_x_start = int(cx + r) + 1
        exit_x_end = int(cx + r + r_ramp) + 1

        for px in range(exit_x_start, exit_x_end):
            sy = _arc_surface_y(float(px), exit_arc_cx)
            if sy is None:
                continue
            sy = min(sy, ground_y)
            angle = _angle_from_neighbors(float(px), exit_arc_cx)
            _place_ramp_pixel(float(px), sy, angle)

        # --- Fill below ramp surface tiles ---
        ramp_tx_ranges = set()
        for px in range(entry_x_start, entry_x_end):
            ramp_tx_ranges.add(int(px) // TILE_SIZE)
        for px in range(exit_x_start, exit_x_end):
            ramp_tx_ranges.add(int(px) // TILE_SIZE)

        for tx in ramp_tx_ranges:
            # Find topmost ramp tile in this column
            top_ty = None
            for ty in range(self.rows):
                tile = self.grid.get_tile(tx, ty)
                if tile is not None and tile.surface_type == SURFACE_SOLID:
                    top_ty = ty
                    break
            if top_ty is None:
                continue
            # Fill below with fully solid tiles
            for ty in range(top_ty + 1, self.rows):
                existing = self.grid.get_tile(tx, ty)
                if existing is None:
                    self.grid.set_tile(tx, ty, TileData(
                        surface_type=SURFACE_SOLID,
                        height_array=[16] * 16,
                        angle=0,
                    ))
                elif existing.surface_type != SURFACE_SOLID:
                    break  # Hit a different surface type; stop filling

    def _fill_interior(self, shape: TerrainShape) -> None:
        """Fill tiles below surface tiles as fully solid.

        For each column, find the topmost surface tile and fill everything below
        it (up to the bottommost surface tile or grid edge) as solid.
        """
        if shape.surface_type == SURFACE_TOP_ONLY:
            return  # Top-only platforms have no interior fill

        for tx in range(self.cols):
            # Find surface tiles in this column
            surface_rows = []
            for ty in range(self.rows):
                tile = self.grid.get_tile(tx, ty)
                if tile is not None and tile.surface_type == shape.surface_type:
                    surface_rows.append(ty)

            if not surface_rows:
                continue

            top_row = min(surface_rows)
            # Fill from top_row + 1 down to bottom of grid (or next shape boundary)
            for ty in range(top_row + 1, self.rows):
                existing = self.grid.get_tile(tx, ty)
                if existing is None:
                    # Fill as solid interior
                    self.grid.set_tile(tx, ty, TileData(
                        surface_type=shape.surface_type,
                        height_array=[16] * 16,
                        angle=0,  # Interior tiles are flat
                    ))
                elif existing.surface_type != shape.surface_type:
                    break  # Hit a different shape; stop filling


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def _byte_angle_diff(a: int, b: int) -> int:
    """Compute minimum circular distance between two byte angles."""
    diff = abs(a - b)
    return min(diff, 256 - diff)


def _is_steep(angle: int) -> bool:
    """Check if angle is steeper than 45°."""
    # Steep: byte angles 32–96 (right quadrant) or 160–224 (left quadrant)
    return (STEEP_LOW <= angle <= 96) or (160 <= angle <= STEEP_HIGH)


SURFACE_NAMES: dict[int, str] = {
    SURFACE_EMPTY: "EMPTY",
    SURFACE_SOLID: "SOLID",
    SURFACE_TOP_ONLY: "TOP_ONLY",
    SURFACE_SLOPE: "SLOPE",
    SURFACE_HAZARD: "HAZARD",
    SURFACE_LOOP: "LOOP",
}


class Validator:
    """Runs validation checks on a rasterized tile grid."""

    def __init__(
        self,
        grid: TileGrid,
        shape_source: dict[tuple[int, int], int] | None = None,
        shape_types: list[int] | None = None,
    ) -> None:
        self.grid = grid
        self.shape_source = shape_source
        self.shape_types = shape_types

    def _shape_context(self, tx: int, ty: int) -> str:
        """Return shape context string for a tile, or empty string if unavailable."""
        if self.shape_source is None or self.shape_types is None:
            return ""
        idx = self.shape_source.get((tx, ty))
        if idx is None or idx >= len(self.shape_types):
            return ""
        name = SURFACE_NAMES.get(self.shape_types[idx], "?")
        return f" [shape #{idx}, {name}]"

    def validate(self) -> list[str]:
        issues: list[str] = []
        issues.extend(self._check_angle_consistency())
        issues.extend(self._check_impassable_gaps())
        issues.extend(self._check_accidental_walls())
        return issues

    def _check_angle_consistency(self) -> list[str]:
        issues = []
        for ty in range(self.grid.rows):
            for tx in range(self.grid.cols):
                tile = self.grid.get_tile(tx, ty)
                if tile is None:
                    continue
                for dtx, dty in [(1, 0), (0, 1)]:
                    ntx, nty = tx + dtx, ty + dty
                    neighbor = self.grid.get_tile(ntx, nty)
                    if neighbor is None:
                        continue
                    diff = _byte_angle_diff(tile.angle, neighbor.angle)
                    if diff > ANGLE_CONSISTENCY_THRESHOLD:
                        ctx = self._shape_context(tx, ty)
                        issues.append(
                            f"Angle inconsistency at ({tx},{ty})->({ntx},{nty}): "
                            f"diff={diff} (angles {tile.angle} vs {neighbor.angle}){ctx}"
                        )
        return issues

    def _check_impassable_gaps(self) -> list[str]:
        issues = []
        for tx in range(self.grid.cols):
            # Scan column top-to-bottom, find gaps between solid tiles
            solid_ranges: list[tuple[int, int]] = []  # (top_px, bottom_px) of solid regions
            for ty in range(self.grid.rows):
                tile = self.grid.get_tile(tx, ty)
                if tile is None:
                    continue
                sol = SOLIDITY_MAP.get(tile.surface_type, NOT_SOLID)
                if sol == NOT_SOLID or sol == TOP_ONLY:
                    continue
                # Tile is solid — compute its pixel range
                max_h = max(tile.height_array)
                if max_h == 0:
                    continue
                top_px = (ty + 1) * TILE_SIZE - max_h
                bottom_px = (ty + 1) * TILE_SIZE
                solid_ranges.append((top_px, bottom_px))

            # Check gaps between consecutive solid ranges
            solid_ranges.sort()
            for j in range(len(solid_ranges) - 1):
                gap = solid_ranges[j + 1][0] - solid_ranges[j][1]
                if 0 < gap < MIN_GAP_PX:
                    issues.append(
                        f"Impassable gap at column {tx}: {gap}px gap at y={solid_ranges[j][1]}"
                    )
        return issues

    def _check_accidental_walls(self) -> list[str]:
        issues = []
        for ty in range(self.grid.rows):
            run_start = -1
            run_count = 0
            for tx in range(self.grid.cols):
                tile = self.grid.get_tile(tx, ty)
                if tile is not None and _is_steep(tile.angle) and not tile.is_loop_upper:
                    if run_count == 0:
                        run_start = tx
                    run_count += 1
                else:
                    if run_count > MAX_STEEP_RUN:
                        ctx = self._shape_context(run_start, ty)
                        issues.append(
                            f"Accidental wall at row {ty}, tiles {run_start}-{run_start + run_count - 1}: "
                            f"{run_count} consecutive steep tiles without loop flag{ctx}"
                        )
                    run_count = 0
            # Check end of row
            if run_count > MAX_STEEP_RUN:
                ctx = self._shape_context(run_start, ty)
                issues.append(
                    f"Accidental wall at row {ty}, tiles {run_start}-{run_start + run_count - 1}: "
                    f"{run_count} consecutive steep tiles without loop flag{ctx}"
                )
        return issues


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------

def _build_meta(
    width_px: int,
    height_px: int,
    grid: TileGrid,
    entities: list[Entity],
) -> dict:
    player_start = None
    checkpoints = []
    for e in entities:
        if e.entity_type == "player_start":
            player_start = {"x": round(e.x), "y": round(e.y)}
        elif e.entity_type == "checkpoint":
            checkpoints.append({"x": round(e.x), "y": round(e.y)})
    return {
        "width_px": width_px,
        "height_px": height_px,
        "width_tiles": grid.cols,
        "height_tiles": grid.rows,
        "player_start": player_start,
        "checkpoints": checkpoints,
    }


class StageWriter:
    """Writes pipeline output files."""

    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir

    def write(
        self,
        grid: TileGrid,
        entities: list[Entity],
        meta: dict,
        issues: list[str],
    ) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        self._write_tile_map(grid)
        self._write_collision(grid)
        self._write_entities(entities)
        self._write_meta(meta)
        self._write_validation(issues)

    def _write_tile_map(self, grid: TileGrid) -> None:
        tile_map = []
        for ty in range(grid.rows):
            row = []
            for tx in range(grid.cols):
                tile = grid.get_tile(tx, ty)
                if tile is None:
                    row.append(None)
                else:
                    row.append({
                        "type": tile.surface_type,
                        "height_array": tile.height_array,
                        "angle": tile.angle,
                    })
            tile_map.append(row)
        with open(os.path.join(self.output_dir, "tile_map.json"), "w") as f:
            json.dump(tile_map, f, indent=2)

    def _write_collision(self, grid: TileGrid) -> None:
        collision = []
        for ty in range(grid.rows):
            row = []
            for tx in range(grid.cols):
                tile = grid.get_tile(tx, ty)
                if tile is None:
                    row.append(NOT_SOLID)
                elif tile.surface_type == SURFACE_LOOP and tile.is_loop_upper:
                    # Upper loop tiles: TOP_ONLY so the player can enter
                    # the loop without hitting the sides as walls.
                    row.append(TOP_ONLY)
                else:
                    row.append(SOLIDITY_MAP.get(tile.surface_type, NOT_SOLID))
            collision.append(row)
        with open(os.path.join(self.output_dir, "collision.json"), "w") as f:
            json.dump(collision, f, indent=2)

    def _write_entities(self, entities: list[Entity]) -> None:
        data = [{"type": e.entity_type, "x": round(e.x), "y": round(e.y)} for e in entities]
        with open(os.path.join(self.output_dir, "entities.json"), "w") as f:
            json.dump(data, f, indent=2)

    def _write_meta(self, meta: dict) -> None:
        with open(os.path.join(self.output_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

    def _write_validation(self, issues: list[str]) -> None:
        with open(os.path.join(self.output_dir, "validation_report.txt"), "w") as f:
            if issues:
                for issue in issues:
                    f.write(issue + "\n")
            else:
                f.write("No issues found.\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert SVG level design to speednik stage data."
    )
    parser.add_argument("input_svg", help="Path to input SVG file")
    parser.add_argument("output_dir", help="Output directory for stage data")
    args = parser.parse_args()

    if not os.path.isfile(args.input_svg):
        print(f"Error: {args.input_svg} not found", file=sys.stderr)
        sys.exit(1)

    svg_parser = SVGParser(args.input_svg)
    shapes, entities = svg_parser.parse()
    print(f"Parsed: {len(shapes)} terrain shapes, {len(entities)} entities")

    rasterizer = Rasterizer(svg_parser.width, svg_parser.height)
    grid = rasterizer.rasterize(shapes)

    tile_count = sum(
        1 for ty in range(grid.rows) for tx in range(grid.cols)
        if grid.get_tile(tx, ty) is not None
    )
    print(f"Rasterized: {grid.cols}x{grid.rows} grid, {tile_count} tiles")

    shape_types = [s.surface_type for s in shapes]
    validator = Validator(grid, rasterizer.shape_source, shape_types)
    issues = validator.validate()
    print(f"Validation: {len(issues)} issues")

    meta = _build_meta(svg_parser.width, svg_parser.height, grid, entities)

    writer = StageWriter(args.output_dir)
    writer.write(grid, entities, meta, issues)
    print(f"Output written to {args.output_dir}")


if __name__ == "__main__":
    main()

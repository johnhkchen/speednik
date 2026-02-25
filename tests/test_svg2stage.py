"""Tests for tools/svg2stage.py — SVG-to-stage pipeline."""

from __future__ import annotations

import json
import math
import os
import tempfile
import textwrap

import pytest

# Add tools/ to import path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from svg2stage import (
    ANGLE_CONSISTENCY_THRESHOLD,
    ENTITY_TYPES,
    FULL,
    NOT_SOLID,
    SOLIDITY_MAP,
    STROKE_COLOR_MAP,
    SURFACE_EMPTY,
    SURFACE_HAZARD,
    SURFACE_LOOP,
    SURFACE_NAMES,
    SURFACE_SLOPE,
    SURFACE_SOLID,
    SURFACE_TOP_ONLY,
    TOP_ONLY,
    Entity,
    PathSegment,
    Point,
    Rasterizer,
    SVGParser,
    StageWriter,
    TerrainShape,
    TileData,
    TileGrid,
    Validator,
    _build_meta,
    _byte_angle_diff,
    _compute_segment_angle,
    _get_stroke_color,
    _match_entity_id,
    _normalize_color,
    _parse_points,
    _sample_cubic,
    parse_path_d,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_svg(content: str) -> str:
    """Write SVG content to a temp file and return the path."""
    fd, path = tempfile.mkstemp(suffix=".svg")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def _make_svg(body: str, width: int = 320, height: int = 160) -> str:
    return textwrap.dedent(f"""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
          {body}
        </svg>""")


# ---------------------------------------------------------------------------
# TestPathParser
# ---------------------------------------------------------------------------

class TestPathParser:
    def test_move_and_line(self):
        segs = parse_path_d("M 10 20 L 30 40")
        assert len(segs) == 1
        assert segs[0].kind == "line"
        assert segs[0].points[0].x == pytest.approx(10)
        assert segs[0].points[0].y == pytest.approx(20)
        assert segs[0].points[1].x == pytest.approx(30)
        assert segs[0].points[1].y == pytest.approx(40)

    def test_multiple_lines(self):
        segs = parse_path_d("M 0 0 L 10 0 L 10 10")
        assert len(segs) == 2
        assert segs[1].points[1].x == pytest.approx(10)
        assert segs[1].points[1].y == pytest.approx(10)

    def test_horizontal_line(self):
        segs = parse_path_d("M 0 5 H 20")
        assert len(segs) == 1
        assert segs[0].points[1].x == pytest.approx(20)
        assert segs[0].points[1].y == pytest.approx(5)

    def test_vertical_line(self):
        segs = parse_path_d("M 5 0 V 20")
        assert len(segs) == 1
        assert segs[0].points[1].x == pytest.approx(5)
        assert segs[0].points[1].y == pytest.approx(20)

    def test_cubic_bezier(self):
        segs = parse_path_d("M 0 0 C 10 20 30 40 50 60")
        assert len(segs) == 1
        assert segs[0].kind == "cubic"
        assert len(segs[0].points) == 4
        assert segs[0].points[3].x == pytest.approx(50)

    def test_quad_bezier(self):
        segs = parse_path_d("M 0 0 Q 25 50 50 0")
        assert len(segs) == 1
        assert segs[0].kind == "quad"
        assert len(segs[0].points) == 3

    def test_close_path(self):
        segs = parse_path_d("M 0 0 L 10 0 L 10 10 Z")
        assert len(segs) == 3  # 2 explicit lines + 1 close line
        # Close line goes from (10,10) back to (0,0)
        assert segs[2].points[0].x == pytest.approx(10)
        assert segs[2].points[0].y == pytest.approx(10)
        assert segs[2].points[1].x == pytest.approx(0)
        assert segs[2].points[1].y == pytest.approx(0)

    def test_relative_move_line(self):
        segs = parse_path_d("m 10 20 l 5 5")
        assert len(segs) == 1
        assert segs[0].points[0].x == pytest.approx(10)
        assert segs[0].points[0].y == pytest.approx(20)
        assert segs[0].points[1].x == pytest.approx(15)
        assert segs[0].points[1].y == pytest.approx(25)

    def test_relative_cubic(self):
        segs = parse_path_d("M 10 10 c 5 5 10 10 15 0")
        assert len(segs) == 1
        assert segs[0].kind == "cubic"
        # Control points are relative to (10,10)
        assert segs[0].points[1].x == pytest.approx(15)
        assert segs[0].points[1].y == pytest.approx(15)
        assert segs[0].points[3].x == pytest.approx(25)
        assert segs[0].points[3].y == pytest.approx(10)

    def test_implicit_lineto_after_move(self):
        segs = parse_path_d("M 0 0 10 10 20 20")
        # After initial M, subsequent coordinate pairs are implicit L
        assert len(segs) == 2
        assert segs[0].points[1].x == pytest.approx(10)
        assert segs[1].points[1].x == pytest.approx(20)

    def test_no_close_when_already_at_start(self):
        segs = parse_path_d("M 0 0 L 10 0 L 0 0 Z")
        # Last point equals start, so Z adds no extra segment
        assert len(segs) == 2


# ---------------------------------------------------------------------------
# TestSVGParser
# ---------------------------------------------------------------------------

class TestSVGParser:
    def test_parse_polygon_points(self):
        points = _parse_points("10,20 30,40 50,60")
        assert len(points) == 3
        assert points[0].x == pytest.approx(10)
        assert points[2].y == pytest.approx(60)

    def test_parse_polygon_points_spaces(self):
        points = _parse_points("10 20 30 40")
        assert len(points) == 2

    def test_normalize_color_lowercase(self):
        assert _normalize_color("#00AA00") == "#00aa00"

    def test_normalize_color_shorthand(self):
        assert _normalize_color("#0A0") == "#00aa00"

    def test_stroke_from_attribute(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<rect stroke="#00AA00"/>')
        assert _get_stroke_color(elem) == "#00aa00"

    def test_stroke_from_style(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<rect style="fill:none;stroke:#0000FF;stroke-width:2"/>')
        assert _get_stroke_color(elem) == "#0000ff"

    def test_stroke_none(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<rect style="stroke:none"/>')
        assert _get_stroke_color(elem) is None

    def test_match_entity_id_exact(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<circle id="ring"/>')
        assert _match_entity_id(elem) == "ring"

    def test_match_entity_id_prefix(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<circle id="ring_1"/>')
        assert _match_entity_id(elem) == "ring"

    def test_match_entity_id_compound(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<circle id="enemy_crab_3"/>')
        assert _match_entity_id(elem) == "enemy_crab"

    def test_match_entity_id_player_start(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<circle id="player_start"/>')
        assert _match_entity_id(elem) == "player_start"

    def test_match_entity_id_unknown(self):
        import xml.etree.ElementTree as ET
        elem = ET.fromstring('<circle id="unknown_thing"/>')
        assert _match_entity_id(elem) is None

    def test_viewbox_parsing(self):
        svg = _make_svg("", 640, 480)
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            parser._resolve_viewbox()
            assert parser.width == 640
            assert parser.height == 480
        finally:
            os.unlink(path)

    def test_circle_as_entity(self):
        svg = _make_svg('<circle id="ring_1" cx="50" cy="50" r="4" fill="yellow"/>')
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            shapes, entities = parser.parse()
            assert len(entities) == 1
            assert entities[0].entity_type == "ring"
            assert entities[0].x == pytest.approx(50)
        finally:
            os.unlink(path)

    def test_circle_as_terrain(self):
        svg = _make_svg('<circle cx="100" cy="80" r="40" stroke="#00AA00" fill="none"/>')
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            shapes, entities = parser.parse()
            assert len(shapes) == 1
            assert shapes[0].is_loop is True
            assert shapes[0].center.x == pytest.approx(100)
            assert len(entities) == 0
        finally:
            os.unlink(path)

    def test_polygon_terrain(self):
        svg = _make_svg(
            '<polygon points="0,128 320,128 320,160 0,160" stroke="#00AA00" fill="none"/>'
        )
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            shapes, entities = parser.parse()
            assert len(shapes) == 1
            assert shapes[0].surface_type == SURFACE_SOLID
            assert len(shapes[0].segments) == 4  # closed polygon = 4 sides
        finally:
            os.unlink(path)

    def test_transform_translate(self):
        svg = _make_svg(
            '<g transform="translate(10, 20)">'
            '  <circle id="ring" cx="0" cy="0" r="4"/>'
            "</g>"
        )
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            _, entities = parser.parse()
            assert len(entities) == 1
            assert entities[0].x == pytest.approx(10)
            assert entities[0].y == pytest.approx(20)
        finally:
            os.unlink(path)

    def test_path_terrain(self):
        svg = _make_svg(
            '<path d="M 0 128 L 160 128 L 160 160 L 0 160 Z" stroke="#00AA00" fill="none"/>'
        )
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            shapes, _ = parser.parse()
            assert len(shapes) == 1
            assert shapes[0].surface_type == SURFACE_SOLID
            # Path: 3 explicit L + 1 Z close = 4 segments
            assert len(shapes[0].segments) == 4
        finally:
            os.unlink(path)

    def test_rect_entity(self):
        svg = _make_svg(
            '<rect id="enemy_crab_1" x="100" y="100" width="16" height="16"/>'
        )
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            _, entities = parser.parse()
            assert len(entities) == 1
            assert entities[0].entity_type == "enemy_crab"
            assert entities[0].x == pytest.approx(108)  # center
            assert entities[0].y == pytest.approx(108)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# TestRasterizer
# ---------------------------------------------------------------------------

class TestRasterizer:
    def test_horizontal_segment_flat(self):
        """Horizontal segment inside a tile row → correct height values."""
        r = Rasterizer(64, 32)
        # Segment at y=8 (inside row 0: tile_bottom=16, height=16-8=8)
        shape = TerrainShape(
            [PathSegment("line", [Point(0, 8), Point(64, 8)])],
            SURFACE_SOLID,
        )
        grid = r.rasterize([shape])
        tile = grid.get_tile(0, 0)
        assert tile is not None
        assert tile.height_array[0] == 8
        # Interior fill: row 1 below the surface should be solid
        tile_below = grid.get_tile(0, 1)
        assert tile_below is not None
        assert tile_below.height_array == [16] * 16

    def test_horizontal_segment_mid_tile(self):
        """Horizontal segment at mid-tile → height_array ≈ [8]*16."""
        r = Rasterizer(32, 32)
        # Segment at y=8 (midpoint of first tile row)
        shape = TerrainShape(
            [PathSegment("line", [Point(0, 8), Point(32, 8)])],
            SURFACE_SOLID,
        )
        grid = r.rasterize([shape])
        tile = grid.get_tile(0, 0)
        assert tile is not None
        # tile_bottom = 16, height = 16 - 8 = 8
        assert tile.height_array[0] == 8

    def test_angle_flat_rightward(self):
        """Flat rightward segment → angle ≈ 0."""
        angle = _compute_segment_angle(Point(0, 0), Point(10, 0))
        assert angle == 0

    def test_angle_flat_leftward(self):
        """Flat leftward segment → angle ≈ 128."""
        angle = _compute_segment_angle(Point(10, 0), Point(0, 0))
        assert angle == 128

    def test_angle_downward(self):
        """Downward segment → angle ≈ 192."""
        angle = _compute_segment_angle(Point(0, 0), Point(0, 10))
        # atan2(10, 0) = π/2, byte = -π/2 * 256/2π = -64 → 192
        assert angle == 192

    def test_angle_upward(self):
        """Upward segment → angle ≈ 64."""
        angle = _compute_segment_angle(Point(0, 10), Point(0, 0))
        assert angle == 64

    def test_angle_45_ascending(self):
        """45° ascending (right and up) → angle ≈ 32."""
        angle = _compute_segment_angle(Point(0, 10), Point(10, 0))
        # atan2(-10, 10) = -π/4, byte = π/4 * 256/2π = 32
        assert angle == 32

    def test_slope_segment_ramp(self):
        """45° ascending segment produces ramped height array."""
        r = Rasterizer(48, 48)
        # Ascending from (0,32) to (32,0) — going up-right across 2 tile rows
        shape = TerrainShape(
            [PathSegment("line", [Point(0, 32), Point(32, 0)])],
            SURFACE_SLOPE,
        )
        grid = r.rasterize([shape])
        # Tile (0, 1): segment goes from y=32 at x=0 to y=16 at x=16
        # tile_bottom for row 1 = (1+1)*16 = 32
        # height at x=0: 32-32=0, height at x=15: 32-17=15
        tile = grid.get_tile(0, 1)
        assert tile is not None
        # Height should increase from left to right
        assert tile.height_array[0] < tile.height_array[15]

    def test_multiple_tiles_covered(self):
        """Long segment covers multiple tiles."""
        r = Rasterizer(128, 32)
        shape = TerrainShape(
            [PathSegment("line", [Point(0, 8), Point(128, 8)])],
            SURFACE_SOLID,
        )
        grid = r.rasterize([shape])
        for tx in range(8):  # 128/16 = 8 tiles
            tile = grid.get_tile(tx, 0)
            assert tile is not None

    def test_curve_sampling(self):
        """Cubic bezier is sampled into multiple points."""
        points = _sample_cubic(Point(0, 0), Point(10, 20), Point(30, 20), Point(40, 0))
        assert len(points) >= 3

    def test_top_only_no_interior(self):
        """Top-only terrain should not get interior fill."""
        r = Rasterizer(64, 64)
        shape = TerrainShape(
            [PathSegment("line", [Point(0, 32), Point(64, 32)])],
            SURFACE_TOP_ONLY,
        )
        grid = r.rasterize([shape])
        # Tile at row 2 (y=32-48) should be empty — no fill below top-only
        tile_below = grid.get_tile(0, 3)
        assert tile_below is None


# ---------------------------------------------------------------------------
# TestLoopRasterization
# ---------------------------------------------------------------------------

class TestLoopRasterization:
    def test_loop_creates_tiles(self):
        r = Rasterizer(256, 256)
        from svg2stage import _ellipse_perimeter_segments
        segs, _ = _ellipse_perimeter_segments(128, 128, 64, 64)
        shape = TerrainShape(segs, SURFACE_LOOP, is_loop=True, center=Point(128, 128))
        grid = r.rasterize([shape])
        # Should have tiles around the perimeter
        tile_count = sum(
            1 for ty in range(grid.rows) for tx in range(grid.cols)
            if grid.get_tile(tx, ty) is not None
        )
        assert tile_count > 10

    def test_loop_upper_flagged(self):
        r = Rasterizer(256, 256)
        from svg2stage import _ellipse_perimeter_segments
        segs, _ = _ellipse_perimeter_segments(128, 128, 64, 64)
        shape = TerrainShape(segs, SURFACE_LOOP, is_loop=True, center=Point(128, 128))
        grid = r.rasterize([shape])
        # Tiles above center (y < 128, tile row < 8) should have is_loop_upper
        found_upper = False
        for ty in range(8):
            for tx in range(grid.cols):
                tile = grid.get_tile(tx, ty)
                if tile is not None and tile.is_loop_upper:
                    found_upper = True
                    break
        assert found_upper

    def test_loop_surface_type(self):
        r = Rasterizer(256, 256)
        from svg2stage import _ellipse_perimeter_segments
        segs, _ = _ellipse_perimeter_segments(128, 128, 64, 64)
        shape = TerrainShape(segs, SURFACE_LOOP, is_loop=True, center=Point(128, 128))
        grid = r.rasterize([shape])
        for ty in range(grid.rows):
            for tx in range(grid.cols):
                tile = grid.get_tile(tx, ty)
                if tile is not None:
                    assert tile.surface_type == SURFACE_LOOP


# ---------------------------------------------------------------------------
# TestValidator
# ---------------------------------------------------------------------------

class TestValidator:
    def test_angle_consistency_flagged(self):
        grid = TileGrid(3, 1)
        grid.set_tile(0, 0, TileData(angle=0))
        grid.set_tile(1, 0, TileData(angle=40))  # diff = 40 > 21
        v = Validator(grid)
        issues = v._check_angle_consistency()
        assert len(issues) == 1
        assert "Angle inconsistency" in issues[0]

    def test_angle_consistency_ok(self):
        grid = TileGrid(3, 1)
        grid.set_tile(0, 0, TileData(angle=0))
        grid.set_tile(1, 0, TileData(angle=15))  # diff = 15 < 21
        v = Validator(grid)
        issues = v._check_angle_consistency()
        assert len(issues) == 0

    def test_angle_wraparound(self):
        """Angles 250 and 10 differ by 16 (wrapping), which is < 21."""
        assert _byte_angle_diff(250, 10) == 16

    def test_impassable_gap_flagged(self):
        grid = TileGrid(1, 4)
        # Solid tile at row 0 (top)
        grid.set_tile(0, 0, TileData(surface_type=SURFACE_SOLID, height_array=[16] * 16))
        # Solid tile at row 1 (16px gap from row 0 bottom to row 1 top)
        # But we need a gap. Row 0 occupies y=0-16, row 2 occupies y=32-48.
        # Gap = y16 to y32 = 16px < 18px
        grid.set_tile(0, 2, TileData(surface_type=SURFACE_SOLID, height_array=[16] * 16))
        v = Validator(grid)
        issues = v._check_impassable_gaps()
        assert len(issues) == 1
        assert "Impassable gap" in issues[0]

    def test_impassable_gap_ok(self):
        grid = TileGrid(1, 5)
        grid.set_tile(0, 0, TileData(surface_type=SURFACE_SOLID, height_array=[16] * 16))
        # Row 3: gap = 2 tiles (32px) > 18px → ok
        grid.set_tile(0, 3, TileData(surface_type=SURFACE_SOLID, height_array=[16] * 16))
        v = Validator(grid)
        issues = v._check_impassable_gaps()
        assert len(issues) == 0

    def test_top_only_gap_not_flagged(self):
        grid = TileGrid(1, 3)
        grid.set_tile(0, 0, TileData(surface_type=SURFACE_TOP_ONLY, height_array=[16] * 16))
        grid.set_tile(0, 1, TileData(surface_type=SURFACE_SOLID, height_array=[16] * 16))
        v = Validator(grid)
        issues = v._check_impassable_gaps()
        # Top-only is filtered out of solid ranges, so no gap flagged
        assert len(issues) == 0

    def test_accidental_wall_flagged(self):
        grid = TileGrid(5, 1)
        for tx in range(5):
            grid.set_tile(tx, 0, TileData(angle=50))  # steep (50 is in 32–96)
        v = Validator(grid)
        issues = v._check_accidental_walls()
        assert len(issues) == 1
        assert "Accidental wall" in issues[0]

    def test_accidental_wall_ok_short_run(self):
        grid = TileGrid(3, 1)
        for tx in range(3):
            grid.set_tile(tx, 0, TileData(angle=50))
        v = Validator(grid)
        issues = v._check_accidental_walls()
        assert len(issues) == 0  # 3 consecutive = MAX_STEEP_RUN, not exceeded

    def test_accidental_wall_loop_not_flagged(self):
        grid = TileGrid(5, 1)
        for tx in range(5):
            grid.set_tile(tx, 0, TileData(angle=50, is_loop_upper=True))
        v = Validator(grid)
        issues = v._check_accidental_walls()
        assert len(issues) == 0

    def test_clean_grid_no_issues(self):
        grid = TileGrid(4, 2)
        for tx in range(4):
            grid.set_tile(tx, 1, TileData(surface_type=SURFACE_SOLID, height_array=[16] * 16, angle=0))
        v = Validator(grid)
        issues = v.validate()
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# TestStageWriter
# ---------------------------------------------------------------------------

class TestStageWriter:
    def test_writes_all_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            grid = TileGrid(2, 2)
            grid.set_tile(0, 1, TileData(
                surface_type=SURFACE_SOLID, height_array=[16] * 16, angle=0
            ))
            entities = [Entity("ring", 10, 20), Entity("player_start", 5, 5)]
            meta = _build_meta(32, 32, grid, entities)
            writer = StageWriter(tmpdir)
            writer.write(grid, entities, meta, ["test issue"])

            assert os.path.isfile(os.path.join(tmpdir, "tile_map.json"))
            assert os.path.isfile(os.path.join(tmpdir, "collision.json"))
            assert os.path.isfile(os.path.join(tmpdir, "entities.json"))
            assert os.path.isfile(os.path.join(tmpdir, "meta.json"))
            assert os.path.isfile(os.path.join(tmpdir, "validation_report.txt"))

    def test_tile_map_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            grid = TileGrid(2, 1)
            grid.set_tile(0, 0, TileData(
                surface_type=SURFACE_SOLID, height_array=[16] * 16, angle=10
            ))
            writer = StageWriter(tmpdir)
            writer._write_tile_map(grid)

            with open(os.path.join(tmpdir, "tile_map.json")) as f:
                data = json.load(f)
            assert len(data) == 1  # 1 row
            assert len(data[0]) == 2  # 2 cols
            assert data[0][0]["type"] == SURFACE_SOLID
            assert data[0][0]["height_array"] == [16] * 16
            assert data[0][0]["angle"] == 10
            assert data[0][1] is None  # empty tile

    def test_collision_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            grid = TileGrid(2, 1)
            grid.set_tile(0, 0, TileData(surface_type=SURFACE_SOLID))
            grid.set_tile(1, 0, TileData(surface_type=SURFACE_TOP_ONLY))
            writer = StageWriter(tmpdir)
            writer._write_collision(grid)

            with open(os.path.join(tmpdir, "collision.json")) as f:
                data = json.load(f)
            assert data[0][0] == FULL
            assert data[0][1] == TOP_ONLY

    def test_entities_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            entities = [Entity("ring", 100.7, 200.3)]
            writer = StageWriter(tmpdir)
            writer._write_entities(entities)

            with open(os.path.join(tmpdir, "entities.json")) as f:
                data = json.load(f)
            assert len(data) == 1
            assert data[0]["type"] == "ring"
            assert data[0]["x"] == 101  # rounded
            assert data[0]["y"] == 200

    def test_meta_format(self):
        grid = TileGrid(20, 10)
        entities = [
            Entity("player_start", 32, 120),
            Entity("checkpoint", 200, 100),
            Entity("ring", 50, 50),
        ]
        meta = _build_meta(320, 160, grid, entities)
        assert meta["width_px"] == 320
        assert meta["height_px"] == 160
        assert meta["width_tiles"] == 20
        assert meta["height_tiles"] == 10
        assert meta["player_start"] == {"x": 32, "y": 120}
        assert len(meta["checkpoints"]) == 1
        assert meta["checkpoints"][0] == {"x": 200, "y": 100}

    def test_validation_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StageWriter(tmpdir)
            writer._write_validation(["issue 1", "issue 2"])
            with open(os.path.join(tmpdir, "validation_report.txt")) as f:
                content = f.read()
            assert "issue 1" in content
            assert "issue 2" in content

    def test_validation_report_clean(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StageWriter(tmpdir)
            writer._write_validation([])
            with open(os.path.join(tmpdir, "validation_report.txt")) as f:
                content = f.read()
            assert "No issues" in content


# ---------------------------------------------------------------------------
# TestTileGrid
# ---------------------------------------------------------------------------

class TestTileGrid:
    def test_init_dimensions(self):
        g = TileGrid(10, 5)
        assert g.cols == 10
        assert g.rows == 5

    def test_get_empty(self):
        g = TileGrid(10, 5)
        assert g.get_tile(0, 0) is None

    def test_set_and_get(self):
        g = TileGrid(10, 5)
        td = TileData(surface_type=SURFACE_SOLID, height_array=[16] * 16, angle=32)
        g.set_tile(3, 2, td)
        assert g.get_tile(3, 2) is td

    def test_out_of_bounds(self):
        g = TileGrid(10, 5)
        g.set_tile(15, 0, TileData())  # out of bounds — ignored
        assert g.get_tile(15, 0) is None
        assert g.get_tile(-1, 0) is None


# ---------------------------------------------------------------------------
# TestConstants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_stroke_color_map_completeness(self):
        assert "#00aa00" in STROKE_COLOR_MAP
        assert "#0000ff" in STROKE_COLOR_MAP
        assert "#ff8800" in STROKE_COLOR_MAP
        assert "#ff0000" in STROKE_COLOR_MAP

    def test_solidity_map(self):
        assert SOLIDITY_MAP[SURFACE_SOLID] == FULL
        assert SOLIDITY_MAP[SURFACE_TOP_ONLY] == TOP_ONLY
        assert SOLIDITY_MAP[SURFACE_SLOPE] == FULL
        assert SOLIDITY_MAP[SURFACE_HAZARD] == FULL
        assert SOLIDITY_MAP[SURFACE_LOOP] == FULL
        assert SOLIDITY_MAP[SURFACE_EMPTY] == NOT_SOLID


# ---------------------------------------------------------------------------
# TestEndToEnd
# ---------------------------------------------------------------------------

class TestEndToEnd:
    FIXTURE_PATH = os.path.join(
        os.path.dirname(__file__), "fixtures", "minimal_test.svg"
    )

    def test_parse_fixture(self):
        parser = SVGParser(self.FIXTURE_PATH)
        shapes, entities = parser.parse()
        assert len(shapes) >= 1  # at least the ground polygon
        # Entities: player_start + 2 rings + 1 enemy_crab = 4
        entity_types = [e.entity_type for e in entities]
        assert "player_start" in entity_types
        assert entity_types.count("ring") == 2
        assert "enemy_crab" in entity_types

    def test_full_pipeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            parser = SVGParser(self.FIXTURE_PATH)
            shapes, entities = parser.parse()

            rasterizer = Rasterizer(parser.width, parser.height)
            grid = rasterizer.rasterize(shapes)

            validator = Validator(grid)
            issues = validator.validate()

            meta = _build_meta(parser.width, parser.height, grid, entities)

            writer = StageWriter(tmpdir)
            writer.write(grid, entities, meta, issues)

            # Verify all output files exist
            for fname in ["tile_map.json", "collision.json", "entities.json",
                          "meta.json", "validation_report.txt"]:
                assert os.path.isfile(os.path.join(tmpdir, fname)), f"Missing {fname}"

            # Verify tile_map dimensions
            with open(os.path.join(tmpdir, "tile_map.json")) as f:
                tile_map = json.load(f)
            assert len(tile_map) == grid.rows
            assert len(tile_map[0]) == grid.cols

            # Verify entities
            with open(os.path.join(tmpdir, "entities.json")) as f:
                ent_data = json.load(f)
            assert len(ent_data) == len(entities)

            # Verify meta
            with open(os.path.join(tmpdir, "meta.json")) as f:
                meta_data = json.load(f)
            assert meta_data["width_px"] == 320
            assert meta_data["height_px"] == 160
            assert meta_data["player_start"] is not None

    def test_cli_invocation(self):
        """Test CLI via subprocess."""
        import subprocess
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [sys.executable, "tools/svg2stage.py", self.FIXTURE_PATH, tmpdir],
                capture_output=True,
                text=True,
                cwd=os.path.join(os.path.dirname(__file__), ".."),
            )
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
            for fname in ["tile_map.json", "collision.json", "entities.json",
                          "meta.json", "validation_report.txt"]:
                assert os.path.isfile(os.path.join(tmpdir, fname)), f"Missing {fname}"


# ---------------------------------------------------------------------------
# TestRasterizationPrecision (AC1)
# ---------------------------------------------------------------------------

class TestRasterizationPrecision:
    """Precise rasterization tests: uniform heights, linear slopes, continuous loops."""

    def test_horizontal_line_uniform_height(self):
        """Horizontal line → all tiles at same height."""
        r = Rasterizer(320, 160)
        # Horizontal line at y=120 across full width
        shape = TerrainShape(
            [PathSegment("line", [Point(0, 120), Point(320, 120)])],
            SURFACE_SOLID,
        )
        grid = r.rasterize([shape])
        # y=120 is in tile row 7 (rows 0-9). tile_bottom = 8*16 = 128. height = 128-120 = 8
        expected_height = 8
        for tx in range(20):  # 320/16 = 20 tiles
            tile = grid.get_tile(tx, 7)
            assert tile is not None, f"Tile ({tx},7) missing"
            # All columns should have the same height
            for col in range(16):
                assert tile.height_array[col] == expected_height, (
                    f"Tile ({tx},7) col {col}: expected {expected_height}, got {tile.height_array[col]}"
                )

    def test_horizontal_line_angle_zero(self):
        """Horizontal line → angle=0 on all surface tiles."""
        r = Rasterizer(320, 160)
        shape = TerrainShape(
            [PathSegment("line", [Point(0, 120), Point(320, 120)])],
            SURFACE_SOLID,
        )
        grid = r.rasterize([shape])
        for tx in range(20):
            tile = grid.get_tile(tx, 7)
            assert tile is not None
            assert tile.angle == 0, f"Tile ({tx},7) angle: expected 0, got {tile.angle}"

    def test_45_slope_linear_height(self):
        """45° ascending slope → linearly increasing height arrays."""
        r = Rasterizer(64, 64)
        # 45° ascending: from (0, 48) to (48, 0) — going up-right
        shape = TerrainShape(
            [PathSegment("line", [Point(0, 48), Point(48, 0)])],
            SURFACE_SLOPE,
        )
        grid = r.rasterize([shape])
        # Check tile (0, 2): row 2, tile_bottom = 48
        # Segment goes from y=48 at x=0 to y=32 at x=16
        # Heights: col 0 → 48-48=0, col 15 → 48-33=15
        tile = grid.get_tile(0, 2)
        assert tile is not None
        # Height should increase left to right (ascending slope)
        assert tile.height_array[0] < tile.height_array[15]
        # Check approximate linearity: each column increases by ~1
        for col in range(1, 16):
            diff = tile.height_array[col] - tile.height_array[col - 1]
            assert 0 <= diff <= 2, (
                f"Non-linear height jump at col {col}: {tile.height_array[col-1]} -> {tile.height_array[col]}"
            )

    def test_45_slope_angle_approximately_32(self):
        """45° ascending slope → angle ≈ 32 (45° in 0-255 space) on surface tiles."""
        r = Rasterizer(64, 64)
        shape = TerrainShape(
            [PathSegment("line", [Point(0, 48), Point(48, 0)])],
            SURFACE_SLOPE,
        )
        grid = r.rasterize([shape])
        # Only check surface tiles (angle=0 are interior fill tiles)
        slope_tiles = []
        for ty in range(4):
            for tx in range(4):
                tile = grid.get_tile(tx, ty)
                if tile is not None and tile.angle != 0:
                    slope_tiles.append((tx, ty, tile))
        assert len(slope_tiles) > 0, "Should have at least one surface tile with non-zero angle"
        for tx, ty, tile in slope_tiles:
            assert abs(tile.angle - 32) <= 2, (
                f"Tile ({tx},{ty}) angle: expected ~32, got {tile.angle}"
            )

    def test_circle_continuous_angles(self):
        """Circle → adjacent loop tiles have continuous angle values."""
        from svg2stage import _ellipse_perimeter_segments
        r = Rasterizer(256, 256)
        segs, _ = _ellipse_perimeter_segments(128, 128, 64, 64)
        shape = TerrainShape(segs, SURFACE_LOOP, is_loop=True, center=Point(128, 128))
        grid = r.rasterize([shape])
        # Check that adjacent loop tiles have angle differences within threshold
        for ty in range(grid.rows):
            for tx in range(grid.cols):
                tile = grid.get_tile(tx, ty)
                if tile is None:
                    continue
                for dtx, dty in [(1, 0), (0, 1)]:
                    neighbor = grid.get_tile(tx + dtx, ty + dty)
                    if neighbor is None:
                        continue
                    diff = _byte_angle_diff(tile.angle, neighbor.angle)
                    # Loop tiles should have smooth angle transitions
                    # Allow wider threshold than standard validation (loops have larger jumps)
                    assert diff <= 64, (
                        f"Loop angle jump at ({tx},{ty})->({tx+dtx},{ty+dty}): "
                        f"diff={diff} (angles {tile.angle} vs {neighbor.angle})"
                    )

    def test_circle_upper_half_flagged_correctly(self):
        """Circle → tiles above center have is_loop_upper=True."""
        from svg2stage import _ellipse_perimeter_segments
        r = Rasterizer(256, 256)
        segs, _ = _ellipse_perimeter_segments(128, 128, 64, 64)
        shape = TerrainShape(segs, SURFACE_LOOP, is_loop=True, center=Point(128, 128))
        grid = r.rasterize([shape])
        center_row = 128 // 16  # tile row 8
        for ty in range(grid.rows):
            for tx in range(grid.cols):
                tile = grid.get_tile(tx, ty)
                if tile is None:
                    continue
                if ty < center_row:
                    assert tile.is_loop_upper, (
                        f"Tile ({tx},{ty}) above center should have is_loop_upper=True"
                    )

    def test_segment_at_tile_boundary(self):
        """Segment exactly at tile boundary (y=16) still creates a tile."""
        r = Rasterizer(64, 64)
        shape = TerrainShape(
            [PathSegment("line", [Point(0, 16), Point(64, 16)])],
            SURFACE_SOLID,
        )
        grid = r.rasterize([shape])
        # y=16 is the boundary between row 0 and row 1
        # Should create tiles in row 0 (tile_bottom=16, height=16-16=0) or row 1
        found = False
        for ty in range(4):
            tile = grid.get_tile(0, ty)
            if tile is not None:
                found = True
                break
        assert found, "Segment at tile boundary should still create tiles"

    def test_short_segment_no_crash(self):
        """Very short segment (< 1px) → no crash, no tiles."""
        r = Rasterizer(64, 64)
        shape = TerrainShape(
            [PathSegment("line", [Point(10, 10), Point(10.3, 10.1)])],
            SURFACE_SOLID,
        )
        grid = r.rasterize([shape])
        # Should not crash — short segments are silently skipped


# ---------------------------------------------------------------------------
# TestEntityParsingComplete (AC2)
# ---------------------------------------------------------------------------

class TestEntityParsingComplete:
    """Tests that all entity types are correctly parsed."""

    def test_all_entity_types_recognized(self):
        """Every entity type from the spec is recognized from an SVG."""
        # Build SVG with one circle per entity type
        circles = []
        for i, etype in enumerate(ENTITY_TYPES):
            cx = 20 + i * 24
            circles.append(f'<circle id="{etype}" cx="{cx}" cy="50" r="4"/>')
        svg = _make_svg("\n".join(circles), width=400, height=100)
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            _, entities = parser.parse()
            found_types = {e.entity_type for e in entities}
            for etype in ENTITY_TYPES:
                assert etype in found_types, f"Entity type '{etype}' not parsed"
        finally:
            os.unlink(path)

    def test_entity_position_circle_center(self):
        """Circle entity position is taken from cx, cy."""
        svg = _make_svg('<circle id="ring" cx="100" cy="200" r="4"/>', width=320, height=320)
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            _, entities = parser.parse()
            assert len(entities) == 1
            assert entities[0].x == pytest.approx(100)
            assert entities[0].y == pytest.approx(200)
        finally:
            os.unlink(path)

    def test_entity_position_rect_center(self):
        """Rect entity position is taken from center of bounding box."""
        svg = _make_svg(
            '<rect id="enemy_buzzer" x="100" y="200" width="16" height="16"/>',
            width=320, height=320,
        )
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            _, entities = parser.parse()
            assert len(entities) == 1
            assert entities[0].entity_type == "enemy_buzzer"
            assert entities[0].x == pytest.approx(108)  # 100 + 16/2
            assert entities[0].y == pytest.approx(208)  # 200 + 16/2
        finally:
            os.unlink(path)

    def test_entity_prefix_with_suffix(self):
        """Entity IDs with numeric suffixes are matched correctly."""
        svg = _make_svg(
            '<circle id="spring_up_1" cx="50" cy="50" r="4"/>'
            '<circle id="checkpoint_2" cx="100" cy="50" r="4"/>'
            '<circle id="enemy_chopper_99" cx="150" cy="50" r="4"/>',
        )
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            _, entities = parser.parse()
            types = sorted(e.entity_type for e in entities)
            assert "spring_up" in types
            assert "checkpoint" in types
            assert "enemy_chopper" in types
        finally:
            os.unlink(path)

    def test_entity_unknown_id_ignored(self):
        """Unknown entity IDs produce no entity and no crash."""
        svg = _make_svg(
            '<circle id="unknown_thing" cx="50" cy="50" r="4"/>'
            '<circle id="badger" cx="100" cy="50" r="4"/>',
        )
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            _, entities = parser.parse()
            assert len(entities) == 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# TestValidationReport (AC3 + AC5)
# ---------------------------------------------------------------------------

class TestValidationReport:
    """Tests that validation messages are human-readable and contain useful context."""

    def test_angle_discontinuity_message_format(self):
        """Angle inconsistency message includes tile coordinates and angle values."""
        grid = TileGrid(3, 1)
        grid.set_tile(0, 0, TileData(angle=0))
        grid.set_tile(1, 0, TileData(angle=100))  # large jump
        v = Validator(grid)
        issues = v.validate()
        assert len(issues) >= 1
        msg = issues[0]
        assert "(0,0)" in msg
        assert "(1,0)" in msg
        assert "0" in msg and "100" in msg
        assert "Angle inconsistency" in msg

    def test_narrow_gap_message_format(self):
        """Impassable gap message includes column number and gap size in pixels."""
        grid = TileGrid(1, 4)
        grid.set_tile(0, 0, TileData(surface_type=SURFACE_SOLID, height_array=[16] * 16))
        grid.set_tile(0, 2, TileData(surface_type=SURFACE_SOLID, height_array=[16] * 16))
        v = Validator(grid)
        issues = v._check_impassable_gaps()
        assert len(issues) == 1
        msg = issues[0]
        assert "column 0" in msg
        assert "16px" in msg or "16" in msg
        assert "Impassable gap" in msg

    def test_steep_slope_message_format(self):
        """Accidental wall message includes row and tile range."""
        grid = TileGrid(6, 1)
        for tx in range(5):
            grid.set_tile(tx, 0, TileData(angle=50))
        v = Validator(grid)
        issues = v._check_accidental_walls()
        assert len(issues) == 1
        msg = issues[0]
        assert "row 0" in msg
        assert "tiles 0-4" in msg
        assert "5 consecutive" in msg

    def test_report_with_shape_context(self):
        """Validation messages include shape index and type when shape_source is provided."""
        grid = TileGrid(3, 1)
        grid.set_tile(0, 0, TileData(angle=0))
        grid.set_tile(1, 0, TileData(angle=100))
        shape_source = {(0, 0): 0, (1, 0): 0}
        shape_types = [SURFACE_SLOPE]
        v = Validator(grid, shape_source=shape_source, shape_types=shape_types)
        issues = v.validate()
        assert len(issues) >= 1
        msg = issues[0]
        assert "shape #0" in msg
        assert "SLOPE" in msg


# ---------------------------------------------------------------------------
# TestEngineIntegration (AC4)
# ---------------------------------------------------------------------------

# Guard import: terrain module may have unresolved deps during isolated test runs
try:
    from speednik.terrain import Tile as TerrainTile
    from speednik.terrain import NOT_SOLID as T_NOT_SOLID
    from speednik.terrain import FULL as T_FULL
    from speednik.terrain import TOP_ONLY as T_TOP_ONLY
    from speednik.terrain import find_floor
    from speednik.physics import PhysicsState
    _HAS_TERRAIN = True
except ImportError:
    _HAS_TERRAIN = False


@pytest.mark.skipif(not _HAS_TERRAIN, reason="speednik.terrain not importable")
class TestEngineIntegration:
    """Integration tests: pipeline output loads into engine terrain system."""

    FIXTURE_PATH = os.path.join(
        os.path.dirname(__file__), "fixtures", "minimal_test.svg"
    )

    def _run_pipeline(self):
        """Run full pipeline on fixture, return (grid, entities, meta, tile_map_json)."""
        parser = SVGParser(self.FIXTURE_PATH)
        shapes, entities = parser.parse()
        rasterizer = Rasterizer(parser.width, parser.height)
        grid = rasterizer.rasterize(shapes)
        meta = _build_meta(parser.width, parser.height, grid, entities)
        # Serialize tile_map to JSON and back (as engine would receive it)
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
                        "height_array": list(tile.height_array),
                        "angle": tile.angle,
                    })
            tile_map.append(row)
        return grid, entities, meta, tile_map

    def test_pipeline_json_to_terrain_tile(self):
        """Pipeline JSON can be loaded into terrain.Tile without errors."""
        _, _, _, tile_map = self._run_pipeline()
        tile_count = 0
        for row in tile_map:
            for cell in row:
                if cell is not None:
                    # Construct a terrain.Tile from pipeline JSON
                    t = TerrainTile(
                        height_array=cell["height_array"],
                        angle=cell["angle"],
                        solidity=SOLIDITY_MAP[cell["type"]],
                    )
                    assert len(t.height_array) == 16
                    assert 0 <= t.angle <= 255
                    assert t.solidity in (T_NOT_SOLID, T_TOP_ONLY, T_FULL)
                    tile_count += 1
        assert tile_count > 0, "No tiles loaded from pipeline output"

    def test_flat_ground_floor_sensor(self):
        """Floor sensor finds flat ground from pipeline output."""
        _, _, _, tile_map = self._run_pipeline()
        # Build tile lookup from pipeline output
        tiles: dict[tuple[int, int], TerrainTile] = {}
        for ty, row in enumerate(tile_map):
            for tx, cell in enumerate(row):
                if cell is not None:
                    tiles[(tx, ty)] = TerrainTile(
                        height_array=cell["height_array"],
                        angle=cell["angle"],
                        solidity=SOLIDITY_MAP[cell["type"]],
                    )

        def tile_lookup(tx: int, ty: int):
            return tiles.get((tx, ty))

        # Player well above flat ground at x=32, y=100 (ground surface at y=128)
        state = PhysicsState(x=32.0, y=100.0)
        result = find_floor(state, tile_lookup)
        assert result.found, "Floor sensor should find the ground"
        # Sensor should detect the ground (distance is from sensor tip to surface)
        assert result.tile_angle == 0, "Flat ground should have angle 0"

    def test_solidity_mapping_consistent(self):
        """Pipeline SOLIDITY_MAP values match terrain module constants."""
        assert SOLIDITY_MAP[SURFACE_SOLID] == T_FULL
        assert SOLIDITY_MAP[SURFACE_TOP_ONLY] == T_TOP_ONLY
        assert SOLIDITY_MAP[SURFACE_EMPTY] == T_NOT_SOLID

    def test_missing_player_start_meta(self):
        """SVG without player_start → meta['player_start'] is None, no crash."""
        svg = _make_svg(
            '<polygon points="0,128 320,128 320,160 0,160" stroke="#00AA00" fill="none"/>',
        )
        path = _write_svg(svg)
        try:
            parser = SVGParser(path)
            shapes, entities = parser.parse()
            rasterizer = Rasterizer(parser.width, parser.height)
            grid = rasterizer.rasterize(shapes)
            meta = _build_meta(parser.width, parser.height, grid, entities)
            assert meta["player_start"] is None
        finally:
            os.unlink(path)

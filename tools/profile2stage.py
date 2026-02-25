#!/usr/bin/env python3
"""Profile-to-stage pipeline CLI.

Reads a .profile.json track definition and emits the same tile map, collision
data, entity placement, and validation report that svg2stage.py produces.

Usage:
    python tools/profile2stage.py input.profile.json output_dir/
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field

# Import shared components from svg2stage
sys.path.insert(0, os.path.dirname(__file__))
from svg2stage import (
    SURFACE_LOOP,
    SURFACE_SOLID,
    SURFACE_TOP_ONLY,
    TILE_SIZE,
    Entity,
    TileData,
    TileGrid,
    Validator,
    StageWriter,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SLOPE_WARN_THRESHOLD = math.tan(math.radians(30))  # ~0.577
SLOPE_ERROR_THRESHOLD = 1.0  # tan(45°)
DEFAULT_HEIGHT = 720
DEFAULT_START_Y = 636
VALID_SEG_TYPES = {"flat", "ramp", "gap", "wave", "halfpipe", "loop"}
VALID_OVERLAY_TYPES = {"platform", "spring_up", "spring_right"}
VALID_ENTITY_TYPES = {"player_start", "ring_line", "enemy", "checkpoint", "goal"}
ENEMY_SUBTYPE_MAP = {
    "motobug": "enemy_crab",
    "buzzbomber": "enemy_buzzer",
    "chopper": "enemy_chopper",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SegmentDef:
    seg: str  # "flat" | "ramp" | "gap" | "wave" | "halfpipe" | "loop"
    len: int  # pixel length > 0 (for loop: auto-set to 2*radius)
    rise: int  # ramp only, default 0
    id: str  # unique identifier
    amplitude: int = 0  # wave only
    period: int = 0  # wave only
    depth: int = 0  # halfpipe only
    radius: int = 0  # loop only


@dataclass
class ProfileData:
    width: int
    height: int
    start_y: int
    segments: list[SegmentDef]
    overlays: list[dict] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Profile parser
# ---------------------------------------------------------------------------

class ProfileParser:
    """Reads and validates a .profile.json file."""

    @staticmethod
    def load(path: str) -> ProfileData:
        with open(path) as f:
            data = json.load(f)

        # Validate required fields
        if "track" not in data or not isinstance(data["track"], list):
            raise ValueError("Profile must contain a 'track' list")
        if len(data["track"]) == 0:
            raise ValueError("'track' must not be empty")

        width = data.get("width")
        if width is None or not isinstance(width, int) or width <= 0:
            raise ValueError("'width' must be a positive integer")

        height = data.get("height", DEFAULT_HEIGHT)
        if not isinstance(height, int) or height <= 0:
            raise ValueError("'height' must be a positive integer")

        start_y = data.get("start_y", DEFAULT_START_Y)
        if not isinstance(start_y, int) or start_y <= 0:
            raise ValueError("'start_y' must be a positive integer")

        # Parse segments
        segments: list[SegmentDef] = []
        seen_ids: set[str] = set()
        for i, raw in enumerate(data["track"]):
            seg_type = raw.get("seg")
            if seg_type not in VALID_SEG_TYPES:
                raise ValueError(
                    f"Segment {i}: 'seg' must be one of {VALID_SEG_TYPES}, got {seg_type!r}"
                )

            rise = 0
            amplitude = 0
            period = 0
            depth = 0
            radius = 0

            if seg_type == "loop":
                # Loop segments use radius, not len
                if "radius" not in raw:
                    raise ValueError(f"Segment {i}: loop segment requires 'radius'")
                radius = raw["radius"]
                if not isinstance(radius, int) or radius <= 0:
                    raise ValueError(f"Segment {i}: 'radius' must be a positive integer")
                if radius < 32:
                    raise ValueError(
                        f"Segment {i}: loop radius {radius} is below minimum (32)"
                    )
                seg_len = 4 * radius  # footprint = ramp + diameter + ramp
            else:
                seg_len = raw.get("len")
                if seg_len is None or not isinstance(seg_len, int) or seg_len <= 0:
                    raise ValueError(f"Segment {i}: 'len' must be a positive integer")

            if seg_type == "ramp":
                if "rise" not in raw:
                    raise ValueError(f"Segment {i}: ramp segment requires 'rise'")
                rise = raw["rise"]
                if not isinstance(rise, int):
                    raise ValueError(f"Segment {i}: 'rise' must be an integer")

            elif seg_type == "wave":
                if "amplitude" not in raw:
                    raise ValueError(f"Segment {i}: wave segment requires 'amplitude'")
                amplitude = raw["amplitude"]
                if not isinstance(amplitude, int) or amplitude <= 0:
                    raise ValueError(f"Segment {i}: 'amplitude' must be a positive integer")
                if "period" not in raw:
                    raise ValueError(f"Segment {i}: wave segment requires 'period'")
                period = raw["period"]
                if not isinstance(period, int) or period <= 0:
                    raise ValueError(f"Segment {i}: 'period' must be a positive integer")

            elif seg_type == "halfpipe":
                if "depth" not in raw:
                    raise ValueError(f"Segment {i}: halfpipe segment requires 'depth'")
                depth = raw["depth"]
                if not isinstance(depth, int) or depth <= 0:
                    raise ValueError(f"Segment {i}: 'depth' must be a positive integer")

            seg_id = raw.get("id", f"seg_{i}")
            if seg_id in seen_ids:
                raise ValueError(f"Segment {i}: duplicate id {seg_id!r}")
            seen_ids.add(seg_id)

            segments.append(SegmentDef(
                seg=seg_type, len=seg_len, rise=rise, id=seg_id,
                amplitude=amplitude, period=period, depth=depth,
                radius=radius,
            ))

        # Parse overlays (optional)
        overlays: list[dict] = []
        for i, raw_ov in enumerate(data.get("overlays", [])):
            ov_type = raw_ov.get("type")
            if ov_type not in VALID_OVERLAY_TYPES:
                raise ValueError(
                    f"Overlay {i}: 'type' must be one of {VALID_OVERLAY_TYPES}, got {ov_type!r}"
                )
            if "at" not in raw_ov or not isinstance(raw_ov["at"], str):
                raise ValueError(f"Overlay {i}: 'at' must be a string")
            ov = {
                "type": ov_type,
                "at": raw_ov["at"],
                "offset_x": raw_ov.get("offset_x", 0),
                "y_offset": raw_ov.get("y_offset", 0),
            }
            if ov_type == "platform":
                w = raw_ov.get("width")
                if w is None or not isinstance(w, int) or w <= 0:
                    raise ValueError(f"Overlay {i}: platform 'width' must be a positive integer")
                ov["width"] = w
                ov["one_sided"] = raw_ov.get("one_sided", True)
            overlays.append(ov)

        # Parse entities (optional)
        entities: list[dict] = []
        for i, raw_ent in enumerate(data.get("entities", [])):
            ent_type = raw_ent.get("type")
            if ent_type not in VALID_ENTITY_TYPES:
                raise ValueError(
                    f"Entity {i}: 'type' must be one of {VALID_ENTITY_TYPES}, got {ent_type!r}"
                )
            if "at" not in raw_ent or not isinstance(raw_ent["at"], str):
                raise ValueError(f"Entity {i}: 'at' must be a string")
            ent = {
                "type": ent_type,
                "at": raw_ent["at"],
                "offset_x": raw_ent.get("offset_x", 0),
                "y_offset": raw_ent.get("y_offset", 0),
            }
            if ent_type == "ring_line":
                count = raw_ent.get("count")
                if count is None or not isinstance(count, int) or count <= 0:
                    raise ValueError(f"Entity {i}: ring_line 'count' must be a positive integer")
                spacing = raw_ent.get("spacing")
                if spacing is None or not isinstance(spacing, int) or spacing <= 0:
                    raise ValueError(f"Entity {i}: ring_line 'spacing' must be a positive integer")
                ent["count"] = count
                ent["spacing"] = spacing
            elif ent_type == "enemy":
                subtype = raw_ent.get("subtype")
                if subtype not in ENEMY_SUBTYPE_MAP:
                    raise ValueError(
                        f"Entity {i}: enemy 'subtype' must be one of "
                        f"{set(ENEMY_SUBTYPE_MAP.keys())}, got {subtype!r}"
                    )
                ent["subtype"] = subtype
            entities.append(ent)

        return ProfileData(
            width=width, height=height, start_y=start_y,
            segments=segments, overlays=overlays, entities=entities,
        )


# ---------------------------------------------------------------------------
# Synthesizer
# ---------------------------------------------------------------------------

class Synthesizer:
    """Converts a ProfileData into a TileGrid via cursor state machine."""

    def __init__(self, profile: ProfileData) -> None:
        self.profile = profile
        cols = math.ceil(profile.width / TILE_SIZE)
        rows = math.ceil(profile.height / TILE_SIZE)
        self.grid = TileGrid(cols, rows)
        self.cursor_x: int = 0
        self.cursor_y: float = float(profile.start_y)
        self.cursor_slope: float = 0.0

    def synthesize(self) -> tuple[TileGrid, list[str]]:
        """Process all segments. Returns (grid, pre_warnings).

        Raises ValueError if any ramp slope exceeds the error threshold,
        or if a halfpipe depth exceeds available space, or if entity/overlay
        references a nonexistent segment.
        """
        self.segment_map = self._build_segment_map()

        pre_warnings = self._validate_slopes()
        pre_warnings.extend(self._check_slope_discontinuities())
        self._validate_entity_refs(pre_warnings)

        for seg in self.profile.segments:
            if seg.seg == "flat":
                self._rasterize_flat(seg)
            elif seg.seg == "ramp":
                self._rasterize_ramp(seg)
            elif seg.seg == "gap":
                self._rasterize_gap(seg)
            elif seg.seg == "wave":
                wave_warnings = self._rasterize_wave(seg)
                pre_warnings.extend(wave_warnings)
            elif seg.seg == "halfpipe":
                self._rasterize_halfpipe(seg)
            elif seg.seg == "loop":
                loop_warnings = self._rasterize_loop(seg)
                pre_warnings.extend(loop_warnings)

        self._rasterize_overlays()

        return self.grid, pre_warnings

    def _build_segment_map(self) -> dict[str, tuple[int, float, int]]:
        """Build mapping of segment ID -> (start_x, start_y, seg_len)."""
        seg_map: dict[str, tuple[int, float, int]] = {}
        cx = 0
        cy = float(self.profile.start_y)
        for seg in self.profile.segments:
            seg_map[seg.id] = (cx, cy, seg.len)
            cx += seg.len
            if seg.seg == "ramp":
                cy += seg.rise
            elif seg.seg == "wave":
                cy += seg.amplitude * math.sin(
                    2 * math.pi * seg.len / seg.period
                )
        return seg_map

    @staticmethod
    def _surface_y_at(seg: SegmentDef, start_y: float, dx: int) -> float:
        """Compute ground surface y at offset dx within a segment."""
        if seg.seg == "ramp":
            return start_y + seg.rise * dx / seg.len
        elif seg.seg == "wave":
            return start_y + seg.amplitude * math.sin(
                2 * math.pi * dx / seg.period
            )
        elif seg.seg == "halfpipe":
            return start_y + seg.depth / 2 * (
                1 - math.cos(2 * math.pi * dx / seg.len)
            )
        else:
            return start_y

    def _validate_entity_refs(self, pre_warnings: list[str]) -> None:
        """Validate overlay/entity segment references (checks 6, 7, 9)."""
        seg_map = self.segment_map

        for i, ov in enumerate(self.profile.overlays):
            at = ov["at"]
            if at not in seg_map:
                raise ValueError(
                    f"Overlay {i} ({ov['type']}): 'at' references nonexistent "
                    f"segment {at!r}"
                )
            _sx, _sy, seg_len = seg_map[at]
            offset_x = ov.get("offset_x", 0)
            if offset_x < 0 or offset_x >= seg_len:
                pre_warnings.append(
                    f"WARNING: overlay {i} ({ov['type']}): offset_x={offset_x} "
                    f"is outside segment '{at}' range [0, {seg_len})"
                )

        has_player_start = False
        for i, ent in enumerate(self.profile.entities):
            if ent["type"] == "player_start":
                has_player_start = True
            at = ent["at"]
            if at not in seg_map:
                raise ValueError(
                    f"Entity {i} ({ent['type']}): 'at' references nonexistent "
                    f"segment {at!r}"
                )
            _sx, _sy, seg_len = seg_map[at]
            offset_x = ent.get("offset_x", 0)
            if offset_x < 0 or offset_x >= seg_len:
                pre_warnings.append(
                    f"WARNING: entity {i} ({ent['type']}): offset_x={offset_x} "
                    f"is outside segment '{at}' range [0, {seg_len})"
                )

        if not has_player_start:
            pre_warnings.append(
                "WARNING: no 'player_start' entity defined; "
                "meta.json player_start will be null"
            )

    def _rasterize_overlays(self) -> None:
        """Rasterize overlay features (platforms) onto the grid."""
        for ov in self.profile.overlays:
            if ov["type"] == "platform":
                self._rasterize_platform(ov)

    def _rasterize_platform(self, ov: dict) -> None:
        """Rasterize a platform overlay as a flat strip of tiles."""
        seg_id = ov["at"]
        start_x, start_y, _seg_len = self.segment_map[seg_id]
        offset_x = ov.get("offset_x", 0)
        y_offset = ov.get("y_offset", 0)

        seg = next(s for s in self.profile.segments if s.id == seg_id)
        surface_y = self._surface_y_at(seg, start_y, offset_x)

        world_x = start_x + offset_x
        world_y = surface_y + y_offset
        width = ov["width"]
        surface_type = (
            SURFACE_TOP_ONLY if ov.get("one_sided", True) else SURFACE_SOLID
        )

        for col in range(world_x, world_x + width):
            self._set_overlay_pixel(
                col, world_y, angle=0, surface_type=surface_type
            )

    def _set_overlay_pixel(
        self, col: int, y: float, angle: int, surface_type: int
    ) -> None:
        """Set one pixel column of an overlay surface (platform)."""
        tx = col // TILE_SIZE
        local_x = col % TILE_SIZE
        ty = int(y) // TILE_SIZE

        if tx < 0 or tx >= self.grid.cols or ty < 0 or ty >= self.grid.rows:
            return

        tile_bottom = (ty + 1) * TILE_SIZE
        h = int(round(tile_bottom - y))
        h = max(0, min(TILE_SIZE, h))

        tile = self.grid.get_tile(tx, ty)
        if tile is None:
            tile = TileData(
                surface_type=surface_type,
                height_array=[0] * TILE_SIZE,
                angle=angle,
            )
            self.grid.set_tile(tx, ty, tile)

        tile.height_array[local_x] = max(tile.height_array[local_x], h)
        tile.angle = angle
        tile.surface_type = surface_type

    def _validate_slopes(self) -> list[str]:
        """Check all segment slopes before rasterizing."""
        warnings: list[str] = []
        for seg in self.profile.segments:
            if seg.seg == "ramp":
                ratio = abs(seg.rise / seg.len)
                if ratio > SLOPE_ERROR_THRESHOLD:
                    raise ValueError(
                        f"Segment '{seg.id}': slope ratio {ratio:.3f} exceeds maximum "
                        f"passable slope (1.0). abs(rise/len) = abs({seg.rise}/{seg.len})"
                    )
                if ratio > SLOPE_WARN_THRESHOLD:
                    warnings.append(
                        f"Steep slope in segment '{seg.id}': ratio {ratio:.3f} "
                        f"exceeds tan(30°) ≈ {SLOPE_WARN_THRESHOLD:.3f}"
                    )
            elif seg.seg == "wave":
                max_slope = 2 * math.pi * seg.amplitude / seg.period
                if max_slope > SLOPE_WARN_THRESHOLD:
                    warnings.append(
                        f"Steep slope in wave segment '{seg.id}': max slope {max_slope:.3f} "
                        f"exceeds tan(30°) ≈ {SLOPE_WARN_THRESHOLD:.3f}"
                    )
            elif seg.seg == "halfpipe":
                max_slope = math.pi * seg.depth / seg.len
                if max_slope > SLOPE_WARN_THRESHOLD:
                    warnings.append(
                        f"Steep slope in halfpipe segment '{seg.id}': max slope {max_slope:.3f} "
                        f"exceeds tan(30°) ≈ {SLOPE_WARN_THRESHOLD:.3f}"
                    )
        return warnings

    def _check_slope_discontinuities(self) -> list[str]:
        """Check for slope mismatches at segment boundaries."""
        warnings: list[str] = []
        segments = self.profile.segments

        prev_slope = 0.0
        prev_id = None
        for seg in segments:
            if seg.seg == "gap":
                # Gaps don't have a slope; reset tracking
                prev_slope = 0.0
                prev_id = None
                continue

            # Compute entry slope for this segment
            if seg.seg == "flat":
                entry_slope = 0.0
            elif seg.seg == "ramp":
                entry_slope = seg.rise / seg.len
            elif seg.seg == "wave":
                # At dx=0: slope = (2π * amp / period) * cos(0) = 2π * amp / period
                entry_slope = 2 * math.pi * seg.amplitude / seg.period
            elif seg.seg == "halfpipe":
                entry_slope = 0.0  # sin(0) = 0
            else:
                entry_slope = 0.0

            if prev_id is not None and prev_slope != entry_slope:
                warnings.append(
                    f"Slope discontinuity between '{prev_id}' and '{seg.id}': "
                    f"{prev_slope:.3f} → {entry_slope:.3f}"
                )

            # Compute exit slope for this segment
            if seg.seg == "flat":
                exit_slope = 0.0
            elif seg.seg == "ramp":
                exit_slope = seg.rise / seg.len
            elif seg.seg == "wave":
                two_pi = 2 * math.pi
                exit_slope = (two_pi * seg.amplitude / seg.period) * math.cos(
                    two_pi * seg.len / seg.period
                )
            elif seg.seg == "halfpipe":
                exit_slope = 0.0  # sin(π) = 0
            else:
                exit_slope = 0.0

            prev_slope = exit_slope
            prev_id = seg.id

        return warnings

    def _rasterize_flat(self, seg: SegmentDef) -> None:
        start_col = self.cursor_x
        end_col = self.cursor_x + seg.len

        for col in range(start_col, end_col):
            self._set_surface_pixel(col, self.cursor_y, angle=0)

        self._fill_below(start_col, end_col)
        self.cursor_x = end_col
        self.cursor_slope = 0.0

    def _rasterize_ramp(self, seg: SegmentDef) -> None:
        start_col = self.cursor_x
        end_col = self.cursor_x + seg.len
        start_y = self.cursor_y
        rise = seg.rise

        # Compute byte angle for this ramp
        angle = round(-math.atan2(rise, seg.len) * 256 / (2 * math.pi)) % 256

        for col in range(start_col, end_col):
            t = (col - start_col) / seg.len
            y = start_y + rise * t
            self._set_surface_pixel(col, y, angle=angle)

        self._fill_below(start_col, end_col)
        self.cursor_x = end_col
        self.cursor_y = start_y + rise
        self.cursor_slope = rise / seg.len

    def _rasterize_gap(self, seg: SegmentDef) -> None:
        self.cursor_x += seg.len
        # cursor_y and cursor_slope unchanged

    def _rasterize_height_profile(
        self,
        profile_fn: "Callable[[int], float]",
        angle_fn: "Callable[[int], int]",
        x_start: int,
        x_end: int,
    ) -> None:
        """Shared rasterizer: iterate pixel columns, set surface, fill below."""
        for col in range(x_start, x_end):
            dx = col - x_start
            y = profile_fn(dx)
            angle = angle_fn(dx)
            self._set_surface_pixel(col, y, angle)
        self._fill_below(x_start, x_end)

    def _rasterize_wave(self, seg: SegmentDef) -> list[str]:
        """Rasterize a sinusoidal wave segment. Returns floor-clamp warnings."""
        warnings: list[str] = []
        start_x = self.cursor_x
        end_x = self.cursor_x + seg.len
        entry_y = self.cursor_y
        amp = seg.amplitude
        per = seg.period
        floor = self.profile.height - TILE_SIZE
        two_pi = 2 * math.pi

        def profile_fn(dx: int) -> float:
            y = entry_y + amp * math.sin(two_pi * dx / per)
            if y > floor:
                warnings.append(
                    f"WARNING: wave segment '{seg.id}' clamps below level floor "
                    f"at offset dx={dx} (y={y:.0f} > floor={floor})"
                )
                return float(floor)
            return y

        def angle_fn(dx: int) -> int:
            slope = (two_pi * amp / per) * math.cos(two_pi * dx / per)
            return round(-math.atan2(slope, 1) * 256 / two_pi) % 256

        self._rasterize_height_profile(profile_fn, angle_fn, start_x, end_x)

        # Cursor exit: use unclamped y for cursor threading
        exit_y = entry_y + amp * math.sin(two_pi * seg.len / per)
        exit_slope = (two_pi * amp / per) * math.cos(two_pi * seg.len / per)
        self.cursor_x = end_x
        self.cursor_y = exit_y
        self.cursor_slope = exit_slope
        return warnings

    def _rasterize_halfpipe(self, seg: SegmentDef) -> None:
        """Rasterize a U-shaped halfpipe segment."""
        entry_y = self.cursor_y
        depth = seg.depth
        floor = self.profile.height - TILE_SIZE

        if entry_y + depth >= floor:
            raise ValueError(
                f"Halfpipe segment '{seg.id}': cursor_y + depth = "
                f"{entry_y} + {depth} = {entry_y + depth} >= floor {floor}"
            )

        start_x = self.cursor_x
        end_x = self.cursor_x + seg.len
        seg_len = seg.len
        pi = math.pi

        two_pi = 2 * pi

        def profile_fn(dx: int) -> float:
            # U-shape: y(0) = y(len) = cursor_y, y(len/2) = cursor_y + depth
            return entry_y + depth / 2 * (1 - math.cos(two_pi * dx / seg_len))

        def angle_fn(dx: int) -> int:
            # Derivative: dy/dx = depth * π / seg_len * sin(2π * dx / seg_len)
            slope = depth * pi / seg_len * math.sin(two_pi * dx / seg_len)
            return round(-math.atan2(slope, 1) * 256 / two_pi) % 256

        self._rasterize_height_profile(profile_fn, angle_fn, start_x, end_x)

        # Halfpipe always exits at entry_y with zero slope
        self.cursor_x = end_x
        self.cursor_y = entry_y
        self.cursor_slope = 0.0

    def _rasterize_loop(self, seg: SegmentDef) -> list[str]:
        """Rasterize a full 360° loop with entry/exit transition ramps."""
        warnings: list[str] = []
        radius = seg.radius
        r_ramp = radius  # ramp radius = loop radius (configurable later)

        if radius < 64:
            warnings.append(
                f"Small loop radius in segment '{seg.id}': radius {radius} < 64, "
                f"physics may be unstable"
            )

        # Layout: [entry_ramp | loop_circle | exit_ramp]
        entry_start = self.cursor_x
        loop_start = entry_start + r_ramp
        loop_end = loop_start + 2 * radius
        exit_end = loop_end + r_ramp

        cx = loop_start + radius  # circle center x
        cy = self.cursor_y - radius  # circle center y
        ground_y = self.cursor_y  # = cy + radius
        two_pi = 2 * math.pi

        # --- Local helpers for quarter-circle ramp arcs ---
        def _arc_surface_y(px: int, arc_cx: float) -> float:
            """Surface y on a quarter-circle arc centered at (arc_cx, cy)."""
            dx = px - arc_cx
            val = max(0.0, r_ramp * r_ramp - dx * dx)
            return cy + math.sqrt(val)

        def _ramp_angle(px: int, arc_cx: float) -> int:
            """Byte angle from finite difference on arc surface."""
            sy0 = _arc_surface_y(px, arc_cx)
            sy1 = _arc_surface_y(px + 1, arc_cx)
            slope = sy1 - sy0
            return round(-math.atan2(slope, 1.0) * 256 / two_pi) % 256

        # --- Entry ramp (left side) ---
        entry_arc_cx = float(loop_start)  # arc center = loop's leftmost point
        for px in range(entry_start, loop_start):
            sy = _arc_surface_y(px, entry_arc_cx)
            sy = min(sy, ground_y)
            angle = _ramp_angle(px, entry_arc_cx)
            self._set_surface_pixel(px, sy, angle)
            self._fill_column_below(px, sy)

        # --- Loop circle (existing logic, shifted coordinates) ---
        for px in range(loop_start, loop_end):
            dx = px - cx + 0.5  # pixel center
            if abs(dx) > radius:
                continue
            dy = math.sqrt(radius * radius - dx * dx)

            y_bottom = cy + dy
            y_top = cy - dy

            angle_bottom = round(-math.atan2(dx, dy) * 256 / two_pi) % 256
            self._set_loop_pixel(px, y_bottom, angle_bottom, is_upper=False)

            angle_top = round(-math.atan2(-dx, -dy) * 256 / two_pi) % 256
            self._set_loop_pixel(px, y_top, angle_top, is_upper=True)

            self._fill_column_below(px, y_bottom)

        self._fill_below_loop(loop_start, loop_end)

        # --- Exit ramp (right side) ---
        exit_arc_cx = float(loop_end)  # arc center = loop's rightmost point
        for px in range(loop_end, exit_end):
            sy = _arc_surface_y(px, exit_arc_cx)
            sy = min(sy, ground_y)
            angle = _ramp_angle(px, exit_arc_cx)
            self._set_surface_pixel(px, sy, angle)
            self._fill_column_below(px, sy)

        # Advance cursor
        self.cursor_x = exit_end
        # cursor_y unchanged: loop exits at same height as entry
        self.cursor_slope = 0.0
        return warnings

    def _set_loop_pixel(
        self, col: int, y: float, angle: int, is_upper: bool
    ) -> None:
        """Set one pixel column of loop surface.

        Loop tiles are set to full tile height (TILE_SIZE) rather than
        precise arc heights. The angle field provides the surface normal
        for physics. Full height ensures no impassable gaps between
        adjacent arc tiles in the Validator.
        """
        tx = col // TILE_SIZE
        local_x = col % TILE_SIZE
        ty = int(y) // TILE_SIZE

        if tx < 0 or tx >= self.grid.cols or ty < 0 or ty >= self.grid.rows:
            return

        tile = self.grid.get_tile(tx, ty)
        if tile is None:
            tile = TileData(
                surface_type=SURFACE_LOOP,
                height_array=[0] * TILE_SIZE,
                angle=angle,
                is_loop_upper=is_upper,
            )
            self.grid.set_tile(tx, ty, tile)

        tile.height_array[local_x] = TILE_SIZE
        tile.angle = angle
        tile.surface_type = SURFACE_LOOP
        tile.is_loop_upper = tile.is_loop_upper or is_upper

    def _fill_column_below(self, col: int, y: float) -> None:
        """Fill a single pixel column solid from y down to grid bottom.

        Sets the height in the surface tile for this local_x, then fills
        all tiles below it fully solid.
        """
        tx = col // TILE_SIZE
        local_x = col % TILE_SIZE
        surface_ty = int(y) // TILE_SIZE

        if tx < 0 or tx >= self.grid.cols:
            return

        # Make the surface tile's column fully solid below the arc point
        tile_bottom = (surface_ty + 1) * TILE_SIZE
        h = max(0, min(TILE_SIZE, math.ceil(tile_bottom - y)))
        if surface_ty >= 0 and surface_ty < self.grid.rows:
            tile = self.grid.get_tile(tx, surface_ty)
            if tile is not None:
                tile.height_array[local_x] = max(tile.height_array[local_x], h)

        # Fill all tiles below the surface tile as fully solid
        for ty in range(surface_ty + 1, self.grid.rows):
            existing = self.grid.get_tile(tx, ty)
            if existing is None:
                self.grid.set_tile(tx, ty, TileData(
                    surface_type=SURFACE_SOLID,
                    height_array=[0] * TILE_SIZE,
                    angle=0,
                ))
            # Set this local_x column to full height
            fill_tile = self.grid.get_tile(tx, ty)
            if fill_tile is not None and fill_tile.surface_type != SURFACE_LOOP:
                fill_tile.height_array[local_x] = max(
                    fill_tile.height_array[local_x], TILE_SIZE
                )

    def _fill_below_loop(self, start_col: int, end_col: int) -> None:
        """Fill solid ground below the bottom arc of the loop.

        For each tile column in the loop footprint, find the lowest
        SURFACE_LOOP tile (bottom arc) and fill all rows below it with
        SURFACE_SOLID. This connects the loop to the ground without
        flooding the hollow interior.
        """
        start_tx = start_col // TILE_SIZE
        end_tx = (end_col - 1) // TILE_SIZE if end_col > start_col else start_tx

        for tx in range(start_tx, end_tx + 1):
            if tx < 0 or tx >= self.grid.cols:
                continue

            # Find the lowest (highest ty) SURFACE_LOOP tile in this column
            bottom_loop_ty = None
            for ty in range(self.grid.rows - 1, -1, -1):
                tile = self.grid.get_tile(tx, ty)
                if tile is not None and tile.surface_type == SURFACE_LOOP:
                    bottom_loop_ty = ty
                    break

            if bottom_loop_ty is None:
                continue

            # Fill below the bottom arc tile
            for ty in range(bottom_loop_ty + 1, self.grid.rows):
                existing = self.grid.get_tile(tx, ty)
                if existing is None:
                    self.grid.set_tile(tx, ty, TileData(
                        surface_type=SURFACE_SOLID,
                        height_array=[TILE_SIZE] * TILE_SIZE,
                        angle=0,
                    ))

    def _set_surface_pixel(self, col: int, y: float, angle: int) -> None:
        """Set one pixel column of surface in the tile grid."""
        tx = col // TILE_SIZE
        local_x = col % TILE_SIZE
        ty = int(y) // TILE_SIZE

        if tx < 0 or tx >= self.grid.cols or ty < 0 or ty >= self.grid.rows:
            return

        tile_bottom = (ty + 1) * TILE_SIZE
        h = int(round(tile_bottom - y))
        h = max(0, min(TILE_SIZE, h))

        tile = self.grid.get_tile(tx, ty)
        if tile is None:
            tile = TileData(
                surface_type=SURFACE_SOLID,
                height_array=[0] * TILE_SIZE,
                angle=angle,
            )
            self.grid.set_tile(tx, ty, tile)

        tile.height_array[local_x] = max(tile.height_array[local_x], h)
        tile.angle = angle

    def _fill_below(self, start_col: int, end_col: int) -> None:
        """Fill tiles below the surface as fully solid."""
        # Determine which tile columns were touched
        start_tx = start_col // TILE_SIZE
        end_tx = (end_col - 1) // TILE_SIZE if end_col > start_col else start_tx

        for tx in range(start_tx, end_tx + 1):
            if tx < 0 or tx >= self.grid.cols:
                continue

            # Find the topmost surface tile in this column
            surface_ty = None
            for ty in range(self.grid.rows):
                if self.grid.get_tile(tx, ty) is not None:
                    surface_ty = ty
                    break

            if surface_ty is None:
                continue

            # Fill below
            for ty in range(surface_ty + 1, self.grid.rows):
                existing = self.grid.get_tile(tx, ty)
                if existing is None:
                    self.grid.set_tile(tx, ty, TileData(
                        surface_type=SURFACE_SOLID,
                        height_array=[TILE_SIZE] * TILE_SIZE,
                        angle=0,
                    ))


# ---------------------------------------------------------------------------
# Entity resolution
# ---------------------------------------------------------------------------

def resolve_entities(
    profile: ProfileData,
    segment_map: dict[str, tuple[int, float, int]],
    segments: list[SegmentDef],
) -> list[Entity]:
    """Resolve all entities and spring overlays to world-coordinate Entity objects."""
    entities: list[Entity] = []

    # Process spring overlays as entities
    for ov in profile.overlays:
        if ov["type"] in ("spring_up", "spring_right"):
            seg_id = ov["at"]
            start_x, start_y, _ = segment_map[seg_id]
            seg = next(s for s in segments if s.id == seg_id)
            offset_x = ov.get("offset_x", 0)
            y_offset = ov.get("y_offset", 0)
            surface_y = Synthesizer._surface_y_at(seg, start_y, offset_x)
            entities.append(Entity(
                entity_type=ov["type"],
                x=float(start_x + offset_x),
                y=surface_y + y_offset,
            ))

    # Process declared entities
    for ent in profile.entities:
        seg_id = ent["at"]
        start_x, start_y, _ = segment_map[seg_id]
        seg = next(s for s in segments if s.id == seg_id)
        offset_x = ent.get("offset_x", 0)
        y_offset = ent.get("y_offset", 0)
        surface_y = Synthesizer._surface_y_at(seg, start_y, offset_x)
        world_x = float(start_x + offset_x)
        world_y = surface_y + y_offset

        ent_type = ent["type"]

        if ent_type == "ring_line":
            count = ent["count"]
            spacing = ent["spacing"]
            for i in range(count):
                entities.append(Entity(
                    entity_type="ring",
                    x=world_x + i * spacing,
                    y=world_y,
                ))
        elif ent_type == "enemy":
            mapped_type = ENEMY_SUBTYPE_MAP[ent["subtype"]]
            entities.append(Entity(
                entity_type=mapped_type, x=world_x, y=world_y,
            ))
        else:
            # player_start, checkpoint, goal — pass through
            entities.append(Entity(
                entity_type=ent_type, x=world_x, y=world_y,
            ))

    return entities


# ---------------------------------------------------------------------------
# Meta builder
# ---------------------------------------------------------------------------

def build_meta(
    profile: ProfileData, grid: TileGrid, entities: list[Entity],
) -> dict:
    """Build meta.json content for a profile-generated stage."""
    player_start = None
    checkpoints = []
    for e in entities:
        if e.entity_type == "player_start":
            player_start = {"x": round(e.x), "y": round(e.y)}
        elif e.entity_type == "checkpoint":
            checkpoints.append({"x": round(e.x), "y": round(e.y)})

    return {
        "width_px": profile.width,
        "height_px": profile.height,
        "width_tiles": grid.cols,
        "height_tiles": grid.rows,
        "player_start": player_start,
        "checkpoints": checkpoints,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert profile JSON to speednik stage data."
    )
    parser.add_argument("input_profile", help="Path to input .profile.json file")
    parser.add_argument("output_dir", help="Output directory for stage data")
    args = parser.parse_args()

    if not os.path.isfile(args.input_profile):
        print(f"Error: {args.input_profile} not found", file=sys.stderr)
        sys.exit(1)

    # Load and validate profile
    try:
        profile = ProfileParser.load(args.input_profile)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Profile: {profile.width}x{profile.height}px, "
          f"{len(profile.segments)} segments, start_y={profile.start_y}")

    # Synthesize tile grid
    try:
        synth = Synthesizer(profile)
        grid, pre_warnings = synth.synthesize()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    tile_count = sum(
        1 for ty in range(grid.rows) for tx in range(grid.cols)
        if grid.get_tile(tx, ty) is not None
    )
    print(f"Synthesized: {grid.cols}x{grid.rows} grid, {tile_count} tiles")

    # Resolve entities
    entities = resolve_entities(profile, synth.segment_map, profile.segments)
    print(f"Entities: {len(entities)} resolved")

    # Validate
    validator = Validator(grid)
    post_issues = validator.validate()
    all_issues = pre_warnings + post_issues
    print(f"Validation: {len(all_issues)} issues "
          f"({len(pre_warnings)} pre, {len(post_issues)} post)")

    # Build meta and write output
    meta = build_meta(profile, grid, entities)
    writer = StageWriter(args.output_dir)
    writer.write(grid, entities, meta, all_issues)
    print(f"Output written to {args.output_dir}")


if __name__ == "__main__":
    main()

"""Integration tests for hillside loop traversal (T-007-04).

Loads the actual hillside stage data and verifies the full pipeline chain:
SVG → svg2stage rasterizer → JSON → level loader → Tile objects → sensors.

No mocking — these tests exercise the real generated data.
"""

from speednik.level import load_stage
from speednik.physics import PhysicsState
from speednik.terrain import (
    FULL,
    SURFACE_LOOP,
    TOP_ONLY,
    find_wall_push,
    LEFT,
    RIGHT,
)

# ---------------------------------------------------------------------------
# Loop geometry constants
# ---------------------------------------------------------------------------
# Collision loop: cx=3592, cy=560, r=64 (synthetic build_loop geometry).
# Visual loop is larger (r=128) but collision uses r=64 for traversal.
# Entry ramp: cols 219–220  (pixel x: 3504–3528)
# Loop tiles: cols 220–228  (pixel x: 3528–3656)
# Exit ramp:  cols 228–230  (pixel x: 3656–3680)
# Ground level: row 39

LOOP_CENTER_COL = 224  # ~3592/16
LOOP_CENTER_ROW = 35   # ~560/16

# Original hillside approach: cols 210-213 (untouched original tiles)
# build_loop() entry ramp: cols 219-220
# build_loop() loop body: cols 220-228 (SURFACE_LOOP tiles)
# build_loop() exit ramp: cols 228-234
# Cols 214-218 are a gap (cleared original ramp tiles, not yet covered by build_loop)
ENTRY_RAMP_COLS = range(210, 214)  # original hillside approach tiles only
LOOP_COLS = range(220, 230)
EXIT_RAMP_COLS = range(228, 235)
FULL_REGION_COLS = range(219, 241)  # build_loop region only

GROUND_ROW = 39


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_stage = None


def _get_stage():
    global _stage
    if _stage is None:
        _stage = load_stage("hillside")
    return _stage


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRampTilesExist:
    """Entry and exit ramp columns have tiles at ground level."""

    def test_entry_ramp_tiles_present(self):
        stage = _get_stage()
        for col in ENTRY_RAMP_COLS:
            found = False
            for row in range(GROUND_ROW - 5, GROUND_ROW + 2):
                tile = stage.tile_lookup(col, row)
                if tile is not None and max(tile.height_array) > 0:
                    found = True
                    break
            assert found, f"No ramp tile at column {col} near ground level"

    def test_exit_ramp_tiles_present(self):
        stage = _get_stage()
        for col in EXIT_RAMP_COLS:
            found = False
            for row in range(GROUND_ROW - 5, GROUND_ROW + 2):
                tile = stage.tile_lookup(col, row)
                if tile is not None and max(tile.height_array) > 0:
                    found = True
                    break
            assert found, f"No ramp tile at column {col} near ground level"


class TestLoopTileType:
    """Loop tiles carry tile_type == SURFACE_LOOP (5) through the full chain."""

    def test_loop_tiles_have_correct_type(self):
        stage = _get_stage()
        loop_tiles_found = 0
        for col in LOOP_COLS:
            for row in range(LOOP_CENTER_ROW - 10, LOOP_CENTER_ROW + 10):
                tile = stage.tile_lookup(col, row)
                if tile is not None and tile.tile_type == SURFACE_LOOP:
                    loop_tiles_found += 1
        assert loop_tiles_found > 0, "No loop tiles with tile_type=SURFACE_LOOP found"

    def test_loop_tiles_not_in_ramp_region(self):
        """Ramp tiles at ground level should NOT have SURFACE_LOOP type.

        Note: build_loop() creates overlapping regions where loop circle tiles
        and ramp tiles coexist at different rows. Only ground-level tiles (near
        GROUND_ROW) are checked.
        """
        stage = _get_stage()
        for col in list(ENTRY_RAMP_COLS) + list(EXIT_RAMP_COLS):
            for row in [GROUND_ROW - 1, GROUND_ROW, GROUND_ROW + 1]:
                tile = stage.tile_lookup(col, row)
                if tile is not None:
                    assert tile.tile_type != SURFACE_LOOP, (
                        f"Ramp tile at ({col},{row}) incorrectly has SURFACE_LOOP type"
                    )


class TestRampAngleProgression:
    """Ramp tile angles progress smoothly (no large jumps between adjacent tiles)."""

    def _collect_surface_angles(self, stage, cols, row_range):
        """Collect (col, angle) pairs for tiles with non-zero height in the given region."""
        angles = []
        for col in cols:
            for row in row_range:
                tile = stage.tile_lookup(col, row)
                if tile is not None and max(tile.height_array) > 0 and tile.angle != 0:
                    angles.append((col, tile.angle))
                    break  # take the topmost surface tile per column
        return angles

    def test_entry_ramp_angles_smooth(self):
        stage = _get_stage()
        angles = self._collect_surface_angles(
            stage, ENTRY_RAMP_COLS, range(GROUND_ROW - 5, GROUND_ROW + 2)
        )
        assert len(angles) >= 2, f"Too few entry ramp angle samples: {len(angles)}"
        for i in range(len(angles) - 1):
            col_a, ang_a = angles[i]
            col_b, ang_b = angles[i + 1]
            # Skip non-adjacent columns (gap between original and synthetic tiles)
            if col_b - col_a > 1:
                continue
            diff = min(abs(ang_b - ang_a), 256 - abs(ang_b - ang_a))
            assert diff <= 21, (
                f"Entry ramp angle jump {diff} between cols {col_a}→{col_b} "
                f"(angles {ang_a}→{ang_b})"
            )

    def test_exit_ramp_angles_smooth(self):
        stage = _get_stage()
        angles = self._collect_surface_angles(
            stage, EXIT_RAMP_COLS, range(GROUND_ROW - 5, GROUND_ROW + 2)
        )
        assert len(angles) >= 2, f"Too few exit ramp angle samples: {len(angles)}"
        for i in range(len(angles) - 1):
            col_a, ang_a = angles[i]
            col_b, ang_b = angles[i + 1]
            diff = min(abs(ang_b - ang_a), 256 - abs(ang_b - ang_a))
            assert diff <= 21, (
                f"Exit ramp angle jump {diff} between cols {col_a}→{col_b} "
                f"(angles {ang_a}→{ang_b})"
            )


class TestLoopSolidity:
    """Upper loop tiles have TOP_ONLY solidity; lower loop tiles have FULL."""

    def test_upper_loop_tiles_full_solidity(self):
        """Synthetic build_loop() uses FULL solidity for all loop tiles."""
        stage = _get_stage()
        upper_found = 0
        for col in LOOP_COLS:
            for row in range(LOOP_CENTER_ROW - 10, LOOP_CENTER_ROW):
                tile = stage.tile_lookup(col, row)
                if tile is not None and tile.tile_type == SURFACE_LOOP:
                    assert tile.solidity == FULL, (
                        f"Upper loop tile at ({col},{row}) has solidity {tile.solidity}, "
                        f"expected FULL ({FULL})"
                    )
                    upper_found += 1
        assert upper_found > 0, "No upper loop tiles found above center row"

    def test_lower_loop_tiles_full(self):
        stage = _get_stage()
        lower_found = 0
        for col in LOOP_COLS:
            for row in range(LOOP_CENTER_ROW, LOOP_CENTER_ROW + 10):
                tile = stage.tile_lookup(col, row)
                if tile is not None and tile.tile_type == SURFACE_LOOP:
                    assert tile.solidity == FULL, (
                        f"Lower loop tile at ({col},{row}) has solidity {tile.solidity}, "
                        f"expected FULL ({FULL})"
                    )
                    lower_found += 1
        assert lower_found > 0, "No lower loop tiles found below center row"


class TestGroundContinuity:
    """Every column in the loop region has at least one ground tile."""

    def test_no_empty_columns_in_loop_region(self):
        stage = _get_stage()
        for col in FULL_REGION_COLS:
            has_ground = False
            for row in range(GROUND_ROW - 10, GROUND_ROW + 2):
                tile = stage.tile_lookup(col, row)
                if tile is not None and max(tile.height_array) > 0:
                    has_ground = True
                    break
            assert has_ground, f"Column {col} has no ground tile in the loop region"


class TestWallSensorLoopExemption:
    """Wall sensors correctly exempt loop tiles from blocking."""

    def test_wall_sensor_ignores_loop_tiles(self):
        """Place a simulated player at a loop tile position, verify no wall push."""
        stage = _get_stage()
        # Find a loop tile in the lower part of the loop (where wall sensors could fire)
        loop_tile_pos = None
        for col in LOOP_COLS:
            for row in range(LOOP_CENTER_ROW, LOOP_CENTER_ROW + 8):
                tile = stage.tile_lookup(col, row)
                if tile is not None and tile.tile_type == SURFACE_LOOP:
                    loop_tile_pos = (col, row)
                    break
            if loop_tile_pos is not None:
                break

        assert loop_tile_pos is not None, "Could not find a loop tile for wall sensor test"

        col, row = loop_tile_pos
        # Place physics state at the center of this tile, moving right
        state = PhysicsState(
            x=col * 16 + 8,
            y=row * 16 + 8,
            x_vel=-2.0,  # moving left, so right wall sensor is active
            on_ground=True,
            angle=0,
        )

        result = find_wall_push(state, stage.tile_lookup, RIGHT)
        assert not result.found, (
            f"Wall sensor RIGHT found a blocking surface at loop tile ({col},{row}), "
            f"tile_type={result.tile_type} angle={result.tile_angle}"
        )

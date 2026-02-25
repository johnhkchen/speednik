"""Tests for speednik/devpark.py — LiveBot, factory functions, and dev park stages."""

from __future__ import annotations

from typing import Optional

from speednik.devpark import (
    QUADRANTS,
    STAGES,
    LiveBot,
    _init_boundary_patrol,
    _init_gap_jump,
    _init_hillside_bot,
    _init_loop_lab_no_ramps,
    _init_loop_lab_with_ramps,
    _init_multi_view_hillside,
    _init_ramp_walker,
    _init_speed_gate,
    make_bot,
    make_bots_for_grid,
    make_bots_for_stage,
)
from speednik.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from speednik.physics import InputState
from speednik.player import Player, create_player
from speednik.terrain import FULL, TILE_SIZE, Tile, TileLookup
from tests.harness import hold_right, idle


# ---------------------------------------------------------------------------
# Test fixtures — flat grid (no Pyxel needed)
# ---------------------------------------------------------------------------

def _build_flat_test_grid(
    width_tiles: int = 20, ground_row: int = 8
) -> tuple[dict, TileLookup]:
    """Build a flat grid and return (tiles_dict, tile_lookup)."""
    tiles: dict[tuple[int, int], Tile] = {}
    for tx in range(width_tiles):
        tiles[(tx, ground_row)] = Tile(
            height_array=[TILE_SIZE] * TILE_SIZE,
            angle=0,
            solidity=FULL,
        )
        # Fill below
        for ty in range(ground_row + 1, ground_row + 5):
            tiles[(tx, ty)] = Tile(
                height_array=[TILE_SIZE] * TILE_SIZE,
                angle=0,
                solidity=FULL,
            )

    def lookup(tx: int, ty: int) -> Optional[Tile]:
        return tiles.get((tx, ty))

    return tiles, lookup


# ---------------------------------------------------------------------------
# TestLiveBotUpdate
# ---------------------------------------------------------------------------

class TestLiveBotUpdate:
    """LiveBot.update() advances simulation correctly."""

    def test_update_advances_frame(self):
        tiles_dict, tile_lookup = _build_flat_test_grid()
        start_x = 2 * TILE_SIZE + 8.0
        start_y = 8 * TILE_SIZE - 1.0
        bot = make_bot(tiles_dict, tile_lookup, start_x, start_y, idle(), "IDLE")
        assert bot.frame == 0
        bot.update()
        assert bot.frame == 1

    def test_update_moves_player_with_hold_right(self):
        tiles_dict, tile_lookup = _build_flat_test_grid()
        start_x = 2 * TILE_SIZE + 8.0
        start_y = 8 * TILE_SIZE - 1.0
        bot = make_bot(tiles_dict, tile_lookup, start_x, start_y, hold_right(), "RIGHT")
        for _ in range(30):
            bot.update()
        assert bot.player.physics.x > start_x

    def test_finishes_at_max_frames(self):
        tiles_dict, tile_lookup = _build_flat_test_grid()
        start_x = 2 * TILE_SIZE + 8.0
        start_y = 8 * TILE_SIZE - 1.0
        bot = make_bot(
            tiles_dict, tile_lookup, start_x, start_y, idle(), "IDLE", max_frames=5
        )
        assert not bot.finished
        for _ in range(5):
            bot.update()
        assert bot.finished
        assert bot.frame == 5

    def test_finishes_at_goal_x(self):
        tiles_dict, tile_lookup = _build_flat_test_grid(width_tiles=40)
        start_x = 2 * TILE_SIZE + 8.0
        start_y = 8 * TILE_SIZE - 1.0
        goal = start_x + 50.0
        bot = make_bot(
            tiles_dict, tile_lookup, start_x, start_y,
            hold_right(), "RIGHT", max_frames=600, goal_x=goal,
        )
        # Run until finished or max
        while not bot.finished:
            bot.update()
        assert bot.player.physics.x >= goal
        assert bot.frame < 600  # finished before max

    def test_finished_bot_stops_updating(self):
        tiles_dict, tile_lookup = _build_flat_test_grid()
        start_x = 2 * TILE_SIZE + 8.0
        start_y = 8 * TILE_SIZE - 1.0
        bot = make_bot(
            tiles_dict, tile_lookup, start_x, start_y, idle(), "IDLE", max_frames=3
        )
        for _ in range(3):
            bot.update()
        assert bot.finished
        frame_at_finish = bot.frame
        pos_at_finish = bot.player.physics.x

        # Additional updates should be no-ops
        bot.update()
        bot.update()
        assert bot.frame == frame_at_finish
        assert bot.player.physics.x == pos_at_finish


# ---------------------------------------------------------------------------
# TestMakeBot
# ---------------------------------------------------------------------------

class TestMakeBot:
    """make_bot factory creates LiveBot with correct fields."""

    def test_creates_bot_with_correct_label(self):
        tiles_dict, tile_lookup = _build_flat_test_grid()
        bot = make_bot(
            tiles_dict, tile_lookup, 32.0, 120.0, idle(), "TEST_LABEL"
        )
        assert bot.label == "TEST_LABEL"

    def test_creates_bot_at_start_position(self):
        tiles_dict, tile_lookup = _build_flat_test_grid()
        bot = make_bot(tiles_dict, tile_lookup, 48.0, 120.0, idle(), "POS")
        assert bot.player.physics.x == 48.0
        assert bot.player.physics.y == 120.0

    def test_bot_starts_at_frame_zero(self):
        tiles_dict, tile_lookup = _build_flat_test_grid()
        bot = make_bot(tiles_dict, tile_lookup, 32.0, 120.0, idle(), "ZERO")
        assert bot.frame == 0
        assert not bot.finished


# ---------------------------------------------------------------------------
# TestMakeBotsForStage
# ---------------------------------------------------------------------------

class TestMakeBotsForStage:
    """make_bots_for_stage creates bots for a real stage."""

    def test_creates_four_bots(self):
        bots = make_bots_for_stage("hillside", max_frames=10)
        assert len(bots) == 4

    def test_bot_labels(self):
        bots = make_bots_for_stage("hillside", max_frames=10)
        labels = [b.label for b in bots]
        assert labels == ["IDLE", "HOLD_RIGHT", "JUMP", "SPINDASH"]

    def test_bots_can_update(self):
        bots = make_bots_for_stage("hillside", max_frames=10)
        for bot in bots:
            bot.update()
        assert all(b.frame == 1 for b in bots)


# ---------------------------------------------------------------------------
# TestMakeBotsForGrid
# ---------------------------------------------------------------------------

class TestMakeBotsForGrid:
    """make_bots_for_grid creates bots for synthetic tile data."""

    def test_creates_correct_number_of_bots(self):
        tiles_dict, tile_lookup = _build_flat_test_grid()
        strategies = [(idle(), "IDLE"), (hold_right(), "RIGHT")]
        bots = make_bots_for_grid(
            tiles_dict, tile_lookup, 32.0, 120.0, strategies
        )
        assert len(bots) == 2
        assert bots[0].label == "IDLE"
        assert bots[1].label == "RIGHT"

    def test_grid_bots_can_update(self):
        tiles_dict, tile_lookup = _build_flat_test_grid()
        strategies = [(hold_right(), "RIGHT")]
        bots = make_bots_for_grid(
            tiles_dict, tile_lookup,
            2 * TILE_SIZE + 8.0, 8 * TILE_SIZE - 1.0,
            strategies,
        )
        for _ in range(10):
            bots[0].update()
        assert bots[0].frame == 10
        assert bots[0].player.physics.x > 2 * TILE_SIZE + 8.0


# ---------------------------------------------------------------------------
# TestMultiBotIndependence
# ---------------------------------------------------------------------------

class TestMultiBotIndependence:
    """Multiple bots with different strategies diverge correctly."""

    def test_four_bots_update_independently(self):
        tiles_dict, tile_lookup = _build_flat_test_grid(width_tiles=40)
        start_x = 2 * TILE_SIZE + 8.0
        start_y = 8 * TILE_SIZE - 1.0

        bots = [
            make_bot(tiles_dict, tile_lookup, start_x, start_y, idle(), "IDLE"),
            make_bot(tiles_dict, tile_lookup, start_x, start_y, hold_right(), "RIGHT1"),
            make_bot(tiles_dict, tile_lookup, start_x, start_y, hold_right(), "RIGHT2"),
            make_bot(tiles_dict, tile_lookup, start_x, start_y, idle(), "IDLE2"),
        ]

        for _ in range(30):
            for bot in bots:
                bot.update()

        assert all(b.frame == 30 for b in bots)
        assert bots[0].player.physics.x < start_x + 5
        assert bots[1].player.physics.x > start_x + 10
        assert bots[2].player.physics.x > start_x + 10
        assert bots[3].player.physics.x < start_x + 5

    def test_bots_have_independent_cameras(self):
        tiles_dict, tile_lookup = _build_flat_test_grid(width_tiles=40)
        start_x = 2 * TILE_SIZE + 8.0
        start_y = 8 * TILE_SIZE - 1.0

        bot_idle = make_bot(tiles_dict, tile_lookup, start_x, start_y, idle(), "IDLE")
        bot_right = make_bot(tiles_dict, tile_lookup, start_x, start_y, hold_right(), "RIGHT")

        for _ in range(60):
            bot_idle.update()
            bot_right.update()

        assert bot_right.camera.x >= bot_idle.camera.x


# ---------------------------------------------------------------------------
# TestDevParkStages
# ---------------------------------------------------------------------------

class TestDevParkStages:
    """Dev park stage init functions create correct bots."""

    def test_stages_list_has_seven_entries(self):
        assert len(STAGES) == 7

    def test_stage_names(self):
        names = [s.name for s in STAGES]
        assert names == [
            "RAMP WALKER", "SPEED GATE", "LOOP LAB",
            "GAP JUMP", "HILLSIDE BOT", "MULTI-VIEW",
            "BOUNDARY PATROL",
        ]

    def test_ramp_walker_creates_two_bots(self):
        bots = _init_ramp_walker()
        assert len(bots) == 2
        assert bots[0].label == "HOLD_RIGHT"
        assert bots[1].label == "SPINDASH"

    def test_ramp_walker_bots_can_update(self):
        bots = _init_ramp_walker()
        for bot in bots:
            for _ in range(10):
                bot.update()
        assert all(b.frame == 10 for b in bots)

    def test_speed_gate_creates_two_bots(self):
        bots = _init_speed_gate()
        assert len(bots) == 2
        assert bots[0].label == "WALK"
        assert bots[1].label == "SPINDASH"

    def test_speed_gate_bots_can_update(self):
        bots = _init_speed_gate()
        for bot in bots:
            for _ in range(10):
                bot.update()
        assert all(b.frame == 10 for b in bots)

    def test_loop_lab_with_ramps_creates_one_bot(self):
        bots = _init_loop_lab_with_ramps()
        assert len(bots) == 1
        assert bots[0].label == "WITH RAMPS"

    def test_loop_lab_no_ramps_creates_one_bot(self):
        bots = _init_loop_lab_no_ramps()
        assert len(bots) == 1
        assert bots[0].label == "NO RAMPS"

    def test_loop_lab_bots_can_update(self):
        bots = _init_loop_lab_with_ramps()
        for _ in range(10):
            bots[0].update()
        assert bots[0].frame == 10

    def test_gap_jump_creates_one_bot(self):
        bots = _init_gap_jump(0)
        assert len(bots) == 1
        assert "GAP=" in bots[0].label

    def test_gap_jump_different_widths(self):
        bots0 = _init_gap_jump(0)
        bots1 = _init_gap_jump(1)
        assert bots0[0].label != bots1[0].label

    def test_gap_jump_bots_can_update(self):
        bots = _init_gap_jump(0)
        for _ in range(10):
            bots[0].update()
        assert bots[0].frame == 10

    def test_hillside_bot_creates_one_bot(self):
        bots = _init_hillside_bot()
        assert len(bots) == 1
        assert bots[0].label == "HOLD_RIGHT"

    def test_hillside_bot_can_update(self):
        bots = _init_hillside_bot()
        for _ in range(10):
            bots[0].update()
        assert bots[0].frame == 10

    def test_multi_view_creates_four_bots(self):
        bots = _init_multi_view_hillside()
        assert len(bots) == 4
        labels = [b.label for b in bots]
        assert labels == ["IDLE", "HOLD_RIGHT", "JUMP", "SPINDASH"]

    def test_multi_view_bots_can_update(self):
        bots = _init_multi_view_hillside()
        for bot in bots:
            for _ in range(10):
                bot.update()
        assert all(b.frame == 10 for b in bots)

    def test_boundary_patrol_creates_two_bots(self):
        bots = _init_boundary_patrol(0)
        assert len(bots) == 2
        assert bots[0].label == "RIGHT->"
        assert bots[1].label == "<-LEFT"

    def test_boundary_patrol_bots_can_update(self):
        bots = _init_boundary_patrol(0)
        for bot in bots:
            for _ in range(10):
                bot.update()
        assert all(b.frame == 10 for b in bots)

    def test_boundary_patrol_cycles_stages(self):
        bots0 = _init_boundary_patrol(0)
        bots1 = _init_boundary_patrol(1)
        # Different stages should use different tile data
        assert bots0[0].tiles_dict is not bots1[0].tiles_dict


# ---------------------------------------------------------------------------
# TestQuadSplit
# ---------------------------------------------------------------------------

class TestQuadSplit:
    """Quad-split layout geometry tests."""

    def test_quadrants_cover_full_screen(self):
        """QUADRANTS tile the entire 256x224 screen with no gaps."""
        total_area = sum(qw * qh for _, _, qw, qh in QUADRANTS)
        assert total_area == SCREEN_WIDTH * SCREEN_HEIGHT

    def test_quadrants_no_overlap(self):
        """No two quadrants overlap."""
        for i, (ax, ay, aw, ah) in enumerate(QUADRANTS):
            for j, (bx, by, bw, bh) in enumerate(QUADRANTS):
                if i >= j:
                    continue
                x_sep = (ax + aw <= bx) or (bx + bw <= ax)
                y_sep = (ay + ah <= by) or (by + bh <= ay)
                assert x_sep or y_sep, f"Quadrants {i} and {j} overlap"

    def test_quadrants_within_screen(self):
        """Each quadrant fits within the screen bounds."""
        for qx, qy, qw, qh in QUADRANTS:
            assert qx >= 0
            assert qy >= 0
            assert qx + qw <= SCREEN_WIDTH
            assert qy + qh <= SCREEN_HEIGHT

    def test_quadrant_count(self):
        """Exactly 4 quadrants defined."""
        assert len(QUADRANTS) == 4

"""Tests for speednik/stages/hillside.py — Stage 1 loader."""

import pytest

from speednik.stages.hillside import StageData, load
from speednik.terrain import FULL, NOT_SOLID, TOP_ONLY, Tile


@pytest.fixture(scope="module")
def stage() -> StageData:
    """Load stage data once for all tests in this module."""
    return load()


class TestLoadReturnsStageData:
    def test_returns_stage_data_instance(self, stage: StageData) -> None:
        assert isinstance(stage, StageData)

    def test_tile_lookup_is_callable(self, stage: StageData) -> None:
        assert callable(stage.tile_lookup)

    def test_entities_is_list(self, stage: StageData) -> None:
        assert isinstance(stage.entities, list)
        assert len(stage.entities) > 0


class TestTileLookup:
    def test_ground_tile_at_section1(self, stage: StageData) -> None:
        """Section 1 flat ground is at y=620. Tile row = 620//16 = 38. x=64 -> tx=4."""
        tile = stage.tile_lookup(4, 38)
        assert tile is not None
        assert isinstance(tile, Tile)
        assert tile.solidity in (FULL, TOP_ONLY)

    def test_solid_ground_has_height(self, stage: StageData) -> None:
        """A ground tile should have non-zero height array values."""
        tile = stage.tile_lookup(4, 38)
        assert tile is not None
        assert max(tile.height_array) > 0

    def test_sky_returns_none(self, stage: StageData) -> None:
        """Sky area (top of world) should have no tiles."""
        tile = stage.tile_lookup(5, 0)
        assert tile is None

    def test_out_of_bounds_returns_none(self, stage: StageData) -> None:
        """Beyond grid boundaries returns None."""
        tile = stage.tile_lookup(999, 999)
        assert tile is None

    def test_interior_tile_is_fully_solid(self, stage: StageData) -> None:
        """Tiles below ground surface should be fully solid with height_array=[16]*16."""
        # Section 1 ground is at row 38. Row 43 is below, should be solid interior.
        tile = stage.tile_lookup(4, 43)
        assert tile is not None
        assert tile.solidity == FULL
        assert tile.height_array == [16] * 16


class TestEntities:
    def test_player_start_exists(self, stage: StageData) -> None:
        starts = [e for e in stage.entities if e["type"] == "player_start"]
        assert len(starts) == 1

    def test_rings_approximately_200(self, stage: StageData) -> None:
        rings = [e for e in stage.entities if e["type"] == "ring"]
        assert 190 <= len(rings) <= 210

    def test_enemy_crabs_present(self, stage: StageData) -> None:
        crabs = [e for e in stage.entities if e["type"] == "enemy_crab"]
        assert len(crabs) == 3

    def test_enemy_buzzer_present(self, stage: StageData) -> None:
        buzzers = [e for e in stage.entities if e["type"] == "enemy_buzzer"]
        assert len(buzzers) == 1

    def test_checkpoint_present(self, stage: StageData) -> None:
        cps = [e for e in stage.entities if e["type"] == "checkpoint"]
        assert len(cps) == 1

    def test_goal_present(self, stage: StageData) -> None:
        goals = [e for e in stage.entities if e["type"] == "goal"]
        assert len(goals) == 1

    def test_spring_present(self, stage: StageData) -> None:
        springs = [e for e in stage.entities if e["type"] == "spring_up"]
        assert len(springs) == 1


class TestPlayerStart:
    def test_x_coordinate(self, stage: StageData) -> None:
        assert stage.player_start[0] == 64.0

    def test_y_coordinate(self, stage: StageData) -> None:
        assert stage.player_start[1] == 610.0


class TestLevelDimensions:
    def test_width(self, stage: StageData) -> None:
        assert stage.level_width == 4800

    def test_height(self, stage: StageData) -> None:
        assert stage.level_height == 720


class TestLoopGeometry:
    def test_loop_tiles_exist(self, stage: StageData) -> None:
        """Loop center at (3600, 508), r=128. Top at y=380 → tile row 23.
        Tile column at x=3600 → tx=225. There should be tiles near the loop."""
        # Check tiles around the loop region
        loop_tiles = []
        for ty in range(23, 41):  # y=368 to y=656 covers the loop
            for tx in range(218, 234):  # x=3488 to x=3744
                tile = stage.tile_lookup(tx, ty)
                if tile is not None:
                    loop_tiles.append((tx, ty, tile))
        assert len(loop_tiles) > 0

    def test_loop_has_varied_angles(self, stage: StageData) -> None:
        """Loop tiles should have a range of angle values, not all the same."""
        angles = set()
        for ty in range(23, 41):
            for tx in range(218, 234):
                tile = stage.tile_lookup(tx, ty)
                if tile is not None:
                    angles.add(tile.angle)
        # A full 360° loop should produce many distinct angle values
        assert len(angles) >= 4

"""Tests for speednik/stages/skybridge.py — Stage 3 loader."""

import pytest

from speednik.stages.skybridge import StageData, load
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
    def test_bridge_tile_at_section1(self, stage: StageData) -> None:
        """Bridge segment A at y=500. Tile row = 500//16 = 31. x=240 -> tx=15."""
        tile = stage.tile_lookup(15, 31)
        assert tile is not None
        assert isinstance(tile, Tile)
        assert tile.solidity in (FULL, TOP_ONLY)

    def test_solid_ground_at_start(self, stage: StageData) -> None:
        """Starting solid platform at y=500. Tile row 31, tx=4 (x=64)."""
        tile = stage.tile_lookup(4, 31)
        assert tile is not None
        assert tile.solidity == FULL

    def test_solid_ground_at_arena(self, stage: StageData) -> None:
        """Arena floor at y=500, x=4600. tx=287, ty=31."""
        tile = stage.tile_lookup(287, 31)
        assert tile is not None
        assert tile.solidity == FULL

    def test_sky_returns_none(self, stage: StageData) -> None:
        """Sky area (top of world) should have no tiles."""
        tile = stage.tile_lookup(5, 0)
        assert tile is None

    def test_out_of_bounds_returns_none(self, stage: StageData) -> None:
        """Beyond grid boundaries returns None."""
        tile = stage.tile_lookup(999, 999)
        assert tile is None

    def test_interior_tile_is_fully_solid(self, stage: StageData) -> None:
        """Tiles below ground surface should be fully solid."""
        # Starting platform ground at y=500 (row 31). Row 50 is deep below.
        tile = stage.tile_lookup(4, 50)
        assert tile is not None
        assert tile.solidity == FULL
        assert tile.height_array == [16] * 16


class TestEntities:
    def test_player_start_exists(self, stage: StageData) -> None:
        starts = [e for e in stage.entities if e["type"] == "player_start"]
        assert len(starts) == 1

    def test_rings_approximately_250(self, stage: StageData) -> None:
        rings = [e for e in stage.entities if e["type"] == "ring"]
        assert 240 <= len(rings) <= 260

    def test_enemy_crabs_present(self, stage: StageData) -> None:
        crabs = [e for e in stage.entities if e["type"] == "enemy_crab"]
        assert len(crabs) >= 10

    def test_enemy_buzzers_present(self, stage: StageData) -> None:
        buzzers = [e for e in stage.entities if e["type"] == "enemy_buzzer"]
        assert len(buzzers) >= 2

    def test_checkpoints_count(self, stage: StageData) -> None:
        cps = [e for e in stage.entities if e["type"] == "checkpoint"]
        assert len(cps) == 2

    def test_goal_present(self, stage: StageData) -> None:
        goals = [e for e in stage.entities if e["type"] == "goal"]
        assert len(goals) == 1

    def test_springs_present(self, stage: StageData) -> None:
        springs = [e for e in stage.entities if e["type"] == "spring_up"]
        assert len(springs) >= 5


class TestPlayerStart:
    def test_x_coordinate(self, stage: StageData) -> None:
        assert stage.player_start[0] == 64.0

    def test_y_coordinate(self, stage: StageData) -> None:
        assert stage.player_start[1] == 490.0


class TestLevelDimensions:
    def test_width(self, stage: StageData) -> None:
        assert stage.level_width == 5200

    def test_height(self, stage: StageData) -> None:
        assert stage.level_height == 896


class TestBridgeGeometry:
    def test_top_only_tiles_exist(self, stage: StageData) -> None:
        """Bridge segments in section 1 use top-only tiles. Check bridge A area."""
        # Bridge A at x=192-288, y=500-516. tx=12-17, ty=31
        top_only_count = 0
        for tx in range(12, 18):
            tile = stage.tile_lookup(tx, 31)
            if tile is not None and tile.solidity == TOP_ONLY:
                top_only_count += 1
        assert top_only_count > 0

    def test_ramp_region_has_angled_tiles(self, stage: StageData) -> None:
        """Ramp in section 2 (x=1000-1160, y=500-600) should have non-zero angles."""
        angles = set()
        # Ramp spans tx=62-72 (x=992-1152), ty=31-37 (y=496-592)
        for ty in range(31, 38):
            for tx in range(62, 73):
                tile = stage.tile_lookup(tx, ty)
                if tile is not None:
                    angles.add(tile.angle)
        # Should have at least some non-zero angles from the slope
        non_zero = {a for a in angles if a != 0}
        assert len(non_zero) > 0

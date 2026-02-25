"""Tests for speednik/stages/pipeworks.py — Stage 2 loader."""

import pytest

from speednik.stages.hillside import StageData
from speednik.stages.pipeworks import load
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
    def test_mid_route_ground_at_section1(self, stage: StageData) -> None:
        """S1 mid platform at y=520. Tile row = 520//16 = 32. x=200 -> tx=12."""
        tile = stage.tile_lookup(12, 32)
        assert tile is not None
        assert isinstance(tile, Tile)
        assert tile.solidity in (FULL, TOP_ONLY)

    def test_high_route_surface_at_section2(self, stage: StageData) -> None:
        """S2 high route at y=160. Tile row = 160//16 = 10. x=1000 -> tx=62."""
        tile = stage.tile_lookup(62, 10)
        assert tile is not None
        assert isinstance(tile, Tile)

    def test_low_route_floor_at_section2(self, stage: StageData) -> None:
        """S2 low route at y=900. Tile row = 900//16 = 56. x=1000 -> tx=62."""
        tile = stage.tile_lookup(62, 56)
        assert tile is not None
        assert isinstance(tile, Tile)
        assert tile.solidity in (FULL, TOP_ONLY)

    def test_sky_returns_none(self, stage: StageData) -> None:
        """Sky area above high route should have no tiles."""
        # x=1000 -> tx=62, y=0 -> ty=0. Above the left wall polygon.
        tile = stage.tile_lookup(62, 0)
        assert tile is None

    def test_out_of_bounds_returns_none(self, stage: StageData) -> None:
        """Beyond grid boundaries returns None."""
        tile = stage.tile_lookup(999, 999)
        assert tile is None

    def test_interior_fill_below_low_route(self, stage: StageData) -> None:
        """Tiles below low route floor should be fully solid."""
        # Low floor at y=900 (ty=56). Row 62 is below, should be solid interior.
        tile = stage.tile_lookup(62, 62)
        assert tile is not None
        assert tile.solidity == FULL
        assert tile.height_array == [16] * 16

    def test_top_only_platform_has_correct_solidity(self, stage: StageData) -> None:
        """S2 low route top-only platform at y=860, x=1000-1200.
        Tile row = 860//16 = 53. x=1050 -> tx=65."""
        tile = stage.tile_lookup(65, 53)
        assert tile is not None
        assert tile.solidity == TOP_ONLY


class TestEntities:
    def test_player_start_exists(self, stage: StageData) -> None:
        starts = [e for e in stage.entities if e["type"] == "player_start"]
        assert len(starts) == 1

    def test_rings_approximately_300(self, stage: StageData) -> None:
        rings = [e for e in stage.entities if e["type"] == "ring"]
        assert 280 <= len(rings) <= 320

    def test_pipe_h_count(self, stage: StageData) -> None:
        pipes = [e for e in stage.entities if e["type"] == "pipe_h"]
        assert len(pipes) == 4

    def test_checkpoints_count(self, stage: StageData) -> None:
        cps = [e for e in stage.entities if e["type"] == "checkpoint"]
        assert len(cps) == 2

    def test_enemy_crabs_present(self, stage: StageData) -> None:
        crabs = [e for e in stage.entities if e["type"] == "enemy_crab"]
        assert len(crabs) >= 4

    def test_enemy_buzzers_present(self, stage: StageData) -> None:
        buzzers = [e for e in stage.entities if e["type"] == "enemy_buzzer"]
        assert len(buzzers) >= 2

    def test_enemy_choppers_present(self, stage: StageData) -> None:
        choppers = [e for e in stage.entities if e["type"] == "enemy_chopper"]
        assert len(choppers) >= 1

    def test_liquid_trigger_exists(self, stage: StageData) -> None:
        triggers = [e for e in stage.entities if e["type"] == "liquid_trigger"]
        assert len(triggers) == 1

    def test_goal_present(self, stage: StageData) -> None:
        goals = [e for e in stage.entities if e["type"] == "goal"]
        assert len(goals) == 1


class TestPlayerStart:
    def test_x_coordinate(self, stage: StageData) -> None:
        assert stage.player_start[0] == 200.0

    def test_y_coordinate(self, stage: StageData) -> None:
        assert stage.player_start[1] == 510.0


class TestLevelDimensions:
    def test_width(self, stage: StageData) -> None:
        assert stage.level_width == 5600

    def test_height(self, stage: StageData) -> None:
        assert stage.level_height == 1024


class TestThreeRoutes:
    def test_high_route_tiles_exist(self, stage: StageData) -> None:
        """High route surface at y=160 (ty=10) should have tiles in S2 (x=800-2800)."""
        high_tiles = []
        for tx in range(50, 175):  # x=800 to x=2800
            tile = stage.tile_lookup(tx, 10)
            if tile is not None:
                high_tiles.append(tx)
        assert len(high_tiles) > 10

    def test_mid_route_tiles_exist(self, stage: StageData) -> None:
        """Mid route surface at y=520 (ty=32) should have tiles in S2."""
        mid_tiles = []
        for tx in range(50, 175):  # x=800 to x=2800
            tile = stage.tile_lookup(tx, 32)
            if tile is not None:
                mid_tiles.append(tx)
        assert len(mid_tiles) > 10

    def test_low_route_tiles_exist(self, stage: StageData) -> None:
        """Low route surface at y=900 (ty=56) should have tiles in S2."""
        low_tiles = []
        for tx in range(50, 175):  # x=800 to x=2800
            tile = stage.tile_lookup(tx, 56)
            if tile is not None:
                low_tiles.append(tx)
        assert len(low_tiles) > 10

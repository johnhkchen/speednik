"""Tests for game state machine components (T-004-03).

Tests goal collision detection, stage loading data structures,
and game-level logic that doesn't require Pyxel initialization.
"""

from speednik.constants import GOAL_ACTIVATION_RADIUS
from speednik.objects import GoalEvent, check_goal_collision
from speednik.player import PlayerState, create_player, damage_player


# ---------------------------------------------------------------------------
# Goal collision
# ---------------------------------------------------------------------------

class TestGoalCollision:
    def test_player_at_goal_returns_reached(self):
        player = create_player(100.0, 200.0)
        result = check_goal_collision(player, 100.0, 200.0)
        assert result == GoalEvent.REACHED

    def test_player_near_goal_returns_reached(self):
        player = create_player(100.0, 200.0)
        result = check_goal_collision(player, 110.0, 200.0)
        assert result == GoalEvent.REACHED

    def test_player_far_from_goal_returns_none(self):
        player = create_player(100.0, 200.0)
        result = check_goal_collision(player, 500.0, 200.0)
        assert result is None

    def test_player_just_outside_radius_returns_none(self):
        player = create_player(100.0, 200.0)
        # Place exactly at the radius boundary (slightly beyond)
        result = check_goal_collision(
            player,
            100.0 + GOAL_ACTIVATION_RADIUS + 1,
            200.0,
        )
        assert result is None

    def test_player_just_inside_radius_returns_reached(self):
        player = create_player(100.0, 200.0)
        result = check_goal_collision(
            player,
            100.0 + GOAL_ACTIVATION_RADIUS - 1,
            200.0,
        )
        assert result == GoalEvent.REACHED

    def test_dead_player_returns_none(self):
        player = create_player(100.0, 200.0)
        player.state = PlayerState.DEAD
        result = check_goal_collision(player, 100.0, 200.0)
        assert result is None

    def test_hurt_player_returns_none(self):
        player = create_player(100.0, 200.0)
        player.state = PlayerState.HURT
        result = check_goal_collision(player, 100.0, 200.0)
        assert result is None

    def test_diagonal_approach(self):
        player = create_player(100.0, 200.0)
        # Diagonal distance: sqrt(10^2 + 10^2) ≈ 14.14 < 24
        result = check_goal_collision(player, 110.0, 210.0)
        assert result == GoalEvent.REACHED


# ---------------------------------------------------------------------------
# StageData tiles_dict field
# ---------------------------------------------------------------------------

class TestStageDataExtension:
    def test_hillside_stagedata_has_tiles_dict(self):
        from speednik.stages.hillside import StageData
        import dataclasses

        fields = {f.name for f in dataclasses.fields(StageData)}
        assert "tiles_dict" in fields

    def test_stagedata_field_order(self):
        from speednik.stages.hillside import StageData
        import dataclasses

        field_names = [f.name for f in dataclasses.fields(StageData)]
        # tiles_dict should come after tile_lookup and before entities
        assert field_names.index("tiles_dict") > field_names.index("tile_lookup")
        assert field_names.index("tiles_dict") < field_names.index("entities")


# ---------------------------------------------------------------------------
# Death and respawn logic
# ---------------------------------------------------------------------------

class TestDeathRespawn:
    def test_death_with_no_rings(self):
        player = create_player(100.0, 200.0)
        player.rings = 0
        player.lives = 3
        damage_player(player)
        assert player.state == PlayerState.DEAD

    def test_death_preserves_lives_count(self):
        player = create_player(100.0, 200.0)
        player.rings = 0
        player.lives = 2
        damage_player(player)
        assert player.state == PlayerState.DEAD
        assert player.lives == 2  # Lives not decremented by damage_player

    def test_damage_with_rings_scatters(self):
        player = create_player(100.0, 200.0)
        player.rings = 10
        player.lives = 3
        damage_player(player)
        assert player.state == PlayerState.HURT
        assert player.rings == 0
        assert len(player.scattered_rings) > 0

    def test_respawn_data_preserved(self):
        player = create_player(100.0, 200.0)
        player.respawn_x = 50.0
        player.respawn_y = 150.0
        player.respawn_rings = 5
        # After death, respawn data should still be available
        player.rings = 0
        damage_player(player)
        assert player.respawn_x == 50.0
        assert player.respawn_y == 150.0
        assert player.respawn_rings == 5


# ---------------------------------------------------------------------------
# GoalEvent enum
# ---------------------------------------------------------------------------

class TestGoalEvent:
    def test_goal_event_value(self):
        assert GoalEvent.REACHED.value == "reached"

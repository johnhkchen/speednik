"""Integration tests for the full game loop (T-004-04).

Tests that all subsystems work together with real stage data.
All tests are Pyxel-free — they test game logic, not rendering.
"""

import math

from speednik.camera import Camera, camera_update, create_camera
from speednik.constants import (
    BOSS_HP,
    BOSS_SPAWN_X,
    BOSS_SPAWN_Y,
    EXTRA_LIFE_THRESHOLD,
    GOAL_ACTIVATION_RADIUS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from speednik.enemies import (
    EnemyEvent,
    check_enemy_collision,
    load_enemies,
    update_enemies,
)
from speednik.level import StageData, load_stage
from speednik.objects import (
    GoalEvent,
    Ring,
    RingEvent,
    check_goal_collision,
    check_ring_collection,
    load_checkpoints,
    load_liquid_zones,
    load_pipes,
    load_rings,
    load_springs,
)
from speednik.physics import InputState, PhysicsState
from speednik.player import Player, PlayerState, create_player, damage_player, player_update


# ---------------------------------------------------------------------------
# Stage loading
# ---------------------------------------------------------------------------

class TestStageLoading:
    def test_load_hillside(self):
        stage = load_stage("hillside")
        assert isinstance(stage, StageData)
        assert stage.level_width > 0
        assert stage.level_height > 0

    def test_load_pipeworks(self):
        stage = load_stage("pipeworks")
        assert isinstance(stage, StageData)
        assert stage.level_width > 0
        assert stage.level_height > 0

    def test_load_skybridge(self):
        stage = load_stage("skybridge")
        assert isinstance(stage, StageData)
        assert stage.level_width > 0
        assert stage.level_height > 0

    def test_all_stages_have_tiles(self):
        for name in ("hillside", "pipeworks", "skybridge"):
            stage = load_stage(name)
            assert len(stage.tiles_dict) > 0, f"{name} has no tiles"

    def test_all_stages_have_entities(self):
        for name in ("hillside", "pipeworks", "skybridge"):
            stage = load_stage(name)
            assert len(stage.entities) > 0, f"{name} has no entities"

    def test_all_stages_have_goal(self):
        for name in ("hillside", "pipeworks", "skybridge"):
            stage = load_stage(name)
            goals = [e for e in stage.entities if e.get("type") == "goal"]
            assert len(goals) >= 1, f"{name} has no goal entity"

    def test_all_stages_have_player_start(self):
        for name in ("hillside", "pipeworks", "skybridge"):
            stage = load_stage(name)
            sx, sy = stage.player_start
            assert sx >= 0
            assert sy >= 0

    def test_unknown_stage_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown stage"):
            load_stage("nonexistent")

    def test_tile_lookup_returns_tiles(self):
        stage = load_stage("hillside")
        # Pick a known tile position from the tiles_dict
        pos = next(iter(stage.tiles_dict))
        tile = stage.tile_lookup(pos[0], pos[1])
        assert tile is not None
        assert len(tile.height_array) == 16

    def test_tile_lookup_returns_none_for_empty(self):
        stage = load_stage("hillside")
        # Very large coordinates should be empty
        tile = stage.tile_lookup(99999, 99999)
        assert tile is None


# ---------------------------------------------------------------------------
# Entity parsing
# ---------------------------------------------------------------------------

class TestEntityParsing:
    def test_hillside_has_rings(self):
        stage = load_stage("hillside")
        rings = load_rings(stage.entities)
        assert len(rings) > 0

    def test_hillside_has_enemies(self):
        stage = load_stage("hillside")
        enemies = load_enemies(stage.entities)
        assert len(enemies) > 0

    def test_pipeworks_has_pipes(self):
        stage = load_stage("pipeworks")
        pipes = load_pipes(stage.entities)
        assert len(pipes) > 0

    def test_pipeworks_has_liquid_zones(self):
        stage = load_stage("pipeworks")
        zones = load_liquid_zones(stage.entities)
        assert len(zones) > 0

    def test_skybridge_has_enemies(self):
        stage = load_stage("skybridge")
        enemies = load_enemies(stage.entities)
        assert len(enemies) > 0
        # Skybridge should have crab and buzzer enemies
        enemy_types = {e.enemy_type for e in enemies}
        assert "enemy_crab" in enemy_types or "enemy_buzzer" in enemy_types

    def test_all_stages_have_checkpoints(self):
        for name in ("hillside", "pipeworks", "skybridge"):
            stage = load_stage(name)
            cps = load_checkpoints(stage.entities)
            assert len(cps) > 0, f"{name} has no checkpoints"

    def test_hillside_has_springs(self):
        stage = load_stage("hillside")
        springs = load_springs(stage.entities)
        assert len(springs) > 0


# ---------------------------------------------------------------------------
# Player lifecycle with real stage data
# ---------------------------------------------------------------------------

class TestPlayerLifecycle:
    def test_player_created_at_stage_start(self):
        stage = load_stage("hillside")
        sx, sy = stage.player_start
        player = create_player(float(sx), float(sy))
        assert player.physics.x == sx
        assert player.physics.y == sy
        assert player.state == PlayerState.STANDING

    def test_player_physics_frame_with_real_tiles(self):
        stage = load_stage("hillside")
        sx, sy = stage.player_start
        player = create_player(float(sx), float(sy))
        inp = InputState()
        # Run a few physics frames — should not crash
        for _ in range(10):
            player_update(player, inp, stage.tile_lookup)
        assert player.state in (PlayerState.STANDING, PlayerState.RUNNING,
                                PlayerState.JUMPING)

    def test_player_moves_right_on_stage(self):
        stage = load_stage("hillside")
        sx, sy = stage.player_start
        player = create_player(float(sx), float(sy))
        inp = InputState(right=True)
        for _ in range(60):
            player_update(player, inp, stage.tile_lookup)
        assert player.physics.x > sx

    def test_player_collects_ring_on_stage(self):
        stage = load_stage("hillside")
        rings = load_rings(stage.entities)
        assert len(rings) > 0
        # Place player at first ring position
        first_ring = rings[0]
        player = create_player(first_ring.x, first_ring.y)
        events = check_ring_collection(player, rings)
        assert RingEvent.COLLECTED in events
        assert player.rings == 1
        assert first_ring.collected


# ---------------------------------------------------------------------------
# Death / respawn integration
# ---------------------------------------------------------------------------

class TestDeathRespawnIntegration:
    def test_damage_with_no_rings_kills_player(self):
        player = create_player(100.0, 200.0)
        player.rings = 0
        player.lives = 3
        damage_player(player)
        assert player.state == PlayerState.DEAD

    def test_damage_with_rings_scatters_and_hurts(self):
        player = create_player(100.0, 200.0)
        player.rings = 15
        damage_player(player)
        assert player.state == PlayerState.HURT
        assert player.rings == 0
        assert len(player.scattered_rings) > 0

    def test_respawn_at_checkpoint_position(self):
        stage = load_stage("hillside")
        sx, sy = stage.player_start
        player = create_player(float(sx), float(sy))

        # Set checkpoint
        player.respawn_x = 500.0
        player.respawn_y = 300.0
        player.respawn_rings = 10

        # Simulate death
        player.rings = 0
        damage_player(player)
        assert player.state == PlayerState.DEAD

        # Simulate respawn (as main.py does)
        new_player = create_player(player.respawn_x, player.respawn_y)
        new_player.rings = player.respawn_rings
        assert new_player.physics.x == 500.0
        assert new_player.physics.y == 300.0
        assert new_player.rings == 10


# ---------------------------------------------------------------------------
# Extra life
# ---------------------------------------------------------------------------

class TestExtraLife:
    def test_100_rings_grants_extra_life(self):
        player = create_player(100.0, 200.0)
        player.rings = EXTRA_LIFE_THRESHOLD - 1
        player.lives = 3

        # Create a ring right at the player
        ring = Ring(x=100.0, y=200.0)
        events = check_ring_collection(player, [ring])

        assert RingEvent.COLLECTED in events
        assert RingEvent.EXTRA_LIFE in events
        assert player.rings == EXTRA_LIFE_THRESHOLD
        assert player.lives == 4

    def test_200_rings_grants_second_extra_life(self):
        player = create_player(100.0, 200.0)
        player.rings = 2 * EXTRA_LIFE_THRESHOLD - 1
        player.lives = 3

        ring = Ring(x=100.0, y=200.0)
        events = check_ring_collection(player, [ring])

        assert RingEvent.EXTRA_LIFE in events
        assert player.lives == 4


# ---------------------------------------------------------------------------
# Boss integration
# ---------------------------------------------------------------------------

class TestBossIntegration:
    def test_stage3_boss_injection(self):
        """Verify boss can be injected into Stage 3 entities as main.py does."""
        stage = load_stage("skybridge")
        enemies = load_enemies(stage.entities)

        # Inject boss (mirrors main.py logic)
        boss_entities = [
            {"type": "enemy_egg_piston", "x": BOSS_SPAWN_X, "y": BOSS_SPAWN_Y}
        ]
        enemies.extend(load_enemies(boss_entities))

        boss_enemies = [e for e in enemies if e.enemy_type == "enemy_egg_piston"]
        assert len(boss_enemies) == 1
        boss = boss_enemies[0]
        assert boss.boss_hp == BOSS_HP
        assert boss.boss_state == "idle"

    def test_boss_takes_spindash_damage(self):
        """Simulate spindash hit on vulnerable boss."""
        boss_entities = [
            {"type": "enemy_egg_piston", "x": 100.0, "y": 100.0}
        ]
        enemies = load_enemies(boss_entities)
        boss = enemies[0]

        # Set boss to vulnerable state
        boss.boss_state = "vulnerable"
        boss.y = boss.boss_ground_y

        # Create player at boss position, rolling with high speed
        player = create_player(100.0, 100.0)
        player.physics.is_rolling = True
        player.physics.ground_speed = 10.0
        player.physics.on_ground = True

        events = check_enemy_collision(player, enemies)
        assert EnemyEvent.BOSS_HIT in events
        assert boss.boss_hp == BOSS_HP - 1

    def test_boss_defeated_after_8_hits(self):
        boss_entities = [
            {"type": "enemy_egg_piston", "x": 100.0, "y": 100.0}
        ]
        enemies = load_enemies(boss_entities)
        boss = enemies[0]
        boss.boss_state = "vulnerable"
        boss.y = boss.boss_ground_y

        for i in range(BOSS_HP):
            boss.boss_hit_timer = 0  # Clear invulnerability between hits
            player = create_player(100.0, 100.0)
            player.physics.is_rolling = True
            player.physics.ground_speed = 10.0
            player.physics.on_ground = True
            events = check_enemy_collision(player, enemies)
            if EnemyEvent.BOSS_DEFEATED in events:
                assert i == BOSS_HP - 1
                break

        assert not boss.alive
        assert boss.boss_hp == 0

    def test_boss_escalates_at_4_hp(self):
        boss_entities = [
            {"type": "enemy_egg_piston", "x": 100.0, "y": 100.0}
        ]
        enemies = load_enemies(boss_entities)
        boss = enemies[0]
        boss.boss_state = "vulnerable"
        boss.y = boss.boss_ground_y

        # Hit boss 4 times (from 8 HP to 4 HP)
        for _ in range(4):
            boss.boss_hit_timer = 0
            player = create_player(100.0, 100.0)
            player.physics.is_rolling = True
            player.physics.ground_speed = 10.0
            player.physics.on_ground = True
            check_enemy_collision(player, enemies)

        assert boss.boss_escalated
        assert boss.boss_hp == 4


# ---------------------------------------------------------------------------
# Camera integration
# ---------------------------------------------------------------------------

class TestCameraIntegration:
    def test_camera_clamps_to_hillside_bounds(self):
        stage = load_stage("hillside")
        cam = create_camera(stage.level_width, stage.level_height, 0.0, 0.0)
        assert cam.x >= 0
        assert cam.y >= 0

    def test_camera_clamps_at_level_end(self):
        stage = load_stage("hillside")
        cam = create_camera(
            stage.level_width, stage.level_height,
            float(stage.level_width), float(stage.level_height),
        )
        max_x = max(0, stage.level_width - SCREEN_WIDTH)
        max_y = max(0, stage.level_height - SCREEN_HEIGHT)
        assert cam.x <= max_x
        assert cam.y <= max_y

    def test_camera_tracks_player_on_stage(self):
        stage = load_stage("hillside")
        sx, sy = stage.player_start
        player = create_player(float(sx), float(sy))
        cam = create_camera(stage.level_width, stage.level_height, float(sx), float(sy))
        inp = InputState(right=True)

        # Run several frames with rightward input
        for _ in range(120):
            player_update(player, inp, stage.tile_lookup)
            camera_update(cam, player, inp)

        # Camera should have moved right
        initial_cam_x = create_camera(
            stage.level_width, stage.level_height, float(sx), float(sy)
        ).x
        assert cam.x > initial_cam_x


# ---------------------------------------------------------------------------
# Game state flow (logic only)
# ---------------------------------------------------------------------------

class TestGameStateFlow:
    def test_goal_collision_with_real_stage(self):
        """Player at goal position triggers REACHED event."""
        stage = load_stage("hillside")
        goals = [e for e in stage.entities if e.get("type") == "goal"]
        assert len(goals) > 0
        goal = goals[0]
        goal_x = float(goal["x"])
        goal_y = float(goal["y"])

        player = create_player(goal_x, goal_y)
        result = check_goal_collision(player, goal_x, goal_y)
        assert result == GoalEvent.REACHED

    def test_all_stages_goal_reachable(self):
        """Each stage's goal position is at a reasonable world coordinate."""
        for name in ("hillside", "pipeworks", "skybridge"):
            stage = load_stage(name)
            goals = [e for e in stage.entities if e.get("type") == "goal"]
            assert len(goals) >= 1, f"{name} missing goal"
            goal = goals[0]
            gx, gy = float(goal["x"]), float(goal["y"])
            assert 0 < gx <= stage.level_width, f"{name} goal x={gx} out of bounds"
            assert 0 < gy <= stage.level_height, f"{name} goal y={gy} out of bounds"

    def test_enemy_update_on_real_stage(self):
        """Enemies can be updated without errors on real stage data."""
        stage = load_stage("hillside")
        enemies = load_enemies(stage.entities)
        # Run 60 frames of enemy updates
        for _ in range(60):
            update_enemies(enemies)
        # No crashes — enemies moved
        for enemy in enemies:
            assert enemy.alive  # No enemies self-destruct


# ---------------------------------------------------------------------------
# Palette and audio wiring (structural checks)
# ---------------------------------------------------------------------------

class TestPaletteAudioWiring:
    def test_stage_palette_names_match(self):
        """Verify palette names used in main.py exist in renderer."""
        from speednik.renderer import STAGE_PALETTES
        for name in ("hillside", "pipeworks", "skybridge"):
            assert name in STAGE_PALETTES, f"Missing palette: {name}"

    def test_stage_music_ids_valid(self):
        """Verify music IDs used in main.py are valid slot indices."""
        from speednik.audio import (
            MUSIC_HILLSIDE, MUSIC_PIPEWORKS, MUSIC_SKYBRIDGE,
            MUSIC_BOSS, MUSIC_CLEAR, MUSIC_GAMEOVER, MUSIC_TITLE,
        )
        for music_id in (MUSIC_HILLSIDE, MUSIC_PIPEWORKS, MUSIC_SKYBRIDGE,
                         MUSIC_BOSS, MUSIC_CLEAR, MUSIC_GAMEOVER, MUSIC_TITLE):
            assert 0 <= music_id <= 6

    def test_sfx_ids_valid(self):
        """Verify SFX IDs used in main.py are valid slot indices."""
        from speednik.audio import (
            SFX_RING, SFX_1UP, SFX_SPRING, SFX_CHECKPOINT,
            SFX_ENEMY_DESTROY, SFX_ENEMY_BOUNCE, SFX_HURT,
            SFX_BOSS_HIT, SFX_LIQUID_RISING, SFX_STAGE_CLEAR,
            SFX_MENU_SELECT, SFX_MENU_CONFIRM,
        )
        for sfx_id in (SFX_RING, SFX_1UP, SFX_SPRING, SFX_CHECKPOINT,
                        SFX_ENEMY_DESTROY, SFX_ENEMY_BOUNCE, SFX_HURT,
                        SFX_BOSS_HIT, SFX_LIQUID_RISING, SFX_STAGE_CLEAR,
                        SFX_MENU_SELECT, SFX_MENU_CONFIRM):
            assert 0 <= sfx_id <= 15

"""Tests for game objects: springs, checkpoints, launch pipes, liquid zones."""

from __future__ import annotations

from speednik.constants import (
    CHECKPOINT_ACTIVATION_RADIUS,
    LIQUID_RISE_SPEED,
    SPRING_COOLDOWN_FRAMES,
    SPRING_RIGHT_VELOCITY,
    SPRING_UP_VELOCITY,
)
from speednik.objects import (
    Checkpoint,
    CheckpointEvent,
    LaunchPipe,
    LiquidEvent,
    LiquidZone,
    PipeEvent,
    Spring,
    SpringEvent,
    aabb_overlap,
    check_checkpoint_collision,
    check_spring_collision,
    load_checkpoints,
    load_liquid_zones,
    load_pipes,
    load_springs,
    update_liquid_zones,
    update_pipe_travel,
    update_spring_cooldowns,
)
from speednik.player import PlayerState, create_player


# ---------------------------------------------------------------------------
# AABB helper
# ---------------------------------------------------------------------------

class TestAABBOverlap:
    def test_overlapping_boxes(self):
        assert aabb_overlap(0, 0, 10, 10, 5, 5, 10, 10) is True

    def test_non_overlapping_boxes(self):
        assert aabb_overlap(0, 0, 10, 10, 20, 20, 10, 10) is False

    def test_touching_edges_no_overlap(self):
        # Touching at edge — not overlapping (< not <=)
        assert aabb_overlap(0, 0, 10, 10, 10, 0, 10, 10) is False


# ---------------------------------------------------------------------------
# TestLoadSprings
# ---------------------------------------------------------------------------

class TestLoadSprings:
    def test_loads_spring_up(self):
        entities = [{"type": "spring_up", "x": 100, "y": 200}]
        springs = load_springs(entities)
        assert len(springs) == 1
        assert springs[0].direction == "up"
        assert springs[0].x == 100.0

    def test_loads_spring_right(self):
        entities = [{"type": "spring_right", "x": 300, "y": 400}]
        springs = load_springs(entities)
        assert len(springs) == 1
        assert springs[0].direction == "right"

    def test_ignores_non_spring_entities(self):
        entities = [
            {"type": "spring_up", "x": 100, "y": 200},
            {"type": "ring", "x": 300, "y": 400},
            {"type": "checkpoint", "x": 500, "y": 600},
        ]
        springs = load_springs(entities)
        assert len(springs) == 1

    def test_empty_entities(self):
        assert load_springs([]) == []


# ---------------------------------------------------------------------------
# TestSpringCollision
# ---------------------------------------------------------------------------

class TestSpringCollision:
    def test_up_spring_overrides_y_vel(self):
        p = create_player(100.0, 100.0)
        springs = [Spring(x=100.0, y=100.0, direction="up")]

        events = check_spring_collision(p, springs)

        assert SpringEvent.LAUNCHED in events
        assert p.physics.y_vel == SPRING_UP_VELOCITY
        assert p.physics.on_ground is False
        assert p.state == PlayerState.JUMPING

    def test_right_spring_overrides_x_vel(self):
        p = create_player(100.0, 100.0)
        springs = [Spring(x=100.0, y=100.0, direction="right")]

        events = check_spring_collision(p, springs)

        assert SpringEvent.LAUNCHED in events
        assert p.physics.x_vel == SPRING_RIGHT_VELOCITY
        assert p.physics.on_ground is False

    def test_spring_out_of_range(self):
        p = create_player(100.0, 100.0)
        springs = [Spring(x=300.0, y=300.0, direction="up")]

        events = check_spring_collision(p, springs)

        assert events == []

    def test_spring_cooldown_prevents_retrigger(self):
        p = create_player(100.0, 100.0)
        spring = Spring(x=100.0, y=100.0, direction="up", cooldown=5)
        springs = [spring]

        events = check_spring_collision(p, springs)

        assert events == []

    def test_spring_cooldown_set_on_trigger(self):
        p = create_player(100.0, 100.0)
        spring = Spring(x=100.0, y=100.0, direction="up")
        check_spring_collision(p, [spring])

        assert spring.cooldown == SPRING_COOLDOWN_FRAMES

    def test_spring_cooldown_decrements(self):
        spring = Spring(x=100.0, y=100.0, direction="up", cooldown=3)
        update_spring_cooldowns([spring])
        assert spring.cooldown == 2

    def test_dead_player_not_affected(self):
        p = create_player(100.0, 100.0)
        p.state = PlayerState.DEAD
        springs = [Spring(x=100.0, y=100.0, direction="up")]

        events = check_spring_collision(p, springs)

        assert events == []

    def test_hurt_player_not_affected(self):
        p = create_player(100.0, 100.0)
        p.state = PlayerState.HURT
        springs = [Spring(x=100.0, y=100.0, direction="up")]

        events = check_spring_collision(p, springs)

        assert events == []


# ---------------------------------------------------------------------------
# TestLoadCheckpoints
# ---------------------------------------------------------------------------

class TestLoadCheckpoints:
    def test_loads_checkpoint_entities(self):
        entities = [
            {"type": "checkpoint", "x": 1620, "y": 610},
            {"type": "checkpoint", "x": 2820, "y": 950},
        ]
        cps = load_checkpoints(entities)
        assert len(cps) == 2
        assert cps[0].x == 1620.0

    def test_ignores_non_checkpoint_entities(self):
        entities = [
            {"type": "checkpoint", "x": 100, "y": 200},
            {"type": "ring", "x": 300, "y": 400},
        ]
        cps = load_checkpoints(entities)
        assert len(cps) == 1

    def test_empty_entities(self):
        assert load_checkpoints([]) == []


# ---------------------------------------------------------------------------
# TestCheckpointActivation
# ---------------------------------------------------------------------------

class TestCheckpointActivation:
    def test_first_contact_saves_respawn(self):
        p = create_player(500.0, 500.0)
        p.rings = 42
        cp = Checkpoint(x=500.0, y=500.0)

        events = check_checkpoint_collision(p, [cp])

        assert CheckpointEvent.ACTIVATED in events
        assert cp.activated is True
        assert p.respawn_x == 500.0
        assert p.respawn_y == 500.0
        assert p.respawn_rings == 42

    def test_already_activated_no_retrigger(self):
        p = create_player(500.0, 500.0)
        cp = Checkpoint(x=500.0, y=500.0, activated=True)

        events = check_checkpoint_collision(p, [cp])

        assert events == []

    def test_out_of_range_no_activation(self):
        p = create_player(100.0, 100.0)
        cp = Checkpoint(x=500.0, y=500.0)

        events = check_checkpoint_collision(p, [cp])

        assert events == []
        assert cp.activated is False

    def test_boundary_distance(self):
        """Checkpoint at exactly the radius is NOT activated (strictly less than)."""
        p = create_player(100.0, 100.0)
        cp = Checkpoint(x=100.0 + CHECKPOINT_ACTIVATION_RADIUS, y=100.0)

        events = check_checkpoint_collision(p, [cp])

        assert cp.activated is False

    def test_dead_player_no_activation(self):
        p = create_player(500.0, 500.0)
        p.state = PlayerState.DEAD
        cp = Checkpoint(x=500.0, y=500.0)

        events = check_checkpoint_collision(p, [cp])

        assert events == []


# ---------------------------------------------------------------------------
# TestLoadPipes
# ---------------------------------------------------------------------------

class TestLoadPipes:
    def test_loads_pipe_h(self):
        entities = [
            {
                "type": "pipe_h",
                "x": 1200, "y": 640,
                "exit_x": 1600, "exit_y": 640,
                "vel_x": 10, "vel_y": 0,
            }
        ]
        pipes = load_pipes(entities)
        assert len(pipes) == 1
        assert pipes[0].exit_x == 1600.0
        assert pipes[0].vel_x == 10.0

    def test_loads_pipe_v(self):
        entities = [
            {
                "type": "pipe_v",
                "x": 800, "y": 200,
                "exit_x": 800, "exit_y": 600,
                "vel_x": 0, "vel_y": 10,
            }
        ]
        pipes = load_pipes(entities)
        assert len(pipes) == 1
        assert pipes[0].vel_y == 10.0

    def test_ignores_non_pipe_entities(self):
        entities = [
            {"type": "ring", "x": 100, "y": 200},
            {
                "type": "pipe_h",
                "x": 1200, "y": 640,
                "exit_x": 1600, "exit_y": 640,
                "vel_x": 10, "vel_y": 0,
            },
        ]
        pipes = load_pipes(entities)
        assert len(pipes) == 1

    def test_empty_entities(self):
        assert load_pipes([]) == []


# ---------------------------------------------------------------------------
# TestPipeTravel
# ---------------------------------------------------------------------------

class TestPipeTravel:
    def test_player_enters_pipe(self):
        p = create_player(1200.0, 640.0)
        pipe = LaunchPipe(x=1200.0, y=640.0, exit_x=1600.0, exit_y=640.0, vel_x=10.0, vel_y=0.0)

        events = update_pipe_travel(p, [pipe])

        assert PipeEvent.ENTERED in events
        assert p.in_pipe is True
        assert p.physics.x_vel == 10.0
        assert p.physics.y_vel == 0.0

    def test_player_invulnerable_during_pipe(self):
        p = create_player(1200.0, 640.0)
        pipe = LaunchPipe(x=1200.0, y=640.0, exit_x=1600.0, exit_y=640.0, vel_x=10.0, vel_y=0.0)

        update_pipe_travel(p, [pipe])

        assert p.invulnerability_timer > 0

    def test_pipe_travel_moves_player(self):
        p = create_player(1200.0, 640.0)
        p.in_pipe = True
        p.physics.x_vel = 10.0
        p.physics.y_vel = 0.0
        pipe = LaunchPipe(x=1200.0, y=640.0, exit_x=1600.0, exit_y=640.0, vel_x=10.0, vel_y=0.0)

        update_pipe_travel(p, [pipe])

        assert p.physics.x == 1210.0  # Moved by x_vel

    def test_player_exits_pipe_at_destination(self):
        p = create_player(1595.0, 640.0)  # Near exit
        p.in_pipe = True
        p.physics.x_vel = 10.0
        p.physics.y_vel = 0.0
        pipe = LaunchPipe(x=1200.0, y=640.0, exit_x=1600.0, exit_y=640.0, vel_x=10.0, vel_y=0.0)

        events = update_pipe_travel(p, [pipe])

        assert PipeEvent.EXITED in events
        assert p.in_pipe is False
        assert p.physics.x == 1600.0  # Snapped to exit
        assert p.invulnerability_timer == 0

    def test_dead_player_cannot_enter_pipe(self):
        p = create_player(1200.0, 640.0)
        p.state = PlayerState.DEAD
        pipe = LaunchPipe(x=1200.0, y=640.0, exit_x=1600.0, exit_y=640.0, vel_x=10.0, vel_y=0.0)

        events = update_pipe_travel(p, [pipe])

        assert events == []
        assert p.in_pipe is False

    def test_out_of_range_no_entry(self):
        p = create_player(100.0, 100.0)
        pipe = LaunchPipe(x=1200.0, y=640.0, exit_x=1600.0, exit_y=640.0, vel_x=10.0, vel_y=0.0)

        events = update_pipe_travel(p, [pipe])

        assert events == []


# ---------------------------------------------------------------------------
# TestLoadLiquidZones
# ---------------------------------------------------------------------------

class TestLoadLiquidZones:
    def test_loads_liquid_trigger(self):
        entities = [
            {
                "type": "liquid_trigger",
                "x": 2800, "exit_x": 3800,
                "floor_y": 1024, "ceiling_y": 384,
            }
        ]
        zones = load_liquid_zones(entities)
        assert len(zones) == 1
        assert zones[0].trigger_x == 2800.0
        assert zones[0].exit_x == 3800.0
        assert zones[0].current_y == 1024.0  # starts at floor

    def test_ignores_non_liquid_entities(self):
        entities = [
            {"type": "ring", "x": 100, "y": 200},
            {
                "type": "liquid_trigger",
                "x": 2800, "exit_x": 3800,
                "floor_y": 1024, "ceiling_y": 384,
            },
        ]
        zones = load_liquid_zones(entities)
        assert len(zones) == 1

    def test_empty_entities(self):
        assert load_liquid_zones([]) == []


# ---------------------------------------------------------------------------
# TestLiquidRise
# ---------------------------------------------------------------------------

class TestLiquidRise:
    def _make_zone(self) -> LiquidZone:
        return LiquidZone(
            trigger_x=2800.0,
            exit_x=3800.0,
            floor_y=1024.0,
            ceiling_y=384.0,
            current_y=1024.0,
        )

    def test_activates_when_player_in_zone(self):
        p = create_player(3000.0, 500.0)
        zone = self._make_zone()

        events = update_liquid_zones(p, [zone])

        assert zone.active is True
        assert LiquidEvent.STARTED_RISING in events

    def test_deactivates_when_player_exits(self):
        p = create_player(4000.0, 500.0)
        zone = self._make_zone()
        zone.active = True

        events = update_liquid_zones(p, [zone])

        assert zone.active is False

    def test_rises_at_correct_speed(self):
        p = create_player(3000.0, 200.0)  # Player above liquid
        zone = self._make_zone()

        update_liquid_zones(p, [zone])

        assert zone.current_y == 1024.0 - LIQUID_RISE_SPEED

    def test_stops_at_ceiling(self):
        p = create_player(3000.0, 200.0)
        zone = self._make_zone()
        zone.current_y = 384.5  # Just above ceiling

        update_liquid_zones(p, [zone])

        assert zone.current_y == 384.0  # Clamped to ceiling

    def test_damages_player_in_liquid(self):
        # Player low enough that their bottom is below liquid surface
        p = create_player(3000.0, 1020.0)
        p.rings = 10  # Has rings to lose
        zone = self._make_zone()
        zone.current_y = 1010.0  # Liquid surface above player bottom

        events = update_liquid_zones(p, [zone])

        assert LiquidEvent.DAMAGE in events
        assert p.state == PlayerState.HURT
        assert p.rings == 0

    def test_invulnerable_player_not_damaged(self):
        p = create_player(3000.0, 1020.0)
        p.rings = 10
        p.invulnerability_timer = 60  # Already invulnerable
        zone = self._make_zone()
        zone.current_y = 1010.0

        events = update_liquid_zones(p, [zone])

        # damage_player checks invulnerability_timer, so no state change
        assert p.rings == 10

    def test_not_active_before_trigger(self):
        p = create_player(2000.0, 500.0)  # Before trigger_x
        zone = self._make_zone()

        update_liquid_zones(p, [zone])

        assert zone.active is False
        assert zone.current_y == 1024.0  # No rise

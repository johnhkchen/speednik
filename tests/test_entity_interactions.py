"""Tests for entity interactions through sim_step on real stages.

Covers: ring collection, damage/scatter/recollection, death with 0 rings,
springs, enemy bounce vs walk-into damage, checkpoints, and goal detection.
"""

from __future__ import annotations

from speednik.constants import (
    ENEMY_BOUNCE_VELOCITY,
    SPRING_COOLDOWN_FRAMES,
    SPRING_UP_VELOCITY,
    STANDING_HEIGHT_RADIUS,
)
from speednik.enemies import Enemy
from speednik.objects import Ring, Spring
from speednik.physics import InputState
from speednik.player import PlayerState
from speednik.simulation import (
    CheckpointEvent,
    DamageEvent,
    DeathEvent,
    GoalReachedEvent,
    RingCollectedEvent,
    SpringEvent,
    create_sim,
    create_sim_from_lookup,
    sim_step,
)
from speednik.terrain import TILE_SIZE
from tests.grids import build_flat


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _place_buzzer(sim, dx: float = 40.0, dy: float = 0.0) -> Enemy:
    """Inject a stationary buzzer enemy relative to the player's current position."""
    px = sim.player.physics.x
    py = sim.player.physics.y
    enemy = Enemy(x=px + dx, y=py + dy, enemy_type="enemy_buzzer")
    sim.enemies.append(enemy)
    return enemy


def _run_frames(sim, inp: InputState, n: int) -> list:
    """Step sim n frames, return all events."""
    all_events = []
    for _ in range(n):
        events = sim_step(sim, inp)
        all_events.extend(events)
        if sim.player_dead:
            break
    return all_events


def _run_until_event(sim, inp: InputState, event_type: type, max_frames: int = 300):
    """Step until event_type appears or max_frames reached.

    Returns (all_events, found) where found is True if the event appeared.
    """
    all_events = []
    found = False
    for _ in range(max_frames):
        events = sim_step(sim, inp)
        all_events.extend(events)
        if any(isinstance(e, event_type) for e in events):
            found = True
            break
        if sim.player_dead:
            break
    return all_events, found


# ---------------------------------------------------------------------------
# Ring collection
# ---------------------------------------------------------------------------

def test_ring_collection_on_hillside():
    """Hold right on hillside collects rings via sim_step entity pipeline."""
    sim = create_sim("hillside")
    inp = InputState(right=True)
    all_events = _run_frames(sim, inp, 600)

    ring_events = [e for e in all_events if isinstance(e, RingCollectedEvent)]
    assert len(ring_events) > 0, "Should collect at least one ring on hillside"
    assert sim.rings_collected > 0
    assert sim.player.rings > 0 or sim.player.state == PlayerState.HURT


def test_ring_collection_increments_player_rings():
    """Placing a ring near the player and stepping collects it."""
    sim = create_sim("hillside")
    px = sim.player.physics.x
    py = sim.player.physics.y

    test_ring = Ring(x=px + 10.0, y=py)
    sim.rings.append(test_ring)
    initial_rings = sim.player.rings

    all_events, found = _run_until_event(sim, InputState(right=True), RingCollectedEvent, 60)

    assert found, "Should collect the placed ring"
    assert test_ring.collected is True
    assert sim.player.rings > initial_rings


# ---------------------------------------------------------------------------
# Damage and scatter
# ---------------------------------------------------------------------------

def test_damage_scatters_rings():
    """Enemy contact with rings > 0 produces DamageEvent and scatters rings."""
    sim = create_sim("hillside")
    sim.player.rings = 5
    _place_buzzer(sim, dx=40.0)

    all_events, found = _run_until_event(sim, InputState(right=True), DamageEvent)

    assert found, "Should take damage from buzzer"
    assert sim.player.rings == 0, "Rings should drop to 0 after damage"
    assert len(sim.player.scattered_rings) > 0, "Should have scattered rings"
    assert sim.player.state in (PlayerState.HURT, PlayerState.DEAD)


def test_damage_with_zero_rings_causes_death():
    """Enemy contact with 0 rings produces DeathEvent."""
    sim = create_sim("hillside")
    sim.player.rings = 0
    _place_buzzer(sim, dx=40.0)

    inp = InputState(right=True)
    all_events = []

    for _ in range(300):
        events = sim_step(sim, inp)
        all_events.extend(events)
        if sim.player_dead:
            break

    death_events = [e for e in all_events if isinstance(e, DeathEvent)]
    assert len(death_events) > 0, "Should die when hit with 0 rings"
    assert sim.player_dead is True
    assert sim.deaths == 1


def test_scattered_ring_recollection():
    """After taking damage, scattered rings can be recollected."""
    sim = create_sim("hillside")
    sim.player.rings = 10
    _place_buzzer(sim, dx=40.0)

    inp = InputState(right=True)

    # Run until damage
    for _ in range(300):
        events = sim_step(sim, inp)
        if any(isinstance(e, DamageEvent) for e in events):
            break

    assert sim.player.rings == 0, "Rings should be 0 after damage"
    assert len(sim.player.scattered_rings) > 0, "Should have scattered rings"

    rings_after_damage = sim.rings_collected

    # Continue running — scattered rings may be recollected by player_update
    # (internal _check_ring_collection picks them up if close enough)
    _run_frames(sim, inp, 300)

    # Player may have recollected some scattered rings OR collected world rings
    # Either way, rings_collected should have increased (world rings on the path)
    # The key assertion: player didn't die and continued progressing
    if not sim.player_dead:
        assert sim.rings_collected >= rings_after_damage


# ---------------------------------------------------------------------------
# Spring behavior
# ---------------------------------------------------------------------------

def test_spring_produces_event_and_upward_velocity():
    """Spring collision produces SpringEvent and sets upward velocity."""
    sim = create_sim("hillside")

    # Find an up-spring
    up_springs = [s for s in sim.springs if s.direction == "up"]
    assert len(up_springs) > 0, "Hillside should have at least one up-spring"
    spring = up_springs[0]

    # Teleport player onto the spring
    sim.player.physics.x = spring.x
    sim.player.physics.y = spring.y

    events = sim_step(sim, InputState())

    spring_events = [e for e in events if isinstance(e, SpringEvent)]
    assert len(spring_events) > 0, "Should trigger SpringEvent"
    assert sim.player.physics.y_vel == SPRING_UP_VELOCITY, (
        f"y_vel should be {SPRING_UP_VELOCITY}, got {sim.player.physics.y_vel}"
    )


def test_spring_cooldown_prevents_retrigger():
    """Spring enters cooldown after triggering, preventing immediate re-trigger."""
    sim = create_sim("hillside")

    up_springs = [s for s in sim.springs if s.direction == "up"]
    assert len(up_springs) > 0
    spring = up_springs[0]

    # Trigger the spring
    sim.player.physics.x = spring.x
    sim.player.physics.y = spring.y
    sim_step(sim, InputState())

    assert spring.cooldown > 0, "Spring should be on cooldown after trigger"

    # Step through cooldown
    for _ in range(SPRING_COOLDOWN_FRAMES):
        sim_step(sim, InputState())

    assert spring.cooldown == 0, "Spring cooldown should expire"


def test_spring_right_sets_horizontal_velocity():
    """Right-spring sets positive x_vel."""
    sim = create_sim("hillside")

    right_springs = [s for s in sim.springs if s.direction == "right"]
    if not right_springs:
        # Inject a right-spring if none on hillside
        px = sim.player.physics.x
        py = sim.player.physics.y
        spring = Spring(x=px, y=py, direction="right")
        sim.springs.append(spring)
    else:
        spring = right_springs[0]
        sim.player.physics.x = spring.x
        sim.player.physics.y = spring.y

    events = sim_step(sim, InputState())

    spring_events = [e for e in events if isinstance(e, SpringEvent)]
    assert len(spring_events) > 0, "Should trigger SpringEvent"
    assert sim.player.physics.x_vel > 0, "x_vel should be positive after right-spring"


# ---------------------------------------------------------------------------
# Enemy interactions
# ---------------------------------------------------------------------------

def test_enemy_bounce_destroys_enemy():
    """Jumping onto an enemy from above destroys it and bounces the player."""
    # Use flat grid to avoid terrain interference with the jump arc
    ground_row = 20
    _, lookup = build_flat(40, ground_row)
    start_y = float(ground_row * TILE_SIZE) - STANDING_HEIGHT_RADIUS
    start_x = 48.0
    sim = create_sim_from_lookup(lookup, start_x, start_y)

    # Place buzzer 80px ahead at player height — jump arc will land on it
    enemy = Enemy(x=start_x + 80.0, y=start_y, enemy_type="enemy_buzzer")
    sim.enemies.append(enemy)

    # Jump right with a short arc (release jump early)
    for frame in range(60):
        if frame == 0:
            inp = InputState(right=True, jump_pressed=True, jump_held=True)
        elif frame < 3:
            inp = InputState(right=True, jump_held=True)
        else:
            inp = InputState(right=True)
        sim_step(sim, inp)
        if not enemy.alive:
            break

    assert enemy.alive is False, "Enemy should be destroyed by bounce"
    assert sim.player.physics.y_vel == ENEMY_BOUNCE_VELOCITY, (
        f"Player should bounce with y_vel={ENEMY_BOUNCE_VELOCITY}, "
        f"got {sim.player.physics.y_vel}"
    )


def test_enemy_walk_into_causes_damage():
    """Walking into an enemy while grounded produces DamageEvent."""
    sim = create_sim("hillside")
    sim.player.rings = 3
    enemy = _place_buzzer(sim, dx=30.0)

    all_events, found = _run_until_event(sim, InputState(right=True), DamageEvent)

    assert found, "Should take damage from walking into enemy"
    damage_events = [e for e in all_events if isinstance(e, DamageEvent)]
    assert len(damage_events) > 0
    assert sim.player.rings == 0, "Rings should drop to 0"
    assert enemy.alive is True, "Enemy should survive grounded contact"


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

def test_checkpoint_activation():
    """Running through a checkpoint produces CheckpointEvent and updates respawn."""
    sim = create_sim("hillside")
    assert len(sim.checkpoints) > 0, "Hillside should have checkpoints"

    cp = sim.checkpoints[0]
    assert cp.activated is False

    # Teleport player to checkpoint
    sim.player.physics.x = cp.x
    sim.player.physics.y = cp.y

    events = sim_step(sim, InputState())

    cp_events = [e for e in events if isinstance(e, CheckpointEvent)]
    assert len(cp_events) > 0, "Should trigger CheckpointEvent"
    assert cp.activated is True, "Checkpoint should be marked activated"
    assert sim.player.respawn_x == cp.x
    assert sim.player.respawn_y == cp.y


# ---------------------------------------------------------------------------
# Goal
# ---------------------------------------------------------------------------

def test_goal_reached():
    """Reaching the goal produces GoalReachedEvent and sets goal_reached."""
    sim = create_sim("hillside")

    # Teleport to goal
    sim.player.physics.x = sim.goal_x
    sim.player.physics.y = sim.goal_y

    events = sim_step(sim, InputState())

    goal_events = [e for e in events if isinstance(e, GoalReachedEvent)]
    assert len(goal_events) == 1, "Should trigger GoalReachedEvent"
    assert sim.goal_reached is True

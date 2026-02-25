"""Tests for speednik/objects.py — ring collection, extra life, and loading."""

from __future__ import annotations

from speednik.constants import (
    EXTRA_LIFE_THRESHOLD,
    RING_COLLECTION_RADIUS,
    SCATTER_RING_LIFETIME,
)
from speednik.objects import Ring, RingEvent, check_ring_collection, load_rings
from speednik.player import Player, PlayerState, ScatteredRing, create_player, player_update
from speednik.physics import InputState
from speednik.terrain import FULL, TILE_SIZE, Tile, TileLookup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def flat_tile() -> Tile:
    return Tile(height_array=[TILE_SIZE] * TILE_SIZE, angle=0, solidity=FULL)


def flat_ground_lookup() -> TileLookup:
    tiles = {}
    for tx in range(30):
        tiles[(tx, 12)] = flat_tile()
    def lookup(tx: int, ty: int) -> Tile | None:
        return tiles.get((tx, ty))
    return lookup


# ---------------------------------------------------------------------------
# TestLoadRings
# ---------------------------------------------------------------------------

class TestLoadRings:
    def test_loads_ring_entities(self):
        entities = [
            {"type": "ring", "x": 100, "y": 200},
            {"type": "ring", "x": 300, "y": 400},
        ]
        rings = load_rings(entities)
        assert len(rings) == 2
        assert rings[0].x == 100.0
        assert rings[0].y == 200.0
        assert rings[1].x == 300.0
        assert rings[1].y == 400.0

    def test_ignores_non_ring_entities(self):
        entities = [
            {"type": "ring", "x": 100, "y": 200},
            {"type": "enemy_crab", "x": 300, "y": 400},
            {"type": "player_start", "x": 50, "y": 100},
        ]
        rings = load_rings(entities)
        assert len(rings) == 1

    def test_empty_entities(self):
        rings = load_rings([])
        assert rings == []


# ---------------------------------------------------------------------------
# TestRingCollection
# ---------------------------------------------------------------------------

class TestRingCollection:
    def test_collect_ring_in_range(self):
        """Player within collection radius collects the ring."""
        p = create_player(100.0, 100.0)
        rings = [Ring(x=105.0, y=100.0)]  # 5px away, within 16px radius

        events = check_ring_collection(p, rings)

        assert rings[0].collected is True
        assert p.rings == 1
        assert RingEvent.COLLECTED in events

    def test_no_collect_out_of_range(self):
        """Player outside collection radius does not collect."""
        p = create_player(100.0, 100.0)
        rings = [Ring(x=200.0, y=200.0)]  # ~141px away

        events = check_ring_collection(p, rings)

        assert rings[0].collected is False
        assert p.rings == 0
        assert events == []

    def test_already_collected_ignored(self):
        """A ring that is already collected is skipped."""
        p = create_player(100.0, 100.0)
        rings = [Ring(x=105.0, y=100.0, collected=True)]

        events = check_ring_collection(p, rings)

        assert p.rings == 0
        assert events == []

    def test_multiple_rings_same_frame(self):
        """Multiple rings in range are all collected in one frame."""
        p = create_player(100.0, 100.0)
        rings = [
            Ring(x=105.0, y=100.0),
            Ring(x=100.0, y=105.0),
        ]

        events = check_ring_collection(p, rings)

        assert all(r.collected for r in rings)
        assert p.rings == 2
        assert events.count(RingEvent.COLLECTED) == 2

    def test_dead_player_cannot_collect(self):
        """Dead player cannot collect rings."""
        p = create_player(100.0, 100.0)
        p.state = PlayerState.DEAD
        rings = [Ring(x=105.0, y=100.0)]

        events = check_ring_collection(p, rings)

        assert rings[0].collected is False
        assert p.rings == 0
        assert events == []

    def test_hurt_player_cannot_collect(self):
        """Hurt player cannot collect world rings."""
        p = create_player(100.0, 100.0)
        p.state = PlayerState.HURT
        rings = [Ring(x=105.0, y=100.0)]

        events = check_ring_collection(p, rings)

        assert rings[0].collected is False
        assert p.rings == 0
        assert events == []

    def test_boundary_distance(self):
        """Ring at exactly the collection radius is NOT collected (strictly less than)."""
        p = create_player(100.0, 100.0)
        # Place ring exactly at radius distance
        rings = [Ring(x=100.0 + RING_COLLECTION_RADIUS, y=100.0)]

        events = check_ring_collection(p, rings)

        # dx*dx + dy*dy == radius*radius, not < radius*radius
        assert rings[0].collected is False
        assert events == []


# ---------------------------------------------------------------------------
# TestExtraLife
# ---------------------------------------------------------------------------

class TestExtraLife:
    def test_100_rings_awards_extra_life(self):
        """Crossing 100 rings awards an extra life."""
        p = create_player(100.0, 100.0)
        p.rings = 99
        rings = [Ring(x=105.0, y=100.0)]

        events = check_ring_collection(p, rings)

        assert p.rings == 100
        assert p.lives == 4  # Started at 3, +1
        assert RingEvent.EXTRA_LIFE in events

    def test_extra_life_event_returned(self):
        """EXTRA_LIFE event is returned alongside COLLECTED."""
        p = create_player(100.0, 100.0)
        p.rings = 99
        rings = [Ring(x=105.0, y=100.0)]

        events = check_ring_collection(p, rings)

        assert RingEvent.COLLECTED in events
        assert RingEvent.EXTRA_LIFE in events

    def test_crossing_200_awards_another(self):
        """Crossing 200 rings awards another extra life."""
        p = create_player(100.0, 100.0)
        p.rings = 199
        rings = [Ring(x=105.0, y=100.0)]

        events = check_ring_collection(p, rings)

        assert p.rings == 200
        assert p.lives == 4

    def test_no_extra_life_below_threshold(self):
        """No extra life when ring count stays below 100."""
        p = create_player(100.0, 100.0)
        p.rings = 50
        rings = [Ring(x=105.0, y=100.0)]

        events = check_ring_collection(p, rings)

        assert p.rings == 51
        assert p.lives == 3
        assert RingEvent.EXTRA_LIFE not in events

    def test_recollect_to_100_after_damage(self):
        """Recollecting to 100 after damage awards another extra life."""
        p = create_player(100.0, 100.0)
        p.rings = 99
        # First, collect to 100
        ring1 = Ring(x=105.0, y=100.0)
        check_ring_collection(p, [ring1])
        assert p.lives == 4

        # Simulate damage: rings reset to 0
        p.rings = 0

        # Collect 100 more rings (set rings to 99, collect 1 more)
        p.rings = 99
        ring2 = Ring(x=105.0, y=100.0)
        events = check_ring_collection(p, [ring2])

        assert p.rings == 100
        assert p.lives == 5
        assert RingEvent.EXTRA_LIFE in events


# ---------------------------------------------------------------------------
# TestRecollectionTimer
# ---------------------------------------------------------------------------

class TestRecollectionTimer:
    def test_scattered_ring_expires(self):
        """Scattered rings disappear after their timer runs out."""
        p = create_player(64.0, 172.0)
        p.scattered_rings = [ScatteredRing(x=200, y=200, vx=0, vy=0, timer=1)]
        lookup = flat_ground_lookup()
        inp = InputState()

        player_update(p, inp, lookup)

        assert len(p.scattered_rings) == 0

    def test_scattered_ring_collectible(self):
        """Scattered rings can be collected before they expire."""
        p = create_player(100.0, 100.0)
        # Place scattered ring right at player position
        p.scattered_rings = [ScatteredRing(x=100, y=100, vx=0, vy=0, timer=60)]
        lookup = flat_ground_lookup()
        inp = InputState()

        player_update(p, inp, lookup)

        # Ring should have been collected
        assert p.rings == 1
        assert len(p.scattered_rings) == 0

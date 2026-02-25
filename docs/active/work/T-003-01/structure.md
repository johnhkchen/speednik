# T-003-01 Structure — Ring System

## New Files

### `speednik/objects.py`

Ring entity data and collection logic. Pyxel-free for testability.

```
Module: speednik/objects.py
Imports: constants (RING_COLLECTION_RADIUS, EXTRA_LIFE_THRESHOLD, GRAVITY, SCATTER_RING_LIFETIME)
         player (Player, PlayerState)
         enum (Enum)
         dataclasses (dataclass)

Exports:
  RingEvent (Enum)
    COLLECTED        — a world ring was collected
    EXTRA_LIFE       — 100-ring threshold crossed
    SCATTER_SFX      — rings were scattered (damage with rings)
    DEATH_SFX        — player died (damage with no rings)

  Ring (dataclass)
    x: float
    y: float
    collected: bool = False

  load_rings(entities: list[dict]) -> list[Ring]
    Filter entities for type=="ring", return Ring objects.

  check_ring_collection(player: Player, rings: list[Ring]) -> list[RingEvent]
    For each uncollected ring, check distance to player center.
    On collection: mark collected, increment player.rings, check extra life.
    Return list of events (one COLLECTED per ring, one EXTRA_LIFE if threshold crossed).
    Skip if player state is DEAD or HURT.

  check_scattered_ring_collection(player: Player) -> list[RingEvent]
    Wraps the existing _check_ring_collection logic from player.py but returns events.
    This allows SFX to fire for scattered ring recollection too.
    (Alternative: leave scattered ring collection in player.py, add events there.)
```

### `tests/test_rings.py`

Unit tests for the ring system.

```
Module: tests/test_rings.py
Imports: objects (Ring, RingEvent, load_rings, check_ring_collection)
         player (Player, create_player, damage_player, PlayerState)
         constants

Test classes:
  TestLoadRings
    - test_loads_ring_entities
    - test_ignores_non_ring_entities
    - test_empty_entities

  TestRingCollection
    - test_collect_ring_in_range
    - test_no_collect_out_of_range
    - test_already_collected_ring_ignored
    - test_multiple_rings_same_frame
    - test_dead_player_cannot_collect
    - test_collect_event_returned

  TestExtraLife
    - test_100_rings_awards_extra_life
    - test_extra_life_event_returned
    - test_crossing_200_awards_another_life
    - test_recollecting_to_100_after_damage_awards_life

  TestScatterCountCap
    - test_scatter_capped_at_32 (existing, verify in new context)

  TestRecollectionTimer
    - test_scattered_ring_expires_after_timeout
    - test_scattered_ring_collectible_before_timeout
```

## Modified Files

### `speednik/constants.py`

Add two constants:

```
+ RING_COLLECTION_RADIUS = 16    # Pixels; used for both world and scattered ring collection
+ EXTRA_LIFE_THRESHOLD = 100     # Rings needed for an extra life
```

### `speednik/player.py`

Minimal changes:

1. Import `RING_COLLECTION_RADIUS` from constants (replace hardcoded `16` on line 308).
2. Modify `_check_ring_collection()` to use the constant.
3. No other structural changes — world ring collection is handled by `objects.py`.

### `speednik/main.py`

Integration changes:

1. Import `objects` module: `Ring`, `RingEvent`, `load_rings`, `check_ring_collection`.
2. Import `play_sfx` and SFX constants from `audio`.
3. In `__init__`: Load demo rings (hardcoded positions for demo level) or load from entities if using stage loader.
4. In `update()`: Call `check_ring_collection()`, map returned events to `play_sfx()` calls.
5. In `draw()`: Render world rings as yellow circles (color 10). Render ring counter HUD with flash-at-zero.

## File Dependency Graph

```
constants.py  ← objects.py ← main.py
                    ↑
player.py ─────────┘

audio.py ← main.py (SFX calls only in main.py)
```

## Interface Boundaries

### objects.py public interface

```python
# Data
class RingEvent(Enum): ...
class Ring: ...

# Functions
def load_rings(entities: list[dict]) -> list[Ring]: ...
def check_ring_collection(player: Player, rings: list[Ring]) -> list[RingEvent]: ...
```

### Integration in main.py update loop

```python
# After player_update():
events = check_ring_collection(self.player, self.rings)
for event in events:
    if event == RingEvent.COLLECTED:
        play_sfx(SFX_RING)
    elif event == RingEvent.EXTRA_LIFE:
        play_sfx(SFX_1UP)
```

### Integration in main.py draw loop

```python
# World rings (before camera reset):
for ring in self.rings:
    if not ring.collected:
        pyxel.circ(int(ring.x), int(ring.y), 3, 10)

# HUD (after camera reset):
ring_color = 10 if self.player.rings > 0 else (10 if pyxel.frame_count % 30 < 15 else 0)
pyxel.text(4, 4, f"RINGS {self.player.rings:03d}", ring_color)
pyxel.text(4, 12, f"LIVES {self.player.lives}", 7)
```

## Ordering

1. Constants first (no dependencies)
2. Objects module (depends on constants, player)
3. Player.py fix (trivial constant reference)
4. Tests (depends on objects module)
5. Main.py integration (depends on all above)

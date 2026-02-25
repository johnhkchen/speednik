# T-003-01 Design — Ring System

## Problem

Implement world ring entities (placed by level designers), collection detection, SFX triggers, 100-ring extra life, and HUD ring counter. The scattered ring system already exists in `player.py` but world rings, SFX integration, extra life logic, and proper HUD display are missing.

## Decision 1: Where to put ring entity logic

### Option A: New `speednik/objects.py` module

The specification lists `objects.py` for "Rings, springs, launch pipes, checkpoints, liquid." Creating it now establishes the pattern for all future object types.

### Option B: Extend `speednik/player.py`

Add world ring collection logic alongside the existing scattered ring logic.

### Option C: New `speednik/rings.py` module

A focused module just for rings.

### Decision: Option A — `speednik/objects.py`

Rationale: The spec already designates `objects.py` for rings and other objects. Starting with rings establishes the module structure that springs, checkpoints, and other objects will follow. This is better than a ring-specific module because the patterns (entity loading, collision detection, update loop) will be shared across object types. It avoids bloating `player.py` which already handles player state, physics integration, and damage.

## Decision 2: SFX coupling strategy

### Option A: Direct `play_sfx()` calls in game logic

Import `audio.py` into `objects.py` and call `play_sfx()` directly when rings are collected.

### Option B: Return events from update functions

Ring collection returns a list of events (e.g., `["ring_collected", "extra_life"]`) that the caller maps to SFX calls.

### Option C: Callback parameter

Pass an optional `on_collect` callback to the ring update function.

### Decision: Option B — Return events

Rationale: This preserves the Pyxel-free testability pattern established by `player.py`. Tests can assert on returned events without mocking audio. The main loop in `main.py` already handles rendering and audio — it can map events to `play_sfx()` calls. The event list is lightweight (a simple list of string constants or an enum). This also aligns with how `damage_player()` works — it modifies state, and the caller is responsible for SFX (though SFX isn't wired yet — this ticket adds it).

## Decision 3: Ring collection detection approach

### Option A: Distance-based (circle overlap)

Same pattern as `_check_ring_collection()` for scattered rings: `dx² + dy² < radius²`.

### Option B: AABB overlap

Check if player rectangle overlaps ring rectangle.

### Decision: Option A — Distance-based

Rationale: Consistent with the existing scattered ring collection in `player.py` (line 308). Rings are conceptually circular. The 16px radius already works well. Simple, fast, and tested.

## Decision 4: Ring data structure

### Option A: Dataclass with `collected` flag

```python
@dataclass
class Ring:
    x: float
    y: float
    collected: bool = False
```

Filter out collected rings during updates.

### Option B: List removal on collection

Maintain a list; remove collected rings from it.

### Decision: Option A — Dataclass with `collected` flag

Rationale: Simpler to reason about than list mutation during iteration. The flag allows deferred removal (e.g., play a collection animation first, then remove next frame). Consistent with game object patterns where entities have state flags.

## Decision 5: Extra life tracking

The 100-ring threshold should trigger once per crossing. If the player has 99 rings and collects 2, they get one extra life, not two. If they lose rings to damage and re-collect to 100, they should get another life.

### Approach

Track the ring count before collection. If `old_rings < 100 <= new_rings`, emit an extra life event. This handles multi-ring-per-frame edge cases and re-crossing after damage.

For simplicity, we track crossing at every 100 mark (100, 200, 300...) using integer division: `old // 100 < new // 100`.

## Decision 6: HUD integration

### Option A: HUD rendering in `main.py`

Keep HUD rendering in the draw method of `main.py`, upgrading the existing debug text.

### Option B: Separate HUD module

Create `speednik/hud.py` with dedicated rendering functions.

### Decision: Option A — HUD rendering in `main.py`

Rationale: The HUD is currently just `pyxel.text()` calls. The specification says HUD is drawn with `pyxel.text()`. A separate module is premature for text rendering. When the HUD becomes more complex (sprite-based numbers, timer, score tally), a module can be extracted. For now, enhance the existing draw method.

## Decision 7: Ring animation

The spec says "small yellow circles with rotating highlight line." For the initial implementation, rings will be rendered as small yellow circles (matching scattered ring rendering). The rotating highlight is a rendering polish detail that can be added later without changing the data model.

## Architecture Summary

```
objects.py (new)
  Ring dataclass
  load_rings(entities) → list[Ring]
  check_ring_collection(player, rings) → list[RingEvent]
  RingEvent enum: COLLECTED, EXTRA_LIFE

constants.py (modified)
  + RING_COLLECTION_RADIUS = 16
  + EXTRA_LIFE_THRESHOLD = 100

player.py (modified)
  damage_player() → returns list[RingEvent] for SFX signaling

main.py (modified)
  - Load rings from entities
  - Call check_ring_collection() each frame
  - Map events to play_sfx() calls
  - Render world rings
  - Upgrade HUD with ring counter flash

tests/test_rings.py (new)
  Ring collection, scatter cap, recollection timer, 100-ring extra life
```

## Rejected Alternatives

- **Ring-specific module**: Unnecessary fragmentation when `objects.py` will house multiple object types
- **Direct SFX calls**: Breaks Pyxel-free testability pattern
- **AABB collision**: Inconsistent with existing distance-based pattern; rings are circular
- **List mutation for collection**: Harder to reason about during iteration; flag pattern is cleaner
- **Separate HUD module**: Premature for `pyxel.text()` calls

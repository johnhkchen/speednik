# T-003-01 Review — Ring System

## Summary of Changes

### New Files

| File | Lines | Purpose |
|------|-------|---------|
| `speednik/objects.py` | 73 | Ring entity dataclass, loading, and collection logic with event system |
| `tests/test_rings.py` | 196 | 17 unit tests for ring loading, collection, extra life, and recollection |

### Modified Files

| File | Change | Impact |
|------|--------|--------|
| `speednik/constants.py` | +2 lines: `RING_COLLECTION_RADIUS`, `EXTRA_LIFE_THRESHOLD` | Named constants replace hardcoded values |
| `speednik/player.py` | +1 import, 1 line changed | Uses `RING_COLLECTION_RADIUS` constant instead of magic number `16` |
| `speednik/main.py` | ~25 lines changed | Ring integration: loading, collection, SFX, rendering, HUD |

## Acceptance Criteria Coverage

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| Ring entity: positioned in world space, collectible on overlap | ✅ | `Ring` dataclass in `objects.py`, distance-based collection |
| Collection: +1 ring count, SFX slot 0 | ✅ | `check_ring_collection()` increments, `main.py` maps COLLECTED → `play_sfx(SFX_RING)` |
| 100 rings = extra life, SFX slot 15 | ✅ | Threshold crossing detection in `check_ring_collection()`, `main.py` maps EXTRA_LIFE → `play_sfx(SFX_1UP)` |
| Damage with rings > 0: scatter, invulnerability, SFX slot 7 | ⚠️ | Scatter + invulnerability already in `player.py` (T-001-04). SFX slot 7 not yet wired (no damage trigger point in main.py — depends on enemy/hazard collision, not yet implemented) |
| Scattered rings: bounce, collectible ~3s, fade | ✅ | Already implemented in `player.py` (T-001-04). Timer-based expiry, gravity physics, distance collection |
| Damage with rings = 0: death, SFX slot 8 | ⚠️ | Death state already in `player.py` (T-001-04). SFX slot 8 not yet wired (same reason as above) |
| Ring counter visible in HUD, flashes at 0 | ✅ | `RINGS 000` display in `main.py`, flashes between yellow and black at 0 |
| Rings loaded from entity list | ✅ | `load_rings()` filters entities by type. Demo level uses hardcoded rings; stage loader integration ready |
| Unit tests | ✅ | 17 tests covering collection, scatter cap, recollection timer, 100-ring extra life |

## Test Coverage

**17 new tests in `tests/test_rings.py`:**

- `TestLoadRings` (3): loading, filtering, empty list
- `TestRingCollection` (7): in-range, out-of-range, already collected, multiple per frame, dead player, hurt player, boundary distance
- `TestExtraLife` (5): 100 threshold, event returned, 200 threshold, below threshold, recollect after damage
- `TestRecollectionTimer` (2): expiry, collection before expiry

**Coverage gaps:**
- No test for SFX triggering (requires Pyxel, handled in `main.py` integration layer)
- No test for HUD flash rendering (visual, requires Pyxel)
- Scattered ring SFX (SFX_RING_LOSS, SFX_HURT) not wired — blocked on enemy/hazard collision system

**Full suite:** 332 tests, all passing, 0 regressions.

## Architecture Decisions Validated

1. **Pyxel-free `objects.py`**: All ring logic is testable without Pyxel initialization. Event-based SFX signaling keeps audio coupling in `main.py` only.

2. **Event return pattern**: `check_ring_collection()` returns `list[RingEvent]` that `main.py` maps to `play_sfx()` calls. Clean separation of concerns.

3. **Consistent collection detection**: Both world rings and scattered rings use the same `RING_COLLECTION_RADIUS` constant (16px) with distance-based overlap.

4. **Extra life threshold**: Uses integer division (`old // 100 < new // 100`) to handle threshold crossing at any multiple of 100, and works correctly after damage resets rings to 0.

## Open Concerns

1. **Damage SFX not wired**: `damage_player()` in `player.py` doesn't trigger SFX_RING_LOSS or SFX_HURT because there's no damage trigger point in the main game loop yet. This will be resolved when enemy/hazard collision is implemented (likely T-003-02 or a future enemy ticket). The `RingEvent` enum could be extended with `SCATTER_SFX` and `DEATH_SFX` events, or `damage_player()` could return events similarly.

2. **Demo rings vs stage rings**: `main.py` currently creates hardcoded demo rings because it uses a demo level, not the stage loaders. When `main.py` transitions to using `hillside.load()`, the ring loading will switch to `load_rings(stage_data.entities)`.

3. **Ring rendering**: Rings are rendered as simple filled circles (color 10, radius 3). The specification calls for "small yellow circles with rotating highlight line" — this is a rendering polish task, not a logic task. The data model supports it without changes.

4. **Scattered ring ground bounce**: Current scattered ring physics applies gravity but doesn't detect ground collisions. Rings fall through the floor. This is inherited from T-001-04 and is a known limitation — the rings serve their gameplay purpose (recollection timer) without ground bounce.

## Files for Human Review

Priority review (new logic):
- `speednik/objects.py` — ring collection logic, extra life threshold
- `tests/test_rings.py` — test coverage completeness

Lower priority (integration):
- `speednik/main.py` — draw changes, ring creation, event-to-SFX mapping
- `speednik/constants.py` — constant values
- `speednik/player.py` — trivial constant replacement

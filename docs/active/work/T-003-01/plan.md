# T-003-01 Plan — Ring System

## Step 1: Add constants

**File:** `speednik/constants.py`

Add:
```python
RING_COLLECTION_RADIUS = 16
EXTRA_LIFE_THRESHOLD = 100
```

**Verification:** Constants importable, no syntax errors.

## Step 2: Create `speednik/objects.py` with Ring and collection logic

**File:** `speednik/objects.py` (new)

Implement:
- `RingEvent` enum: `COLLECTED`, `EXTRA_LIFE`
- `Ring` dataclass: `x`, `y`, `collected`
- `load_rings(entities)`: Filters for `type == "ring"`, returns `list[Ring]`
- `check_ring_collection(player, rings)`: Distance check against each uncollected ring. On collect: mark `collected=True`, increment `player.rings`, check extra life threshold (using `old_rings // EXTRA_LIFE_THRESHOLD < new_rings // EXTRA_LIFE_THRESHOLD`). Returns event list. Skips DEAD and HURT players.

**Verification:** Module imports cleanly, no circular dependencies.

## Step 3: Fix hardcoded radius in `player.py`

**File:** `speednik/player.py`

- Import `RING_COLLECTION_RADIUS` from constants
- Replace `16 * 16` in `_check_ring_collection()` with `RING_COLLECTION_RADIUS * RING_COLLECTION_RADIUS`

**Verification:** Existing tests still pass (`uv run pytest tests/test_player.py`).

## Step 4: Write unit tests

**File:** `tests/test_rings.py` (new)

Test classes:

### TestLoadRings
- `test_loads_ring_entities`: `load_rings([{"type": "ring", "x": 100, "y": 200}])` returns one Ring at (100, 200)
- `test_ignores_non_ring_entities`: Non-ring entities filtered out
- `test_empty_entities`: Returns empty list

### TestRingCollection
- `test_collect_ring_in_range`: Player within 16px of ring → ring.collected, player.rings += 1, COLLECTED event
- `test_no_collect_out_of_range`: Player far from ring → no collection
- `test_already_collected_ignored`: Ring with collected=True is skipped
- `test_multiple_rings_same_frame`: Two rings in range → both collected, two COLLECTED events
- `test_dead_player_cannot_collect`: Player in DEAD state → no collection
- `test_hurt_player_cannot_collect`: Player in HURT state → no collection

### TestExtraLife
- `test_100_rings_awards_extra_life`: Player at 99 rings collects 1 → lives += 1, EXTRA_LIFE event
- `test_crossing_200_awards_another`: Player at 199 collects 1 → lives += 1 again
- `test_no_extra_life_below_threshold`: Player at 50 collects 1 → no EXTRA_LIFE event
- `test_recollect_to_100_after_damage`: Player reaches 100, loses rings to damage, recollects to 100 → another extra life

### TestRecollectionTimer (verifies existing scattered ring behavior)
- `test_scattered_ring_expires`: Scattered ring with timer=1 disappears after one update
- `test_scattered_ring_collectible`: Scattered ring within range is collected

**Verification:** `uv run pytest tests/test_rings.py -v` — all pass.

## Step 5: Integrate into `main.py`

**File:** `speednik/main.py`

Changes:
1. Add imports: `objects.Ring, RingEvent, load_rings, check_ring_collection` and `audio.play_sfx, SFX_RING, SFX_1UP`
2. In `__init__`: Create demo rings (a line of rings above flat ground for testing)
3. In `update()`: After `player_update()`, call `check_ring_collection()`. Loop events and call `play_sfx()` for COLLECTED and EXTRA_LIFE.
4. In `draw()`:
   - Render uncollected world rings as yellow circles (color 10, radius 3)
   - Replace debug HUD with proper ring counter that flashes at zero
   - Show lives count

**Verification:** `uv run python -m speednik.main` — rings visible, collectible, SFX plays, counter updates, flash at zero.

## Step 6: Run full test suite

**Verification:** `uv run pytest tests/ -v` — all tests pass, no regressions.

## Testing Strategy

| Category | Tests | Method |
|----------|-------|--------|
| Ring loading | 3 tests | Unit: load_rings with various entity lists |
| Ring collection | 6 tests | Unit: check_ring_collection with positioned player/rings |
| Extra life | 4 tests | Unit: ring count threshold crossing |
| Scattered rings | 2 tests | Unit: timer expiry and collection (existing behavior) |
| Integration | Manual | Run game, collect rings, take damage, verify SFX and HUD |

Total: ~15 unit tests.

## Commit Plan

1. **Commit 1**: Steps 1-3 (constants + objects module + player.py fix)
2. **Commit 2**: Step 4 (tests)
3. **Commit 3**: Step 5 (main.py integration)
4. Or: Single commit if all steps complete atomically

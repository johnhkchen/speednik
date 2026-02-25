# T-003-01 Progress — Ring System

## Step 1: Add constants ✅

Added `RING_COLLECTION_RADIUS = 16` and `EXTRA_LIFE_THRESHOLD = 100` to `speednik/constants.py`.

## Step 2: Create `speednik/objects.py` ✅

Created with:
- `RingEvent` enum (COLLECTED, EXTRA_LIFE)
- `Ring` dataclass (x, y, collected)
- `load_rings()` — filters entity list for ring type
- `check_ring_collection()` — distance-based collection with extra life threshold crossing detection

Returns events for SFX mapping. Pyxel-free for testability.

## Step 3: Fix hardcoded radius in `player.py` ✅

- Imported `RING_COLLECTION_RADIUS` from constants
- Replaced `16 * 16` with `RING_COLLECTION_RADIUS * RING_COLLECTION_RADIUS`
- All existing player tests pass

## Step 4: Write unit tests ✅

Created `tests/test_rings.py` with 17 tests:
- TestLoadRings (3 tests): loads, filters, handles empty
- TestRingCollection (7 tests): in-range, out-of-range, already collected, multiple, dead/hurt player, boundary
- TestExtraLife (5 tests): 100 threshold, 200 threshold, below threshold, recollect after damage
- TestRecollectionTimer (2 tests): expiry, collectibility

All 17 tests pass.

## Step 5: Integrate into `main.py` ✅

- Imported objects module and audio functions
- Added 20 demo rings above flat ground
- Ring collection events trigger `play_sfx(SFX_RING)` and `play_sfx(SFX_1UP)`
- World rings rendered as yellow circles (color 10, radius 3)
- HUD upgraded: `RINGS 000` with flash-at-zero, `LIVES 3`
- Debug info condensed to state and speed

## Step 6: Full test suite ✅

All 332 tests pass (17 new + 315 existing). No regressions.

## Deviations

None. Plan followed exactly.

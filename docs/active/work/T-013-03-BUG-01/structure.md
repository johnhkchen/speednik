# Structure: T-013-03-BUG-01 — skybridge-terrain-pocket-trap-x413

## Files Modified

### 1. `speednik/stages/skybridge/tile_map.json`

**What changes:** The `angle` field of specific tile objects in the 2D array.

**Tiles affected (row 31):**
- `tile_map[31][12]` — angle: 64 → 0
- `tile_map[31][18]` — angle: 192 → 0
- `tile_map[31][20]` — angle: 64 → 0
- `tile_map[31][26]` — angle: 192 → 0
- `tile_map[31][29]` — angle: 64 → 0
- `tile_map[31][35]` — angle: 192 → 0
- `tile_map[31][39]` — angle: 64 → 0

**Tiles affected (row 32):**
- `tile_map[32][12]` — angle: 64 → 0
- `tile_map[32][20]` — angle: 64 → 0
- `tile_map[32][29]` — angle: 64 → 0
- `tile_map[32][39]` — angle: 64 → 0

**Total:** 11 tile angle changes in one JSON file.

Note: Row 32 left-edge tiles (cols 18, 26, 35) have angle=128 which is the correct
underside angle and should NOT be changed. These are interior-type ceiling tiles that
properly define the underside surface. The issue is only with angle=64 (right wall)
and angle=192 (left wall) on platform edge tiles.

## Files NOT Modified

- `speednik/stages/skybridge/collision.json` — solidity values are correct
- `speednik/terrain.py` — engine logic is correct
- `speednik/objects.py` — spring behavior is correct
- `speednik/simulation.py` — no changes needed
- `speednik/constants.py` — no changes needed

## Scope Check

Before committing, verify there are no additional edge tiles beyond col 50 in the
skybridge stage that exhibit the same pattern. The research identified gaps at:
- cols 19 (1 tile gap)
- cols 27-28 (2 tile gap)
- cols 36-38 (3 tile gap)
- cols 73-76 (4 tile gap)

The col 73-76 gap edges also need checking and fixing.

## Architecture Notes

No new modules, interfaces, or abstractions. This is a pure data correction in an
existing JSON asset file. The change is atomic — all angle corrections go in a single
commit.

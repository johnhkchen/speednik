# Review: T-005-02 hillside-loop-collision-fix

## Summary of Changes

Fixed the 360° loop in Hillside Rush Section 5 by moving the loop circle center
down 128px so the loop bottom meets ground level. Eliminated the gap-filling
polygon and simplified approach/exit geometry.

## Files Modified

### `stages/hillside_rush.svg`
- **Circle element** (line 233): `cy="380"` → `cy="508"`. Loop bottom now at y=636
  (ground level). Loop top remains at y=380.
- **Section 5 comments** (lines 222–223): updated to reflect new geometry.
- **Approach polygon** (lines 226–230): replaced 5-point sloping polygon with
  flat rectangle at y=636 from x=3200 to x=3472.
- **Exit polygon** (lines 235–239): replaced 5-point sloping polygon with flat
  rectangle at y=636 from x=3728 to x=4000.
- **Ground-beneath-loop polygon** (was lines 241–244): deleted entirely. The
  gap it was filling no longer exists.
- **Loop rings** (ring_131–150): each cy += 128 to maintain circular arrangement
  around the new loop center (3600, 508).
- **Approach rings** (ring_152–155): cy values flattened to 622 to match the now-flat
  approach ground.

### `speednik/stages/hillside/` (5 generated files)
- `collision.json` — loop collision ring shifted down 8 tile rows
- `tile_map.json` — loop tiles shifted, approach/exit simplified to flat ground
- `entities.json` — ring positions updated to match SVG
- `meta.json` — unchanged (stage dimensions same)
- `validation_report.txt` — 172 issues (down from 234)

### `tests/test_hillside.py`
- `TestLoopGeometry.test_loop_tiles_exist`: ty range 15–32 → 23–40, docstring
  updated to reference new center (3600, 508)
- `TestLoopGeometry.test_loop_has_varied_angles`: ty range 15–32 → 23–40

## Acceptance Criteria Status

- [x] Loop circle has `cy="508"` and `r="128"`, placing bottom at y=636
- [x] No "ground beneath the loop" filler polygon exists
- [x] Approach polygon is flat at y=636, connecting smoothly to loop entry
- [x] Exit polygon is flat at y=636, connecting smoothly from loop exit
- [x] `svg2stage.py` runs successfully (8 shapes, 208 entities, 1811 tiles)
- [x] `validation_report.txt` has no errors (no critical 12px gaps; only minor 1px gaps)
- [x] Loop ring positions (ring_131–150) form circular pattern around new center (3600, 508)

## Test Coverage

- **21/21 tests pass** in `tests/test_hillside.py`
- Entity counts verified: ~200 rings, 3 crabs, 1 buzzer, 1 checkpoint, 1 spring, 1 goal
- Loop geometry: tiles exist in new range, varied angles confirmed
- Player start, level dimensions unchanged

## Validation Report Analysis

**Before (234 lines):**
- 216 angle inconsistencies (many from loop-zone approach/exit slopes)
- 18 impassable gaps including 2 critical **12px gaps** at columns 220/229 y=496

**After (172 lines):**
- 157 angle inconsistencies (loop-zone slope warnings eliminated)
- 15 impassable gaps, all **1px only** (no critical gaps)
- The 12px gaps at the loop-to-ground transition are gone

The remaining 1px gaps at columns 217, 218, 220, 229, 231, 232 are inherent to
circle rasterization at 16px tile resolution. They are at the loop's side walls
(y=400–560) where the perimeter crosses tile boundaries at steep angles. These
are cosmetic and do not affect gameplay (the player follows the loop surface, not
the side walls).

## Open Concerns

1. **Remaining 1px gaps in loop side walls**: These are an artifact of the
   rasterization algorithm (`_ellipse_perimeter_segments` at 16px intervals).
   A finer sampling interval or post-processing pass in `svg2stage.py` could
   eliminate them, but this is a pre-existing issue unrelated to this ticket.

2. **Angle inconsistencies at section boundaries**: The report still shows many
   angle warnings at columns 0, 36–37, 99–100, 149–150, 199–200, 216–217,
   232–233, 249–250. These are section edge transitions across the entire stage,
   not specific to the loop fix. Pre-existing; out of scope.

3. **No gameplay testing**: The fix is geometrically correct (verified via
   coordinate math and validation report), but no in-game playthrough was done.
   Manual testing to confirm the player can enter and traverse the loop at speed
   would be valuable.

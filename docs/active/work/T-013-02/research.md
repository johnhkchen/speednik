# T-013-02 Research — skybridge-collision-gap-fix

## 1. The Gap

Skybridge collision.json (56 rows × 325 cols) has a missing collision tile at
column 11 (px 176–191), rows 31–32. Player starts at x=64, y=490.

Committed (HEAD) state of column 11 across all 56 rows: every value is `0`
(NOT_SOLID). No solid, no TOP_ONLY — fully empty column.

Adjacent columns:
- Col 10: `2` (FULL) at rows 31–35 (solid ground block, x=160–175)
- Col 12: `1` (TOP_ONLY) at rows 31–32 (first floating platform, x=192–207)

The gap is exactly 16px wide (one tile column), sitting between the solid
ground block and the first TOP_ONLY platform.

## 2. tile_map.json Discrepancy

tile_map.json *does* have entries at col 11, rows 31–32:
- Row 31: `{type: 2, height_array: [12×16], angle: 0}` (TOP_ONLY surface, 12/16 fill)
- Row 32: `{type: 2, height_array: [16×16], angle: 0}` (TOP_ONLY surface, full fill)

`level.py:_build_tiles` creates Tile objects for col 11 (tile_map cell is not
None), but sets `solidity=0` from collision.json. The terrain sensor check in
`terrain.py` requires `tile.solidity != NOT_SOLID`, so the tiles are invisible
to collision resolution despite existing in the tiles dict.

## 3. SVG Source Analysis

`stages/skybridge_gauntlet.svg` defines two shapes near this region:
- SOLID polygon (#00AA00): vertices `0,500  160,500  160,896  0,896`
  → covers x=0..160, so col 10's left edge (x=160) is the rightmost pixel.
- TOP_ONLY polygon (#0000FF): vertices `192,500  288,500  288,516  192,516`
  → starts at x=192 = col 12.

Col 11 (x=176–191) falls in the 32px gap between these two polygons. Neither
polygon covers it.

## 4. Pipeline Root Cause

`tools/svg2stage.py` rasterizes polygon edges via `_rasterize_line_segment`:
- The SOLID polygon's right edge is at x=160. At `sx=160.0`: `tx = 160//16 = 10`.
  The walk never reaches x=176 (col 11).
- The TOP_ONLY polygon starts at x=192: `tx = 192//16 = 12`. Col 11 untouched.
- `_fill_interior` only fills columns that already have surface markers. Col 11
  has no markers, so fill skips it.
- `_fill_interior` also explicitly skips TOP_ONLY shapes.

The pipeline correctly produces col 11 = NOT_SOLID given the SVG geometry. The
tile_map.json having col 11 data implies it was generated from a different SVG
revision or a manual edit was applied to tile_map but not collision.

## 5. Level Layout Intent

Player starts at x=64, y=490. The ground block spans cols 0–10 (x=0–175).
Rings at x=160 and x=180 sit on this ground — the ring at x=180 would be
unreachable if col 11 is a pit. The first spring recovery is at x=304 (col 19),
far too late to catch a col-11 fall. Entities list shows continuous ring
placement across the gap zone, confirming the intent is walkable ground.

## 6. Collision Encoding

- `0` = NOT_SOLID: no collision check
- `1` = TOP_ONLY: can land from above, pass through from below
- `2` = FULL: solid in all directions

For this gap fix, the appropriate value is `1` (TOP_ONLY) to match col 12's
surface type. The ground block (cols 0–10) uses `2` (FULL), but col 11 serves
as a transition tile between FULL ground and TOP_ONLY platforms.

## 7. Working Tree State

The working tree already contains a fix in collision.json:
- Row 31, col 11: changed from `0` to `1`
- Row 32, col 11: changed from `0` to `1`

However, the entire collision.json has been minified (18,314 deleted lines →
1 line) which makes the diff massive and hard to review. The semantic change is
just two values but the formatting change affects the entire file.

## 8. Test Infrastructure

`tests/test_audit_skybridge.py` has 6 tests (one per archetype) using
`run_audit()` from `speednik/qa.py`. All tests assert `len(bugs) == 0`.
Previously marked `@pytest.mark.xfail` referencing T-012-04-BUG-01, but the
current working tree has removed those xfail markers, expecting the fix to
make tests pass.

## 9. Related Tickets

- T-012-04-BUG-01: Documents the bottomless-pit-at-x170 bug. Notes walker
  falls at frame 339–340, accumulates 11,197 invariant errors. Proposes three
  fixes: collision patch, pit death mechanism, spring recovery.
- T-013-01: Pit death mechanism (separate ticket, may handle y-boundary kills).

## 10. Files Relevant to Fix

| File | Role |
|------|------|
| `speednik/stages/skybridge/collision.json` | Collision data (needs col 11 fix) |
| `speednik/stages/skybridge/tile_map.json` | Tile data (already has col 11 entries) |
| `speednik/level.py` | Loads tiles, merges tile_map + collision |
| `speednik/terrain.py` | Sensor checks using solidity values |
| `tests/test_audit_skybridge.py` | Verification tests |
| `stages/skybridge_gauntlet.svg` | SVG source (has the 32px gap) |
| `tools/svg2stage.py` | Pipeline tool |

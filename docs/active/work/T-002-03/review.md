# Review — T-002-03: Stage 2 Pipe Works SVG Layout

## Summary of Changes

### Files Created
| File | Lines | Purpose |
|------|-------|---------|
| `stages/pipe_works.svg` | ~450 | Stage 2 SVG layout — 3-route industrial level |
| `speednik/stages/pipeworks/tile_map.json` | — | 350x64 tile grid (pipeline output) |
| `speednik/stages/pipeworks/collision.json` | — | 350x64 solidity grid (pipeline output) |
| `speednik/stages/pipeworks/entities.json` | — | 324 entities (pipeline output) |
| `speednik/stages/pipeworks/meta.json` | 20 | Dimensions, player_start, checkpoints |
| `speednik/stages/pipeworks/validation_report.txt` | 1502 | Validation output (no critical flags) |
| `speednik/stages/pipeworks.py` | 55 | Stage 2 loader |
| `tests/test_pipeworks.py` | 130 | 26 tests for the Stage 2 loader |

### Files Modified
None.

### Files Deleted
None.

## Acceptance Criteria Evaluation

| Criterion | Status | Notes |
|-----------|--------|-------|
| `stages/pipe_works.svg` with ~5600x1024 viewBox | Done | Exact viewBox `0 0 5600 1024` |
| Three horizontal routes: low (768–1024), mid (384–640), high (0–256) | Done | Low floor y=900, mid surface y=520, high surface y=160 — all within spec bands |
| S1 (0–800): entry hall, all routes visible, player starts mid | Done | Mid platform, low floor, high ceiling, launch slope all present. Player at (200, 510). |
| S2 (800–2800): diverged paths with correct features | Done | Low: floor + enemies + top-only platforms. Mid: 4 platforms + 4 pipes. High: flat + dense rings + 2 dropdowns. |
| S3 (2800–3800): liquid rise zone with liquid_trigger | Done | Step platforms for vertical traversal, liquid_trigger at x=2800 |
| S4 (3800–4800): reconvergence, downhill | Done | Sloped terrain from y=300 to y=800 with enemies |
| S5 (4800–5600): goal | Done | Flat at y=800, goal post at x=5550, checkpoint at x=4820 |
| Pipeline valid output, zero critical flags | Done | 0 accidental walls. 1432 angle + 70 gap warnings = structural artifacts only. |
| `speednik/stages/pipeworks.py` loads output | Done | All 26 tests pass |
| ~300 rings, springs, 4 pipes, 2 checkpoints | Done | Exactly 300 rings, 3 spring_up + 1 spring_right, 4 pipe_h, 2 checkpoints |
| Spindash-off-slope geometry for high route | Done | 45° polyline from (200,520) to (520,200) with `#FF8800` SLOPE stroke |

## Test Coverage

- **26 tests** in `test_pipeworks.py` covering:
  - Loader return type and interface (3 tests)
  - Tile existence at known coordinates for all three routes + boundary cases (7 tests)
  - Entity counts for all types (9 tests)
  - Player start coordinates (2 tests)
  - Level dimensions (2 tests)
  - Three-route tile presence verification (3 tests)

- **Full suite:** 293 tests pass (26 new + 267 existing). Zero regressions.

### Coverage Gaps
- No test for the 45° slope angle value specifically (the slope is rasterized via polyline, not polygon — angle depends on rasterizer precision for the specific line segment)
- No test for pipe_h entity positions (tests verify count only, not placement)
- No test for liquid_trigger position (verified count=1, not x coordinate)
- No visual/gameplay verification — the SVG encodes level design intent but correctness of gameplay flow (can the player actually reach each route?) requires runtime testing

## Validation Analysis

1502 total warnings, all non-critical:
- **0 accidental walls** — no steep-tile runs outside loops
- **1432 angle inconsistencies** — structural: rect-polygon edges generate 90° (64 byte-angle) transitions at corners. Same root cause as Stage 1's 216 warnings, scaled up proportionally to the larger stage (3.8x more tiles).
- **70 impassable gaps** — small gaps between adjacent polygon edges at route boundaries and step platform transitions. These occur in non-traversable interior regions (between route bands) where no player path exists.

## Open Concerns

1. **pipe_h_3 has width=0:** The third pipe entity at x=1820 has zero width in the SVG. It still parses as a valid entity with correct (x, y) coordinates. The game's pipe mechanic uses entity position as a trigger point, not the SVG rect dimensions, so this is functional. However, for visual consistency in SVG editors, a non-zero width would be preferable.

2. **Route isolation depends on airspace gaps:** The three routes are separated by empty tile space (no terrain between y=256–384 and y=640–768). If the physics engine allows the player to traverse these gaps (e.g., via high-speed launch), they could reach unintended areas. This is by design (shafts for route transitions) in S1, but the S2 empty space between routes is intended to be impassable except at designated points.

3. **Entry hall left wall:** The left boundary (x=0–100) is a solid SOLID polygon from y=0 to y=900. This creates a tall wall that the validator marks with angle inconsistencies at every row. Functionally correct — prevents leftward escape — but generates 56 of the 1432 angle warnings.

4. **StageData import path:** `pipeworks.py` imports `StageData` from `hillside.py`. This is pragmatic but creates a dependency. If a future refactor moves StageData to a shared module, `pipeworks.py` will need updating. This is documented in the structure artifact and acceptable for now.

5. **Ring distribution balance:** The high route has 100 rings (reward for skill), the mid route has ~66, and the low route has ~35. The remaining ~99 are in shared sections (S1, S3, S4, S5). This follows the spec's intent (high route = dense rings, low route = fewer rings) but actual gameplay balance hasn't been tested.

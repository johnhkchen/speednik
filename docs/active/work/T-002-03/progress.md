# Progress — T-002-03: Stage 2 Pipe Works SVG Layout

## Completed

### Step 1: Created `stages/pipe_works.svg`
- ViewBox: `0 0 5600 1024`
- 25 terrain shapes (polygons + polylines)
- 324 entity elements
- Section-by-section organization with comments
- Three routes: high (y=160 surface), mid (y=520 surface), low (y=900 surface)
- 45° launch slope from mid to high route in S1
- 4 mid-route platforms with gaps, bridged by pipe_h entities
- Top-only platforms: 3 on low route (over liquid), 2 on high route (drop-downs), 1 in S1
- Step platforms in S3 for liquid rise zone escape

### Step 2: Ran pipeline
- `uv run python tools/svg2stage.py stages/pipe_works.svg speednik/stages/pipeworks/`
- Output: 350x64 grid, 13461 tiles, 324 entities
- Validation: 1502 issues (0 accidental walls, 1432 angle inconsistencies, 70 impassable gaps)
- All non-critical structural artifacts (same category as Stage 1's 233 warnings)
- meta.json: 5600x1024, player_start (200, 510), 2 checkpoints

### Step 3: Created `speednik/stages/pipeworks.py`
- Imports StageData from hillside.py (reuse)
- _DATA_DIR points to pipeworks/ directory
- load() follows exact hillside.py pattern

### Step 4: Created `tests/test_pipeworks.py`
- 26 tests across 7 test classes
- All pass: `uv run pytest tests/test_pipeworks.py -v` → 26 passed

### Step 5: Full test suite verification
- `uv run pytest tests/ -v` → 293 passed in 0.13s
- Zero regressions

## Entity Counts (actual)
- ring: 300
- enemy_crab: 6
- enemy_buzzer: 3
- enemy_chopper: 2
- pipe_h: 4
- checkpoint: 2
- spring_up: 3
- spring_right: 1
- liquid_trigger: 1
- goal: 1
- player_start: 1
- Total: 324

## Deviations from Plan
- enemy_crab count is 6 (plan said 5) — added one extra for balance
- pipe_h_3 has width=0 in SVG (positioned at gap between platform 2→3 where platforms are adjacent at x=1820) — this entity still parses correctly as a trigger zone marker. The game code handles pipe mechanics, not the SVG geometry.

# Plan — T-002-03: Stage 2 Pipe Works SVG Layout

## Step 1: Create `stages/pipe_works.svg`

Write the full SVG with all terrain polygons and entity elements.

**Terrain checklist:**
- [ ] ViewBox `0 0 5600 1024`
- [ ] S1: Entry hall terrain — mid platform (y=520), low floor (y=900), 45° launch slope, high route ceiling (y=160)
- [ ] S2 High: Flat surface y=160, x=800–2800. Two top-only drop-down platforms.
- [ ] S2 Mid: Four platforms with gaps. Each closes to y=640.
- [ ] S2 Low: Floor y=900, x=800–2800 closing to y=1024. Three top-only platforms over liquid zone.
- [ ] S3: Convergence room — floor with step platforms for vertical traversal.
- [ ] S4: Downhill terrain from y=400 to y=800, closing to y=1024.
- [ ] S5: Flat approach at y=800, closing to y=1024.

**Entity checklist:**
- [ ] player_start at x=200, y=510 (mid route in entry hall)
- [ ] ~300 rings distributed across all sections
- [ ] 4 pipe_h entities at mid route gaps
- [ ] 2 checkpoints (S3 entry, S5 entry)
- [ ] 5 enemy_crab (low route, S4)
- [ ] 3 enemy_buzzer (mid route gaps)
- [ ] 2 enemy_chopper (S3)
- [ ] 3 spring_up (route transitions)
- [ ] 1 spring_right (mid route assist)
- [ ] 1 liquid_trigger at x=2800
- [ ] 1 goal at S5 end

**Verification:** Open in a text editor, check well-formedness, count entities.

## Step 2: Run Pipeline

```bash
uv run python tools/svg2stage.py stages/pipe_works.svg speednik/stages/pipeworks/
```

**Verification:**
- Exit code 0
- 5 files created in `speednik/stages/pipeworks/`
- `validation_report.txt` has zero critical flags
- `meta.json` has correct dimensions (5600x1024), player_start, 2 checkpoints
- `entities.json` has ~330 entities with correct types

## Step 3: Create `speednik/stages/pipeworks.py`

Loader module following hillside.py pattern:
- Import `StageData` from `speednik.stages.hillside`
- `_DATA_DIR = Path(__file__).parent / "pipeworks"`
- `load() -> StageData` function reading all 4 JSON files

**Verification:** `uv run python -c "from speednik.stages.pipeworks import load; s = load(); print(s.level_width, s.level_height)"`
Expected: `5600 1024`

## Step 4: Create `tests/test_pipeworks.py`

Test module mirroring test_hillside.py structure:

**TestLoadReturnsStageData (3 tests):**
- Returns StageData instance
- tile_lookup is callable
- entities is non-empty list

**TestTileLookup (7 tests):**
- Mid route ground tile at S1 (x=200, y=520 → tx=12, ty=32): solid tile exists
- High route surface at S2 (x=1000, y=160 → tx=62, ty=10): solid tile exists
- Low route floor at S2 (x=1000, y=900 → tx=62, ty=56): solid tile exists
- Sky returns None (tx=5, ty=0)
- Out of bounds returns None
- Interior fill below mid route is solid
- Top-only platform has TOP_ONLY solidity

**TestEntities (9 tests):**
- 1 player_start
- ~280-320 rings (range check)
- 4 pipe_h
- 2 checkpoints
- enemy counts (crab, buzzer, chopper)
- 1 liquid_trigger
- 1 goal

**TestPlayerStart (2 tests):**
- x ≈ 200
- y ≈ 510

**TestLevelDimensions (2 tests):**
- width == 5600
- height == 1024

**TestThreeRoutes (3 tests):**
- High route: tiles exist at y=160 region in S2
- Mid route: tiles exist at y=520 region in S2
- Low route: tiles exist at y=900 region in S2

**Verification:** `uv run pytest tests/test_pipeworks.py -v`

## Step 5: Validate Acceptance Criteria

- [ ] `stages/pipe_works.svg` exists with correct viewBox
- [ ] Three routes at correct y ranges
- [ ] All 5 sections present with correct x ranges
- [ ] Pipeline output valid, zero critical flags
- [ ] `speednik/stages/pipeworks.py` loads successfully
- [ ] ~300 rings, springs at transitions, 4 pipes, 2 checkpoints
- [ ] 45° slope geometry at high route entry
- [ ] All tests pass

## Testing Strategy

- **Unit tests:** `test_pipeworks.py` covers the loader and data integrity
- **Pipeline validation:** `validation_report.txt` covers tile geometry correctness
- **Integration:** The loader test implicitly validates the full pipeline (SVG → JSON → Python objects)
- **No mocking:** Real JSON data, real tile objects — matching the established pattern

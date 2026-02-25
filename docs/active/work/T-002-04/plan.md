# Plan — T-002-04: Skybridge Gauntlet SVG Layout

## Step 1: Create SVG File

Create `stages/skybridge_gauntlet.svg` with viewBox `0 0 5200 896`.

### Section 1 (0–800): Opening Bridges
- Solid starting platform: polygon (0,500)→(160,500)→(160,896)→(0,896), stroke `#00AA00`
- Bridge segment A: polygon (192,500)→(288,500)→(288,516)→(192,516), stroke `#0000FF` (96px wide)
- 32px gap
- Bridge segment B: polygon (320,500)→(416,500)→(416,516)→(320,516), stroke `#0000FF`
- 48px gap
- Bridge segment C: polygon (464,500)→(560,500)→(560,516)→(464,516), stroke `#0000FF`
- 64px gap
- Bridge segment D: polygon (624,500)→(800,500)→(800,516)→(624,516), stroke `#0000FF`
- Player start at (64, 490)
- 3 springs under gaps, 3 crabs on bridges, 1 buzzer, ~40 rings

### Section 2 (800–1600): Rhythm ×1
- Downhill slope: solid polygon from (800,500) descending to (1000,600), stroke `#00AA00`
- 30° ramp: solid polygon from (1000,600) ascending to (1160,507), stroke `#00AA00`
- 80px gap (1160–1240)
- Landing platform: top-only polygon at y=500, width 160px (1240–1400), stroke `#0000FF`
- Ascend platform: top-only polygon at y=400, width 96px (1350–1446), stroke `#0000FF`
- Checkpoint at (780, 490)
- 2 crabs on landing, ~45 rings, 1 spring under gap

### Section 3 (1600–2400): Rhythm ×2
- Same structure, 35° ramp, 112px gap
- Downhill: (1600,500)→(1800,600)
- Ramp: (1800,600) ascending to (1960,488)
- Gap: 112px (1960–2072)
- Landing: top-only at y=500, width 160px (2072–2232)
- Ascend: top-only at y=400, width 96px (2180–2276)
- 2 crabs + 1 buzzer, ~45 rings, 1 spring under gap

### Section 4 (2400–3200): Rhythm ×3
- Same structure, 40° ramp, 144px gap
- Downhill: (2400,500)→(2600,600)
- Ramp: (2600,600) ascending to (2760,466)
- Gap: 144px (2760–2904)
- Landing: top-only at y=500, width 160px (2904–3064)
- Ascend: top-only at y=400, width 96px (3010–3106)
- 3 crabs + 1 buzzer, ~50 rings, 1 spring under gap

### Section 5 (3200–4000): Path Split
- Main bridge: top-only at y=500 from (3200–4000), stroke `#0000FF`
- Guardian enemy (as enemy_crab) at (3600, 484)
- Low detour: 3 top-only platforms at y=700, widths 80px each, gaps 48px
- Spring_up at end of detour to return to bridge level
- 2 crabs on low detour, ~30 rings

### Section 6 (4000–5200): Boss Arena
- Arena floor: solid polygon (4000,500)→(5200,500)→(5200,896)→(4000,896), stroke `#00AA00`
- Left wall: solid polygon (4000,200)→(4032,200)→(4032,500)→(4000,500), stroke `#00AA00`
- Right wall: solid polygon (5168,200)→(5200,200)→(5200,500)→(5168,500), stroke `#00AA00`
- Checkpoint at (3980, 490)
- 20 rings in arena, goal at (5150, 464)

### Ring Distribution (target ~250)
Sections 1–6 rings + 20 transition rings scattered at section boundaries.

**Verification:** Count all ring elements. Must be 240–260.

## Step 2: Run Pipeline

```bash
mkdir -p speednik/stages/skybridge
uv run python tools/svg2stage.py stages/skybridge_gauntlet.svg speednik/stages/skybridge/
```

**Verification:** All 5 output files exist. meta.json shows width_px=5200, height_px=896.

## Step 3: Review Validation Report

Read `speednik/stages/skybridge/validation_report.txt`.

**Accept if:**
- Angle inconsistencies < 200 (bridge edges will generate some)
- Impassable gaps < 20
- No accidental wall warnings in intended bridge/platform areas

**Iterate on SVG if:** Critical geometry errors detected (e.g., ramps producing
wrong angles, landing platforms unreachable).

## Step 4: Create Loader Module

Create `speednik/stages/skybridge.py` following hillside.py pattern exactly.
Only differences: module docstring, _DATA_DIR path.

**Verification:** `python -c "from speednik.stages.skybridge import load; s = load(); print(s.level_width, s.level_height)"`
should print `5200 896`.

## Step 5: Create Tests

Create `tests/test_skybridge.py` with test classes per structure.md.

**Verification:** `uv run pytest tests/test_skybridge.py -v` — all tests pass.

## Step 6: Run Full Test Suite

```bash
uv run pytest
```

**Verification:** All existing tests still pass. No regressions.

## Testing Strategy

| What | How | Pass Criteria |
|------|-----|--------------|
| Pipeline output | Run svg2stage.py | 5 files created, meta.json correct |
| Validation | Read report | < 200 angle warnings, < 20 gap warnings |
| Loader | Import and call load() | Returns StageData with correct dimensions |
| Entities | Count by type | ~250 rings, 2 checkpoints, enemies, springs, goal |
| Tile data | Spot-check coordinates | Bridge tiles are TOP_ONLY, arena tiles are FULL |
| Angles | Spot-check ramp tiles | Non-zero angles in ramp regions |
| Regression | Full pytest | All tests pass |

## Commit Plan

1. **Commit A:** SVG file + pipeline output + loader + tests (single atomic commit)
   - All files are interdependent; partial commits would break tests

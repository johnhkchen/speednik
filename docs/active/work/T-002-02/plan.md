# Plan — T-002-02: Stage 1 Hillside Rush

## Step 1: Create the SVG file — Section 1 (Flat Runway)

Create `stages/hillside_rush.svg` with the viewBox and section 1 terrain:
- `viewBox="0 0 4800 720"`
- Flat ground polygon: `(0,620) → (600,620) → (600,720) → (0,720)`, stroke `#00AA00`
- Player start entity: `<circle id="player_start" cx="64" cy="610" r="8">`
- Ring arc: ~12 rings in a gentle arc from x=100 to x=550, y=580–600

**Verify:** SVG is valid XML, opens in a viewer, viewBox is correct.

## Step 2: Add Section 2 (Gentle Slopes)

Add undulating terrain polygon from x=600 to x=1600:
- Surface follows: flat → 25° uphill → crest → 25° downhill → valley → repeat
- 3 hill/valley cycles across 1000px
- Heights: crests at y≈560, valleys at y≈640, baseline y=620
- 3 enemy_crab entities on flat sections between hills
- ~30 rings along slope contours

**Verify:** Slope angles stay within 25° as specified. Terrain connects seamlessly
at x=600 with section 1 (both at y=620).

## Step 3: Add Section 3 (Half-Pipe Valleys)

Add three U-shaped valley polygons from x=1600 to x=2400:
- Valley 1: depth ~80px (y=620→700), width ~200px
- Valley 2: depth ~120px (y=620→700, walls steeper), width ~220px
- Valley 3: depth ~160px (y=620→700, steepest walls), width ~240px
- Checkpoint entity at x=1620
- Spring (spring_up) entity at the exit of valley 3 (~x=2380)
- ~30 rings at crests between valleys

**Verify:** U-shape polyline points produce gradual angle changes. Walls don't
exceed the accidental-wall validator threshold (≤3 consecutive steep tiles).

## Step 4: Add Section 4 (Acceleration Runway)

Flat to slight downhill polygon from x=2400 to x=3200:
- Entry at y=620, exit at y=640 (very gentle 1.4° slope)
- Continuous ring line: ~40 rings in a straight line along the surface

**Verify:** Connects with section 3 exit. Nearly flat terrain produces byte angle ≈0.

## Step 5: Add Section 5 (The Loop)

Add loop and surrounding terrain from x=3200 to x=4000:
- Flat approach polygon: x=3200→3450, y=640
- `<circle cx="3600" cy="380" r="128" stroke="#00AA00">` for the loop
- Ground polygon connecting loop base to ground: x=3450→3750 at loop-bottom height
- Exit polygon: x=3750→4000, y=640 transitioning to section 6
- ~25 rings inside the loop (placed as entities at positions along the inner circle)

**Verify:** Loop center at y=380 with r=128 means bottom at y=508, top at y=252.
Ground terrain meets the loop bottom. Pipeline loop handler generates continuous
angles.

## Step 6: Add Section 6 (Goal Run)

Gentle downhill polygon from x=4000 to x=4800:
- Entry at y=640, exit at y=660 (gentle slope)
- 1 enemy_buzzer entity at ~x=4400
- ~20 scattered rings
- Goal entity at x=4750

**Verify:** Connects with section 5 exit. Goal position is near the end.

## Step 7: Ring Count Audit and Adjustment

Count all ring entities across sections. Target: ~200.
- Section 1: ~12, Section 2: ~30, Section 3: ~30, Section 4: ~40
- Section 5: ~25, Section 6: ~20, extras along transitions: ~43
Adjust ring density to hit target.

**Verify:** grep/count ring entities in the SVG. Should be 190–210.

## Step 8: Run the Pipeline

```bash
mkdir -p speednik/stages/hillside
python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/
```

**Verify:**
- All 5 output files created
- validation_report.txt has zero critical flags (or only minor warnings)
- tile_map.json has the expected dimensions (300 cols × 45 rows)
- entities.json contains all placed entities
- meta.json player_start matches (64, 610)
- Loop tiles have continuous angle values

## Step 9: Create Stage Loader — speednik/stages/hillside.py

Implement the `StageData` dataclass and `load()` function:
- Read JSON files from `Path(__file__).parent / "hillside"`
- Construct `terrain.Tile` objects from tile_map.json + collision.json
- Build tile dict and TileLookup closure
- Extract metadata and entities
- Return StageData

**Verify:** `from speednik.stages.hillside import load; data = load()` works.

## Step 10: Create Tests — tests/test_hillside.py

Write tests for the stage loader:
- Load returns StageData with all fields populated
- Tile lookup returns Tile at known ground coordinates
- Tile lookup returns None for sky coordinates
- Entities list contains player_start, rings, enemies, checkpoint, goal
- Player start coordinates match expected values
- Level dimensions are 4800x720
- Ring count is approximately 200
- Loop tiles at the loop center column have expected angle progression

**Verify:** `uv run pytest tests/test_hillside.py -v` passes.

## Step 11: Fix Any Pipeline or Loader Issues

If validation report has flags or tests fail:
- Adjust SVG geometry to eliminate angle consistency warnings
- Fix loader bugs
- Re-run pipeline if SVG changes
- Re-run tests

**Verify:** Clean validation report, all tests pass.

## Testing Strategy

| Component | Test Type | Scope |
|-----------|-----------|-------|
| SVG file | Pipeline validation | Zero critical flags in report |
| Pipeline output | Integration | Correct file structure and content |
| Stage loader | Unit | StageData fields, TileLookup behavior |
| Tile data | Spot checks | Known tiles have expected height/angle |
| Entity data | Completeness | All required entity types present |
| Ring count | Acceptance | ~200 rings total |
| Loop geometry | Spot checks | Continuous angle values |

# Structure — T-002-02: Stage 1 Hillside Rush

## Files Created

### 1. `stages/hillside_rush.svg`

The SVG source file for Stage 1. ViewBox: `0 0 4800 720`.

**Terrain elements** (closed `<polygon>` elements, stroke `#00AA00`):
- Section 1: flat ground rectangle, y=620 to y=720, x=0 to x=600
- Section 2: polygon with undulating top edge (hills and valleys), x=600 to x=1600
- Section 3: three U-shaped polygon segments, x=1600 to x=2400
- Section 4: flat/slight downhill polygon, x=2400 to x=3200
- Section 5 approach/exit: flat ground polygons flanking the loop, x=3200 to x=4000
- Section 5 loop: `<circle cx="3600" cy="380" r="128" stroke="#00AA00">`
- Section 6: gentle downhill polygon, x=4000 to x=4800

**Entity elements** (`<circle>` and `<rect>` with `id` attributes):
- 1 `player_start` at (64, 610)
- ~200 `ring` circles distributed across sections
- 3 `enemy_crab` rects in section 2
- 1 `enemy_buzzer` circle in section 6
- 1 `spring_up` rect at section 3 exit
- 1 `checkpoint` circle at section 3 entry
- 1 `goal` rect at section 6 end

### 2. `speednik/stages/hillside/` (directory)

Pipeline output directory containing:
- `tile_map.json` — 300x45 2D array of tile objects
- `collision.json` — 300x45 2D array of solidity integers
- `entities.json` — flat array of `{type, x, y}` objects
- `meta.json` — `{width_px, height_px, width_tiles, height_tiles, player_start, checkpoints}`
- `validation_report.txt` — validation results

### 3. `speednik/stages/hillside.py`

Stage loader module. Public interface:

```python
@dataclass
class StageData:
    tile_lookup: TileLookup          # Callable[[int, int], Optional[Tile]]
    entities: list[dict]             # [{type, x, y}, ...]
    player_start: tuple[float, float]  # (x, y) world coordinates
    checkpoints: list[dict]          # [{x, y}, ...]
    level_width: int                 # world pixels
    level_height: int                # world pixels

def load() -> StageData:
    """Load Hillside Rush stage data from pipeline JSON output."""
```

Internal implementation:
- Resolves JSON paths via `Path(__file__).parent / "hillside"`
- Reads tile_map.json → constructs `terrain.Tile` objects → populates dict
- Reads collision.json → applies solidity to corresponding Tile objects
- Reads entities.json → stores as entity list
- Reads meta.json → extracts dimensions and player_start
- Constructs TileLookup closure from tile dict
- Returns StageData instance

### 4. `tests/test_hillside.py`

Tests for the stage loader:
- `test_load_returns_stage_data` — verifies return type and fields
- `test_tile_lookup_returns_tiles` — spot-checks known tile coordinates
- `test_tile_lookup_returns_none_for_empty` — sky tiles return None
- `test_entities_populated` — verifies entity list is non-empty, has player_start
- `test_player_start_position` — verifies correct coordinates
- `test_level_dimensions` — verifies 4800x720
- `test_ring_count` — verifies approximately 200 rings

## Files Modified

None. All work creates new files.

## Module Boundaries

```
tools/svg2stage.py          # Build-time only: SVG → JSON
                                    ↓ (generates files)
speednik/stages/hillside/   # Static JSON data (checked into repo)
                                    ↓ (loaded by)
speednik/stages/hillside.py # Runtime loader → StageData
                                    ↓ (consumed by)
speednik/terrain.py         # TileLookup used by collision system
speednik/camera.py          # level_width/height for camera bounds
speednik/main.py            # (future) game loop integration
```

The loader imports `terrain.Tile` and `terrain.TileLookup` from the engine.
No engine module imports from the stages package — data flows one-way.

## Interface Contracts

### Pipeline output → Loader (JSON schema)

**tile_map.json cell:**
```json
{"type": 1, "height_array": [0,1,2,...,15], "angle": 32}
```
Maps to `Tile(height_array=..., angle=..., solidity=...)` where solidity comes
from the corresponding collision.json cell.

**collision.json cell:** Integer 0, 1, or 2.
Maps to terrain.NOT_SOLID, terrain.TOP_ONLY, terrain.FULL.

**entities.json entry:**
```json
{"type": "ring", "x": 400, "y": 320}
```
Stored directly as dict in StageData.entities.

**meta.json:**
```json
{"width_px": 4800, "height_px": 720, "width_tiles": 300, "height_tiles": 45,
 "player_start": {"x": 64, "y": 610}, "checkpoints": [{"x": 1620, "y": 580}]}
```

### Loader → Engine (Python types)

```python
tile_lookup(tx: int, ty: int) -> Tile | None
# tx, ty are tile coordinates (world_px // 16)
```

This matches the existing `TileLookup` protocol used by `resolve_collision()`.

## Ordering of Changes

1. Create the SVG file (no dependencies)
2. Run the pipeline to generate JSON output (depends on SVG)
3. Create the stage loader module (depends on pipeline output existing)
4. Create tests (depends on loader module)
5. Verify pipeline validation report has zero critical flags

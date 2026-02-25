# T-006-02 Design: profile2stage-core

## Decision: Standalone script importing shared components from svg2stage

### Options Considered

**Option A: Extract shared library, two thin CLIs**
Move TileGrid, TileData, Validator, StageWriter into `tools/stage_common.py`. Both
svg2stage and profile2stage import from it. Clean separation, no duplication.

Pros: DRY, clean module boundaries.
Cons: Refactors svg2stage (risk to working tool), creates a dependency between
the two tools that doesn't exist today. Over-engineering for MVP.

**Option B: Standalone script, import from svg2stage directly**
profile2stage.py imports the needed classes from svg2stage.py using the same
`sys.path.insert` pattern the tests use. No refactoring of svg2stage.

Pros: Zero risk to existing code, fast to implement, tests already prove the
import pattern works. Can extract a shared library later if warranted.
Cons: Couples profile2stage to svg2stage's internal API. If svg2stage renames
TileGrid, profile2stage breaks. Acceptable for MVP.

**Option C: Copy-paste the needed classes**
Duplicate TileGrid, TileData, Validator, StageWriter into profile2stage.py.

Pros: Fully independent.
Cons: Maintenance burden, divergence risk. Violates DRY with zero benefit.

### Decision: Option B

Import directly from svg2stage. The import surface is small and stable (TileGrid,
TileData, Validator, StageWriter, _build_meta, constants). The test suite already
validates this import path. Extraction to a shared library can happen in a future
ticket if a third tool appears.

---

## Architecture

### Input Parsing & Validation

```
ProfileParser.load(path) → ProfileData
  - Read JSON
  - Validate required fields: track (list), width (int>0), height (int>0)
  - Apply defaults: height=720, start_y=636
  - Validate each segment: seg type in {flat, ramp, gap}, len > 0
  - Ramp: validate rise exists, check slope limits
  - Assign auto-IDs where seg.id is missing
  - Check ID uniqueness
  - Return ProfileData(width, height, start_y, segments)
```

### Pre-rasterization Warnings

Before rasterizing, scan segments for:
1. Slope ratio `abs(rise/len) > tan(30°)` → warning
2. Slope ratio `abs(rise/len) > 1.0` → error (raise, don't continue)
3. Slope discontinuity between adjacent non-gap segments → warning with IDs

### Cursor State Machine (Synthesizer)

```
Synthesizer.__init__(width, height, start_y)
  - Creates TileGrid(cols=ceil(width/TILE_SIZE), rows=ceil(height/TILE_SIZE))
  - cursor_x = 0, cursor_y = start_y, cursor_slope = 0.0

Synthesizer.process(segments) → TileGrid
  For each segment:
    flat:  rasterize_flat(seg)  → horizontal tiles, advance x by len
    ramp:  rasterize_ramp(seg)  → interpolated tiles, advance x by len, y by rise
    gap:   advance x by len (no tiles)
    Update cursor_slope (0 for flat/gap, rise/len for ramp)
```

### Rasterization Details

**flat segment:**
For each pixel column in [cursor_x, cursor_x + len):
- `tx = col // 16`, `local_x = col % 16`
- `ty = floor(cursor_y / 16)` (tile row containing the surface)
  Actually: `ty` such that `(ty+1)*16 > cursor_y >= ty*16`
  More precisely: `ty = int(cursor_y) // 16` since cursor_y is the surface y-position.
  But: height_array is from bottom, so `h = (ty+1)*16 - cursor_y`.
  Clamp h to [0, 16].
- Set `tile.height_array[local_x] = max(existing, h)`
- `tile.angle = 0` (flat), `tile.surface_type = SURFACE_SOLID`

**ramp segment:**
For each pixel column in [cursor_x, cursor_x + len):
- `t = (col - cursor_x) / len`
- `y = cursor_y + rise * t` (linear interpolation)
- Rasterize same as flat but at varying y
- `angle = round(-atan2(rise, len) * 256 / (2π)) % 256`

**Interior fill:**
After rasterizing each segment's surface tiles, fill below:
for each tile column touched by the segment, find the surface tile, fill all tiles
below it to the grid bottom as fully solid `[16]*16`.

**gap segment:**
No tiles. Just advance cursor_x by len. cursor_y and cursor_slope unchanged.

### Tangent Matching (Stub)

After processing all segments, check consecutive non-gap pairs:
if `prev_slope != curr_slope` at boundary, log warning:
`"Slope discontinuity between '{prev_id}' and '{curr_id}': {prev_slope:.3f} → {curr_slope:.3f}"`

Collected as pre-rasterization warnings (included in validation report).

### Output

After synthesizing the grid:
1. Run `Validator(grid).validate()` → post-rasterization issues
2. Combine pre-rasterization warnings + post-rasterization issues
3. Build meta: `_build_meta(width, height, grid, entities=[])` but override
   `player_start` to `None` since there are no entities.
4. Write via `StageWriter(output_dir).write(grid, entities=[], meta, issues)`

### CLI

```
argparse:
  input_profile: positional, .profile.json path
  output_dir: positional, output directory
```

Validate input exists, parse, synthesize, validate, write. Print summary to stdout.
Non-zero exit on errors (invalid profile, unpassable slope).

---

## Testing Strategy

New file `tests/test_profile2stage.py`. Same import pattern as test_svg2stage.py.

Test categories:
1. **ProfileParser**: valid/invalid JSON, missing fields, defaults, ID auto-generation
2. **Flat segment**: height_array = [h]*16 for all tiles in segment
3. **Ramp segment**: linearly interpolated heights across tiles
4. **Gap segment**: no tiles generated, cursor advances
5. **Cursor threading**: y advances by rise through multiple segments
6. **Slope warnings**: tan(30°) threshold, tan(45°) = 1.0 error
7. **Integration**: end-to-end profile → output files, JSON parseable

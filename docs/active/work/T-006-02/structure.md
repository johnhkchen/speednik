# T-006-02 Structure: profile2stage-core

## Files Created

### `tools/profile2stage.py` (~350 lines)

New standalone CLI. Imports shared components from svg2stage.

```
Imports from svg2stage:
  TileData, TileGrid, Validator, StageWriter, _build_meta
  TILE_SIZE, SURFACE_SOLID, NOT_SOLID, SOLIDITY_MAP
  _byte_angle_diff (used indirectly via Validator)

Module-level constants:
  SLOPE_WARN_THRESHOLD = tan(30°)  # ~0.577
  SLOPE_ERROR_THRESHOLD = 1.0      # tan(45°)
  DEFAULT_HEIGHT = 720
  DEFAULT_START_Y = 636

@dataclass SegmentDef:
  seg: str          # "flat" | "ramp" | "gap"
  len: int          # pixel length > 0
  rise: int         # ramp only, default 0
  id: str           # unique identifier

@dataclass ProfileData:
  width: int
  height: int
  start_y: int
  segments: list[SegmentDef]

class ProfileParser:
  @staticmethod
  load(path: str) → ProfileData
    - Read JSON file
    - Validate required fields
    - Apply defaults
    - Parse segments, assign auto-IDs
    - Return ProfileData

class Synthesizer:
  __init__(self, profile: ProfileData)
    - Create TileGrid
    - Initialize cursor state

  synthesize(self) → tuple[TileGrid, list[str]]
    - Pre-validate slopes (warnings + errors)
    - Process each segment
    - Return (grid, pre_warnings)

  _rasterize_flat(self, seg: SegmentDef) → None
  _rasterize_ramp(self, seg: SegmentDef) → None
  _rasterize_gap(self, seg: SegmentDef) → None
  _fill_below(self, start_col: int, end_col: int) → None
  _check_slope_discontinuities(self) → list[str]

def main() → None:
  - argparse CLI
  - Load profile
  - Synthesize
  - Validate (reuse Validator)
  - Build meta (player_start=None override)
  - Write output
```

### `tests/test_profile2stage.py` (~300 lines)

New test file.

```
Import pattern: sys.path.insert(0, tools/) + from profile2stage import ...

class TestProfileParser:
  - test_valid_profile_loads
  - test_missing_track_raises
  - test_defaults_applied
  - test_auto_id_generation
  - test_duplicate_id_raises
  - test_ramp_missing_rise_raises

class TestFlatSegment:
  - test_flat_height_array (all columns = uniform height)
  - test_flat_at_different_y
  - test_flat_interior_fill

class TestRampSegment:
  - test_ramp_ascending (rise < 0)
  - test_ramp_descending (rise > 0)
  - test_ramp_interpolation_accuracy

class TestGapSegment:
  - test_gap_no_tiles
  - test_gap_cursor_advance

class TestCursorState:
  - test_cursor_y_advances_through_ramp
  - test_cursor_y_unchanged_after_flat
  - test_cursor_y_unchanged_after_gap
  - test_multi_segment_cursor_threading

class TestSlopeValidation:
  - test_slope_warning_above_30deg
  - test_slope_error_above_45deg
  - test_slope_ok_below_30deg
  - test_discontinuity_warning

class TestIntegration:
  - test_end_to_end_output_files
  - test_output_json_parseable
  - test_meta_player_start_null
  - test_entities_empty_list
```

## Files Modified

None. This ticket is additive only.

## Module Boundaries

```
tools/profile2stage.py
  ├── imports from → tools/svg2stage.py (TileGrid, TileData, Validator, StageWriter, ...)
  └── standalone CLI entry point

tests/test_profile2stage.py
  ├── imports from → tools/profile2stage.py
  └── imports from → tools/svg2stage.py (constants for assertions)
```

## Interface Contracts

**ProfileParser.load(path) → ProfileData**
- Input: path to `.profile.json`
- Output: validated ProfileData
- Raises: `ValueError` on invalid profile, `FileNotFoundError` on missing file

**Synthesizer(profile).synthesize() → (TileGrid, list[str])**
- Input: ProfileData
- Output: populated grid + list of pre-rasterization warning strings
- Raises: `ValueError` if slope ratio > 1.0 (unpassable)

**CLI exit codes:**
- 0: success
- 1: file not found or invalid profile
- 2: unpassable slope error

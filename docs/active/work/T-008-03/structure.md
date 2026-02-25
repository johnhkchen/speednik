# T-008-03 Structure: Elemental Terrain Tests

## Files

### Created

- `tests/test_elementals.py` — all elemental terrain tests.

### Not Modified

No existing files are modified. This ticket adds one new test file only.

## Module Layout: `tests/test_elementals.py`

```
# Docstring
# Imports
# Constants / helpers

_deg_to_byte(deg) -> int
_diag(result, label) -> str          # builds diagnostic string for assertion msgs

GROUND_ROW = 10
LOOP_GROUND_ROW = 40
START_X = 48.0
FRAMES = 600

# --- Ground Adhesion ---
test_idle_on_flat()
test_idle_on_slope()
test_idle_on_tile_boundary()

# --- Walkability Threshold ---
test_walk_climbs_gentle_ramp()
test_walk_stalls_on_steep_ramp()
test_walkability_sweep(angle_deg)       # @pytest.mark.parametrize 0–90 step 5

# --- Speed Gates ---
test_spindash_clears_steep_ramp()
test_walk_blocked_by_steep_ramp()

# --- Loop Traversal ---
test_loop_spindash_traversal()
test_loop_no_ramps_blocked()
test_loop_walk_speed_fails()

# --- Gap Clearing ---
test_gap_clearing(gap_tiles, strategy_factory, should_clear)  # parametrized
```

## Imports

```python
import pytest

from speednik.terrain import TILE_SIZE

from tests.grids import build_flat, build_gap, build_loop, build_ramp, build_slope
from tests.harness import (
    ScenarioResult,
    hold_right,
    hold_right_jump,
    idle,
    run_scenario,
    spindash_right,
)
```

## Internal Helpers

### `_deg_to_byte(deg: float) -> int`

Convert degrees to byte angle: `round(deg * 256 / 360) % 256`.

### `_diag(result: ScenarioResult, label: str) -> str`

Builds a diagnostic string for assertion messages:
```
"{label} | x={final.x:.1f} y={final.y:.1f} gspd={final.ground_speed:.2f}
 angle={final.angle} on_ground={final.on_ground} q={final.quadrant}
 stuck={stuck_at()}"
```

## Constants

- `GROUND_ROW = 10` — surface at y=160 for standard tests.
- `LOOP_GROUND_ROW = 40` — surface at y=640 for loop tests.
- `START_X = 48.0` — 3 tiles into approach.
- `FRAMES = 600` — default simulation length.
- `WALKABLE_CEILING = 20` — degrees guaranteed walkable.
- `UNWALKABLE_FLOOR = 50` — degrees guaranteed unwalkable.

## Test Details

### Ground Adhesion

All three: build grid, run `idle()` for FRAMES, assert all `on_ground`, Y stable.
Slope test uses `build_slope(5, 15, _deg_to_byte(20), GROUND_ROW)`.
Tile boundary test starts at `x = 5 * TILE_SIZE` (exactly on boundary).

### Walkability Sweep

`@pytest.mark.parametrize("angle_deg", range(0, 91, 5))`

Each iteration: `build_ramp(5, 10, 0, _deg_to_byte(angle_deg), GROUND_ROW)`.
Run `hold_right()` for 300 frames (shorter — just need to see progress/stall).

Classification:
- angle_deg <= WALKABLE_CEILING → assert not stuck
- angle_deg >= UNWALKABLE_FLOOR → assert stuck
- Between → no assertion, just documenting transition zone

### Speed Gates

Both use same ramp: `build_ramp(5, 10, 0, _deg_to_byte(50), GROUND_ROW)`.
- Spindash: `spindash_right()`, assert final X past ramp, not stuck.
- Walk: `hold_right()`, assert stuck.

### Loop Traversal

Loop geometry with approach=10, radius=128:
- `loop_exit_x = (10 * TILE_SIZE) + 128 + (2 * 128) + 128 = 160 + 512 = 672`
- Actually: approach_px=160, ramp_radius=128, loop_diameter=256.
  loop_exit ≈ 160 + 128 + 256 + 128 = 672px.

Assertions compare final.x against computed loop_exit_x.

### Gap Clearing

`build_gap(10, gap_tiles, 10, GROUND_ROW)`.
Landing starts at `(10 + gap_tiles) * TILE_SIZE`.
- should_clear=True: final.x > landing_start_x
- should_clear=False: final.x < landing_start_x

Strategy factories are passed as callables and invoked within the test.

## Public Interface

None — this is a test file only. No exports consumed by other modules.

## Ordering

Single file, no ordering dependencies. All tests independent.

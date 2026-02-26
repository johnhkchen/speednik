# Progress — T-012-06: Composable Mechanic Probes

## Completed

### Step 1: Scaffold test file
- Created `tests/test_mechanic_probes.py` with infrastructure
- FrameSnap, ProbeResult dataclasses
- `_run_mechanic_probe()` probe runner (supports synthetic grids + entity injection)
- Strategy helpers: `_hold_right`, `_make_spindash_strategy`, `_make_gap_jump_strategy`

### Step 2: Loop probes
- Parameterized across radii [32, 48, 64, 96]
- All 4 radii fail `test_loop_traverses_all_quadrants` — player never reaches ceiling quadrant (2)
- Radii 32/48 pass exit tests; radii 64/96 fail (player overshoots exit)
- Filed T-012-06-BUG-01 (no ceiling traversal) and T-012-06-BUG-02 (large loop exit overshoot)
- All failing tests marked with `@pytest.mark.xfail(strict=True)`

### Step 3: Ramp probes
- Parameterized across end_angles [10, 20, 30, 40, 50]
- All pass — no wall-slam velocity zeroing, player advances past ramp region

### Step 4: Gap probes
- Parameterized across gap_tiles [2, 3, 4, 5]
- All pass — running jump clears all tested gap widths
- Required careful strategy design: build speed first, jump near edge, release jump

### Step 5: Spring probe
- All 3 tests pass: event fires, height matches impulse, player lands
- Required wider grid (200 tiles) so player has ground for landing after arc

### Step 6: Slope adhesion probes
- Angles 0-30 pass (100% on_ground in slope region)
- Angles 35, 40, 45 fail (~50% on_ground) — adhesion limit at byte angle ~35
- Filed T-012-06-BUG-03 (slope adhesion fails at steep angles)

### Step 7: Full suite run
- `uv run pytest tests/test_mechanic_probes.py -v`: 28 passed, 11 xfailed

### Step 8: Bug tickets filed
- T-012-06-BUG-01: Synthetic loops not fully traversable (all radii)
- T-012-06-BUG-02: Large loop exit overshoot (radii 64/96)
- T-012-06-BUG-03: Slope adhesion fails at byte angle >= 35

## Deviations from Plan

1. Player start_y: needed `GROUND_ROW * TILE_SIZE - 20` (not `GROUND_ROW * TILE_SIZE`)
   for proper on_ground positioning.
2. Gap strategy: original jump-on-landing approach jumped too early (before building speed).
   Changed to position-triggered jump near gap edge with jump release for shorter arc.
3. Spring grid width: increased from 30 to 200 tiles — player flies far during spring arc
   with air acceleration.

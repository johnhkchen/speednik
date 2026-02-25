# T-007-03 Plan: profile2stage Loop Entry/Exit Ramps

## Step 1: Update segment length in parser

**File:** `tools/profile2stage.py`, line 135
**Change:** `seg_len = 2 * radius` → `seg_len = 4 * radius`
**Verify:** Existing parser tests still pass (loop parsed correctly test will need expected len update)

## Step 2: Rewrite `_rasterize_loop` with ramp generation

**File:** `tools/profile2stage.py`, lines 627–672
**Change:** Replace the method with expanded version that:

1. Computes r_ramp = radius
2. Computes entry_start, loop_start, loop_end, exit_end, cx, cy, ground_y
3. Defines local `_arc_surface_y(px, arc_cx)` helper
4. Defines local `_ramp_angle(px, arc_cx)` helper
5. Entry ramp loop: for px in [entry_start, loop_start), compute surface y and angle, call `_set_surface_pixel`, then `_fill_below(entry_start, loop_start)`
6. Loop circle: existing logic with adjusted start_col/end_col using loop_start/loop_end and shifted cx
7. Exit ramp loop: for px in [loop_end, exit_end), compute surface y and angle, call `_set_surface_pixel`, then `_fill_below(loop_end, exit_end)`
8. Update cursor_x to exit_end

**Verify:** `uv run pytest tests/test_profile2stage.py::TestLoopParser -x` (parser tests)

## Step 3: Update existing loop tests

**File:** `tests/test_profile2stage.py`

Changes needed:

a. `_make_loop_profile`: Update width calculation
   - `total = flat_before + 4 * radius + flat_after`

b. `test_loop_parsed_correctly`: Update expected len
   - `assert seg.len == 4 * radius` (was `2 * radius`)

c. `test_loop_cursor_advance`:
   - `assert synth.cursor_x == 4 * radius`
   - Update width to 512 or `4 * radius + margin`

d. `test_loop_interior_hollow`:
   - `cx = 128 + 2 * radius` (was `128 + radius`)
   - `cy = 400 - radius` (unchanged)

e. `test_loop_upper_lower_solidity`:
   - Same center shift as above

f. `test_loop_ground_fill`:
   - Update `loop_cx_tx` calculation for shifted center

g. `test_loop_end_to_end`:
   - Width 512 = 128 + 256 + 128 = 512. With radius=64: 128 + 4*64 + 128 = 512. Exact fit — no change needed if we're careful.

**Verify:** `uv run pytest tests/test_profile2stage.py::TestLoopSegment -x`

## Step 4: Add new ramp-specific tests

**File:** `tests/test_profile2stage.py`

Add to `TestLoopSegment` class:

a. `test_loop_ramp_tiles_exist`:
   - Create loop profile with flat_before=128, radius=64
   - Entry ramp spans px [128, 192), exit ramp spans px [320, 384)
   - Check that SURFACE_SOLID tiles exist in entry ramp tile columns
   - Check that SURFACE_SOLID tiles exist in exit ramp tile columns

b. `test_loop_ramp_angles_progress`:
   - Collect angles from entry ramp tiles
   - Verify they're not all identical (angles vary as arc curves)

c. `test_loop_ramp_no_gaps_at_junction`:
   - Check the tile column at the entry ramp / loop boundary
   - Verify validator produces no "Impassable gap" errors (already covered by test_loop_no_gap_errors, but explicit boundary check is valuable)

d. `test_loop_ramp_surface_solid`:
   - All tiles in entry ramp region should be SURFACE_SOLID
   - None should have is_loop_upper = True

e. `test_loop_cursor_includes_ramps`:
   - Single loop segment with radius=64
   - cursor_x == 256 (4 * 64)
   - cursor_y unchanged
   - cursor_slope == 0.0

**Verify:** `uv run pytest tests/test_profile2stage.py::TestLoopSegment -x`

## Step 5: Full test suite

**Verify:** `uv run pytest tests/test_profile2stage.py -x`

Ensure no regressions in:
- TestProfileParser (parser validation tests)
- TestFlatSegment, TestRampSegment, TestGapSegment
- TestWaveSegment, TestHalfpipeSegment
- TestOverlays, TestEntities
- TestEndToEnd

## Testing Strategy

| Test | Type | What it verifies |
|------|------|-----------------|
| test_loop_ramp_tiles_exist | Unit | Ramp tiles generated in correct pixel range |
| test_loop_ramp_angles_progress | Unit | Ramp angle variation (smooth transition) |
| test_loop_ramp_no_gaps_at_junction | Integration | No validator errors at ramp-loop boundary |
| test_loop_ramp_surface_solid | Unit | Ramp tile type and solidity |
| test_loop_cursor_includes_ramps | Unit | Cursor accounts for ramp extent |
| Existing test updates | Regression | Center coordinates, cursor position, widths |

## Risk Mitigation

1. **Float precision at arc boundaries:** Use `max(0, val)` before sqrt to avoid domain errors
2. **Off-by-one at ramp/loop junction:** Entry ramp range is `[entry_start, loop_start)`, loop range is `[loop_start, loop_end)` — no overlap, no gap
3. **Exit ramp range:** `[loop_end, exit_end)` — starts immediately after loop ends
4. **Width overflow:** Profile width must accommodate the expanded loop footprint; test helpers updated accordingly

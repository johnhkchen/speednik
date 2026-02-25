# T-007-03 Progress: profile2stage Loop Entry/Exit Ramps

## Completed

### Step 1: Update segment length in parser
- Changed `seg_len = 2 * radius` → `seg_len = 4 * radius` in `ProfileParser.load()` (line 135)
- Loop segment footprint now includes entry ramp + circle diameter + exit ramp

### Step 2: Rewrite `_rasterize_loop` with ramp generation
- Added quarter-circle entry ramp before loop circle (px range: [cursor_x, cursor_x + r_ramp))
- Added quarter-circle exit ramp after loop circle (px range: [loop_end, exit_end))
- Each ramp uses `_arc_surface_y` local helper: `cy + sqrt(max(0, r_ramp² - dx²))`
- Angles computed via finite difference: `_ramp_angle` helper
- Ramp tiles placed via `_set_surface_pixel` (SURFACE_SOLID)
- Per-pixel `_fill_column_below` for ground fill under steep arc sections

**Deviation from plan:** Originally planned to use `_fill_below(start, end)` for ramp ground fill. Testing revealed that steep arc sections span multiple tile rows per tile column, leaving height-array gaps within surface tiles. Switched to per-pixel `_fill_column_below` calls (same pattern as loop circle rasterization) to ensure every pixel column is solidly filled from the surface down. This eliminated all validator gap errors.

### Step 3: Update existing loop tests
- `_make_loop_profile`: width calculation uses `4 * radius`
- `test_loop_parsed_correctly`: expected len changed to 256 (4*64)
- `test_loop_no_len_required`: expected len changed to 256
- `test_loop_radius_warning_below_64`: SegmentDef len updated to 192 (4*48)
- `test_loop_cursor_advance`: expected cursor_x changed to `4 * radius`
- `test_loop_interior_hollow`: center shifted to `128 + 2 * radius`
- `test_loop_upper_lower_solidity`: center shifted to `128 + 2 * radius`
- `test_loop_ground_fill`: center tile column updated for shifted center

### Step 4: Add new ramp-specific tests
- `test_loop_ramp_tiles_exist`: verifies SURFACE_SOLID tiles in entry/exit ramp regions
- `test_loop_ramp_angles_progress`: verifies ramp angles vary (not all identical)
- `test_loop_ramp_no_gaps_at_junction`: verifies no validator gaps at ramp-loop boundaries
- `test_loop_ramp_surface_solid`: verifies ramp tiles are SURFACE_SOLID, not SURFACE_LOOP
- `test_loop_cursor_includes_ramps`: verifies cursor advances by 4*radius

### Step 5: Full test suite
- All 88 tests pass (83 updated existing + 5 new)
- No regressions in any other test class

## Remaining
None. All plan steps complete.

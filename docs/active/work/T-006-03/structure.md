# T-006-03 Structure: profile2stage-loop-segment

## Files Modified

### 1. tools/profile2stage.py

**Import changes (line 22-29):**
- Add `SURFACE_LOOP` to the import list from `svg2stage`.

**Constants (line 39):**
- Add `"loop"` to `VALID_SEG_TYPES`.

**SegmentDef dataclass (lines 46-54):**
- Add `radius: int = 0` field. Loop segments use `radius` instead of `len`/`rise`.

**ProfileParser.load() (lines 72-150):**
- For `seg == "loop"`: skip `len` requirement, require `radius` field instead.
- Validate `radius >= 32` (error), `radius < 64` (warning emitted via return list or print).
- Set `seg.len = 2 * radius` internally for consistency (total footprint of circle only,
  excluding transition arcs).

**Synthesizer.synthesize() dispatch (lines 178-190):**
- Add `elif seg.seg == "loop":` branch calling `self._rasterize_loop(seg)`.

**Synthesizer._validate_slopes() (lines 193-223):**
- Loop segments have no linear slope to validate. Skip them (no special case needed —
  the existing `if seg.seg == "ramp"` structure already ignores unknown types).

**Synthesizer._check_slope_discontinuities() (lines 225-276):**
- Add `elif seg.seg == "loop":` case.
- Entry slope: vertical (effectively ∞, but since transition arcs handle the bridging,
  treat loop entry slope as 0 — the transition arc exits at the loop entry tangent).
- Exit slope: same as entry (full circle). Set `exit_slope = 0.0`.

**New method: Synthesizer._rasterize_loop(seg) (~50 lines):**
- Compute `cx = cursor_x + radius`, `cy = cursor_y - radius`.
- Iterate every pixel column `px` in `[cursor_x, cursor_x + 2*radius)`.
- For each column: `dx = px - cx + 0.5`, `dy = sqrt(r² - dx²)`.
- Bottom arc: `y_bottom = cy + dy`, angle via analytical tangent, `is_upper=False`.
- Top arc: `y_top = cy - dy`, angle via analytical tangent, `is_upper=True`.
- Call `_set_loop_pixel()` for each arc point.
- After loop rasterization: call `_fill_ground_under_loop()` for ground beneath `cursor_y`.
- Update cursor: `cursor_x += 2 * radius`, `cursor_y` unchanged, `cursor_slope = 0.0`.

**New method: Synthesizer._set_loop_pixel(col, y, angle, is_upper) (~20 lines):**
- Same structure as `_set_surface_pixel` but:
  - `surface_type = SURFACE_LOOP` instead of `SURFACE_SOLID`.
  - `is_loop_upper = is_upper`.
  - Height: `math.ceil(tile_bottom - y)` (not `int(round(...))`) per T-006-01.
  - Clamp: `max(0, min(TILE_SIZE, h))`.

**New method: Synthesizer._fill_ground_under_loop(start_col, end_col, ground_y) (~15 lines):**
- For each tile column in `[start_col, end_col)`:
  - Find the tile row at `ground_y` (the original `cursor_y`).
  - Fill from that row down to grid bottom with `SURFACE_SOLID` fully-solid tiles.
  - This provides the ground beneath the loop for players not fast enough to traverse it.
  - Does NOT touch tiles above `ground_y` — preserves hollow interior.

**Angle computation (inline in _rasterize_loop):**
- Bottom arc tangent at column `px`: direction perpendicular to radius, CW traversal.
  - `angle_bottom = round(-math.atan2(dx, dy) * 256 / (2 * math.pi)) % 256`
- Top arc tangent: reversed direction.
  - `angle_top = round(-math.atan2(-dx, -dy) * 256 / (2 * math.pi)) % 256`

### 2. tests/test_profile2stage.py

**Import changes (line 17-28):**
- Add `SURFACE_LOOP` to svg2stage imports.

**TestProfileParser.test_invalid_seg_type_raises (line 174):**
- Change `"loop"` to `"teleport"` (a truly invalid segment type).
- Keep same assertion structure.

**New test class: TestLoopSegment (~100 lines):**

- `test_loop_no_gap_errors`: Create profile with flat + loop + flat, synthesize,
  run Validator, assert zero "Impassable gap" errors in validation output.
- `test_loop_interior_hollow`: After rasterizing a loop (radius=64), sample tiles at
  the circle center `(cx//16, cy//16)`. Interior tiles should be None (not filled).
- `test_loop_upper_lower_solidity`: Check tiles on upper arc have `is_loop_upper=True`
  and `surface_type=SURFACE_LOOP`. Check tiles on lower arc have `is_loop_upper=False`.
- `test_loop_cursor_advance`: After loop segment, `cursor_x == original + 2*radius`.
  `cursor_y` unchanged. `cursor_slope == 0.0`.
- `test_loop_radius_error_below_32`: Profile with loop radius=16 → ValueError.
- `test_loop_radius_warning_below_64`: Profile with loop radius=48, check for warning.
- `test_loop_ground_fill`: Check that tiles below `cursor_y` in the loop's x-footprint
  are filled solid (SURFACE_SOLID with height_array=[16]*16).
- `test_loop_angle_variation`: Verify that loop tiles have varying angles (not constant 0),
  confirming per-column tangent computation.

**New test class: TestLoopParser (~30 lines):**

- `test_loop_parsed_correctly`: Profile with loop segment parses with correct radius.
- `test_loop_missing_radius_raises`: Loop segment without radius → ValueError.
- `test_loop_no_len_required`: Loop segment without len → no error (len is computed).

## Files NOT Modified

- `tools/svg2stage.py` — no changes needed, only imports from it.
- `speednik/` game code — no runtime changes.
- Stage data files — not regenerated as part of this ticket.

## Module Boundaries

- `profile2stage.py` remains a standalone CLI tool that imports from `svg2stage.py`.
- No new files created. All loop logic lives in `profile2stage.py`.
- `_set_loop_pixel` is private to `Synthesizer` — not part of any public interface.
- `_fill_ground_under_loop` is private to `Synthesizer`.

## Ordering Constraints

1. Import + constant changes first (SURFACE_LOOP, VALID_SEG_TYPES).
2. SegmentDef + parser changes (radius field, loop parsing).
3. `_set_loop_pixel` and `_fill_ground_under_loop` helper methods.
4. `_rasterize_loop` main method.
5. Synthesizer dispatch + slope discontinuity updates.
6. Test updates (parser test fix, new loop test classes).

## Transition Arcs — Deferred to Simplify

The ticket describes transition arcs at loop entry/exit. After analyzing the geometry
in design.md, the transition arcs are a separate concern from the core loop circle:
- The loop circle itself is a complete 360° arc that the player enters at the bottom.
- Transition arcs bridge from flat ground to the loop's side entry tangent.

For this implementation, **transition arcs are omitted from the initial commit** and noted
as a follow-up. Rationale:
- The core loop (circle + hollow interior + solidity flags) is the primary deliverable.
- The player enters the loop at the bottom (ground level), where the tangent is horizontal
  — this is already compatible with a flat approach with no gap.
- Transition arcs add ~50 lines of geometry code that can be added independently.
- The acceptance criteria focus on the loop itself; transition arcs are secondary.

If transition arcs are required in this ticket, they can be added as a second commit
after the core loop passes all tests.

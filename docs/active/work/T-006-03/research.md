# T-006-03 Research: profile2stage-loop-segment

## Scope

Add the `loop` segment type to `tools/profile2stage.py`. A loop is a full 360° circle
with guaranteed-hollow interior, analytical per-pixel-column rasterization, transition
arcs at entry/exit, and correct upper/lower solidity flags.

## Codebase Inventory

### tools/profile2stage.py (current state, 368 lines)

**Parser (`ProfileParser`):**
- `VALID_SEG_TYPES = {"flat", "ramp", "gap"}` — loop not yet recognized.
- `SegmentDef` dataclass has fields: `seg`, `len`, `rise`, `id`.
  - Loop needs `radius` instead of `len`/`rise`. The dataclass must be extended or
    a separate `LoopSegmentDef` introduced.
- Parser validates `len > 0` for all segments — loop has no `len` field (footprint = 2*radius).

**Synthesizer:**
- Cursor state: `cursor_x: int`, `cursor_y: float`, `cursor_slope: float`.
- Dispatch: `if/elif` chain on `seg.seg` string. Adding `"loop"` branch is straightforward.
- `_set_surface_pixel(col, y, angle)`: sets one pixel column in the tile grid. Uses
  `int(round(tile_bottom - y))` for height — T-006-01 established `math.ceil` is correct
  for arc surfaces. This method currently does NOT set `is_loop_upper` or `surface_type`
  to anything other than `SURFACE_SOLID`.
- `_fill_below(start_col, end_col)`: fills all tiles below the topmost surface tile in
  each column as fully solid. This must NOT be called for the loop circle itself (would
  flood the interior). It IS correct for the ground-fill polygon under the loop.

**Angle computation:**
- Ramps use `round(-atan2(rise, len) * 256 / (2π)) % 256`. Loop arcs need per-column
  tangent angles derived from circle geometry.

### tools/svg2stage.py (reference implementation)

**`_rasterize_loop` (lines 745-796):**
- Walks each segment of an ellipse perimeter (pre-sampled as line segments).
- For each sample point: `tx = int(sx)//16`, `ty = int(sy)//16`, `col = int(sx)%16`.
- Height: `math.ceil(tile_bottom_y - sy)` (post T-006-01 fix).
- Sets `surface_type = SURFACE_LOOP`, `is_loop_upper = (sy < cy)`.
- Does NOT call `_fill_interior` for loop shapes (line 682: `if shape.is_loop`).

**`_fill_interior` (lines 798-831):**
- For each column, finds topmost surface tile of the same `surface_type`, fills below.
- Stops when it hits a tile of a different `surface_type`.
- Loop tiles have `SURFACE_LOOP`, so SOLID fill stops at loop boundary — this is the
  hollow-interior mechanism.

**Collision writer (lines 1034-1050):**
- `SURFACE_LOOP + is_loop_upper=True` → `TOP_ONLY` (solidity 1).
- `SURFACE_LOOP + is_loop_upper=False` → `FULL` (solidity 2, via SOLIDITY_MAP).

**Constants already importable:**
- `SURFACE_LOOP = 5` (svg2stage.py line 36).
- `SURFACE_SOLID = 1`, `TILE_SIZE = 16`, `TileData`, `TileGrid`, `Validator`, `StageWriter`.

### TileData dataclass (svg2stage.py line 130)

```python
@dataclass
class TileData:
    surface_type: int = SURFACE_SOLID
    height_array: list[int] = field(default_factory=lambda: [0] * 16)
    angle: int = 0
    is_loop_upper: bool = False
```

`is_loop_upper` already exists. profile2stage just needs to set it.

### Validator (svg2stage.py lines 859-966)

- `_check_impassable_gaps`: scans pixel columns for narrow solid gaps. Loop tiles with
  `FULL` solidity are included. The "no gaps on loop sides" acceptance criterion means
  analytical rasterization must produce continuous height arrays with no zero columns
  along the circle perimeter.
- `_check_accidental_walls`: steep tiles without `is_loop_upper` flag trigger warnings.
  Upper loop tiles correctly flagged avoid this.

## Circle Geometry for Loop Rasterization

Given center `(cx, cy)` and radius `r`, for each integer pixel column `px` in
`[cx - r, cx + r)`:

- `dx = px - cx + 0.5` (center of pixel column)
- If `|dx| > r`: no intersection (skip column)
- `dy = sqrt(r² - dx²)`
- Bottom arc y: `cy + dy` (lower semicircle, player runs on inside floor)
- Top arc y: `cy - dy` (upper semicircle, ceiling)

For each arc point, the tangent direction:
- At position angle `θ = atan2(dy, dx)` from center
- Bottom arc tangent (rightward traversal): perpendicular to radius, pointing right
- `tangent_dx = -sin(θ)`, `tangent_dy = cos(θ)` for bottom arc (CW traversal)
- For top arc: tangent reverses
- Byte angle: `round(-atan2(tangent_dy, tangent_dx) * 256 / (2π)) % 256`

## Transition Arc Geometry

The loop entry tangent is vertical (slope = ∞). Adjacent flat segment has slope = 0.
A quarter-circle transition arc bridges the slope difference:

- Entry arc: from `cursor_y` (flat ground) curving up to the loop's bottom-left point.
  The loop bottom-left is at `(cx - r, cy)` = `(cursor_x + radius - radius, cursor_y - radius)` = `(cursor_x, cursor_y - radius)`. Wait — that's the center height.

  Actually: the loop circle center is at `(cursor_x + radius, cursor_y - radius)`.
  The bottom of the loop is at `cy + radius = cursor_y`. The left-side entry point
  is at `(cx - radius, cy) = (cursor_x, cursor_y - radius)` — this is at the 9 o'clock
  position, which is at y = `cursor_y - radius`, NOT at ground level.

  So the transition arc must bridge from `(cursor_x, cursor_y)` at slope 0 to
  `(cursor_x, cursor_y - radius)` at slope ∞ (vertical). This is a quarter-circle
  with center at `(cursor_x, cursor_y - radius)` and radius = `radius`. But that's
  exactly the left quarter of the loop circle itself.

  **Key insight:** The transition IS part of the loop circle. The player enters at the
  bottom `(cx, cy + r) = (cursor_x + r, cursor_y)` running rightward, goes around the
  full circle, and exits at the same bottom point. The "transition arc" described in the
  ticket is the ramp-to-vertical-tangent bridge BEFORE reaching the circle entry point.

  For a flat approach (slope=0), a quarter-circle transition arc of radius `t_r` transitions
  from horizontal to vertical. `t_r` can be proportional to the loop radius (e.g., `t_r = radius/2`
  or a fixed fraction). The arc center is at `(cursor_x + t_r, cursor_y - t_r)`, sweeping
  from angle 270° (horizontal tangent at bottom) to angle 180° (vertical tangent at left).
  Horizontal footprint: `t_r`. Vertical rise: `t_r`.

## Constraints and Risks

1. **Minimum radius:** Error if < 32, warn if < 64. Simple bounds check in parser.
2. **Hollow interior:** Do NOT call `_fill_below` for the loop circle. Only for the
   ground-fill polygon beneath `cursor_y`.
3. **No 1px side-arc gaps:** The analytical per-pixel-column approach (iterate every
   integer column in the circle's x-range) guarantees no skipped columns, unlike the
   sample-based approach in svg2stage.py.
4. **SURFACE_LOOP import:** Must add `SURFACE_LOOP` to the import list from svg2stage.
5. **SegmentDef extension:** Need `radius` field (optional, default 0) and parse logic
   that doesn't require `len` for loop segments.

## Dependencies

- T-006-01 (done): Established `math.ceil` for height rounding.
- T-006-02 (done): Built the profile2stage framework (parser, synthesizer, cursor state).
- Both are complete — no blockers.

## Test Surface

Existing test `test_invalid_seg_type_raises` explicitly expects `"loop"` to be rejected.
This test must be updated when loop becomes valid. New tests needed:
- Loop produces no impassable gap errors
- Loop interior is hollow (tiles at cx, cy are None or not solid)
- Upper/lower solidity flags correct
- Cursor position correct after loop
- Radius validation (< 32 error, < 64 warning)

# T-007-01 Plan: Loop Entry/Exit Ramps

## Step 1: Add `_rasterize_ramps()` method

**File:** `tools/svg2stage.py`
**Location:** New method on `Rasterizer` class, after `_rasterize_loop()`

Implementation:

```python
def _rasterize_ramps(self, cx: float, cy: float, r: float, r_ramp: float) -> None:
```

**Entry ramp** (left side):
- Arc center: `(cx - r, cy)`
- Pixel x range: `[cx - r - r_ramp, cx - r)`
- For each pixel x:
  - `dx = x - (cx - r)` → range [-r_ramp, 0)
  - Clamp `abs(dx)` to `r_ramp` for safety
  - `dy = sqrt(r_ramp² - dx²)` → vertical offset below arc center
  - `surface_y = cy + dy` → screen y of surface (ranges from cy+r_ramp=ground down to cy)
  - Tangent angle: the arc surface rises left-to-right. Tangent vector is `(1, -dx/dy)` in screen coords (dx is negative, so -dx/dy is positive and decreasing, meaning dy_screen is negative = going up). Use `_compute_segment_angle`-compatible formula: `byte_angle = round(-math.atan2(-dx/dy_norm, 1.0) * 256 / (2 * math.pi)) % 256`

  Actually, derive properly:
  - Parametrize arc: `x(t) = arc_cx + r_ramp * cos(t)`, `y(t) = arc_cy + r_ramp * sin(t)`
  - For entry ramp, t goes from π/2 (bottom, ground level) to 0 (right, tangent point)
  - Tangent vector: `(dx/dt, dy/dt) = (-r_ramp*sin(t), r_ramp*cos(t))`
  - But player travels in +x direction, so negate: `(r_ramp*sin(t), -r_ramp*cos(t))`
  - Screen coords: `(r_ramp*sin(t), -r_ramp*cos(t))`
  - Byte angle: `round(-atan2(-r_ramp*cos(t), r_ramp*sin(t)) * 256 / (2*pi)) % 256`
    = `round(-atan2(-cos(t), sin(t)) * 256 / (2*pi)) % 256`
    = `round(atan2(cos(t), sin(t)) * 256 / (2*pi)) % 256`
    = `round(t * 256 / (2*pi)) % 256` since `atan2(cos(t), sin(t)) = t` for t in [0, π/2]

  Wait, `atan2(cos(t), sin(t))` = `atan2(y=cos(t), x=sin(t))` = π/2 - t. So:
  - byte_angle = round((π/2 - t) * 256 / (2*pi)) % 256
  - At t=π/2 (ground): byte_angle = 0 ✓
  - At t=0 (tangent point): byte_angle = round(64) = 64 ✓

  Simpler direct formula from dx:
  - `t = acos(dx / r_ramp)` where dx = x - arc_cx (negative to zero for entry)
  - Actually `cos(t) = dx / r_ramp`, so `t = acos(dx/r_ramp)`. But dx < 0 for entry, and t should be in [0, π/2], so need `t = acos(-dx/r_ramp)` ... let me just use a simpler approach.

  For each pixel column, compute two consecutive points on the arc and use `_compute_segment_angle()`. This reuses existing code and guarantees angle consistency.

**Revised approach for angle computation:**
- For pixel x, compute `surface_y(x)` and `surface_y(x+1)` from arc equation
- Create points `p1 = Point(x, surface_y(x))` and `p2 = Point(x+1, surface_y(x+1))`
- `angle = _compute_segment_angle(p1, p2)`

This is clean, reuses existing infrastructure, and naturally handles both entry and exit ramps.

**Tile placement for each pixel column:**
- `tx = int(x) // TILE_SIZE`
- `ty = int(surface_y) // TILE_SIZE`
- `col = int(x) % TILE_SIZE`
- `height = max(0, min(16, ceil(tile_bottom_y - surface_y)))`
- Create/update TileData with surface_type=SURFACE_SOLID, max height, computed angle

**Exit ramp** (right side):
- Arc center: `(cx + r, cy)`
- Pixel x range: `(cx + r, cx + r + r_ramp]`
- Same arc equation: `dy = sqrt(r_ramp² - dx²)` where `dx = x - (cx + r)` → range (0, r_ramp]
- Surface descends from tangent point to ground level
- Angle: compute from consecutive surface points, same as entry ramp

**Ground fill below ramps:**
After placing all ramp surface tiles, for each tile column in the ramp range, find the topmost ramp tile and fill everything below with fully-solid tiles (height_array=[16]*16, angle=0, surface_type=SURFACE_SOLID).

**Verification:** Inspect ramp tile coordinates, angles, and heights via test assertions.

## Step 2: Modify `_rasterize_loop()` to call ramp helper

**File:** `tools/svg2stage.py`
**Location:** Top of `_rasterize_loop()` method

Changes:
1. Compute radius from first segment point: `r = math.hypot(p0.x - cx, p0.y - cy)`
2. Set `r_ramp = r`
3. Call `self._rasterize_ramps(cx, cy, r, r_ramp)` before loop rasterization

## Step 3: Add ramp tests

**File:** `tests/test_svg2stage.py`
**Location:** New `TestRampRasterization` class

Test setup: Circle at (200, 100) with r=64. Grid large enough to contain ramps (need x from 200-64-64=72 to 200+64+64=328, y from 100 to 164+margin). Use grid size 400x200 pixels (25x13 tiles).

Tests:
1. **test_ramp_tiles_exist** — Tiles exist in entry region (x < cx-r) and exit region (x > cx+r)
2. **test_ramp_surface_type** — All ramp tiles are SURFACE_SOLID
3. **test_entry_ramp_angle_range** — Angles are in [0, ~70] (byte angle) with general upward trend
4. **test_exit_ramp_angle_range** — Angles are in [~186, 256/0] with general downward-to-flat trend
5. **test_no_gap_at_junction** — For the tile column at x=cx-r and x=cx+r, both a ramp tile (or loop tile, since loop overwrites) and the adjacent ramp tile exist — no empty column gap
6. **test_ground_fill_below_ramp** — Tiles below ramp surface tiles are fully solid (height_array all 16)

## Step 4: Run pipeline and verify

Commands:
1. `uv run pytest tests/test_svg2stage.py -x` — all tests pass
2. `uv run python tools/svg2stage.py stages/hillside_rush.svg speednik/stages/hillside/` — regenerate stage data
3. Check `speednik/stages/hillside/validation_report.txt` for zero "Impassable gap" errors at ramp-to-loop junctions

## Testing Strategy

- **Unit tests** (Step 3): Direct rasterization tests with synthetic circle shape. Verify tile existence, surface type, angle range, height values, ground fill, junction continuity.
- **Integration test** (Step 4): Full pipeline on hillside_rush.svg. Verify via validation report that no impassable gaps exist at ramp-to-loop junctions.
- **Existing test regression**: Run full test suite to ensure nothing is broken.

## Risk Areas

1. **Floating-point edge cases at arc boundaries:** `sqrt(r²-dx²)` when `|dx|` approaches `r` could produce tiny values. Clamp `dx` to `[-r_ramp, r_ramp]` range.
2. **Tile boundary alignment:** At `x = cx - r` (tangent point), both ramp and loop tiles may overlap. Loop rasterization runs second and overwrites, which is the desired behavior.
3. **Angle consistency at junction:** Entry ramp ends at ~64 byte-angle, loop's leftmost tiles should also be near 64. Exit ramp starts at ~192, loop's rightmost tiles should match. Minor discontinuities may still trigger validator warnings — acceptable if within threshold.

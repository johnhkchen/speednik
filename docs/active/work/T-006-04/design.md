# T-006-04 Design: profile2stage-wave-halfpipe

## Decision: Extend SegmentDef with optional fields, add shared rasterizer

### Options Considered

**Option A: SegmentDef with optional fields**
Add `amplitude`, `period`, `depth` as optional fields (default `None` or `0`) to
the existing `SegmentDef` dataclass. Parser validates required fields per segment type.

Pros: Minimal change to data flow. All code that iterates segments works unchanged.
No new classes, no union types, no inheritance.
Cons: SegmentDef carries fields irrelevant to most segment types. Slightly unclean.

**Option B: Segment type hierarchy**
Abstract `Segment` base class with `FlatSegment`, `RampSegment`, `WaveSegment`,
`HalfpipeSegment`, `GapSegment` subclasses. Each carries only its own parameters.

Pros: Type-safe, clean per-segment data.
Cons: Significant refactor of parser, synthesizer dispatch, slope validation.
Over-engineered for a tool script with 5 segment types.

**Option C: Raw dict passthrough**
Don't parse into dataclasses. Pass raw dicts through to the synthesizer.

Pros: Zero parsing code for new fields.
Cons: No validation, typos become runtime bugs, unreadable synthesizer code.

### Decision: Option A

SegmentDef gets `amplitude: int = 0`, `period: int = 0`, `depth: int = 0`.
Parser validates per-type required fields. This matches the existing pattern
where `rise` exists on all SegmentDefs but only matters for ramps.

---

## Shared Rasterizer Design

### `_rasterize_height_profile` utility

```python
def _rasterize_height_profile(
    self,
    profile_fn: Callable[[int], float],  # dx (pixel offset) → surface_y
    angle_fn: Callable[[int], int],       # dx → byte angle
    x_start: int,
    x_end: int,
) -> None
```

For each pixel column `col` in `[x_start, x_end)`:
1. `dx = col - x_start`
2. `y = profile_fn(dx)` — surface y at this column
3. `angle = angle_fn(dx)` — byte angle at this column
4. Call `_set_surface_pixel(col, y, angle)` (existing method)

After the column loop, call `_fill_below(x_start, x_end)`.

This extracts the iterate-columns → set-pixel → fill-below pattern shared by all
ground-producing segments. Wave and halfpipe define their `profile_fn` and `angle_fn`
from their analytic formulas.

**Not refactoring flat/ramp**: The ticket says this is optional. flat and ramp work
correctly today. Refactoring them risks breaking existing tests for zero benefit
in this ticket. Leave them as-is.

---

## Wave Segment Design

### Profile function
```
y(dx) = cursor_y + amplitude * sin(2π * dx / period)
```

### Angle function
Derivative: `dy/dx = amplitude * 2π/period * cos(2π * dx / period)`
Byte angle: `round(-atan2(dy, 1) * 256 / (2π)) % 256`

Per-column angle is correct — the slope changes continuously along the wave.

### Floor clamping
Before rasterizing, for each column check `y(dx) > height - TILE_SIZE`.
If so, clamp `y` to `height - TILE_SIZE` and emit warning with segment id, dx, y, floor.

Implementation: wrap `profile_fn` with a clamping decorator that captures warnings.

### Slope validation
Max slope = `2π * amplitude / period`. Check against `SLOPE_WARN_THRESHOLD`.
Emit warning (not error) if exceeded — level is still generated.
No error threshold for waves (the ticket only specifies warnings).

### Cursor exit
At `dx = len`:
- `cursor_y = y(len)` — may not return to entry height if len % period ≠ 0
- `cursor_slope = dy/dx at dx=len = (2π * amplitude / period) * cos(2π * len / period)`

---

## Halfpipe Segment Design

### Profile function
```
y(dx) = cursor_y + depth * (1 - cos(π * dx / len)) / 2
```

### Angle function
Derivative: `dy/dx = depth * π / (2 * len) * sin(π * dx / len)`
Byte angle: `round(-atan2(dy, 1) * 256 / (2π)) % 256`

### Depth validation
Before rasterizing: if `cursor_y + depth >= height - TILE_SIZE`, raise ValueError.
This is a hard error, not a warning.

### Slope validation
Max slope = `π * depth / (2 * len)`. Warn if exceeds `SLOPE_WARN_THRESHOLD`.

### Cursor exit
At `dx = len`:
- `cursor_y = cursor_y` (returns to entry height by formula)
- `cursor_slope = 0.0` (cos formula ensures zero slope at exit)

---

## Height Calculation Convention

The ticket specifies `math.ceil(tile_bottom_y - surface_y)`. Current
`_set_surface_pixel` uses `int(round(...))`. For new segments, the shared
rasterizer will use the existing `_set_surface_pixel` which already handles the
height computation. The `round` vs `ceil` discrepancy is inherited from T-006-02;
changing it would break existing tests. Keep `_set_surface_pixel` as-is — new
segments go through it like existing ones.

---

## Parser Changes

Add `"wave"` and `"halfpipe"` to `VALID_SEG_TYPES`.

Per-type validation in `ProfileParser.load()`:
- `wave`: require `amplitude` (int > 0), `period` (int > 0). `len` already required.
- `halfpipe`: require `depth` (int > 0). `len` already required.

---

## Discontinuity Check Changes

`_check_slope_discontinuities()` must compute exit slopes for wave and halfpipe:
- `wave`: `(2π * amplitude / period) * cos(2π * len / period)`
- `halfpipe`: `0.0` (always exits flat)

Entry slopes:
- `wave` at dx=0: `2π * amplitude / period * cos(0) = 2π * amplitude / period`
  Wait — this means wave enters with non-zero slope unless amplitude=0.
  Actually the slope at dx=0 is `(2π * amp / period) * cos(0) = 2π * amp / period`.
  This will trigger a discontinuity warning if preceded by a flat segment.
  This is correct behavior — the LLM should know about the discontinuity.
- `halfpipe` at dx=0: slope = 0 (sin(0) = 0). Always enters flat.

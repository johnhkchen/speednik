# Design — T-006-01: fix-loop-arc-rasterization

## Problem Restatement

Two rasterization functions use `round()` to convert floating-point arc/line sample
positions to integer tile heights. Python's banker's rounding causes `round(0.5) = 0`,
producing `height = 0` tiles where the arc physically occupies the tile. Fix needed in
`_rasterize_loop` and `_rasterize_line_segment`.

## Options Evaluated

### Option A: Replace `round()` with `math.ceil()`

**Change:** `round(tile_bottom_y - sy)` → `math.ceil(tile_bottom_y - sy)`

Behavior:
- `ceil(0.01) = 1` — any sub-pixel intersection → ≥1px of solid
- `ceil(0.0) = 0` — no intersection → no solid (correct)
- `ceil(15.7) = 16` — near-full tile → clamped to 16 (correct)

Pros:
- One-line change per function (two total)
- Guarantees any arc point within a tile registers as solid
- Conservative: slightly over-estimates height, which is the safe direction for collision
- `math` already imported
- Directly matches the fix described in the ticket

Cons:
- Slightly changes height values for all tiles, not just boundary cases. A tile where
  `tile_bottom_y - sy = 3.2` currently gets height=3 but would get height=4.
- This is actually correct for collision — the sample point is 3.2px above the bottom,
  meaning 3.2px of the tile is occupied, so 4px of solid is the safer representation.

### Option B: Replace `round()` with `int()` + conditional

```python
raw = tile_bottom_y - sy
height = max(0, min(16, int(raw) + (1 if raw > int(raw) else 0)))
```

This is just a verbose reimplementation of `math.ceil` for non-negative values.
Rejected: unnecessarily complex for no benefit.

### Option C: Use `round()` with a bias

```python
height = max(0, min(16, round(tile_bottom_y - sy + 0.01)))
```

Adding a small epsilon to avoid the exact-0.5 case.

Pros:
- Minimal change to existing rounding behavior for most values.

Cons:
- Fragile: the epsilon must be tuned and may not cover all floating-point edge cases.
- Doesn't fix the fundamental problem — it just shifts the problematic boundary.
- Harder to reason about correctness.
- Rejected.

### Option D: Use `math.floor()` instead

Rejected immediately: `floor(0.5) = 0` has the same problem as `round(0.5) = 0`.
`floor` would produce even more gaps.

## Decision: Option A — `math.ceil()`

**Rationale:**
1. Directly addresses the root cause (banker's rounding at 0.5 boundaries).
2. Minimal change — one token per call site.
3. `ceil` is the semantically correct operation: "how many integer pixels of solid
   does this sub-pixel intersection require?"
4. The `max(0, min(16, ...))` clamp ensures bounds are still respected.
5. Matches the ticket's specified fix exactly.
6. `math.ceil` returns `int` in Python 3, so no type change.

**Impact on existing data:**
- All tiles where the fractional part of `tile_bottom_y - sy` is > 0 will have
  height increased by 1 compared to the current `round()` behavior (when the
  fractional part is < 0.5). When the fractional part is exactly 0.5, height
  increases by 1 (the bug fix). When fractional part is > 0.5, height stays the
  same (ceil and round agree).
- This is the conservative (safe) direction — slightly more solid is always better
  than slightly less for collision detection.
- The angle values are unaffected — they're computed from segment direction, not height.

**Risk assessment:**
- Low risk. The change makes collision strictly more conservative (more solid, never less).
- The fill interior logic (`_fill_interior`) already fills everything below surface tiles
  as fully solid, so the line segment change only matters for `TOP_ONLY` surfaces.
- Existing tests may need height values updated if they assert exact heights computed
  with `round()`. This is expected and correct.

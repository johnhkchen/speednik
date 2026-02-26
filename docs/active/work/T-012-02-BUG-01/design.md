# Design — T-012-02-BUG-01: hillside-wall-at-x601

## Problem Restatement

Tile (37, 38) in `hillside/tile_map.json` has `angle=64` (right-wall). Its
height_array and all neighbors indicate it should be `angle≈2` (gentle floor
slope). The wrong angle causes the physics engine to enter wall mode and halt
forward progress.

## Options Evaluated

### Option A: Fix the angle value in tile_map.json (CHOSEN)

Change `tile_map.json[38][37]["angle"]` from 64 to 2.

**Pros:**
- Directly fixes the root cause at the data layer.
- Zero code changes — no risk of regressions in physics, terrain, or loader.
- Matches the pattern of neighboring tiles (38→angle=2, 39→angle=2).
- The height array `[4,...4,5,...5]` has a 1px rise over 16 cols → byte angle ≈ 2.55 → 2 is the correct rounded value.

**Cons:**
- Only fixes this one tile. Does not prevent future pipeline errors.

### Option B: Runtime angle correction in the loader

Add validation in `_build_tiles()` that cross-checks the stored angle against
the geometry implied by the height_array, flagging or auto-correcting mismatches.

**Pros:**
- Would catch any future data errors automatically.

**Cons:**
- Over-engineering for a single tile fix. The height-to-angle mapping is
  non-trivial (depends on adjacent tile heights, not just local array).
- Risk of false positives on intentional steep tiles (e.g., loop interiors).
- Adds runtime cost to every tile load.
- The angle field encodes information that cannot always be reconstructed from
  a single tile's height array alone (e.g., curved surface segments).

### Option C: Add angle smoothing in resolve_collision

Insert a check that if a tile's angle differs too dramatically from its
neighbors, interpolate to a smoother value.

**Pros:**
- Self-healing at runtime.

**Cons:**
- Extremely fragile — legitimate sharp transitions (loop entry, walls at slope
  edges) must not be smoothed.
- Adds per-frame cost to a hot path.
- Masks data bugs rather than fixing them.

## Decision

**Option A** — fix the angle in tile_map.json from 64 to 2.

Rationale: This is a data bug, not a code bug. The physics engine behaves
correctly given correct data. The fix is minimal, precise, and verifiable. The
neighboring tiles provide strong evidence for the correct value (angle=2).

### Why angle=2 specifically?

Computed from the height array:
- Height transitions from 4 to 5 over ~7 columns (cols 8→9 boundary).
- Averaged over 16 columns: rise = 1px, run = 16px.
- `atan(1/16) × 256/(2π) ≈ 2.55`, rounds to **2** or **3**.
- Tiles (38, 38) and (39, 38) both use angle=2.
- Choosing **2** for consistency with immediate neighbors.

## Verification Strategy

1. **Unit test**: Load hillside, inspect tile (37, 38), assert angle=2.
2. **Integration test**: Run Walker strategy on hillside for 3600 frames,
   assert max_x > 4700 (previously stuck at ≈601).
3. **Regression check**: Run existing test suite — no tests should break
   because no code changed; only a data file was corrected.

## Rejected Alternatives Summary

| Option | Verdict  | Reason                                        |
|--------|----------|-----------------------------------------------|
| A      | **Chosen** | Direct, minimal, correct                    |
| B      | Rejected | Over-engineering, false positive risk          |
| C      | Rejected | Masks bugs, fragile heuristic, runtime cost   |

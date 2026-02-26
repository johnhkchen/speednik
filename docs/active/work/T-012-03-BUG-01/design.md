# Design — T-012-03-BUG-01: pipeworks-slope-wall-blocks-progress

## Problem Restatement

Tile column 32 in Pipeworks has `angle=64` on all tiles from row 10 to row 16.
The fully solid underground tiles at rows 13–16 (`h=[16]*16`) should be
`angle=0` (flat floor) since they sit beneath the surface. The player walks up a
45° slope (angle=32 tiles, cols 24–31) and hits these angle=64 tiles, causing
the physics engine to switch to wall mode and block all forward progress.

## Options Evaluated

### Option A: Fix angle values for fully solid underground tiles (CHOSEN)

Change `angle` from 64 to 0 for tiles at column 32, rows 13–16. These tiles
have `h=[16]*16` (fully solid) and sit underground — the player walks across
their top surface. Neighboring fully-solid tiles at column 31 (rows 14–16)
already use `angle=0`. This makes column 32 consistent.

Leave rows 10–12 unchanged — they have partial height arrays that genuinely
describe a pipe wall edge, and the player does not contact them during normal
slope traversal.

**Pros:**
- Directly fixes the root cause at the data layer.
- Zero code changes — the physics engine is correct, the data is wrong.
- Consistent with neighboring tiles (col 31 underground tiles use angle=0).
- Identical pattern to the successful Hillside fix (T-012-02-BUG-01).
- Minimal blast radius: 4 tile angle values in one JSON file.

**Cons:**
- Does not address rows 10–12 (pipe wall cap). These retain angle=64, which is
  correct for their wall geometry but could theoretically cause issues if a
  player lands on them via unusual trajectory. Acceptable risk — the slope
  approach directs players below row 12.

### Option B: Fix all 7 tiles in column 32 (rows 10–16)

Change angle to 0 for all tiles in column 32 rows 10–16.

**Pros:**
- More comprehensive — eliminates all angle=64 in the left pipe wall.

**Cons:**
- Rows 10–12 have genuine wall geometry. Setting angle=0 would make the pipe
  wall traversable where it should be solid, potentially allowing the player
  to clip into the pipe interior from above.
- Misrepresents the physical geometry of the pipe entrance.
- Row 10's height array (`[0...,16,16,16,16,16,16,16,16]`) describes a
  half-solid tile — angle=0 would let the player walk across it as a floor
  step, which may or may not be desired.

### Option C: Runtime angle correction in the terrain loader

Add validation in the tile loader that auto-corrects angle for fully solid
tiles.

**Pros:**
- Catches all similar data bugs automatically.

**Cons:**
- Over-engineering. Not all `h=[16]*16` tiles should have angle=0 — some are
  intentional wall or ceiling sections. Automatic correction cannot distinguish
  intent without broader structural context.
- Same rejection rationale as Option B from the Hillside design.

### Option D: Add slope-to-wall transition smoothing in resolve_collision

Interpolate angle when the player crosses a large angle delta.

**Pros:**
- Self-healing at runtime.

**Cons:**
- Fragile — legitimate sharp transitions (loop entry, wall edges) must not be
  smoothed. The physics engine already handles angle transitions correctly when
  the data is correct.
- Masks data bugs rather than fixing them.
- Per-frame cost on a hot path.

## Decision

**Option A** — fix angle from 64 to 0 for tiles at (32, 13), (32, 14),
(32, 15), and (32, 16).

### Rationale

These four tiles are fully solid (`h=[16]*16`) and sit underground. Their top
surface is flat (the top of a fully-solid tile is always a flat floor). The
correct angle for a flat floor surface is 0. This matches:

1. Adjacent tiles at column 31 rows 14–16 (angle=0, same geometry)
2. All other fully-solid underground tiles in the stage
3. The Hillside fix pattern (data-only fix, no code changes)

The pipe wall tiles at rows 10–12 retain angle=64. They have partial height
arrays describing genuine vertical surfaces. The player's slope approach
reaches at most row 12–13 — the blocker is row 13 (the first fully-solid tile).

### Why angle=0 specifically?

- `h=[16]*16` means all 16 pixel columns are fully solid to height 16. The top
  surface is perfectly flat with zero slope.
- `atan(0/16) × 256/(2π) = 0`. The correct byte angle is exactly 0.
- Adjacent underground tiles at (31,14), (31,15), (31,16) all use angle=0.

## Verification Strategy

1. **Unit tests**: Load pipeworks, assert tiles (32,13–16) have angle=0.
2. **Integration test**: Run Jumper on pipeworks for 3600 frames, assert
   max_x > 520 (previously stuck at 518).
3. **Audit tests**: The 4 xfail tests referencing BUG-01 (jumper, speed_demon,
   cautious, chaos) should be evaluated. If archetypes now pass their slope
   obstacle, the xfail annotations need updating. However, they may still fail
   due to other downstream obstacles — those failures would be separate bugs.
4. **Regression**: Full test suite must pass with no new failures.

## Rejected Alternatives Summary

| Option | Verdict  | Reason                                        |
|--------|----------|-----------------------------------------------|
| A      | **Chosen** | Minimal, correct, matches Hillside pattern  |
| B      | Rejected | Over-broad: destroys legitimate pipe wall geometry |
| C      | Rejected | Over-engineering, can't distinguish intent    |
| D      | Rejected | Masks bugs, fragile heuristic, runtime cost   |

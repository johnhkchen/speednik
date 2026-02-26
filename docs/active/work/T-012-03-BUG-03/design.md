# Design — T-012-03-BUG-03: pipeworks-chaos-early-clipping

## Problem Restatement

`_eject_from_solid()` only scans upward. When the player enters a
vertically-continuous solid column (column 6 in Pipeworks — 40 tiles tall,
only 1 pixel wide at col 4), the upward scan exhausts its 8-tile budget
without finding free space. The fallback `y -= TILE_SIZE` places the player
in another solid tile. Result: 2 `inside_solid_tile` invariant errors persist
across frames 369 and 413.

## Options Evaluated

### Option A: Add horizontal ejection fallback to `_eject_from_solid` (CHOSEN)

After the upward scan fails (exhausts `_EJECT_SCAN_TILES`), try horizontal
ejection: check columns left and right of the player's current position within
the same tile. Push the player to the nearest non-solid column.

Implementation: after the upward scan loop, if no free space was found, check
whether the player center column within the current tile is flanked by empty
columns. Compute the nearest empty column and push the player horizontally to
it.

**Pros:**
- Directly addresses the failure mode: vertical scan fails, horizontal escape
  is obvious (columns 0–3 and 5–15 of the tile are empty).
- Contained within `_eject_from_solid()` — no interface changes.
- Cheap: only activates when upward scan already failed (rare path).
- Consistent with BUG-02 design which acknowledged lateral ejection as a
  possible recovery direction.

**Cons:**
- Adds complexity to `_eject_from_solid()`.
- Must choose a direction (left vs right) — could push player into an adjacent
  solid tile. Mitigated by checking both directions and choosing the shorter
  distance.

### Option B: Tile data fix — remove solid from column 4 of tile column 6

Change the height_array for column 6 tiles so that h[4]=0, making the thin
wall post non-solid.

**Pros:**
- Zero code changes. Data-only fix like BUG-01.

**Cons:**
- Destroys legitimate geometry. Column 6's h[4]=16 represents the right edge
  of the pipe wall. Removing it creates a 1-pixel gap in the wall boundary that
  players could clip through.
- Inconsistent: column 5 (fully solid) would have no right-edge extension,
  making the wall boundary abrupt.
- Doesn't fix the general problem — any other thin vertical solid in any stage
  would trigger the same bug.

**Rejected:** Destroys intentional geometry and doesn't fix the general case.

### Option C: Increase `_EJECT_SCAN_TILES` to cover the full column

Change `_EJECT_SCAN_TILES` from 8 to 40+ to scan the entire column height.

**Pros:**
- Simple constant change.

**Cons:**
- Wasteful for the general case (8 tiles is plenty for normal solid blocks).
- Still fails for columns that extend the full level height — the scan would
  succeed only if the level has free space above the top row.
- Doesn't fix the core issue: vertical ejection is the wrong direction for
  vertically-continuous geometry.

**Rejected:** Masks the problem without solving the fundamental direction issue.

### Option D: Make `_is_inside_solid` skip thin-wall tiles

If a tile's height array has fewer than N solid columns, treat it as not solid
for invariant purposes.

**Pros:**
- Removes false positives for thin geometry.

**Cons:**
- The player IS inside solid geometry. Suppressing the detection is masking,
  not fixing. The player still clips through the wall visually.
- Changes invariant semantics — other thin-wall tiles that should be detected
  would also be skipped.

**Rejected:** Masking approach.

## Decision

**Option A** — add horizontal ejection fallback to `_eject_from_solid()`.

### Rationale

The upward-only scan in `_eject_from_solid()` is the correct primary strategy
(most solid clipping comes from high-speed vertical entry into pipe interiors,
where upward escape is natural). But it fails for vertically-continuous,
horizontally-thin geometry. Adding a horizontal fallback handles this edge case
without changing the primary strategy.

The fix is general: any future tile with similar geometry (tall thin solid
column) will also benefit from horizontal ejection.

### Ejection Direction Logic

When the upward scan fails:
1. Get the tile at the player's current position.
2. Scan left and right from the player's column within the tile to find the
   nearest empty column (height_array[col] == 0 or height_array[col] such that
   the player y is above the solid top).
3. Also check the adjacent tile in each direction for additional escape room.
4. Push the player to the nearest free column + 1px margin.
5. Set airborne, zero velocity, angle=0.

If horizontal ejection also fails (tile is fully solid in all columns), retain
the existing `y -= TILE_SIZE` fallback as last resort.

## Verification Strategy

1. Run chaos audit: 0 `inside_solid_tile` errors.
2. Existing tests pass (walker, wall_hugger, other archetypes).
3. Unit test: player inside a vertically-continuous thin column, verify
   horizontal ejection succeeds.
4. Full test suite regression check.

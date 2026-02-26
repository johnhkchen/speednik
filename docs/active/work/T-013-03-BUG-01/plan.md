# Plan: T-013-03-BUG-01 — skybridge-terrain-pocket-trap-x413

## Step 1: Identify all affected tiles

Run a script to find ALL tiles in rows 31-32 of skybridge tile_map.json that have
angle=64 or angle=192 and are at gap edges (adjacent to null/missing tiles). This
ensures we don't miss any tiles beyond the initial research (especially the col 73-76
gap identified later).

**Verification:** Script output lists all tiles to fix with their current angles.

## Step 2: Fix tile angles in tile_map.json

Write a Python script to programmatically update the identified tiles in
`speednik/stages/skybridge/tile_map.json`:
- Row 31 edge tiles with angle=64 → change to angle=0
- Row 31 edge tiles with angle=192 → change to angle=0
- Row 32 edge tiles with angle=64 → change to angle=0
- Row 32 edge tiles with angle=128 at gap edges: leave unchanged (correct underside)

Use a script rather than manual editing to avoid errors in the large JSON file.

**Verification:** Re-read modified JSON and confirm only the target tiles changed.

## Step 3: Run walker archetype simulation

Execute the walker archetype on skybridge and verify:
- Walker no longer transitions to wall/ceiling mode at gap edges
- Walker falls through gaps normally
- max_x_reached improves significantly (was 581.0, should be higher)
- No infinite oscillation at x≈413

**Verification:** Simulation trace shows angle stays at 0 (quadrant 0) through gap regions.

## Step 4: Run wall_hugger archetype simulation

Execute the wall_hugger archetype on skybridge and verify similar improvement.

**Verification:** max_x_reached improves, no ceiling-walking.

## Step 5: Run existing test suite

Run the full test suite to catch any regressions.

**Verification:** All existing tests pass.

## Testing Strategy

- **Primary:** Walker and wall_hugger archetype simulations on skybridge
- **Regression:** Full pytest suite
- **Spot check:** Verify pillar tiles (rows 38+) were NOT modified
- **Edge cases:** Check that the last gap (cols 73-76) edges are also fixed

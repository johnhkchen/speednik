# Design — T-012-02-BUG-02: hillside-no-right-boundary-clamp

## Problem

Player position is never clamped to the right level boundary. The player can
reach x=34023 on a level with width=4800, generating 5444 invariant errors.

## Options Considered

### Option A: Clamp in `sim_step()` after `player_update()`

Add position clamping in `simulation.py:sim_step()` immediately after the
`player_update()` call (line 231). Since `sim_step` has access to
`sim.level_width`, it can clamp `sim.player.physics.x` directly.

**Pros:**
- Single insertion point — one place to add clamping
- `sim_step` already has level dimensions, no signature changes needed
- Mirrors the camera clamping pattern (post-update clamp)
- Minimal diff — 3-4 lines added to an existing function
- Easy to extend for left/bottom boundaries later (BUG-03)

**Cons:**
- Clamping happens after collision resolution, which is slightly out of order
  vs. where a "wall" collision would normally occur
- Player velocity is not zeroed — they'll keep "pushing" into the wall each
  frame (velocity gets re-applied, position gets re-clamped)

### Option B: Clamp in `apply_movement()` by passing level dimensions

Add `level_width` parameter to `apply_movement()` in `physics.py`, then clamp
`state.x` after the position update.

**Pros:**
- Clamping happens at the exact moment position changes
- Follows the pattern of velocity clamping already in `apply_input()`

**Cons:**
- Requires changing the `apply_movement()` signature
- Requires `player_update()` to receive level dimensions (signature change)
- `apply_movement` is a pure physics function — boundary awareness is a
  level-design concern, not a physics concern
- Cascading signature changes across 3+ functions
- Breaks existing test calls to `apply_movement`

### Option C: Add virtual boundary tiles to the tile lookup

Modify the tile lookup to return solid tiles beyond the level boundary, so the
collision system naturally blocks the player.

**Pros:**
- No new code paths — uses existing collision resolution
- Physically "correct" — the player bounces off a wall

**Cons:**
- Complex: requires wrapping the tile lookup function
- Height arrays and angles must be set correctly for the virtual wall
- Risk of interfering with legitimate near-boundary tiles
- Over-engineered for a simple clamp

### Option D: Clamp in `sim_step()` with velocity zeroing

Same as Option A but also zero out rightward velocity when clamped.

**Pros:**
- Player doesn't perpetually push into the boundary
- More physically realistic — hitting a wall stops you

**Cons:**
- Zeroing x_vel/ground_speed can interfere with slope physics
- The player should be allowed to move left after hitting the wall, but
  ground_speed carries direction information
- More lines of code, more edge cases

## Decision: Option A — Clamp in `sim_step()` after `player_update()`

**Rationale:**

1. **Minimal change**: 3-4 lines in a single file. No signature changes, no
   cascading modifications.

2. **Correct layer**: Level boundaries are a simulation concern, not a physics
   concern. `sim_step` is where the simulation knows about level dimensions.
   Physics (`apply_movement`) should remain dimension-agnostic.

3. **Precedent**: The camera uses the same post-update clamp pattern. The player
   should follow it.

4. **Velocity zeroing is unnecessary**: In Sonic 2, the player pushes against
   walls without velocity zeroing — the wall (or boundary) simply prevents
   position change. The engine re-applies velocity each frame and re-clamps.
   This is the standard Sonic engine behavior.

5. **BUG-03 compatibility**: The same insertion point can clamp left boundary
   (`x = max(0, x)`) when that ticket is implemented.

## Clamping Value

Clamp to `sim.level_width` exactly (not level_width + margin). The POSITION_MARGIN
in invariants.py is a detection threshold, not a gameplay boundary. The player
should not go past the level width at all.

## Rejected Alternatives

- **Option B** rejected: Cascading signature changes violate minimal-diff
  principle. Physics should not know about level geometry.
- **Option C** rejected: Virtual tiles add complexity for a problem that is
  solved by a 2-line clamp. Over-engineered.
- **Option D** rejected: Velocity zeroing creates edge cases with slope physics
  and directional ground_speed. Unnecessary for correct behavior.

## Test Strategy

1. Synthetic grid test: place player past level_width, step once, assert clamped
2. Synthetic grid test: player approaching boundary at speed, run N frames,
   assert never exceeds level_width
3. Regression: run the reproduction scenario from the ticket and verify zero
   `position_x_beyond_right` violations

# Structure — T-012-02-BUG-02: hillside-no-right-boundary-clamp

## Files Modified

### 1. `speednik/simulation.py`

**Change:** Add right-boundary position clamp in `sim_step()`.

**Location:** After line 231 (`player_update(sim.player, inp, sim.tile_lookup)`)
and before line 234 (`sim.frame += 1`).

**Interface:** No changes to any public interface. `sim_step` signature remains
`sim_step(sim: SimState, inp: InputState) -> list[Event]`.

**Logic:**
```
# After player_update, before frame counter increment:
if sim.player.physics.x > sim.level_width:
    sim.player.physics.x = float(sim.level_width)
```

This is a hard clamp — if `player_update` moved the player past the right edge,
snap them back to the edge. No velocity modification.

### 2. `tests/test_simulation.py`

**Change:** Add boundary-clamp tests to the existing test file.

**New test functions (appended to end of file):**

- `test_right_boundary_clamp_immediate()`:
  Place player at `level_width + 100`, step once, assert `x == level_width`.
  Uses `create_sim_from_lookup` with a small synthetic grid so level_width
  is controlled.

- `test_right_boundary_clamp_running()`:
  Start player on a flat grid near the right edge, hold right for many frames.
  Assert `player.physics.x <= level_width` on every frame. Uses the existing
  `build_flat` and `create_sim_from_lookup` helpers.

Both tests follow the existing patterns in `test_simulation.py`:
- Use `create_sim_from_lookup` + `build_flat` from `tests.grids`
- Use `InputState` for input
- Use `sim_step` for frame advance
- Named with `test_` prefix, grouped under a section comment

## Files NOT Modified

- `speednik/physics.py` — No changes. Position clamping is not a physics concern.
- `speednik/player.py` — No changes. No signature changes needed.
- `speednik/terrain.py` — No changes. Collision system unchanged.
- `speednik/invariants.py` — No changes. Detection logic stays as-is for
  regression monitoring. If the clamp works, this invariant should never fire.
- `speednik/env.py` — No changes. The env wraps `sim_step`, so it inherits
  the fix automatically.

## Ordering

1. Modify `simulation.py` (the fix)
2. Add tests to `test_simulation.py` (verification)
3. Run tests to confirm

## Dependency Notes

- BUG-03 (left boundary) will add a symmetric clamp at the same insertion
  point: `sim.player.physics.x = max(0.0, sim.player.physics.x)`. This ticket
  does not add that — scope is right boundary only.
- No dependencies on other open tickets.

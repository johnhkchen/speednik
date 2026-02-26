# Review — T-012-02-BUG-02: hillside-no-right-boundary-clamp

## Summary of Changes

### Files Modified

1. **`speednik/simulation.py`** — Added right-boundary position clamp
   - 3 lines inserted in `sim_step()` after `player_update()` (line ~233)
   - Clamps `sim.player.physics.x` to `float(sim.level_width)` when exceeded
   - No signature changes, no new imports, no interface changes

2. **`tests/test_simulation.py`** — Added 2 regression tests
   - `test_right_boundary_clamp_immediate()`: teleport past boundary → clamped
   - `test_right_boundary_clamp_running()`: 600 frames hold-right → never exceeds

### Files NOT Modified

- `speednik/physics.py` — Correctly left unchanged (position clamping is a
  simulation concern, not a physics concern)
- `speednik/player.py` — No changes needed
- `speednik/invariants.py` — Detection logic preserved for ongoing monitoring
- `speednik/env.py` — Inherits fix via `sim_step`

## What the Fix Does

After `player_update()` advances the player's physics (input → slope → gravity →
movement → collision resolution), `sim_step()` now checks if the player's x
position exceeds `level_width`. If so, it snaps the position back to the edge.

This prevents the player from escaping rightward into unbounded space, which was
generating 5444 `position_x_beyond_right` invariant violations on the jumper
archetype's 3600-frame hillside run.

## Test Coverage

| Test | What It Verifies |
|---|---|
| `test_right_boundary_clamp_immediate` | Player teleported past boundary is snapped back |
| `test_right_boundary_clamp_running` | Player running into boundary is held at edge every frame |
| All 30 existing tests | No regressions (parity, smoke, events, death, goal, enemies) |

**Coverage assessment:** The two new tests cover the core fix behavior. The
"running" test is particularly important as it exercises the real gameplay
scenario (player accumulates velocity over many frames and hits the boundary).

**Gap:** No test using the actual hillside stage with the jumper archetype.
The ticket's reproduction scenario uses `speednik.qa.run_audit` which is a
higher-level QA tool — this is better tested at the integration/QA layer than
in unit tests. The unit tests verify the mechanism works correctly.

## Design Decisions

1. **Clamp location in `sim_step` (not physics):** Level boundaries are a
   simulation concern. `physics.py` remains dimension-agnostic.

2. **No velocity zeroing:** Matches Sonic 2 behavior where the player pushes
   against walls without losing velocity state. The wall prevents movement
   but doesn't kill speed — you can turn around immediately.

3. **Clamp to `level_width` exactly (not `level_width + margin`):** The
   64px `POSITION_MARGIN` in `invariants.py` is a detection tolerance, not
   a gameplay boundary. Players should stop at the actual level edge.

## Open Concerns

1. **Left boundary (BUG-03):** The symmetric fix (`x = max(0, x)`) is not
   included here — it's scoped to T-012-02-BUG-03. The insertion point is
   ready for it (same location in `sim_step`).

2. **Bottom boundary:** No y-axis clamp was added. If a player falls below
   `level_height`, they are not stopped. This may be intentional (death pits)
   or may need a separate ticket.

3. **`main.py` parity:** The fix is in the headless `simulation.py`, which is
   used by both the Gymnasium env and the QA framework. The rendered game in
   `main.py` calls `player_update` directly — it does NOT go through
   `sim_step()`. If `main.py` has the same boundary problem, it would need
   a separate clamp. However, `main.py` is not in scope for this ticket
   (the bug was filed against the simulation/QA layer).

4. **No commit made:** Per workflow instructions, the implementation is complete
   and tested but not committed. The user/Lisa handles commit decisions.

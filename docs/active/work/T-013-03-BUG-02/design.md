# Design — T-013-03-BUG-02: audit-no-respawn-after-pit-death

## Option A: Respawn inside `sim_step()` (rejected)

Add respawn logic directly into `sim_step()` so that after pit death, the simulation
automatically resets the player to checkpoint coordinates on the next frame.

**Pros**: All callers benefit (main.py, run_audit, future callers). Single source of truth.

**Cons**: `sim_step()` is a pure physics step — it shouldn't own respawn policy. The game
(main.py) has a 120-frame death animation delay, a lives system, and a game-over transition.
Embedding respawn in `sim_step()` would either (a) break main.py's death flow or (b) require
a config parameter on SimState to control respawn behavior, which pollutes the data model.
The game already handles respawn outside `sim_step()` via `_update_gameplay()` →
`_respawn_player()`. This would create two competing respawn paths.

## Option B: Respawn inside `run_audit()` (selected)

Add respawn logic to the `run_audit()` loop. When a `DeathEvent` is detected in the events
returned by `sim_step()`, respawn the player at their checkpoint coordinates. Track deaths
and terminate when `max_deaths` is exceeded (set `sim.player_dead = True`).

Also fix `sim_step()` to set `sim.player_dead = True` when pit death occurs, so the existing
break condition works for callers that don't want respawn.

**Pros**:
- Clean separation: `sim_step()` signals death, `run_audit()` decides what to do
- Mirrors main.py pattern: main.py handles respawn outside sim_step too
- `max_deaths` budget is already in `BehaviorExpectation`
- No changes to sim_step's contract beyond fixing the missing `player_dead` flag
- Immediate respawn (no 120-frame delay) is correct for audit — no animation to wait for

**Cons**: If future callers need respawn, they'd need their own logic too. Acceptable since
respawn policy is inherently caller-specific (game has lives, audit has max_deaths budget).

## Option C: Add a `respawn_player()` helper to `simulation.py` (rejected)

Extract the respawn logic from main.py into a reusable `respawn_player(sim)` function in
simulation.py. Call it from both main.py and run_audit().

**Pros**: DRY between main.py and qa.py.

**Cons**: main.py's respawn also resets camera, death_timer, and lives — none of which exist
in SimState. The overlapping logic is only 3–4 lines (reset player at respawn coords). Not
worth an abstraction for something this small. The main.py respawn replaces the entire Player
object (`self.player = create_player(rx, ry)`), which is a different pattern than what the
audit needs (reset in-place to preserve the same SimState reference).

## Selected: Option B

### Design Details

**1. Fix `sim.player_dead` in `sim_step()`**

In the pit death block (`simulation.py:247–252`), add `sim.player_dead = True` so that
callers who don't handle respawn get early termination. This makes the existing break
condition in `run_audit()` work for the terminal-death case.

Wait — we need to be careful. If we set `player_dead = True` immediately on death, the
audit loop will break before it can respawn. The `player_dead` flag should mean "permanently
dead" (no more respawns), not "currently dead". So:

- `sim_step()` sets `player.state = DEAD` and emits `DeathEvent` (already does this)
- `sim_step()` does NOT set `sim.player_dead` — that's a policy decision for callers
- `run_audit()` detects `DeathEvent`, decides whether to respawn or terminate

This means `player_dead` semantics: "caller has determined the player is permanently dead."
The audit sets it when deaths exceed budget. Other callers can set it based on their own
rules. This is the cleanest contract.

Actually, looking again: `sim_step()` already guards on `sim.player_dead` at the top
(line 221). If `player_dead` is never set, the loop continues calling `sim_step()` which
returns early because `player_update()` bails on `DEAD` state. The current code is
technically harmless (just wasteful). The fix is in `run_audit()`, not `sim_step()`.

**2. Respawn logic in `run_audit()`**

After each `sim_step()`, check if the returned events contain a `DeathEvent`. If so:
- Increment a local death counter (already tracked by `sim.deaths`)
- If `sim.deaths > expectation.max_deaths`: set `sim.player_dead = True` (terminates loop)
- Otherwise: reset the player to checkpoint coordinates

Respawn means:
- `sim.player.state = PlayerState.STANDING`
- `sim.player.physics.x = sim.player.respawn_x`
- `sim.player.physics.y = sim.player.respawn_y`
- `sim.player.physics.on_ground = True`
- `sim.player.rings = sim.player.respawn_rings`
- Zero out velocities: `x_vel = 0, y_vel = 0, ground_speed = 0`
- Clear rolling/spindash flags
- Clear invulnerability timer
- Clear scattered rings

This is simpler than main.py's approach (which creates a whole new Player object) because
we can reset in-place. We don't need to worry about camera, death_timer, lives, or audio.

**3. Death budget termination**

When `sim.deaths > expectation.max_deaths`, set `sim.player_dead = True`. The loop's
existing break condition `if sim.goal_reached or sim.player_dead: break` handles the rest.

Note: `max_deaths` is the *maximum allowed*. If `max_deaths=1`, one death is OK (respawn),
two deaths terminate. Use `sim.deaths > expectation.max_deaths` as the threshold for the
respawn decision, not for setting `player_dead`. Wait — the audit checks `sim.deaths >
expectation.max_deaths` in `_build_findings()` to generate a finding. The audit should
still respawn up to the budget but terminate beyond it.

Decision: respawn if `sim.deaths <= expectation.max_deaths`, otherwise set `player_dead`.
This way the archetype gets its full death budget before termination.

**4. No changes to `_build_findings()`**

The existing findings logic already checks `sim.deaths > expectation.max_deaths` and
`sim.max_x_reached < expectation.min_x_progress`. With respawn working, these checks
will now reflect the archetype's true cumulative performance. No changes needed.

**5. No changes to `BehaviorExpectation`**

The `max_deaths` field already carries the death budget. No new fields needed.

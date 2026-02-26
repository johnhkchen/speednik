# T-010-03 Research — simulation-parity-tests

## Scope

Verify the headless simulation (`sim_step`) produces identical player physics
to the test harness (`run_scenario`) on synthetic grids, then verify full
simulation features (rings, enemies, goal) on real stages.

## Existing Systems

### Test harness (`tests/harness.py`)

- `run_scenario(tile_lookup, start_x, start_y, strategy, frames)` — creates a
  `Player`, loops `frames` times calling `strategy(frame, player) -> InputState`
  then `player_update(player, inp, tile_lookup)`, captures `FrameSnapshot` each
  frame. Returns `ScenarioResult` with snapshots and final Player.
- Operates at the player-physics-only level. No rings, springs, enemies, goals.
- Strategies: `idle()`, `hold_right()`, `hold_left()`, `hold_right_jump()`,
  `spindash_right(charge_frames, redash_threshold)`, `scripted(timeline)`.
- `run_on_stage(stage_name, strategy, frames)` — loads a real stage, delegates.

### Simulation (`speednik/simulation.py`)

- `SimState` — full game state: player, tile_lookup, entity lists, goal,
  metrics (frame, max_x_reached, rings_collected, deaths, goal_reached,
  player_dead), level dimensions.
- `create_sim(stage_name)` — only factory. Loads real stage from JSON.
  No way to create a SimState from a raw `TileLookup` + start position.
- `sim_step(sim, inp)` — mirrors `main.py:_update_gameplay()`:
  1. Death guard (return early with DeathEvent)
  2. `player_update(player, inp, tile_lookup)` — same function as harness
  3. Frame counter increment
  4. Ring collection, spring collision, checkpoint, pipes, liquid zones
  5. Enemy update + collision
  6. Spring cooldowns
  7. Goal collision
  8. Metrics update

### Synthetic grids (`tests/grids.py`)

- `build_flat(width, ground_row)` → `(tiles_dict, TileLookup)`
- `build_gap`, `build_slope`, `build_ramp`, `build_loop` — same pattern.
- All return a `(dict, TileLookup)` tuple. No Pyxel dependencies.

### Existing tests (`tests/test_simulation.py`)

17 tests from T-010-02: `create_sim` for all 3 stages, boss injection,
entity lists, event types, no-pyxel-import, SimState defaults, and `sim_step`
smoke tests (hold_right, frame counter, death detection/persistence/no-physics,
max_x tracking, returns-list, enemy update, goal detection). All use
`create_sim("hillside")` — no synthetic grids, no parity checks.

## Key Observations

### Parity is guaranteed by construction

Both `run_scenario` and `sim_step` call the **same** `player_update` function.
On a synthetic grid with no entities, `sim_step` does:
1. `player_update(player, inp, tile_lookup)` — identical to harness
2. Frame counter increment (harness doesn't track frames, it uses loop index)
3. Entity checks — all empty lists → no-ops, zero events
4. Metrics update — trivial

The only difference: `sim_step` increments `sim.frame` after physics. The
harness captures snapshots after `player_update` indexed by the loop counter.
There is no state mutation difference — both produce identical player state
after `player_update`. Parity should be exact (not approximate).

### Missing factory

`create_sim` requires a stage name and loads from disk. To test with synthetic
grids we need `create_sim_from_lookup(tile_lookup, start_x, start_y)` that
builds a `SimState` with empty entity lists. This is a small addition to
`simulation.py`.

### SimState construction for synthetic grids

`SimState` has required fields: `player, tile_lookup, rings, springs,
checkpoints, pipes, liquid_zones, enemies, goal_x, goal_y, level_width,
level_height`. For synthetic grids, all entity lists are `[]`, goal is at
`(0.0, 0.0)` (unreachable), dimensions from grid size.

### Performance benchmark

`sim_step` on hillside with entities calls `player_update` + entity iteration.
The ticket spec estimates 20,000-50,000 updates/sec. Testing: run 1000 frames,
measure wall time, compute rate. Use `time.perf_counter()`.

### Starting position for synthetic grids

The harness uses `start_x, start_y` directly. For `build_flat(40, 20)`:
- Ground surface at tile row 20, pixel y = 20 * 16 = 320.
- Player starts at pixel position: x given directly, y = ground_y - standing
  height offset. The `create_player` function places player at exact (x, y)
  with `on_ground=True`.
- Harness tests typically start at `(48.0, y)` where y is calculated to be
  on the surface. Need to use the same y for both systems.

### Strategy adapter

Harness strategies are `Callable[[int, Player], InputState]`. For parity tests,
we need the same strategy for both systems. The sim uses raw `InputState`, so
we call `strategy(frame, sim.player)` to get the same input.

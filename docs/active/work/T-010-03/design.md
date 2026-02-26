# T-010-03 Design — simulation-parity-tests

## Core Decision: Parity Test Architecture

### Option A: Compare final positions only

Run both systems N frames, compare final (x, y). Simple, but misses per-frame
divergence — could mask compensating errors.

### Option B: Compare full trajectories (chosen)

Run both systems N frames, compare (x, y, x_vel, y_vel, ground_speed) at every
frame. If any frame diverges, the test fails with the exact frame number. This
is more diagnostic and catches ordering issues immediately.

**Why**: Both systems call the same `player_update`, so every frame *must* be
identical. Per-frame comparison costs nothing (300 frames × 5 floats) and gives
precise failure diagnostics.

### Option C: Hash-based trajectory comparison

Hash the entire trajectory and compare. Compact but loses diagnostic info.
Rejected — per-frame comparison is cheap and more useful.

## `create_sim_from_lookup` Design

Add to `simulation.py`:

```python
def create_sim_from_lookup(
    tile_lookup: TileLookup,
    start_x: float,
    start_y: float,
    *,
    level_width: int = 10000,
    level_height: int = 10000,
) -> SimState:
```

Returns a `SimState` with empty entity lists, goal at `(0.0, 0.0)`, and
reasonable defaults. The `level_width/height` defaults are large enough that
boundary checks don't interfere.

Placed in `simulation.py` alongside `create_sim` — it's a public factory for
the same type, used by tests but potentially by the gym wrapper too.

## Parity Test Strategy

### Helper function

```python
def assert_trajectories_match(tile_lookup, start_x, start_y, strategy, frames):
```

1. Run `run_scenario(tile_lookup, start_x, start_y, strategy, frames)`.
2. Run `create_sim_from_lookup(tile_lookup, start_x, start_y)` then loop
   `frames` times calling `strategy(frame, sim.player)` → `sim_step(sim, inp)`.
3. At each frame, compare harness snapshot to sim player physics. Assert
   exact equality on x, y, x_vel, y_vel, ground_speed.

### Scenarios

| Test | Grid | Strategy | Frames |
|------|------|----------|--------|
| flat_idle | `build_flat(40, 20)` | `idle()` | 300 |
| flat_hold_right | `build_flat(40, 20)` | `hold_right()` | 300 |
| flat_spindash | `build_flat(40, 20)` | `spindash_right()` | 300 |

Starting y: `20 * 16 - 1 = 319` (one pixel above ground surface). This is the
standard position used in existing physics tests — player feet at tile surface.

## Full Simulation Tests

### Ring collection (hillside)

Run `hold_right` on hillside for 600 frames. The first ring line is close to
the start. Assert `sim.rings_collected > 0` and that `RingCollectedEvent`
appeared in at least one frame's events.

### Goal detection

Use `create_sim("hillside")`, teleport player to `(goal_x, goal_y)`, step once.
Assert `GoalReachedEvent` and `sim.goal_reached`. (Similar to existing test but
grouped with full-sim tests.)

### Enemy collision / damage

Use `create_sim("hillside")`, teleport player onto a known enemy position. Step.
Assert `DamageEvent` appears. Verify `sim.player.state` changes (HURT or DEAD).

### Death from falling (pipeworks gap)

Run `hold_right` on pipeworks for many frames. The player should eventually fall
into liquid or off-screen. Check `sim.deaths > 0` or `DamageEvent` occurs.

## Performance Benchmark

Not a pass/fail test — use `pytest.mark` or print to stdout.

```python
def test_performance_benchmark_hillside(capsys):
    sim = create_sim("hillside")
    t0 = time.perf_counter()
    for _ in range(1000):
        sim_step(sim, InputState(right=True))
    elapsed = time.perf_counter() - t0
    rate = 1000 / elapsed
    print(f"\nBenchmark: {rate:.0f} sim_step/sec (1000 frames, hillside)")
```

Log to stdout via capsys — visible with `pytest -s`. Not gated on a threshold
to avoid flaky CI failures on different hardware.

## Rejected Alternatives

- **Property-based testing (Hypothesis)**: Overkill for deterministic parity.
  The systems are identical by construction — we just need regression guards.
- **Approximate matching (pytest.approx)**: Unnecessary. Both call the same
  function with the same state. Results must be bit-identical, not approximate.
- **Separate test file**: Ticket says `tests/test_simulation.py`. Existing tests
  are already there. Add parity and full-sim tests to the same file.

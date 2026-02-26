# Design — T-012-06: Composable Mechanic Probes

## Approach: Direct sim_step with Synthetic Grids

### Why not reuse `_run_probe` from test_geometry_probes.py?

The existing `_run_probe` calls `create_sim(stage_name)` — it loads a real stage. Our probes
must use synthetic grids exclusively. We need a similar probe runner that takes a TileLookup
from grid builders and uses `create_sim_from_lookup`.

### Why not reuse `run_scenario` from strategies.py?

`run_scenario` calls `player_update` directly, bypassing `sim_step`. This means no entity
processing (springs, etc.) and no events. For the spring probe, we need `sim_step` to fire
`SpringEvent`. For consistency, all probes should use the same runner.

### Decision: New probe runner in test_mechanic_probes.py

Create a `_run_mechanic_probe()` function that:
1. Builds synthetic grid via grid builder
2. Creates SimState via `create_sim_from_lookup`
3. Optionally injects entities (springs) into the SimState
4. Runs `sim_step` in a loop with a strategy, collecting FrameSnap + events
5. Returns a ProbeResult (reuse the dataclass from test_geometry_probes or duplicate locally)

**Rationale**: Keeps the test file self-contained. The FrameSnap/ProbeResult classes are
small (~30 lines) and duplicating them avoids coupling to test_geometry_probes internals.

## Probe Design

### 1. Loop Probe — Parameterized across radii

```
@pytest.mark.parametrize("radius", [32, 48, 64, 96])
```

Strategy: spindash then hold right. Approach tiles: 15 (enough runway for spindash).
Ramp radius: radius // 2 (proportional entry ramp).

Assertions:
- `quadrants_visited == {0, 1, 2, 3}` — full loop traversal
- Exit with positive ground_speed
- Exit on_ground

Expected findings: Some radii may fail due to insufficient loop geometry resolution
(smaller loops = fewer tiles = less smooth curves). Document which work.

### 2. Loop Exit Momentum Probe

Same loop setup. After the loop exit region, check:
- `ground_speed > 0` (positive momentum preserved)
- `on_ground == True` (landed, not stuck airborne)

Can be combined with loop probe as additional assertions.

### 3. Ramp Probe — Parameterized across angles

```
@pytest.mark.parametrize("end_angle", [10, 20, 30, 40, 50])
```

Strategy: hold right at TOP_SPEED (pre-set ground_speed). Approach tiles: 10, ramp tiles: 10.

Key distinction: "wall slam" = ground_speed drops from >1.0 to ~0 in a single frame.
"Slope slowdown" = gradual speed reduction over multiple frames.

Assertions:
- No single-frame velocity zeroing in ramp region
- Player reaches end of ramp tiles (doesn't get stuck)

### 4. Gap Probe — Parameterized across widths

```
@pytest.mark.parametrize("gap_tiles", [2, 3, 4, 5])
```

Strategy: hold right + jump. Need to reach near-TOP_SPEED before the gap, then jump.
Approach tiles: 15 (enough to reach top speed). Landing tiles: 10.

Assertions:
- Player crosses past gap end X
- Player not dead (y < level_height equivalent)

### 5. Spring Probe

Build flat grid, inject Spring entity at a known position. Walk into it.

Strategy: hold right.

Assertions:
- SpringEvent fires
- Player reaches expected height: `start_y - (SPRING_UP_VELOCITY^2 / (2 * GRAVITY))`
  = 228.6 px above start. Use generous tolerance (±30px for frame discretization).
- Player lands back on ground within 120 frames

### 6. Slope Adhesion Probe — Sweep across angles

```
@pytest.mark.parametrize("angle", range(0, 50, 5))
```

Strategy: hold right. Pre-set ground_speed to 4.0 (moderate speed).
Approach tiles: 5, slope tiles: 15.

Assertions:
- Player stays on_ground while on slope tiles
- Document the angle where adhesion fails

## Rejected Approaches

### A. Using `run_scenario` from strategies.py
Rejected because it bypasses sim_step and entity processing. Spring probe requires
full simulation with entity collision checks.

### B. Shared probe infrastructure module
Rejected as over-engineering. The probe runner is ~25 lines. Keeping it in the test file
is simpler and matches the pattern of test_geometry_probes.py.

### C. Testing with real stages + filtering to mechanic regions
Rejected — the whole point is isolation. Real stages mix multiple mechanics and
level-design choices. Synthetic grids test one building block at a time.

## Strategy Adaptation

The `strategies.py` strategies take `(frame, player)`, but our probe loop calls `sim_step`
which needs an `InputState`. We'll write lightweight strategy closures inline (matching
test_geometry_probes.py pattern) that take `(frame, sim)` and return `InputState`.

For the spindash strategy, reuse the `_make_spindash_strategy` pattern from
test_geometry_probes.py (it takes `(frame, sim)` already).

## Bug Filing

When a probe fails:
1. Keep assertion as-is (what SHOULD work)
2. Add `@pytest.mark.xfail(strict=True, reason="BUG: ...")`
3. Create `docs/active/tickets/T-012-06-BUG-NN.md` with frontmatter + details

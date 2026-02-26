# Research — T-012-06: Composable Mechanic Probes

## Goal

Test game mechanics (loops, ramps, gaps, springs, slopes) in isolation using synthetic
grids from `speednik/grids.py`. Each probe asks: "given ideal conditions, does this element
work?" Failures indicate engine/physics bugs, not level design issues.

## Relevant Code

### Grid Builders (`speednik/grids.py`)

All builders return `tuple[dict[tuple[int,int], Tile], TileLookup]`.

| Builder | Parameters | Notes |
|---------|-----------|-------|
| `build_flat` | `width_tiles, ground_row` | Flat ground + fill below |
| `build_gap` | `approach_tiles, gap_tiles, landing_tiles, ground_row` | Gap = no tiles at all |
| `build_slope` | `approach_tiles, slope_tiles, angle, ground_row` | Constant byte-angle slope |
| `build_ramp` | `approach_tiles, ramp_tiles, start_angle, end_angle, ground_row` | Linearly interpolated angles |
| `build_loop` | `approach_tiles, radius, ground_row, ramp_radius=None` | Full 360° loop with optional entry/exit ramps |

All use `_fill_below()` for FILL_DEPTH=4 rows of solid fill beneath surface tiles.
Tiles are 16×16 pixels (TILE_SIZE=16).

### Simulation API (`speednik/simulation.py`)

- `create_sim_from_lookup(tile_lookup, start_x, start_y, *, level_width=10000, level_height=10000)` — creates SimState from synthetic grid, no entities.
- `sim_step(sim, inp)` — advances one frame, returns `list[Event]`.
- `SimState` fields: `player`, `tile_lookup`, `springs` (list), `frame`, `player_dead`, etc.
- Springs can be injected by setting `sim.springs = [Spring(x, y, "up")]`.

### Player Physics (`speednik/physics.py`, `speednik/constants.py`)

Key state via `sim.player.physics`:
- `x, y` — position in pixels
- `x_vel, y_vel` — cartesian velocity (px/frame)
- `ground_speed` — tangent velocity when on_ground
- `angle` — byte angle 0-255 (0=flat, increases CCW)
- `on_ground, is_rolling, facing_right`
- `spinrev, is_charging_spindash`

Key constants:
- `GRAVITY = 0.21875`
- `JUMP_FORCE = 6.5` (initial y_vel = -6.5)
- `TOP_SPEED = 6.0` (running)
- `SPINDASH_BASE_SPEED = 8.0`
- `SPRING_UP_VELOCITY = -10.0`
- `MAX_X_SPEED = 16.0`

### Quadrant System (`speednik/terrain.py`)

`get_quadrant(angle)` maps byte angles to quadrants 0-3:
- 0: floor (0-32, 224-255) — sensors point DOWN
- 1: right wall (33-96) — sensors point RIGHT
- 2: ceiling (97-160) — sensors point UP
- 3: left wall (161-223) — sensors point LEFT

A full loop traversal visits all 4 quadrants.

### Existing Probe Infrastructure (`tests/test_geometry_probes.py`)

Already has `FrameSnap`, `ProbeResult`, `_run_probe()` for real-stage probes.
Strategies: `_hold_right`, `_make_spindash_strategy()`, `_make_hold_right_jump_strategy()`.

The key difference: existing probes use `create_sim(stage_name)` for real stages.
Our probes will use `create_sim_from_lookup()` for synthetic grids.

### Strategy Library (`speednik/strategies.py`)

Canonical strategies usable with `run_scenario()`:
- `hold_right()`, `hold_right_jump()`, `spindash_right()`, `idle()`, `scripted()`
- Signature: `(frame: int, player: Player) -> InputState`
- Note: strategies.py strategies take `(frame, player)`, but `sim_step` needs `InputState`.
  For synthetic probes we call `sim_step` directly, so we'll adapt strategies accordingly.

### Spring Entity (`speednik/objects.py`)

```python
@dataclass
class Spring:
    x: float
    y: float
    direction: str  # "up" or "right"
    cooldown: int = 0
```

Springs are injected into `sim.springs`. `check_spring_collision()` uses AABB overlap
with SPRING_HITBOX_W=16, SPRING_HITBOX_H=16 centered on spring position.

## Observations

1. **No spring in synthetic grids**: `create_sim_from_lookup` creates empty entity lists.
   For the spring probe, we'll need to manually inject a `Spring` into `sim.springs`.

2. **Loop probes need sufficient approach**: Spindash base speed is 8.0, which should be
   enough for a loop, but the approach tiles and ramp_radius affect entry dynamics.

3. **Gap clearability depends on horizontal + vertical travel**: At TOP_SPEED=6.0 with
   JUMP_FORCE=6.5 and GRAVITY=0.21875, the jump arc determines max clearable distance.
   Theoretical jump duration: 2 * 6.5 / 0.21875 ≈ 59.4 frames. Horizontal distance at
   6.0 px/frame ≈ 356 px ≈ 22.3 tiles. So 2-5 tile gaps should be clearable easily.

4. **Slope adhesion**: The engine uses sensor-based ground detection. At high angles the
   player may detach. The slip system activates at SLIP_ANGLE_THRESHOLD=33 byte-angles
   (~46°) with speed below SLIP_SPEED_THRESHOLD=2.5.

5. **build_slope continuity issue**: The `col_offset = i * TILE_SIZE` creates increasingly
   large offsets, which with `_slope_height_array` may produce heights that saturate at 0
   or 16 for steep angles over many tiles. This may cause discontinuities.

6. **Player start position**: For synthetic grids, player start_y should be positioned
   just above the ground surface: `ground_row * TILE_SIZE - 20` (standing height_radius=20)
   or similar. The exact value depends on how collision resolution snaps the player.

7. **Level bounds**: With `level_height=10000`, death by falling through gaps won't trigger
   via `player_dead` (that's stage logic), but we can check `y > ground_row * TILE_SIZE + 200`.

## Constraints

- All probes must use synthetic grids only (no real stage data)
- Failing probes get `@pytest.mark.xfail(strict=True, reason="BUG: ...")`
- Bug tickets filed as `T-012-06-BUG-*.md`
- Test file: `tests/test_mechanic_probes.py`
- Must run clean with `uv run pytest tests/test_mechanic_probes.py -v`

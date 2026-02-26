# Structure — T-010-16: directional-terrain-raycast

## Files Modified

### `speednik/terrain.py`

**Add one public function** at the end of the file, before `resolve_collision` or after all
sensor-related code (between the sensor dispatch section and the collision resolution
section — after line ~495 and before line ~497).

Actually, place it in a new section between the solidity filters (line ~513) and the
quadrant direction tables (line ~517). Or better: create a new clearly-labeled section
right before the "Top-level collision resolution" section (before line 681).

```
# ---------------------------------------------------------------------------
# Directional terrain raycast (observation)
# ---------------------------------------------------------------------------

def cast_terrain_ray(
    tile_lookup: TileLookup,
    origin_x: float,
    origin_y: float,
    angle_deg: float,
    max_range: float = 128.0,
) -> tuple[float, int]:
```

**Internal helper** (module-private):

```
def _pixel_is_solid(tile_lookup: TileLookup, px: int, py: int) -> tuple[bool, int]:
    """Check if integer pixel (px, py) is inside solid terrain.
    Returns (is_solid, tile_angle).
    """
```

This helper encapsulates the tile-lookup + height-array check. It's used by
`cast_terrain_ray` at each step along the ray.

**No other functions in terrain.py are modified.** The existing sensor functions, collision
resolution, and all supporting code remain untouched.

**New import**: `math` is already imported (line 9). No new imports needed.

### `tests/test_terrain.py`

**Add one new test class**: `TestCastTerrainRay`

Tests exercise the function against synthetic tile grids:

1. **Flat ground, ray straight down (90°)** — known distance to surface
2. **Flat ground, ray horizontal (0°)** — should miss (no wall), return max_range
3. **Wall, ray horizontal (0°)** — known distance to wall
4. **Open air, any angle** — return (max_range, 0)
5. **Ray at 45° toward slope** — verify distance is geometrically correct
6. **Player inside solid** — first step hits, return (0 or very small, angle)
7. **Half-height tile, ray straight down** — distance to surface at mid-tile
8. **Surface angle propagation** — hit tile's angle is returned correctly
9. **Max range boundary** — surface at exactly max_range, surface beyond max_range

**New imports in test file**: `cast_terrain_ray` from terrain module.

---

## Files NOT Modified

- `speednik/observation.py` — wiring rays into the observation vector is T-010-17
- `speednik/env.py` — no changes (observation space dimension unchanged)
- `speednik/constants.py` — no new constants needed (max_range is a parameter, not a global)
- `speednik/physics.py` — unrelated
- `speednik/simulation.py` — unrelated

---

## Public Interface

### `cast_terrain_ray`

```python
def cast_terrain_ray(
    tile_lookup: TileLookup,
    origin_x: float,
    origin_y: float,
    angle_deg: float,
    max_range: float = 128.0,
) -> tuple[float, int]:
    """Cast a ray at an arbitrary angle, checking for solid terrain.

    Args:
        tile_lookup: Callable returning Tile at grid (tx, ty) or None.
        origin_x: Ray origin X in pixel coordinates.
        origin_y: Ray origin Y in pixel coordinates.
        angle_deg: Ray angle in degrees. 0=right, 90=down, 180=left, 270=up.
        max_range: Maximum ray distance in pixels.

    Returns:
        (distance, surface_angle) where:
        - distance: pixels from origin to first solid surface [0, max_range]
        - surface_angle: byte angle (0–255) of the hit tile, or 0 if none found
    """
```

### `_pixel_is_solid`

```python
def _pixel_is_solid(
    tile_lookup: TileLookup,
    px: int,
    py: int,
) -> tuple[bool, int]:
    """Test if integer pixel position is inside solid terrain.

    Returns (is_solid, tile_angle_byte). If not solid, tile_angle is 0.
    """
```

This is module-private (underscore prefix). Not exported, not tested directly — tested
indirectly through `cast_terrain_ray`.

---

## Module Boundary

The `cast_terrain_ray` function:
- **Depends on**: `TileLookup`, `Tile`, `TILE_SIZE`, `NOT_SOLID` — all in terrain.py
- **Depends on**: `math` (cos, sin, radians, floor, sqrt) — stdlib
- **Does NOT depend on**: PhysicsState, SensorResult, any sensor function, any constant
  from constants.py
- **Does NOT import**: Pyxel or any external package

The function is self-contained within terrain.py's existing abstraction layer.

---

## Ordering

1. Add `_pixel_is_solid` helper (small, foundational)
2. Add `cast_terrain_ray` (uses the helper)
3. Add test class with all test cases
4. Run full test suite to confirm no regressions

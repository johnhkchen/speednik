# Design — T-007-02: exempt-loop-tiles-from-wall-push

## Problem

Loop arc tiles can have steep angles (byte angle 49–207) that pass the wall angle gate
in `find_wall_push`. When a player's wall sensors hit these tiles — especially during
high-speed entry or at ramp/loop seams — the physics engine treats them as walls and
pushes the player back. The angle gate is necessary for general cases but insufficient
for loop geometry.

## Approach A: Tile-type propagation through SensorResult (Chosen)

Add `tile_type: int = 0` to `Tile` and `SensorResult`. Load `type` from tile_map.json
in `_build_tiles`. Propagate it through sensor casts. Check it in `find_wall_push`.

**Pros:**
- Minimal code change (one field added to two dataclasses, ~10 lines modified).
- The tile type info is available to any future consumer (ceiling sensors, floor sensors)
  without additional plumbing.
- Default value of 0 makes all existing code backward-compatible.
- Matches the ticket's specification exactly.

**Cons:**
- Every `SensorResult(found=True, ...)` site in the four cast functions needs updating
  to propagate `tile.tile_type`. There are many such sites (extension/regression branches).

## Approach B: Solidity-based exemption

Use a new solidity value (e.g., `LOOP_SOLID = 4`) for loop tiles and filter them out
in wall sensors' solidity filter.

**Rejected.** The solidity values come from collision.json, which is a separate grid
from tile_map.json. Changing solidity would affect floor and ceiling sensors too — loop
tiles must still be solid for floor/ceiling. Selective solidity filtering per sensor type
would be more complex than tile-type propagation.

## Approach C: Separate loop tile lookup

Maintain a parallel set/dict of loop tile coordinates. In `find_wall_push`, after finding
a hit, check if the hit tile's grid coordinates are in the loop set.

**Rejected.** The sensor cast functions don't expose which tile was hit (only distance
and angle). Recovering tile coordinates from sensor position and distance is fragile and
direction-dependent. Propagating coordinates through SensorResult would be more invasive
than propagating tile_type.

## Approach D: Tag loop tiles with a sentinel angle

Use an unused angle value to mark loop tiles, then filter on that angle.

**Rejected.** Angle values are meaningful physics data (0–255 byte angles). Using one as
a sentinel would corrupt the angle-based physics calculations. Loop tiles need real
angles for floor sensor snapping when the player is actually running the loop.

## Detailed Design for Approach A

### 1. `SURFACE_LOOP` constant

Add `SURFACE_LOOP = 5` to `speednik/terrain.py` alongside the existing solidity
constants. This keeps all tile-collision constants in one module. The value 5 matches
the pipeline tools (svg2stage.py, profile2stage.py).

### 2. `Tile.tile_type` field

```python
@dataclass
class Tile:
    height_array: list[int]
    angle: int
    solidity: int
    tile_type: int = 0
```

Default 0 means "unknown/unclassified". Existing constructors are unaffected.

### 3. `_build_tiles` in level.py

Read `cell.get("type", 0)` and pass to `Tile(tile_type=...)`. All three stages' cells
have the `type` field, but `.get()` with default is defensive.

### 4. `SensorResult.tile_type` field

```python
@dataclass
class SensorResult:
    found: bool
    distance: float
    tile_angle: int
    tile_type: int = 0
```

Default 0. All existing `SensorResult(found=False, ...)` sites are unaffected.

### 5. Sensor cast propagation

Every `SensorResult(found=True, distance=dist, tile_angle=X.angle)` site needs
`tile_type=X.tile_type` added. There are ~20 such sites across the four cast functions.
The `found=False` return sites don't need changes (default 0 is correct).

For regression/extension branches, the tile_type comes from whichever tile was actually
hit (tile_above, tile_below, tile_left, tile_right), not the original tile.

### 6. `find_wall_push` exemption

After the existing angle gate (lines 665–668), add:

```python
if result.tile_type == SURFACE_LOOP:
    return SensorResult(found=False, distance=0.0, tile_angle=0)
```

This runs only when `result.found` is True and the angle gate didn't already reject it.
Loop tiles are unconditionally exempt from wall push-back regardless of angle.

### 7. No changes to floor/ceiling sensors

Loop tiles must still function as floor and ceiling surfaces. The exemption is only in
`find_wall_push`. Floor/ceiling sensors ignore `tile_type`.

## Testing Strategy

Two new tests in `TestWallSensorAngleGate`:

1. **Loop tile at wall angle → not blocked:** Create a Tile with `angle=64` (wall-like)
   and `tile_type=SURFACE_LOOP`. `find_wall_push` should return `found=False`.

2. **Non-loop tile at same angle → blocked:** Same setup but `tile_type=1` (or default 0).
   `find_wall_push` should return `found=True` with negative distance (existing behavior).

These directly correspond to the ticket's last two acceptance criteria.

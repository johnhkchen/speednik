# Review — T-007-02: exempt-loop-tiles-from-wall-push

## Summary of Changes

### Files Modified

| File | Change |
|------|--------|
| `speednik/terrain.py` | Added `SURFACE_LOOP = 5` constant; added `tile_type: int = 0` to `Tile` and `SensorResult` dataclasses; propagated `tile_type` through all 22 `SensorResult(found=True)` sites across four sensor cast functions; added loop tile exemption in `find_wall_push` |
| `speednik/level.py` | Added `tile_type=cell.get("type", 0)` to `Tile` constructor in `_build_tiles` |
| `tests/test_terrain.py` | Added `SURFACE_LOOP` import; added 2 new tests to `TestWallSensorAngleGate` |

### Files NOT Modified

- `speednik/constants.py` — `SURFACE_LOOP` placed in `terrain.py` with other tile constants.
- `tools/svg2stage.py`, `tools/profile2stage.py` — pipeline tools define `SURFACE_LOOP`
  independently; no coupling introduced.
- `speednik/physics.py` — no changes needed.

## Acceptance Criteria Verification

- [x] `Tile` dataclass has `tile_type: int = 0` field — `terrain.py:62`
- [x] `_build_tiles` reads `type` from tile_map.json cells — `level.py:110`
- [x] `SensorResult` has `tile_type: int = 0` field — `terrain.py:89`
- [x] `_sensor_cast` functions set `tile_type` on hits — 22 sites across 4 functions
- [x] `find_wall_push` skips push-back for `SURFACE_LOOP` — `terrain.py:675–676`
- [x] `SURFACE_LOOP = 5` defined — `terrain.py:35`
- [x] Existing tests pass — 649 pre-existing tests pass (651 total - 2 new)
- [x] New test: loop tile at wall angle not treated as wall — `test_loop_tile_at_wall_angle_not_blocked`
- [x] New test: non-loop tile at same angle IS treated as wall — `test_non_loop_tile_at_wall_angle_blocked`

## Test Coverage

**New tests (2):**
- `test_loop_tile_at_wall_angle_not_blocked`: Creates a `Tile` with `angle=64`,
  `tile_type=SURFACE_LOOP`. Verifies `find_wall_push` returns `found=False`.
- `test_non_loop_tile_at_wall_angle_blocked`: Same setup with `tile_type=1`.
  Verifies `find_wall_push` returns `found=True` with negative distance.

**Existing tests (649):** All pass unchanged. The default `tile_type=0` means no
behavioral change for any test that doesn't explicitly set `tile_type`.

**Coverage gaps:**
- No integration test loading actual stage tile_map.json and verifying loop tiles have
  `tile_type=5`. This would be fragile (depends on stage data) and is covered implicitly
  by the pipeline tests in `test_svg2stage.py` and `test_profile2stage.py`.
- No test for left-wall sensor with loop tile. The exemption is in `find_wall_push`
  which is direction-agnostic (the check happens after the cast returns), so direction
  doesn't affect the tile_type filter.
- Floor/ceiling sensor tile_type propagation is tested implicitly (existing tests still
  pass), but no test explicitly asserts `result.tile_type` on floor/ceiling results.
  This is intentional — floor/ceiling sensors don't use tile_type for any logic.

## Design Decisions

1. **SURFACE_LOOP in terrain.py, not constants.py:** The constant is tile-collision
   specific and sits alongside `NOT_SOLID`, `TOP_ONLY`, `FULL`, `LRB_ONLY`. The
   constants.py module holds physics constants from the specification sections.

2. **Unconditional loop exemption in wall sensors:** The exemption fires for ALL loop
   tiles regardless of angle. This is intentional — loop tiles should never act as walls.
   If a loop tile happens to have a floor-range angle, the angle gate already catches it;
   if it has a wall-range angle, the tile_type check catches it.

3. **`.get("type", 0)` in level.py:** Defensive default even though all current tiles
   have the field. Protects against future stages or manual JSON editing.

## Open Concerns

- **Duplicate SURFACE_LOOP definitions:** The value 5 is defined in three places:
  `terrain.py`, `svg2stage.py`, and `profile2stage.py`. These are independent modules
  (runtime vs. pipeline tools) with no import path between them. If the value changes,
  all three must be updated. This is acceptable given the clear separation between
  pipeline and runtime.

- **tile_type propagation volume:** 22 `SensorResult` sites were modified. If a new
  field is added to `SensorResult` in the future, the same 22 sites need updating. This
  is inherent to the explicit-construction pattern used throughout terrain.py.

## Final Test Run

```
uv run pytest -x: 651 passed in 1.02s
```

# T-001-03 Plan: Tile Collision System

## Step 1: Tile data structure and width_array

**Create** `speednik/terrain.py` with:
- Solidity constants: NOT_SOLID, TOP_ONLY, FULL, LRB_ONLY
- Direction constants: DOWN, RIGHT, UP, LEFT
- TILE_SIZE = 16, MAX_SENSOR_RANGE = 32
- `Tile` dataclass with height_array, angle, solidity, width_array() method
- `SensorResult` dataclass
- `TileLookup` type alias

**Tests:**
- Tile with flat ground (all 16s): width_array is all 16s
- Tile with 45° slope [0,1,2,...,15]: width_array is the correct 90° rotation
- Tile with empty column: width_array handles 0s
- SensorResult construction

**Commit:** "Add tile data structures and width_array (T-001-03)"

## Step 2: Quadrant mapping

**Add** to terrain.py:
- `get_quadrant(angle: int) -> int` function
- Quadrant table for sensor direction lookup

**Tests:**
- All four quadrant ranges with interior values
- All four boundary transitions (32→33, 96→97, 160→161, 223→224)
- Edge cases: angle 0, angle 255

**Commit:** "Add angle quadrant mapping (T-001-03)"

## Step 3: Vertical sensor cast

**Add** to terrain.py:
- `_sensor_cast_down(sensor_x, sensor_y, tile_lookup, solidity_filter) -> SensorResult`
- `_sensor_cast_up(sensor_x, sensor_y, tile_lookup, solidity_filter) -> SensorResult`
- Height array lookup: given world X, find tile, find column within tile, read height
- Extension logic: height=0 at column → check tile below
- Regression logic: height=16 at column → check tile above
- Distance computation: sensor_y to detected surface y
- Range enforcement: reject if distance > MAX_SENSOR_RANGE

**Tests:**
- Sensor directly above flat ground (height 16 everywhere): correct distance
- Sensor above empty tile (height 0): extends to tile below
- Sensor above full tile (height 16): regresses to tile above
- Sensor above 45° slope: distance varies by column
- Sensor too far from any tile: found=False
- Top-only filter: solidity_filter rejects/accepts based on flag

**Commit:** "Add vertical sensor cast with extension/regression (T-001-03)"

## Step 4: Horizontal sensor cast

**Add** to terrain.py:
- `_sensor_cast_left(sensor_x, sensor_y, tile_lookup, solidity_filter) -> SensorResult`
- `_sensor_cast_right(sensor_x, sensor_y, tile_lookup, solidity_filter) -> SensorResult`
- Same logic as vertical but uses width_array and horizontal axis
- Extension/regression along horizontal axis

**Tests:**
- Sensor to the left of a full wall: correct distance
- Sensor to the right of a wall: correct distance
- Extension/regression for walls
- Width_array correctly used for slope walls

**Commit:** "Add horizontal sensor cast for wall detection (T-001-03)"

## Step 5: Floor sensor resolution (A/B)

**Add** to terrain.py:
- `find_floor(state, tile_lookup) -> SensorResult`
- Compute A and B positions from state.x, state.y, quadrant, radii
- Cast both in floor direction for current quadrant
- Apply top-only filter (skip when y_vel < 0)
- Return shorter distance; A wins ties

**Tests:**
- Standing on flat ground: correct snap position
- Tile boundary crossing: A on tile N, B on tile N+1
- A wins ties: both sensors equidistant, A's angle used
- Top-only platform: y_vel < 0 → pass through; y_vel >= 0 → collide
- Different quadrants: verify sensor positions rotate correctly

**Commit:** "Add floor sensor resolution with A-wins-ties (T-001-03)"

## Step 6: Ceiling sensor resolution (C/D)

**Add** to terrain.py:
- `find_ceiling(state, tile_lookup) -> SensorResult`
- Mirror of find_floor but casting in ceiling direction
- TOP_ONLY tiles never collide with ceiling
- Return shorter of C/D

**Tests:**
- Jumping into ceiling: detected, correct distance
- No ceiling above: found=False
- Top-only ceiling: ignored

**Commit:** "Add ceiling sensor resolution (T-001-03)"

## Step 7: Wall sensor resolution (E/F)

**Add** to terrain.py:
- `find_wall_push(state, tile_lookup, direction) -> SensorResult`
- E sensor casts left, F sensor casts right
- Disabled when moving away from wall (check velocity)
- Uses current width_radius for position

**Tests:**
- Wall on right, moving right: detected, push left
- Wall on right, moving left: sensor disabled
- Rolling: narrower detection
- Wall both sides: both detected independently

**Commit:** "Add wall sensor resolution (T-001-03)"

## Step 8: Collision resolution (resolve_collision)

**Add** to terrain.py:
- `resolve_collision(state, tile_lookup) -> None`
- Full integration: floor → wall → ceiling priority
- Landing: air → ground transition with angle snap and calculate_landing_speed()
- Detachment: ground → air when no floor found
- Wall push: zero velocity toward wall
- Ceiling hit: push down, zero upward velocity

**Tests:**
- Walking on flat ground: stays grounded, correct y
- Walking off ledge: detaches, enters air
- Landing from air: snaps angle, recalculates speed
- 45° slope adherence: angle continuously updated
- Wall collision: pushed out, velocity zeroed
- Ceiling collision: pushed down, y_vel zeroed
- Top-only pass-through from below
- Loop traversal (all four quadrants): angle rotates through 0→64→128→192→0

**Commit:** "Add collision resolution with landing and detachment (T-001-03)"

## Step 9: Integration verification

- Run full test suite (`uv run pytest`) — all tests pass
- Verify no regressions in test_physics.py
- Verify terrain.py imports work correctly

**Commit:** None (verification only, unless fixes needed)

## Testing Strategy

- **Unit tests per function:** Each sensor cast function tested in isolation with hand-crafted tile maps
- **Tile map fixtures:** Helper function that creates a TileLookup from a dict of (tx, ty) → Tile
- **Integration tests:** resolve_collision tested with multi-tile scenarios
- **No mocking:** All tests use real Tile objects and real tile lookup functions
- **Target:** ~30-40 tests covering all acceptance criteria items

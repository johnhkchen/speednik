# Plan — T-001-04: Player Module

## Step 1: Add Player Constants

**File:** `speednik/constants.py`
**Changes:** Append 5 new constants for damage/invulnerability system.
**Verification:** Existing 98 tests still pass (`uv run pytest`).

## Step 2: Create Player Module Core

**File:** `speednik/player.py`
**Changes:**
- `PlayerState` enum (7 states)
- `ScatteredRing` dataclass
- `Player` dataclass (owns PhysicsState + game state)
- `create_player(x, y)` factory function

**Verification:** Module imports without error.

## Step 3: Implement Frame Update Orchestration

**File:** `speednik/player.py`
**Changes:**
- `player_update(player, inp, tile_lookup)` — the main frame function
- Calls physics steps 1–4 in order, then `resolve_collision`, then `update_slip_timer`
- Calls `_pre_physics` and `_post_physics` for state machine transitions

**Verification:** Unit test: create player on flat ground, call update with right input, verify position advances.

## Step 4: Implement Pre-Physics State Machine

**File:** `speednik/player.py`
**Changes:** `_pre_physics(player, inp)`:
- Jump initiation from STANDING/RUNNING/ROLLING
- Roll start from STANDING/RUNNING when down + speed threshold
- Spindash enter (down held while standing still)
- Spindash charge (jump pressed during spindash)
- Spindash release (down released during spindash)
- Variable jump height (jump released while airborne)

**Verification:** Unit tests for each transition.

## Step 5: Implement Post-Physics State Sync

**File:** `speednik/player.py`
**Changes:** `_post_physics(player)`:
- JUMPING + on_ground → STANDING or RUNNING (based on ground_speed)
- Ground state + !on_ground → JUMPING (walked off edge)
- ROLLING + !is_rolling (physics unrolled) → STANDING
- HURT + on_ground + invulnerability expired → STANDING

**Verification:** Unit tests for landing, edge detach, unroll sync.

## Step 6: Implement Damage System

**File:** `speednik/player.py`
**Changes:**
- `damage_player(player)`: check invulnerability, scatter rings or die
- `_scatter_rings(player)`: create ScatteredRing objects in fan pattern
- `_update_scattered_rings(player)`: gravity, timer, removal
- `_collect_scattered_ring(player, index)`: recollect ring
- Ring collection check in `player_update` (distance test each frame)

**Verification:** Unit tests: damage with rings scatters, damage without rings kills, invulnerability prevents damage, scattered rings move and expire.

## Step 7: Implement Animation State

**File:** `speednik/player.py`
**Changes:**
- `_update_animation(player)`: set anim name from state, advance timer/frame
- Running animation speed scales with |ground_speed|
- `get_player_rect(player)`: return position and current hitbox dimensions

**Verification:** Unit tests: correct anim name per state, frame advances.

## Step 8: Write Full Test Suite

**File:** `tests/test_player.py`
**Changes:** Complete test suite (~300 lines):
- TestCreatePlayer (2 tests)
- TestStateTransitions (8 tests)
- TestSpindashFlow (4 tests)
- TestJumpFlow (4 tests)
- TestRollFlow (3 tests)
- TestDamage (5 tests)
- TestAnimationState (3 tests)
- TestScatteredRings (3 tests)

**Verification:** All new tests pass. All 98 existing tests still pass. Total ~130 tests.

## Step 9: Implement Demo Mode

**File:** `speednik/main.py`
**Changes:**
- Hardcode demo level: 30+ flat tiles, 5 slope tiles, ~8 loop tiles
- Create Player at start position
- Map Pyxel input to InputState each frame
- Call player_update in App.update()
- Draw colored rect for player, tile outlines for level, debug text HUD
- Initialize and update audio
- Arrow keys + Z for jump + Q to quit

**Verification:** `uv run python -m speednik.main` launches, player moves on flat ground, jumps, rolls, traverses slope. Visual confirmation only.

## Step 10: Final Regression

**Verification:** `uv run pytest` — all tests pass (existing 98 + new ~32).

## Testing Strategy

**Unit tested (Pyxel-free):**
- All player state transitions
- Frame update ordering (mock tile_lookup)
- Spindash charge/release mechanics
- Damage and ring scatter
- Animation state tracking

**Not unit tested (visual/integration):**
- Demo level rendering
- Pyxel input mapping
- Audio playback

**Test pattern:** Same as existing — pytest, dataclass factories, dict-based tile lookups. No mocking framework needed; physics and terrain functions are pure.

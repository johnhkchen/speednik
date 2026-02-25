# Progress — T-001-04: Player Module

## Completed Steps

### Step 1: Add Player Constants
- Added 5 constants to `speednik/constants.py`: INVULNERABILITY_DURATION, MAX_SCATTER_RINGS, SCATTER_RING_LIFETIME, HURT_KNOCKBACK_X, HURT_KNOCKBACK_Y
- All 98 existing tests pass after change

### Step 2: Create Player Module Core
- Created `speednik/player.py` with PlayerState enum (7 states), ScatteredRing dataclass, Player dataclass, create_player() factory
- Module imports cleanly

### Step 3: Implement Frame Update Orchestration
- Implemented `player_update()` calling physics steps 1–4, resolve_collision, update_slip_timer in correct order
- Pre/post physics state machine hooks integrated

### Step 4: Implement Pre-Physics State Machine
- Jump initiation from STANDING/RUNNING/ROLLING
- Roll start from STANDING/RUNNING when down + speed threshold
- Spindash enter (down held while standing still)
- Spindash charge (jump pressed during spindash)
- Spindash decay (each frame while holding)
- Spindash release (down released)
- Variable jump height (jump released while airborne)
- HURT state blocks input

### Step 5: Implement Post-Physics State Sync
- JUMPING + on_ground → STANDING/RUNNING/ROLLING
- Ground state + !on_ground → JUMPING (edge walk-off)
- ROLLING + !is_rolling → STANDING (physics unroll)
- HURT + on_ground + invulnerability expired → STANDING
- STANDING ↔ RUNNING sync based on ground_speed

### Step 6: Implement Damage System
- damage_player(): invulnerability check, ring scatter or death
- _scatter_rings(): fan pattern, up to 32 rings
- _update_scattered_rings(): gravity, timer, removal
- _check_ring_collection(): distance-based collection (16px radius)

### Step 7: Implement Animation State
- _update_animation(): state→anim mapping, running frame advance
- Running animation speed scales with |ground_speed|
- Frame/timer reset on anim change
- get_player_rect(): hitbox dimensions for rendering

### Step 8: Write Full Test Suite
- Created `tests/test_player.py` with 32 tests across 9 test classes
- All 130 tests pass (98 existing + 32 new)

### Step 9: Implement Demo Mode
- Rewrote `speednik/main.py` with demo level:
  - 50 tiles of flat ground at y=12
  - 4 slope tiles at y=11 (15°–25° angles)
  - Player colored rectangle, tile rendering, debug HUD
  - Simple horizontal camera following player
  - Arrow keys + Z for jump + Q to quit
  - Audio initialization and per-frame update

### Step 10: Final Regression
- `uv run pytest tests/ -v`: 130 passed in 0.03s
- No deviations from plan

## Deviations

None. All steps executed as planned.

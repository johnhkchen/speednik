# Design — T-012-05: Cross-Stage Behavioral Invariants

## Design Decision: Test Architecture

### Option A: Use run_audit() from qa.py
Run full archetype playthroughs and check for specific events/states afterward.
- Pro: Reuses existing audit infrastructure
- Con: Non-deterministic enemy encounters; hard to isolate single invariants; slow (3600 frames per test)
- Rejected: Audit tests already exist in test_audit_*.py. Behavioral invariants need surgical precision.

### Option B: Direct sim_step with scripted setups (Chosen)
Each invariant gets a focused test that sets up the exact conditions, steps a minimal number of frames, and asserts on the specific outcome.
- Pro: Fast, deterministic, isolates exactly one behavior, clear failure messages
- Pro: Parametrized across stages via `@pytest.mark.parametrize("stage", STAGES)`
- Pro: Each test is self-contained — failures pinpoint the broken invariant
- Con: More setup code per test
- Decision: The setup cost is low given existing helpers. Precision matters more than brevity.

### Option C: Hybrid (audit + targeted)
Run audit for trajectory, then assert on specific invariants within the trajectory.
- Rejected: Mixes concerns. Audit tests check progression, invariant tests check physics laws.

## Per-Invariant Design

### 1. Damage with rings scatters (not kills)
- Setup: `create_sim(stage)`, set `player.rings = 5`, inject buzzer at dx=40
- Run: hold right until DamageEvent (max 300 frames)
- Assert: state is HURT (not DEAD), rings == 0, scattered_rings non-empty
- Parametrize: all 3 stages

### 2. Damage without rings kills
- Setup: `create_sim(stage)`, set `player.rings = 0`, inject buzzer at dx=40
- Run: hold right until DeathEvent or max frames
- Assert: player_dead is True, deaths == 1
- Parametrize: all 3 stages

### 3. Invulnerability after damage
- Setup: `create_sim(stage)`, set `player.rings = 10`, inject buzzer at dx=40
- Run: hold right until first DamageEvent
- Then: inject second buzzer at dx=40 from current position
- Run: step 119 more frames (within i-frame window), hold right
- Assert: no second DamageEvent in those 119 frames
- Parametrize: all 3 stages

### 4. Wall recovery
- Setup: `create_sim(stage)`, hold right to build speed
- Detection: monitor for ground_speed dropping to ~0 while on_ground (stall)
- After stall: send jump input
- Assert: player leaves the ground (on_ground becomes False), proving not stuck
- Parametrize: all 3 stages (each stage has walls)
- Fallback: if no natural wall stall found, use a flat grid with injected wall

### 5. Slope adhesion at low speed
- Setup: `create_sim(stage)`, teleport to a known slope location per stage
- Walk slowly (tap right) onto gentle slope
- Assert: on_ground stays True, y position changes (follows slope)
- Parametrize: all 3 stages with per-stage slope positions
- Note: Need to find gentle slopes (angle < 20 byte-angle ≈ < 28°) per stage

### 6. Fall death below level bounds
- Setup: `create_sim(stage)`, teleport player below level_height + 64
- Step a few frames
- Assert: either player_dead is True OR player.state == DEAD
- Note: sim doesn't auto-kill on fall. We need to check if the invariant checker's
  `position_y_below_world` catches this. If the engine doesn't kill the player,
  we document it as expected behavior and test the boundary detection instead.
- Alternative: verify the position invariant fires, asserting the engine at least
  detects the impossible state even if it doesn't auto-kill.

### 7. Spindash speed
- Setup: `create_sim(stage)`, scripted inputs: down_held for 1 frame (enter spindash),
  then jump_pressed+down_held for 3 frames (charge), then release (right only)
- Assert: ground_speed ≥ SPINDASH_BASE_SPEED (8.0) on the release frame
- Parametrize: all 3 stages

### 8. Camera tracking
- Approach: Implement a minimal camera model using the constants from constants.py
- Camera follows player: if player.x > camera.x + CAMERA_RIGHT_BORDER, camera scrolls right
- After running a walker for N frames, verify player.x is always within
  [camera.x, camera.x + SCREEN_WIDTH]
- Parametrize: all 3 stages
- Constants: CAMERA_LEFT_BORDER=144, CAMERA_RIGHT_BORDER=160, SCREEN_WIDTH=256, CAMERA_H_SCROLL_CAP=16

## Test Organization

```
STAGES = ["hillside", "pipeworks", "skybridge"]

@pytest.mark.parametrize("stage", STAGES)
def test_damage_with_rings_scatters(stage): ...

@pytest.mark.parametrize("stage", STAGES)
def test_damage_without_rings_kills(stage): ...
# ... 8 total invariants
```

## Bug Ticket Policy

If any invariant fails on a specific stage, file `T-012-05-BUG-XX.md` with:
- Which invariant failed
- Which stage(s)
- Observed vs expected behavior
- Root cause if determinable

No xfail in this file — the ticket says "All failures are bugs."
However, if the engine genuinely doesn't implement a feature (like auto-kill on fall),
we adapt the test to verify the closest available behavior.

## Dependencies

- `speednik.simulation`: create_sim, sim_step, DamageEvent, DeathEvent, SpringEvent
- `speednik.physics`: InputState
- `speednik.player`: PlayerState
- `speednik.constants`: INVULNERABILITY_DURATION, SPINDASH_BASE_SPEED, SCREEN_WIDTH, CAMERA_*
- `speednik.enemies`: Enemy
- `tests.test_entity_interactions`: borrow helper patterns (_place_buzzer, _run_frames, _run_until_event)

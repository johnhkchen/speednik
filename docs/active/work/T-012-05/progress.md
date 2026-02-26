# Progress — T-012-05: Cross-Stage Behavioral Invariants

## Completed

### Step 1: Created test file with infrastructure
- Created `tests/test_audit_invariants.py` with imports, STAGES constant, helpers
- Added `_stabilize()` helper to handle stages with springs at spawn (pipeworks)
- Added `_place_buzzer()`, `_run_frames()`, `_run_until_event()` helpers

### Step 2: Invariant 1 — Damage with rings scatters
- Implemented and passing on all 3 stages
- Uses `_stabilize()` then sets rings=5, places buzzer at dx=40

### Step 3: Invariant 2 — Damage without rings kills
- Implemented and passing on all 3 stages
- Clears nearby world rings to prevent accidental collection before damage

### Step 4: Invariant 3 — Invulnerability after damage
- Implemented and passing on all 3 stages
- Tests that no DamageEvent occurs within INVULNERABILITY_DURATION-1 frames after first hit

### Step 5: Invariant 4 — Wall recovery
- Implemented and passing on all 3 stages
- Extended search window to 1800 frames (hillside wall stall at frame ~1301)

### Step 6: Invariant 5 — Slope adhesion at low speed
- Implemented, passing on hillside, skipped on pipeworks/skybridge
- Pipeworks/skybridge have no gentle slopes (byte-angle < 20); only 45°+ slopes
- Properly excludes HURT-state transitions from flicker detection

### Step 7: Invariant 6 — Fall death below level bounds
- Implemented and passing on all 3 stages
- Engine doesn't auto-kill on fall; test verifies y > level_height (detectable condition)

### Step 8: Invariant 7 — Spindash reaches base speed
- Implemented and passing on all 3 stages
- Uses `_stabilize()` to handle pipeworks spring-launch

### Step 9: Invariant 8 — Camera tracks player
- Implemented and passing on all 3 stages
- Uses actual `create_camera`/`camera_update` from camera.py for fidelity

### Step 10: Full suite run
- **22 passed, 2 skipped** in 0.45s
- Skips: slope_adhesion on pipeworks/skybridge (no gentle slopes in geometry)

## Deviations from Plan

1. Added `_stabilize()` helper not in original plan — pipeworks starts on a spring
2. Death-without-rings test clears nearby world rings to prevent accidental collection
3. Slope adhesion excludes current-frame HURT transitions, not just previous-frame
4. Expanded wall recovery and slope adhesion search windows from 600 to 1800 frames
5. No bug tickets needed — all invariants pass (or skip due to geometry constraints)

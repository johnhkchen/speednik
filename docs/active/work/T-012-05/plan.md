# Plan — T-012-05: Cross-Stage Behavioral Invariants

## Step 1: Create test file with imports, constants, and helpers

Create `tests/test_audit_invariants.py` with:
- Module docstring
- All imports
- `STAGES = ["hillside", "pipeworks", "skybridge"]`
- Helper functions: `_place_buzzer`, `_run_frames`, `_run_until_event`

Verify: file imports cleanly (`python -c "import tests.test_audit_invariants"`)

## Step 2: Implement invariant 1 — Damage with rings scatters

```
@pytest.mark.parametrize("stage", STAGES)
def test_damage_with_rings_scatters(stage):
```
- create_sim, set rings=5, inject buzzer, run until DamageEvent
- Assert: HURT not DEAD, rings==0, scattered_rings non-empty

Verify: `uv run pytest tests/test_audit_invariants.py::test_damage_with_rings_scatters -v`

## Step 3: Implement invariant 2 — Damage without rings kills

```
@pytest.mark.parametrize("stage", STAGES)
def test_damage_without_rings_kills(stage):
```
- create_sim, set rings=0, inject buzzer, run until dead
- Assert: player_dead, deaths==1

Verify: `uv run pytest tests/test_audit_invariants.py::test_damage_without_rings_kills -v`

## Step 4: Implement invariant 3 — Invulnerability after damage

```
@pytest.mark.parametrize("stage", STAGES)
def test_invulnerability_after_damage(stage):
```
- create_sim, set rings=10, inject buzzer, run until first DamageEvent
- Inject second buzzer, run 119 frames (within i-frame window)
- Assert: no second DamageEvent

Verify: `uv run pytest tests/test_audit_invariants.py::test_invulnerability_after_damage -v`

## Step 5: Implement invariant 4 — Wall recovery

```
@pytest.mark.parametrize("stage", STAGES)
def test_wall_recovery(stage):
```
- create_sim, build speed (hold right), detect stall (ground_speed near 0 while on_ground after moving)
- After stall, send jump input
- Assert: player leaves ground (can escape)
- If no natural stall found, use a synthetic grid with injected wall

Verify: `uv run pytest tests/test_audit_invariants.py::test_wall_recovery -v`

## Step 6: Implement invariant 5 — Slope adhesion at low speed

```
@pytest.mark.parametrize("stage", STAGES)
def test_slope_adhesion_at_low_speed(stage):
```
- create_sim, walk slowly on a gentle slope
- Assert: on_ground stays True, y changes

Verify: `uv run pytest tests/test_audit_invariants.py::test_slope_adhesion_at_low_speed -v`

## Step 7: Implement invariant 6 — Fall death below level bounds

```
@pytest.mark.parametrize("stage", STAGES)
def test_fall_below_level_bounds(stage):
```
- create_sim, teleport player below level_height
- Step frames, check player dies or engine detects impossible position
- If engine doesn't auto-kill, assert the invariant checker catches it

Verify: `uv run pytest tests/test_audit_invariants.py::test_fall_below_level_bounds -v`

## Step 8: Implement invariant 7 — Spindash reaches base speed

```
@pytest.mark.parametrize("stage", STAGES)
def test_spindash_reaches_base_speed(stage):
```
- create_sim, scripted spindash inputs (crouch, charge 3x, release)
- Assert: ground_speed ≥ SPINDASH_BASE_SPEED on release

Verify: `uv run pytest tests/test_audit_invariants.py::test_spindash_reaches_base_speed -v`

## Step 9: Implement invariant 8 — Camera tracks player

```
@pytest.mark.parametrize("stage", STAGES)
def test_camera_tracks_player(stage):
```
- create_sim, run walker for 600 frames, compute camera.x from player trajectory
- Assert: player is always within [camera_x, camera_x + SCREEN_WIDTH]

Verify: `uv run pytest tests/test_audit_invariants.py::test_camera_tracks_player -v`

## Step 10: Full test suite run

Run all invariant tests together:
```
uv run pytest tests/test_audit_invariants.py -v
```

Expected: 24 test cases (8 × 3 stages) all pass.
If any fail, investigate root cause and file bug tickets.

## Testing Strategy

- **Unit scope**: Each test isolates a single behavioral invariant
- **Parametrization**: Every invariant runs on all 3 stages
- **Determinism**: Scripted inputs, injected entities, no randomness
- **Speed**: Each test runs ≤ 600 frames (≤ 10 seconds at worst)
- **Bug tickets**: Any failure gets T-012-05-BUG-XX.md with analysis

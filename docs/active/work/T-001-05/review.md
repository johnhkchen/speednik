# Review — T-001-05: Camera System

## Summary of Changes

### Files Created
- **`speednik/camera.py`** (149 lines) — Camera module with `Camera` dataclass, `create_camera()` factory, `camera_update()` main function, and internal helpers for horizontal tracking, vertical tracking, look up/down, and boundary clamping.
- **`tests/test_camera.py`** (225 lines) — 25 unit tests across 6 test classes covering all camera behaviors.
- **`docs/active/work/T-001-05/`** — RDSPI artifacts: research.md, design.md, structure.md, plan.md, progress.md, review.md.

### Files Modified
- **`speednik/constants.py`** — Added 12 camera constants (horizontal borders, vertical scroll caps, focal point, air borders, look parameters, ground speed threshold).
- **`speednik/physics.py`** — Added `up_held: bool = False` to `InputState` dataclass. Single line, backward compatible.
- **`speednik/main.py`** — Replaced placeholder lerp camera with full Sonic 2 camera system. Switched from manual `cam_x` subtraction to `pyxel.camera()`. Added vertical viewport culling. Added up arrow input reading. Updated HUD help text.

## Acceptance Criteria Evaluation

| Criterion | Status | Notes |
|-----------|--------|-------|
| Horizontal borders: left 144px, right 160px | Done | Tested: dead zone, scroll left/right, cap at 16px |
| Horizontal scroll cap: 16px/frame | Done | Tested: large delta clamped |
| Vertical focal point: 96px | Done | Tested: ground scroll converges to focal |
| Airborne vertical borders: ±32px | Done | Tested: within borders → no scroll, outside → scroll |
| Airborne vertical scroll cap: 16px/frame | Done | Tested: cap enforced |
| Ground vertical scroll: 6px (slow) / 16px (fast) | Done | Tested: speed threshold at ground_speed 8.0 |
| Look up: -104px at 2px/step | Done | Tested: accumulation, clamping |
| Look down: +88px at 2px/step | Done | Tested: accumulation, clamping |
| Look release: return at 2px/step | Done | Tested: offset returns to 0 |
| Camera bounded to level dimensions | Done | Tested: all 4 edges + small level |
| Integrates with `pyxel.camera()` | Done | main.py uses `pyxel.camera(x, y)` + reset for HUD |
| Smooth tracking (no jitter) | Done | Border-based system prevents jitter by design; scroll caps ensure smooth motion |
| Works with T-001-04 player demo | Done | main.py integrates camera with player update loop |

## Test Coverage

- **25 unit tests** in `tests/test_camera.py`
- **All 225 tests pass** across the full suite
- Camera logic is pure math — zero Pyxel dependency in tests
- Test helper `make_player()` creates players with targeted physics state for precise testing
- Edge cases covered: small levels, boundary clamping, scroll caps, standing-only look constraint

### Coverage gaps
- No explicit test for look up/down interacting with vertical scroll (look_offset feeds into vertical calculation, but tested indirectly through the update flow)
- No negative level dimension test (unlikely scenario, handled by `max(0, ...)`)

## Architecture Notes

- Camera follows the established codebase pattern: dataclass + module-level functions
- Camera only reads player state, never writes to it (clean unidirectional dependency)
- `camera.py` imports from `player.py` only for the `Player` type — could be further decoupled by passing primitives instead, but this matches the existing style and avoids unnecessary API churn
- `pyxel.camera()` integration is confined to `main.py` — the camera module is Pyxel-free

## Open Concerns

1. **Demo level is very small** — vertical camera behavior barely exercises because the level height (208px) is less than the screen height (224px). The camera correctly clamps to y=0 in this case, but full vertical testing requires a taller level (which will come with future stage tickets).

2. **Look up/down only activates when `ground_speed == 0.0`** — This is a strict float equality check. In practice, friction in physics.py drives ground_speed to exactly 0.0, so this works. But if a future change causes ground_speed to settle at a very small epsilon, look would never activate. Could use `abs(ground_speed) < epsilon` if this becomes an issue.

3. **No audio feedback for look up/down** — Sonic 2 plays a subtle sound when looking up/down. Not in the AC for this ticket, so omitted.

4. **Camera initialization positions player at left border** — The factory uses `start_x - CAMERA_LEFT_BORDER` for initial camera x. This means the player starts at the left border (144px from left), not centered. This matches Sonic 2 behavior where the camera is slightly biased toward showing what's ahead, but could feel off at the very start of a level.

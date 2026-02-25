# Review — T-009-01: debug-flag-and-hud-overlay

## Summary of Changes

### Files Created
- **`speednik/debug.py`** (5 lines) — Single `DEBUG` constant read from `SPEEDNIK_DEBUG` env var.
- **`tests/test_debug.py`** (~100 lines) — 14 tests covering the debug flag and HUD overlay.

### Files Modified
- **`speednik/renderer.py`** — Added `draw_debug_hud(player, frame_counter)` function (~10 lines). Renders 3 lines of debug text in the top-right area (x=136, y=14/22/30) showing F, X, Y, GS, A, Q, STATE, GND.
- **`speednik/main.py`** — Four changes:
  1. Import `DEBUG` from `speednik.debug`.
  2. Stage select navigation and rendering now includes a "DEV PARK" entry (stage 0) when `DEBUG` is True.
  3. New "dev_park" state added to both update/draw dispatchers with placeholder screen.
  4. Debug HUD rendered during gameplay when `DEBUG` is True.

## Test Coverage

| Component | Tests | Coverage |
|-----------|-------|----------|
| `DEBUG` flag (env=unset) | `test_debug_false_by_default` | Default behavior |
| `DEBUG` flag (env="1") | `test_debug_true_when_set` | Enabled path |
| `DEBUG` flag (env="0") | `test_debug_false_when_zero` | Explicit disable |
| `DEBUG` flag (env="") | `test_debug_false_when_empty` | Edge case |
| HUD line count | `test_draws_three_lines` | 3 pyxel.text calls |
| HUD frame counter | `test_shows_frame_counter` | F: field |
| HUD position | `test_shows_position` | X:, Y: fields |
| HUD ground speed | `test_shows_ground_speed` | GS: field |
| HUD angle/quadrant | `test_shows_angle_and_quadrant` | A:, Q: fields |
| HUD state | `test_shows_state` | STATE: field |
| HUD ground flag | `test_shows_ground_flag_yes/no` | GND:Y / GND:N |
| HUD screen position | `test_positioned_in_top_right` | x >= 136 |
| HUD below main HUD | `test_positioned_below_main_hud` | y >= 14 |

**Full suite**: 773 passed, 2 xfailed (pre-existing). Zero regressions.

## Coverage Gaps

- **Stage select navigation with DEV PARK**: Not unit-tested (requires Pyxel initialization for `App` class). The logic is straightforward conditional branching. Verifiable manually with `SPEEDNIK_DEBUG=1 uv run python -m speednik.main`.
- **Dev park placeholder state**: Not unit-tested for same reason. The placeholder is trivial (two text draws + return on Z).
- **Integration between DEBUG flag and main.py**: The `if DEBUG:` guard in `_draw_gameplay` is not tested in isolation. Since `DEBUG` defaults to `False`, all existing rendering tests pass unchanged.

## Acceptance Criteria Verification

- [x] `SPEEDNIK_DEBUG=1` enables debug features; unset or `0` disables them — tested in `TestDebugFlag`.
- [x] Debug HUD renders during gameplay showing F, X, Y, GS, A, Q, STATE, GND — tested in `TestDebugHUD`.
- [x] Debug HUD does not overlap the existing lives/rings/time HUD — positioned at y=14+ (main HUD at y=4), x=136+ (main HUD at x=4–208). Tested in `test_positioned_*`.
- [x] Debug HUD only appears when DEBUG is True — guarded by `if DEBUG:` in `_draw_gameplay`.
- [x] Stage select shows "DEV PARK" entry when DEBUG is True — conditional rendering added.
- [x] Stage select hides "DEV PARK" when DEBUG is False — `if DEBUG:` guard.
- [x] "DEV PARK" is always selectable (not gated by unlocked_stages) — navigation allows reaching stage 0 regardless of unlock state.
- [x] Selecting "DEV PARK" transitions to a dev park state (placeholder) — shows "DEV PARK" centered text.
- [x] No behavior changes when SPEEDNIK_DEBUG is unset — `DEBUG` is `False`, all debug codepaths skipped.
- [x] `uv run pytest tests/ -x` passes — 773 passed.

## Open Concerns

- **None blocking.** The implementation is minimal and self-contained.
- The DEV PARK placeholder is intentionally bare — T-009-03 will implement the actual dev park stages.
- The debug HUD uses hardcoded x=136 positioning. If the existing HUD layout changes (e.g., wider timer display), the gap might shrink. Not a concern until it happens.

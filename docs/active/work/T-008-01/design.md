# Design — T-008-01: scenario-runner-and-strategies

## Decision: Module Location

**Chosen:** `tests/harness.py` — a plain Python module (no `test_` prefix) in the tests
directory, imported by test files.

**Rejected:** `tests/conftest.py` fixtures — fixtures add pytest coupling and make it
harder to use the runner from non-test scripts. The ticket explicitly prefers a plain
module.

**Rejected:** `speednik/testing/` package — over-engineering for what's essentially test
infrastructure. Keeps game code and test harness cleanly separated.

## Decision: Strategy Implementation Style

**Chosen:** Factory functions that return `Callable[[int, Player], InputState]`. Each
factory returns a closure. Strategies that need internal state (like `hold_right_jump`
and `spindash_right`) use mutable closure variables. `idle`, `hold_right`, and
`scripted` are stateless or state-from-args only.

```python
def hold_right() -> Callable[[int, Player], InputState]:
    def strategy(frame: int, player: Player) -> InputState:
        return InputState(right=True)
    return strategy
```

**Rejected:** Class-based strategies — adds boilerplate for something closures handle
cleanly. Classes would be warranted if strategies needed serialization or introspection,
but they don't.

**Rejected:** Bare functions (not factories) — works for stateless strategies but breaks
for stateful ones like `hold_right_jump` (needs to track `was_airborne`). Using
factories consistently for all strategies keeps the API uniform.

## Decision: FrameSnapshot Capture

**Chosen:** Capture snapshot *after* `player_update` each frame. The snapshot reflects
the state at the end of the frame, which is the observable game state. Quadrant is
computed at capture time via `get_quadrant(player.physics.angle)`.

**Rejected:** Capture before update — less useful; you'd see pre-collision state that
doesn't reflect what the player "sees" on screen.

## Decision: `stuck_at` Algorithm

**Chosen:** Sliding window approach. Scan snapshots with a window (default 30 frames).
If `max(x) - min(x) < tolerance` within any window, return the average X of that window.
Return None if no stuck window found.

This is simple, deterministic, and detects the right thing: sustained lack of horizontal
progress. The window size could be a parameter but a hardcoded 30 frames is reasonable
for 60fps gameplay.

**Rejected:** Derivative-based (speed < threshold for N frames) — overly sensitive to
momentary pauses (spindash charging, landing lag). Position-based is more robust.

## Decision: `run_on_stage` Signature

**Chosen:** Simple helper that composes `load_stage` + `create_player` + `run_scenario`:

```python
def run_on_stage(
    stage_name: str,
    strategy: Callable[[int, Player], InputState],
    frames: int = 600,
) -> ScenarioResult:
```

No `on_ground` parameter — real stages always start on ground at `player_start`. The
`on_ground` param in `run_scenario` is for synthetic tile setups.

## Decision: Self-Tests

**Chosen:** Put self-tests in a new `tests/test_harness.py` file, not inside
`tests/harness.py`. Keeps the harness module clean and importable. Tests will exercise:
1. `idle` on flat ground → player stays grounded 60 frames
2. `hold_right` on flat ground → player X advances
3. `FrameSnapshot` field access
4. `ScenarioResult` helper properties (`max_x`, `final`, `quadrants_visited`, `stuck_at`)

## Design: Spindash Strategy State Machine

The `spindash_right` strategy operates as a mini state machine within its closure:

1. **CROUCH** phase: emit `down_held=True` for 1 frame → enters SPINDASH
2. **CHARGE** phase: emit `down_held=True, jump_pressed=True` for N frames
3. **RELEASE** phase: emit `down_held=False` for 1 frame → enters ROLLING
4. **RUN** phase: emit `right=True` until `ground_speed` drops below threshold
5. Return to CROUCH

Parameters: `charge_frames` (how many charge pulses, default 3) and
`redash_threshold` (speed below which to re-spindash, default 2.0).

## Design: Scripted Strategy

`scripted(timeline)` takes a list of `(start, end, InputState)` tuples. On each frame,
returns the InputState from the first matching window, or empty InputState if no window
matches. Windows can overlap — first match wins.

## Pyxel-Free Guarantee

The harness imports only from: `speednik.player` (Player, PlayerState, create_player,
player_update), `speednik.physics` (InputState, PhysicsState), `speednik.terrain`
(TileLookup, get_quadrant), `speednik.level` (load_stage). None of these import pyxel.

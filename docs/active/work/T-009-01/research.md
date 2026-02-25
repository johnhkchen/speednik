# Research — T-009-01: debug-flag-and-hud-overlay

## Scope

Add a `SPEEDNIK_DEBUG` environment variable that gates a debug HUD overlay during gameplay and a "DEV PARK" entry in the stage select menu. When unset, zero player-facing impact.

---

## Relevant Files

### `speednik/main.py` (564 lines)

The game's state machine and entry point. Five states: TITLE, STAGE_SELECT, GAMEPLAY, RESULTS, GAME_OVER.

**Stage configuration** (lines 86–90):
- `_STAGE_LOADER_NAMES`: dict mapping stage number → loader name (1: hillside, 2: pipeworks, 3: skybridge)
- `_STAGE_NAMES`: dict mapping stage number → display name
- `_STAGE_MUSIC`: dict mapping stage number → music constant
- `_STAGE_PALETTE`: dict mapping stage number → palette name
- `_NUM_STAGES = 3`: used by stage select rendering

**Stage select** (lines 210–238):
- `_update_stage_select`: UP/DOWN navigation, clamped between 1 and `self.unlocked_stages`. Confirm loads and transitions to gameplay.
- `_draw_stage_select`: iterates `range(1, _NUM_STAGES + 1)`. Locked stages show "???" in color 12. Selected stage gets "> " prefix and color 11. Each entry rendered at `y = 60 + (i - 1) * 24`.

**Gameplay draw** (lines 401–481):
- `_draw_gameplay` renders terrain, objects, enemies, player, particles.
- Lines 478–480: after drawing the world, calls `pyxel.camera()` to reset to screen space, then `renderer.draw_hud(...)` for the HUD.
- The debug HUD should be drawn after `draw_hud` while still in screen space (after `pyxel.camera()` reset).

**Stage loading** (lines 244–294):
- `_load_stage(stage_num)`: looks up `_STAGE_LOADER_NAMES[stage_num]`, calls `load_stage(stage_name)`.
- Stage num 0 is not in any dict. Dev Park selection needs special handling — either add stage 0 entries or branch before the lookup.

### `speednik/renderer.py` (571 lines)

All visuals drawn with Pyxel primitives. Relevant:

**HUD** (lines 555–571):
- `draw_hud(player, timer_frames, frame_count)`: draws RINGS (top-left, y=4), TIME (x=90, y=4), lives (x=200, y=4).
- All HUD text is on y=4. The debug HUD should go to the **top-right** to avoid overlap with the existing RINGS/TIME/lives line.

**Screen dimensions**: imported from constants: SCREEN_WIDTH=256, SCREEN_HEIGHT=224.

**Pyxel text**: `pyxel.text(x, y, string, color)`. Each character is 4px wide (Pyxel default font). A string of N chars occupies ~4*N pixels.

### `speednik/player.py`

**PlayerState enum** (lines 49–56): STANDING, RUNNING, JUMPING, ROLLING, SPINDASH, HURT, DEAD. The `.value` is a lowercase string.

**Player dataclass** (lines 74–92): holds `physics: PhysicsState`, `state: PlayerState`, `rings`, `lives`, animation state.

### `speednik/physics.py`

**PhysicsState dataclass** (lines 66–91):
- `x`, `y`: world position (float)
- `ground_speed`: current speed (float)
- `angle`: byte angle 0–255
- `on_ground`: bool

**Quadrant**: Not stored explicitly. Derived from `angle` at display time — `angle // 64` gives quadrant 0–3.

### `speednik/constants.py`

- `SCREEN_WIDTH = 256`, `SCREEN_HEIGHT = 224`
- No existing debug constants.

### `speednik/level.py`

- `_DATA_DIRS`: maps stage names to filesystem paths. Dev park placeholder doesn't need real stage data yet (per ticket: "can show DEV PARK text on a blank screen").

---

## Patterns Observed

1. **No existing debug/env-var infrastructure.** This is the first debug flag.
2. **Stage select is hardcoded to 1-based integer indices.** The `_STAGE_*` dicts, `selected_stage`, `unlocked_stages`, and rendering loop all assume stages start at 1.
3. **`pyxel.text()` uses a built-in 4px-wide font.** No way to measure string width programmatically — must calculate manually.
4. **Tests mock `pyxel` module** via `@patch("speednik.renderer.pyxel")`. The same pattern works for testing the debug HUD.
5. **The debug flag module does not exist.** It needs to be created as `speednik/debug.py`.

---

## Constraints and Assumptions

- The debug flag must read from `os.environ` at import time. No runtime toggling needed.
- The debug HUD shows physics data that exists on `PhysicsState` and `PlayerState`. No new fields needed.
- Frame counter: `App._update_gameplay` increments `self.timer_frames` each frame — this is the gameplay frame counter. Alternatively, `pyxel.frame_count` is the global Pyxel frame counter. The ticket says "incremented each gameplay update," so `timer_frames` is the right source.
- "DEV PARK" stage select: selecting it should transition to a placeholder state. The simplest implementation: load a "dev_park" state in the gameplay draw that just shows text. Or, add a new state "dev_park" to the state machine. The ticket says "placeholder for now — can show DEV PARK text on a blank screen until T-009-03."
- Quadrant: `angle // 64` gives 0–3 corresponding to the Sonic 2 quadrant system (0=floor, 1=right wall, 2=ceiling, 3=left wall).

---

## Key Questions Resolved

- **Where to render debug HUD**: After `pyxel.camera()` reset at line 479, after `draw_hud` at line 480. Top-right corner.
- **How to add DEV PARK to stage select**: Add it as a special entry. The simplest approach: use stage number 0 for dev park, displayed after the real stages.
- **What data the debug HUD needs**: `player` (has `.physics.x`, `.physics.y`, `.physics.ground_speed`, `.physics.angle`, `.physics.on_ground`, `.state`) and `timer_frames` (frame counter).

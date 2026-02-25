# Design — T-009-02: live-bot-runner

## Problem

Bridge the headless test harness (strategies + `run_scenario`) and the visual game
(renderer + camera) so strategies can run live in the game loop, one `player_update`
per frame, renderable by Pyxel.

---

## Approach A: Dataclass with Separate tile_lookup + tiles_dict

Store both `tile_lookup: TileLookup` (for physics via `player_update`) and
`tiles_dict: dict` (for rendering via `draw_terrain`) on the LiveBot.

**Pros:**
- Clean separation: physics uses callable, rendering uses dict.
- Matches existing API signatures exactly — no changes to renderer or terrain.
- `make_bots_for_stage` gets both from `StageData`.
- `make_bots_for_grid` can accept both from caller.

**Cons:**
- Slight redundancy (dict and callable wrapping the same data).
- Grid builders don't expose the dict — caller must supply it.

---

## Approach B: LiveBot stores only TileLookup, refactor draw_terrain

Change `draw_terrain` to accept `TileLookup` instead of `dict`.

**Pros:**
- Unified interface — one type everywhere.

**Cons:**
- Invasive change to renderer, main.py, and all call sites.
- `draw_terrain` iterates visible tiles by coordinate range — needs dict-style access.
  A callable would require iterating all possible (tx, ty) in viewport, which is correct
  but changes the rendering loop structure.
- Out of scope for this ticket.

**Rejected:** Too invasive, changes existing working code.

---

## Approach C: LiveBot stores only tiles_dict, derives TileLookup

Derive the `TileLookup` callable from the dict at construction time via
`lambda tx, ty: tiles_dict.get((tx, ty))`.

**Pros:**
- Single storage, no redundancy.
- Works for both stage and grid scenarios.

**Cons:**
- Grid builders return `TileLookup` — caller would need to also pass the underlying dict,
  or we'd need to change grid builders to return dicts.
- Subtle: the closure-derived lookup may differ from the original if the builder does
  anything beyond `dict.get`. Currently they don't, so this is safe.

**Viable** but Approach A is simpler for the caller.

---

## Decision: Approach A

Store both `tile_lookup` and `tiles_dict` on LiveBot. This:
1. Requires zero changes to existing modules (renderer, terrain, level, grids).
2. Maps directly to the existing API signatures.
3. For `make_bots_for_stage`, both come from `StageData`.
4. For `make_bots_for_grid`, the caller passes both (the dict they built and the wrapped lookup).

---

## LiveBot Design

```python
@dataclass
class LiveBot:
    player: Player
    strategy: Callable[[int, Player], InputState]
    tile_lookup: TileLookup
    tiles_dict: dict
    camera: Camera
    label: str
    max_frames: int = 600
    goal_x: float | None = None
    frame: int = 0
    finished: bool = False
```

### update()

```
if finished: return
inp = strategy(frame, player)
player_update(player, inp, tile_lookup)
camera_update(camera, player, inp)
frame += 1
if frame >= max_frames: finished = True
if goal_x and player.physics.x >= goal_x: finished = True
```

### draw()

```
pyxel.camera(int(camera.x), int(camera.y))
draw_terrain(tiles_dict, int(camera.x), int(camera.y))
draw_player(player, frame)
```

The caller is responsible for `pyxel.clip()` (for multi-view) and resetting camera after.
LiveBot.draw() does NOT manage clipping — that's T-009-04's concern.

---

## Factory Design

### make_bot(tiles_dict, tile_lookup, start_x, start_y, strategy, label, ...) -> LiveBot

Creates Player, Camera, returns LiveBot. The camera needs `level_width` and `level_height`
for boundary clamping. Options:
- Compute from tiles_dict: `max(tx for tx, ty in tiles_dict) * TILE_SIZE` etc.
- Accept as parameters.

For simplicity, compute from tiles_dict. This avoids extra params and works for both
stage tiles and synthetic grids.

### make_bots_for_stage(stage_name, max_frames=600) -> list[LiveBot]

Loads stage, creates 4 bots (idle, hold_right, hold_right_jump, spindash) from stage data.
All share the same tiles_dict and tile_lookup (read-only data).

### make_bots_for_grid(tiles_dict, tile_lookup, start_x, start_y, strategies, ...) -> list[LiveBot]

Creates bots for synthetic grid data. Accepts explicit tiles_dict + tile_lookup from caller.

---

## Location

`speednik/devpark.py` — as specified in the ticket. Keeping it in the game package
because it imports Pyxel for rendering. The strategy imports from `tests/harness.py`
are gated to runtime (called only when DEBUG is True).

---

## DEBUG Gating

The module itself does NOT check DEBUG. The caller (main.py, in T-009-03) checks
`if DEBUG:` before importing/using devpark. The strategies import from tests/ which
is available in the dev environment.

Actually, the ticket says "Only imported/active when DEBUG is True". Since `devpark.py`
imports from `tests/harness.py` at module level, we should gate the import:

```python
# In devpark.py — conditional strategy imports
from speednik.debug import DEBUG
if DEBUG:
    from tests.harness import idle, hold_right, hold_right_jump, spindash_right
```

This way, `import speednik.devpark` is always safe, but `make_bots_for_stage` only works
when DEBUG is True (which is the only time it's called).

---

## Testing Strategy

Unit tests in `tests/test_devpark.py` that:
1. Construct LiveBot with a synthetic flat grid.
2. Verify `update()` advances frame, mutates player position.
3. Verify `finished` flag after max_frames.
4. Verify `finished` flag after reaching goal_x.
5. Verify finished bot stops updating.
6. Test `make_bot` factory creates correct LiveBot.
7. Test `make_bots_for_stage` creates 4 bots (requires stage data on disk — integration test).

Tests do NOT need Pyxel — skip `draw()` testing (it calls `pyxel.camera`, `draw_terrain`,
`draw_player` which all need Pyxel initialized). The update/logic tests are Pyxel-free.

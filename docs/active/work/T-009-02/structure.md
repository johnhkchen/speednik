# Structure — T-009-02: live-bot-runner

## Files

### Created

#### `speednik/devpark.py` (~100 lines)

The LiveBot class, factory helpers, and dev park utilities.

**Imports:**
```
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

import pyxel

from speednik import renderer
from speednik.camera import Camera, camera_update, create_camera
from speednik.debug import DEBUG
from speednik.level import load_stage
from speednik.physics import InputState
from speednik.player import Player, create_player, player_update
from speednik.terrain import TILE_SIZE, TileLookup
```

**Conditional imports (only when DEBUG=True):**
```python
if DEBUG:
    from tests.harness import idle, hold_right, hold_right_jump, spindash_right
```

**Public interface:**

| Symbol | Type | Description |
|--------|------|-------------|
| `LiveBot` | dataclass | Bot state: player, strategy, tiles, camera, label, frame, finished |
| `make_bot` | function | Factory: tiles_dict + tile_lookup + position + strategy → LiveBot |
| `make_bots_for_stage` | function | Factory: stage_name → 4 LiveBots (idle/right/jump/spindash) |
| `make_bots_for_grid` | function | Factory: tiles + lookup + position + strategies → LiveBots |

**LiveBot fields:**
- `player: Player` — owned player instance
- `strategy: Callable[[int, Player], InputState]` — decision function
- `tile_lookup: TileLookup` — collision lookup (for player_update)
- `tiles_dict: dict` — tile data (for draw_terrain)
- `camera: Camera` — owned camera instance
- `label: str` — text label for HUD overlay (e.g., "HOLD_RIGHT")
- `max_frames: int` — completion threshold (default 600)
- `goal_x: float | None` — completion X position (optional)
- `frame: int` — frame counter (starts at 0)
- `finished: bool` — whether bot has stopped

**LiveBot methods:**
- `update()` — if not finished: call strategy → player_update → camera_update → check completion
- `draw()` — set pyxel camera → draw_terrain → draw_player (caller manages clip regions)

**Helper functions:**
- `_compute_level_bounds(tiles_dict) -> (int, int)` — compute (width_px, height_px) from tiles

---

#### `tests/test_devpark.py` (~120 lines)

Unit tests for LiveBot and factory functions.

**Test classes:**

| Class | Tests | What it covers |
|-------|-------|----------------|
| `TestLiveBotUpdate` | 5–6 tests | update advances frame, moves player, finishes at max_frames, finishes at goal_x, stops when finished |
| `TestMakeBot` | 2–3 tests | factory creates LiveBot with correct fields, camera centered on start |
| `TestMakeBotsForStage` | 1–2 tests | creates 4 bots, correct labels |
| `TestMakeBotsForGrid` | 1–2 tests | creates bots from tiles_dict + tile_lookup |

**Test fixtures:**
- Uses `build_flat(20, 8)` from `tests/grids.py` for synthetic tile data.
- Extracts tiles_dict by building it inline (same pattern as `build_flat` internals).
- Uses `idle()` and `hold_right()` strategies from `tests/harness.py`.

---

### Modified

None. This ticket creates a new module — no existing files are modified.

The `devpark.py` module is self-contained. T-009-03 will integrate it into `main.py`'s
dev_park state, and T-009-04 will add multi-view rendering.

---

## Module Boundaries

```
tests/harness.py          speednik/devpark.py          speednik/main.py
  (strategies)  ──import──►  (LiveBot, factories)  ◄──import── (T-009-03)
                                    │
                                    ├──► speednik/player.py (player_update)
                                    ├──► speednik/camera.py (camera_update, create_camera)
                                    ├──► speednik/renderer.py (draw_terrain, draw_player)
                                    ├──► speednik/level.py (load_stage)
                                    └──► speednik/debug.py (DEBUG flag)
```

The reverse import (game package → tests/) is acceptable per ticket:
- `tests/harness.py` is a utility module, not a test file.
- Import is conditional on DEBUG.
- Only used in dev context.

---

## Data Flow

```
make_bot(tiles_dict, tile_lookup, x, y, strategy, label)
    └──► create_player(x, y) → Player
    └──► create_camera(width, height, x, y) → Camera
    └──► LiveBot(player, strategy, tile_lookup, tiles_dict, camera, label)

LiveBot.update()
    └──► strategy(frame, player) → InputState
    └──► player_update(player, inp, tile_lookup)  [mutates player]
    └──► camera_update(camera, player, inp)        [mutates camera]
    └──► frame += 1; check completion

LiveBot.draw()
    └──► pyxel.camera(cam_x, cam_y)
    └──► draw_terrain(tiles_dict, cam_x, cam_y)
    └──► draw_player(player, frame)
```

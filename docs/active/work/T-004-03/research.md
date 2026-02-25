# Research — T-004-03: Game State Machine

## Current Entry Point

`speednik/main.py` contains the `App` class — a single-state game loop with a hardcoded demo level (`_build_demo_level()`). It initializes Pyxel at 256x224@60fps, sets up a palette, audio, a flat test level with rings/enemies, and runs `update()`/`draw()` callbacks. There is no state machine — the loop always runs gameplay.

## Stage Loaders

Three stage modules under `speednik/stages/`:
- `hillside.py` — Stage 1, defines `StageData` dataclass and `load()` → returns `StageData`
- `pipeworks.py` — Stage 2, imports `StageData` from hillside, defines `load()`
- `skybridge.py` — Stage 3, duplicates `StageData` definition (doesn't import from hillside)

`StageData` fields: `tile_lookup` (callable), `entities` (list[dict]), `player_start` (tuple), `checkpoints`, `level_width`, `level_height`.

Each loader reads 4 JSON files (tile_map, collision, entities, meta) from its subdirectory, builds a `tiles` dict internally, wraps it in a closure for `tile_lookup`, and returns `StageData`. The `tiles` dict is captured inside the closure — not directly accessible from outside.

## The Tiles Dict Problem

`renderer.draw_terrain()` takes a `dict[tuple[int,int], Tile]` and iterates `.items()` for viewport culling. The current demo level builds this dict explicitly. Stage loaders only expose a `TileLookup` callable (the closure), not the dict itself. The state machine needs the dict to pass to the renderer.

Options: (a) extend `StageData` with `tiles_dict`, (b) refactor `draw_terrain` to take a lookup + bounds, (c) have the state machine rebuild the dict. Option (a) is simplest.

## Goal Entity

Each stage has a `"goal"` entity in entities.json:
- Hillside: `{type: "goal", x: 4758, y: 642}`
- Pipeworks: `{type: "goal", x: 5558, y: 782}`
- Skybridge: `{type: "goal", x: 5158, y: 482}`

No code currently detects goal collision. `renderer.py` has `_draw_goal()` registered in `_OBJECT_DRAWERS` but the demo level never renders goals. The state machine needs a goal collision check to trigger the RESULTS state.

## Boss Entity (Stage 3)

Skybridge entities.json does not contain `enemy_egg_piston`. The boss entity type is fully implemented in `enemies.py` (8 HP, idle/descend/vulnerable/ascend state machine, escalation at 4 HP) and in `renderer.py` (`_draw_enemy_egg_piston`, `draw_boss_indicator`). It needs to be injected programmatically when loading Stage 3.

## Player Data Model

`Player` dataclass in `player.py`:
- `physics: PhysicsState`, `state: PlayerState`, `rings: int`, `lives: int = 3`
- `invulnerability_timer`, `anim_*`, `scattered_rings`
- `respawn_x/y/rings` — checkpoint respawn
- `in_pipe: bool`

`create_player(x, y)` factory sets `on_ground=True`, `respawn_x/y = x/y`.
`damage_player()` handles ring scatter or death (sets `PlayerState.DEAD`).

Death detection: `player.state == PlayerState.DEAD`. No respawn logic exists — the player just stays dead.

## Audio System

`audio.py` defines 7 music tracks (slots 0-6):
- `MUSIC_TITLE(0)`, `MUSIC_HILLSIDE(1)`, `MUSIC_PIPEWORKS(2)`, `MUSIC_SKYBRIDGE(3)`
- `MUSIC_BOSS(4)`, `MUSIC_CLEAR(5)`, `MUSIC_GAMEOVER(6)`

16 SFX (slots 0-15), including `SFX_MENU_SELECT(13)`, `SFX_MENU_CONFIRM(14)`.
API: `play_music(id)`, `stop_music()`, `play_sfx(id)`, `update_audio()`.
Jingle tracks (CLEAR, GAMEOVER) play once without looping. Looping tracks loop.

## Renderer

`renderer.py` has functions for: `draw_terrain`, `draw_player`, `draw_hud`, `draw_particles`, `draw_scattered_rings`, `draw_entities`, `draw_boss_indicator`, plus entity drawers.

`draw_hud(player, timer_frames, frame_count)` draws ring count, timer (from `timer_frames`), and lives. The timer is computed as `timer_frames // 60` → minutes:seconds.

`set_stage_palette(name)` swaps terrain color slots. Three palettes defined: hillside, pipeworks, skybridge.

`_particles` is a module-level list — needs `.clear()` between stages.

## Input

`_read_input()` in main.py maps Pyxel keys to `InputState(left, right, jump_pressed, jump_held, down_held, up_held)`. Menu navigation needs different inputs: arrow keys + confirm (Z/Return).

## Camera

`camera.py` exposes `create_camera(level_w, level_h, start_x, start_y)` and `camera_update(cam, player, inp)`. The camera has `x, y` fields used as viewport offset.

## Existing Object Systems

All interaction systems return event lists:
- `check_ring_collection()` → `RingEvent`
- `check_spring_collision()` → `SpringEvent`
- `check_checkpoint_collision()` → `CheckpointEvent`
- `update_pipe_travel()` → `PipeEvent`
- `update_liquid_zones()` → `LiquidEvent`
- `check_enemy_collision()` → `EnemyEvent` (includes `BOSS_DEFEATED`)

## Specification Requirements

Section 1: Title Screen → Stage Select → Gameplay → Results
Section 8: 3 lives, 100 rings = extra life, death → checkpoint/stage start, 0 lives → game over

States needed: TITLE, STAGE_SELECT, GAMEPLAY, RESULTS, GAME_OVER.

## Constraints and Gaps

1. No goal collision detection exists
2. No death/respawn logic exists (player just freezes in DEAD state)
3. No stage loading integration in main.py (demo level only)
4. Tiles dict not exposed by stage loaders
5. Boss not in skybridge entity data — must be injected
6. Particles need clearing between stages
7. Skybridge duplicates StageData instead of importing from hillside
8. No pause system (ESC currently not handled; spec mentions Pyxel default quit)

## File Inventory

| File | Role | Needs Changes |
|------|------|--------------|
| `main.py` | Entry point, demo loop | Complete rewrite |
| `stages/hillside.py` | Stage 1 loader | Add `tiles_dict` to StageData |
| `stages/pipeworks.py` | Stage 2 loader | Pass `tiles_dict` |
| `stages/skybridge.py` | Stage 3 loader | Import StageData, pass `tiles_dict` |
| `objects.py` | Ring/spring/checkpoint/pipe/liquid | Add goal collision check |
| `renderer.py` | All visuals | Clear particles helper |
| `player.py` | Player state/damage | No changes needed |
| `audio.py` | Music/SFX | No changes needed |
| `camera.py` | Camera system | No changes needed |
| `constants.py` | Game constants | Goal collision radius constant |
| `enemies.py` | Enemy behaviors | No changes needed |

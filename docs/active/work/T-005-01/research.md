# Research — T-005-01: mp3-music-playback

## Scope

Replace chiptune `pyxel.playm()` with `afplay` subprocess for four stage music tracks
(title, hillside, pipeworks, skybridge) while preserving chiptune playback for boss,
clear, and gameover tracks.

## Codebase Map

### `speednik/audio.py` (599 lines)

The single audio module. Public API consumed by `main.py`:

| Function        | Purpose                                          |
|-----------------|--------------------------------------------------|
| `init_audio()`  | Defines all SFX (slots 0–15) and music (slots 16–36) via Pyxel MML |
| `play_sfx()`    | Plays SFX on CH_SFX (ch 3), ducks percussion     |
| `play_music()`  | Starts a music track via `pyxel.playm()`          |
| `stop_music()`  | Stops channels 0–2                                |
| `update_audio()`| Per-frame: resumes percussion after SFX ducking   |

Module state:
- `_current_music: int | None` — currently playing track ID
- `_sfx_ducking: bool` — whether percussion is ducked for SFX

Constants:
- `MUSIC_TITLE=0`, `MUSIC_HILLSIDE=1`, `MUSIC_PIPEWORKS=2`, `MUSIC_SKYBRIDGE=3`
- `MUSIC_BOSS=4`, `MUSIC_CLEAR=5`, `MUSIC_GAMEOVER=6`
- `_JINGLE_TRACKS = {MUSIC_CLEAR, MUSIC_GAMEOVER}` — played without loop

Channel allocation: `CH_MELODY=0`, `CH_BASS=1`, `CH_PERCUSSION=2`, `CH_SFX=3`.

### `speednik/main.py` (564 lines)

Imports and calls all public audio functions. Key call sites:
- `App.__init__`: calls `init_audio()`, then `play_music(MUSIC_TITLE)`
- `_load_stage()`: `stop_music()` then `play_music(_STAGE_MUSIC[stage_num])`
- Boss trigger: `stop_music()` + `play_music(MUSIC_BOSS)`
- Goal reached: `stop_music()` + `play_music(MUSIC_CLEAR)`
- Death: `stop_music()` + `play_music(MUSIC_GAMEOVER)`
- Results/game-over end: `stop_music()` + `play_music(MUSIC_TITLE)`
- `update()`: calls `update_audio()` every frame

Pattern: always `stop_music()` before `play_music()` for transitions.

### MP3 Assets

All four files confirmed present in `assets/`:
- `assets/MAIN_MENU_Genesis_of_Glory.mp3`
- `assets/LV1_Pixel_Pursuit.mp3`
- `assets/LV2_Chrome_Citadel.mp3`
- `assets/LV3_Genesis_Gauntlet.mp3`

### Tests

`tests/test_audio.py` — single test `test_init_audio_does_not_raise()`:
- Mocks `pyxel` entirely via `sys.modules`
- Calls `init_audio()` and asserts musics[0–3].set was called
- Does NOT test `play_music`, `stop_music`, `play_sfx`, or `update_audio`

### Exit / Cleanup

No `atexit`, `signal`, or `__del__` handlers anywhere in the codebase. `pyxel.quit()`
is called on Q key press. The Pyxel event loop (`pyxel.run`) handles exit internally.
Any subprocess spawned by `audio.py` must be explicitly cleaned up.

### Web Export

`web_entry.py` imports `App` and runs it. The `speednik.pyxapp` web archive exists.
`afplay` is macOS-only — web builds cannot use it. The ticket scope is desktop only.

## Key Constraints

1. **`afplay` is macOS-only.** No cross-platform concern raised in ticket.
2. **No cleanup infrastructure.** Must add atexit handler to kill orphan processes.
3. **Percussion ducking depends on pyxel channels.** When MP3 is active, pyxel channels
   0–2 are unused for music, so ducking percussion (ch 2) is a no-op / harmful.
4. **Looping.** `afplay` plays once and exits. Looping requires monitoring the process
   and relaunching. A daemon thread with a `while` loop is the standard pattern.
5. **Thread safety.** Module state (`_current_music`, `_sfx_ducking`) is accessed from
   main thread only (Pyxel is single-threaded). The loop thread only needs to relaunch
   `afplay`; it shouldn't mutate module state beyond the subprocess handle.
6. **Standalone test mode.** The `__main__` block runs an `AudioTest` class. It should
   still work — MP3 playback should be triggered there too.

## Patterns and Boundaries

- The public API surface (`play_music`, `stop_music`, etc.) must remain unchanged.
- `main.py` always calls `stop_music()` before `play_music()` — this simplifies the
  transition logic (we don't need to handle "switch from MP3 to MP3" without stop).
  However, `play_music` should still be defensive and kill any existing subprocess.
- The `_current_music` variable already tracks what's playing. We need an additional
  flag or check to know whether the current track is MP3-backed or pyxel-backed.

## Open Questions

- Should `_define_track_*` still be called for MP3 tracks? Yes — the chiptune defs
  are harmless and the standalone test mode might want to toggle between MP3/chiptune.
  Also, the web export needs them.

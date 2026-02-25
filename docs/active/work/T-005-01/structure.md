# Structure — T-005-01: mp3-music-playback

## Files Modified

### `speednik/audio.py` (only file modified)

No new files. No files deleted. All changes are contained in `audio.py`.

## Import Additions

```python
import subprocess
import threading
import os
import atexit
```

Added at top of file alongside existing `import pyxel`.

## New Constants

```python
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_MP3_TRACKS: dict[int, str] = {
    MUSIC_TITLE: os.path.join(_PROJECT_ROOT, "assets", "MAIN_MENU_Genesis_of_Glory.mp3"),
    MUSIC_HILLSIDE: os.path.join(_PROJECT_ROOT, "assets", "LV1_Pixel_Pursuit.mp3"),
    MUSIC_PIPEWORKS: os.path.join(_PROJECT_ROOT, "assets", "LV2_Chrome_Citadel.mp3"),
    MUSIC_SKYBRIDGE: os.path.join(_PROJECT_ROOT, "assets", "LV3_Genesis_Gauntlet.mp3"),
}
```

Placed after the channel allocation section, before module state.

## New Module State

```python
_afplay_proc: subprocess.Popen | None = None
_loop_stop: threading.Event | None = None
_mp3_active: bool = False
```

Added to the existing module state section alongside `_current_music` and `_sfx_ducking`.

## New Internal Helpers

### `_stop_afplay() -> None`

Kills active afplay subprocess. Sets stop event for loop thread. Waits for process
to terminate. Resets `_afplay_proc`, `_loop_stop`, `_mp3_active` to None/False.
Safe to call when no subprocess is running (no-op).

Placed in the "Internal helpers" section after `_get_percussion_for_track`.

### `_afplay_loop(path: str, stop_event: threading.Event) -> None`

Loop function for daemon thread. Spawns `afplay` in a loop:
1. Launch `subprocess.Popen(["afplay", path])`
2. Store reference in module `_afplay_proc`
3. `proc.wait()`
4. If `stop_event.is_set()`, break
5. Otherwise, loop back to step 1

Thread exits cleanly when stop event is set.

Placed after `_stop_afplay`.

## Modified Functions

### `play_music(track_id: int) -> None`

New logic:
1. Call `_stop_afplay()` unconditionally (kills any prior MP3 playback)
2. If `track_id in _MP3_TRACKS`:
   - Resolve path from `_MP3_TRACKS`
   - If file exists:
     - If looping track (not in `_JINGLE_TRACKS`):
       - Create `threading.Event`
       - Start daemon thread running `_afplay_loop(path, event)`
       - Store event in `_loop_stop`
     - Else (jingle):
       - Spawn single `subprocess.Popen(["afplay", path])`
       - Store in `_afplay_proc`
     - Set `_mp3_active = True`
   - Else (file missing): fall through to pyxel
3. Else (no MP3 mapping):
   - `pyxel.playm(track_id, loop=...)`
   - Set `_mp3_active = False`
4. Set `_current_music = track_id`

### `stop_music() -> None`

New logic:
1. Call `_stop_afplay()`
2. Stop pyxel channels 0–2 (existing behavior, harmless if not playing)
3. Reset `_current_music = None`, `_sfx_ducking = False`, `_mp3_active = False`

### `play_sfx(sfx_id: int) -> None`

Change: Guard percussion ducking with `not _mp3_active`:
```python
if _current_music is not None and not _mp3_active:
    pyxel.stop(CH_PERCUSSION)
    _sfx_ducking = True
```

### `update_audio() -> None`

Change: Guard percussion resume with `not _mp3_active`:
```python
if _sfx_ducking and not _mp3_active and pyxel.play_pos(CH_SFX) is None:
    ...
```

### `init_audio() -> None`

Addition: Register atexit handler:
```python
atexit.register(_stop_afplay)
```

## Interface Stability

- All public API signatures unchanged: `init_audio()`, `play_sfx(int)`,
  `play_music(int)`, `stop_music()`, `update_audio()`.
- All constants unchanged.
- `main.py` requires zero changes.

## Test Impact

- Existing `test_init_audio_does_not_raise` continues to pass (it only tests
  `init_audio()` which still calls the same define functions).
- New test needed: verify `play_music` dispatches to subprocess for MP3 tracks
  and to `pyxel.playm()` for non-MP3 tracks. Mock `subprocess.Popen` and
  `threading.Thread`.
- New test: verify `stop_music` terminates subprocess.
- New test: verify percussion ducking is skipped when `_mp3_active` is True.

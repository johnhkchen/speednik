# Design — T-005-01: mp3-music-playback

## Problem

Four stage tracks have professional MP3 files. The game currently plays chiptune
versions via `pyxel.playm()`. Replace with `afplay` subprocess for those four tracks.

## Approach A: Direct Subprocess with Loop Thread

Add a thin subprocess layer in `audio.py`. For MP3-mapped tracks, `play_music()`
kills any existing `afplay` process and spawns a new one. A daemon thread monitors the
process and relaunches it for looping tracks. Non-MP3 tracks fall through to
`pyxel.playm()`.

**Pros:** Minimal code. No new files. No new dependencies. Matches ticket spec exactly.
**Cons:** macOS-only. Thread adds small complexity.

## Approach B: pygame.mixer or playsound Library

Use a cross-platform audio library (e.g., `pygame.mixer` or `playsound`) for MP3
playback. Would require `uv add pygame` or similar.

**Pros:** Cross-platform. Library-managed looping.
**Cons:** Adds heavy dependency (pygame is large). Potential conflicts with Pyxel's
SDL audio. `playsound` is unmaintained. Ticket explicitly specifies `afplay`.

## Approach C: Pyxel's Built-in WAV/Audio Support

Convert MP3s to a format Pyxel can load natively.

**Pros:** No subprocess. No threads.
**Cons:** Pyxel only supports its own MML format for music — no WAV/MP3 loading.
Would require a different engine entirely. Not viable.

## Decision: Approach A

The ticket explicitly specifies `subprocess.Popen(['afplay', path])` and a threading
loop for restart. This is a macOS game development context where `afplay` is available.
Cross-platform is out of scope. The implementation is simple and self-contained.

## Detailed Design

### MP3 Path Mapping

```python
_MP3_TRACKS: dict[int, str] = {
    MUSIC_TITLE: "assets/MAIN_MENU_Genesis_of_Glory.mp3",
    MUSIC_HILLSIDE: "assets/LV1_Pixel_Pursuit.mp3",
    MUSIC_PIPEWORKS: "assets/LV2_Chrome_Citadel.mp3",
    MUSIC_SKYBRIDGE: "assets/LV3_Genesis_Gauntlet.mp3",
}
```

Paths are relative to the working directory. `os.path.join(os.path.dirname(__file__), "..")`
resolves to the project root regardless of cwd.

### Module State Additions

```python
_afplay_proc: subprocess.Popen | None = None   # active afplay process
_loop_stop: threading.Event | None = None       # signals loop thread to stop
_mp3_active: bool = False                       # True when current track is MP3
```

### `play_music(track_id)` Changes

```
if track_id in _MP3_TRACKS:
    _stop_afplay()                    # kill existing subprocess + loop thread
    resolve absolute path
    spawn afplay subprocess
    if looping (not in _JINGLE_TRACKS):
        start daemon thread that waits for process exit, respawns if not stopped
    set _mp3_active = True
else:
    _stop_afplay()                    # ensure no orphan MP3 process
    pyxel.playm(track_id, loop=...)   # existing behavior
    _mp3_active = False
set _current_music = track_id
```

### `stop_music()` Changes

```
_stop_afplay()          # kill subprocess + thread
pyxel.stop(0,1,2)       # stop pyxel channels (harmless if not playing)
_current_music = None
_mp3_active = False
```

### `_stop_afplay()` Helper

```
if _afplay_proc is not None:
    _loop_stop.set()              # signal thread to stop
    _afplay_proc.terminate()      # SIGTERM
    _afplay_proc.wait()           # reap
    _afplay_proc = None
```

### Loop Thread Design

```python
def _afplay_loop(path, stop_event):
    while not stop_event.is_set():
        proc = subprocess.Popen(["afplay", path])
        proc.wait()
        if stop_event.is_set():
            break
        # process exited naturally — restart for loop
    # Thread exits when stop_event is set
```

The thread owns the subprocess lifecycle during looping. `_afplay_proc` in module state
always points to the current subprocess (updated by the thread). This requires care:
the thread sets `_afplay_proc` to each new `Popen`, and `_stop_afplay` terminates it.

Simpler: have the thread itself hold a reference. The module `_afplay_proc` is set to
the initial process. `_stop_afplay` terminates it and sets the event. The thread checks
the event after each `wait()` and won't restart.

Actually simplest: The loop thread spawns processes in a loop. The module stores the
event. `_stop_afplay` sets the event and kills the current process. The thread's
`proc.wait()` returns, it checks the event, and exits.

To kill the right process, the thread should update `_afplay_proc` each iteration.
Since the main thread only reads/kills `_afplay_proc` and the loop thread only writes
it, this is safe (Python GIL protects the reference assignment).

### Percussion Ducking Skip

In `play_sfx()`:
```python
if _current_music is not None and not _mp3_active:
    pyxel.stop(CH_PERCUSSION)
    _sfx_ducking = True
```

In `update_audio()`:
```python
if _sfx_ducking and not _mp3_active and pyxel.play_pos(CH_SFX) is None:
    ...
```

When MP3 is active, pyxel channels 0–2 aren't playing music, so ducking/resuming
percussion is meaningless.

### Cleanup on Exit

Register `atexit.register(_stop_afplay)` in `init_audio()` to prevent zombie processes.

### Standalone Test Mode

The `AudioTest` class in the `__main__` block will automatically use MP3 playback
since it calls `play_music()` through the public API. No changes needed.

## Rejected Details

- **Volume control for afplay:** `afplay` supports `-v` flag but the ticket doesn't
  mention volume. Skip.
- **Fade in/out:** Not in scope.
- **Process group management:** Overkill for 1 subprocess. `terminate()` is sufficient.

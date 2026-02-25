# Progress — T-005-01: mp3-music-playback

## Completed

### Step 1–2: Imports and Module State
- Added `import atexit, os, subprocess, threading` at top of `audio.py`
- Added `_PROJECT_ROOT`, `_MP3_TRACKS` dict with absolute paths for 4 MP3 files
- Added `_afplay_proc`, `_loop_stop`, `_mp3_active` to module state

### Step 3–4: Internal Helpers
- Implemented `_stop_afplay()` — kills subprocess, sets stop event, resets state
- Implemented `_afplay_loop(path, stop_event)` — daemon thread loop for afplay restart

### Step 5: Modified `play_music()`
- Calls `_stop_afplay()` first (kills any prior MP3)
- Branches on `_MP3_TRACKS.get(track_id)` + `os.path.isfile()`
- MP3 looping tracks: creates Event + daemon Thread with `_afplay_loop`
- MP3 jingle tracks: single `subprocess.Popen`
- Non-MP3: falls through to `pyxel.playm()` as before

### Step 6: Modified `stop_music()`
- Added `_stop_afplay()` call before pyxel channel stops
- Added `_mp3_active = False` reset

### Step 7: Modified `play_sfx()`
- Added `not _mp3_active` guard to percussion ducking condition

### Step 8: Modified `update_audio()`
- Added `not _mp3_active` guard to percussion resume condition

### Step 9: Registered atexit Handler
- `atexit.register(_stop_afplay)` called in `init_audio()`

### Step 10–11: Tests
- Wrote 6 new tests (7 total) in `tests/test_audio.py`
- All 566 tests pass across the full test suite

## Deviations

None. Implementation followed the plan exactly.

## Remaining

Nothing. All steps complete.

# Plan — T-005-01: mp3-music-playback

## Step 1: Add Imports and Constants

**File:** `speednik/audio.py`

Add `import subprocess`, `import threading`, `import os`, `import atexit` at top.

Add `_PROJECT_ROOT` and `_MP3_TRACKS` dict after channel allocation section.

**Verify:** Module still imports cleanly (`python -c "import speednik.audio"`).

## Step 2: Add Module State Variables

**File:** `speednik/audio.py`

Add `_afplay_proc`, `_loop_stop`, `_mp3_active` to the module state section.

**Verify:** No import errors.

## Step 3: Add `_stop_afplay()` Helper

**File:** `speednik/audio.py`

Implement the helper that:
1. Checks if `_loop_stop` exists, calls `.set()`
2. Checks if `_afplay_proc` exists, calls `.terminate()` then `.wait()`
3. Resets `_afplay_proc = None`, `_loop_stop = None`, `_mp3_active = False`

**Verify:** Function exists and is callable.

## Step 4: Add `_afplay_loop()` Thread Function

**File:** `speednik/audio.py`

Implement the loop function:
1. Accept `path` and `stop_event` args
2. While not `stop_event.is_set()`:
   - Spawn `subprocess.Popen(["afplay", path])`
   - Update global `_afplay_proc`
   - Call `proc.wait()`
   - If `stop_event.is_set()`, break

**Verify:** Function exists.

## Step 5: Modify `play_music()`

**File:** `speednik/audio.py`

Replace body:
1. Call `_stop_afplay()`
2. Branch on `track_id in _MP3_TRACKS`:
   - Resolve path, check `os.path.isfile()`
   - For looping: create Event, start daemon Thread with `_afplay_loop`
   - For jingle: single `Popen`
   - Set `_mp3_active = True`
3. Else: existing `pyxel.playm()`, `_mp3_active = False`
4. Set `_current_music`, reset `_sfx_ducking`

**Verify:** Existing tests still pass.

## Step 6: Modify `stop_music()`

**File:** `speednik/audio.py`

Add `_stop_afplay()` call at top. Add `_mp3_active = False` reset.
Keep existing pyxel channel stops.

**Verify:** Existing tests pass.

## Step 7: Modify `play_sfx()` — Skip Percussion Ducking

**File:** `speednik/audio.py`

Add `not _mp3_active` guard to the ducking condition:
```python
if _current_music is not None and not _mp3_active:
```

**Verify:** Existing tests pass.

## Step 8: Modify `update_audio()` — Skip Percussion Resume

**File:** `speednik/audio.py`

Add `not _mp3_active` guard:
```python
if _sfx_ducking and not _mp3_active and pyxel.play_pos(CH_SFX) is None:
```

**Verify:** Existing tests pass.

## Step 9: Register atexit Handler

**File:** `speednik/audio.py`

Add `atexit.register(_stop_afplay)` at end of `init_audio()`.

**Verify:** `init_audio()` test passes.

## Step 10: Write Tests

**File:** `tests/test_audio.py`

Add tests:

1. `test_play_music_mp3_spawns_subprocess` — Mock `subprocess.Popen` and
   `threading.Thread`. Call `play_music(MUSIC_TITLE)`. Assert `Popen` called
   with `["afplay", <expected_path>]`. Assert thread started (looping track).

2. `test_play_music_chiptune_uses_pyxel` — Call `play_music(MUSIC_BOSS)`.
   Assert `pyxel.playm` called. Assert `Popen` NOT called.

3. `test_stop_music_terminates_afplay` — Set up a mock process in `_afplay_proc`.
   Call `stop_music()`. Assert `terminate()` and `wait()` called.

4. `test_play_sfx_skips_ducking_when_mp3_active` — Set `_mp3_active = True`,
   `_current_music = MUSIC_TITLE`. Call `play_sfx(SFX_RING)`. Assert
   `pyxel.stop(CH_PERCUSSION)` NOT called.

5. `test_play_sfx_ducks_when_chiptune_active` — Set `_mp3_active = False`,
   `_current_music = MUSIC_BOSS`. Call `play_sfx(SFX_RING)`. Assert
   `pyxel.stop(CH_PERCUSSION)` called.

6. `test_update_audio_skips_resume_when_mp3_active` — Set `_mp3_active = True`,
   `_sfx_ducking = True`. Call `update_audio()`. Assert percussion NOT resumed.

**Verify:** All tests pass with `uv run pytest tests/test_audio.py -v`.

## Step 11: Run Full Test Suite

**Command:** `uv run pytest tests/ -v`

Verify no regressions across all test files.

## Commit Strategy

Single atomic commit after all steps complete and tests pass.
Message: `feat: play MP3 music via afplay for stage tracks`

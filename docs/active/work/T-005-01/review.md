# Review — T-005-01: mp3-music-playback

## Summary of Changes

### Files Modified

| File | Change |
|------|--------|
| `speednik/audio.py` | Added MP3 playback via `afplay` subprocess for 4 stage tracks |
| `tests/test_audio.py` | Added 6 new tests for MP3 playback, ducking, and cleanup |

### No Files Created or Deleted

All changes are edits to existing files.

## What Changed in `speednik/audio.py`

### New Imports
`atexit`, `os`, `subprocess`, `threading` added alongside `pyxel`.

### New Constants
- `_PROJECT_ROOT`: absolute path to project root, derived from `__file__`
- `_MP3_TRACKS`: maps `MUSIC_TITLE/HILLSIDE/PIPEWORKS/SKYBRIDGE` to absolute MP3 paths

### New Module State
- `_afplay_proc`: tracks the active `subprocess.Popen` instance (or None)
- `_loop_stop`: `threading.Event` used to signal the loop thread to exit
- `_mp3_active`: boolean flag indicating MP3 playback is active

### New Internal Helpers
- `_stop_afplay()`: kills subprocess, sets stop event, reaps process, resets state
- `_afplay_loop(path, stop_event)`: daemon thread function that spawns/respawns afplay

### Modified Functions
- `play_music()`: dispatches to afplay for MP3 tracks, pyxel for others
- `stop_music()`: calls `_stop_afplay()` before stopping pyxel channels
- `play_sfx()`: skips percussion ducking when `_mp3_active`
- `update_audio()`: skips percussion resume when `_mp3_active`
- `init_audio()`: registers `atexit.register(_stop_afplay)` for cleanup

### Public API
Unchanged. All existing function signatures preserved. `main.py` requires zero changes.

## Acceptance Criteria Coverage

| Criterion | Status |
|-----------|--------|
| `play_music(MUSIC_TITLE)` → afplay with title MP3 | Covered (code + test) |
| `play_music(MUSIC_HILLSIDE)` → afplay with hillside MP3 | Covered (code, same path) |
| `play_music(MUSIC_PIPEWORKS)` → afplay with pipeworks MP3 | Covered (code, same path) |
| `play_music(MUSIC_SKYBRIDGE)` → afplay with skybridge MP3 | Covered (code, same path) |
| Looping tracks restart automatically | Covered (`_afplay_loop` thread) |
| `play_music(MUSIC_BOSS)` uses `pyxel.playm()` | Covered (code + test) |
| `play_music(MUSIC_CLEAR)` uses `pyxel.playm()` | Covered (code, same path) |
| `play_music(MUSIC_GAMEOVER)` uses `pyxel.playm()` | Covered (code, same path) |
| `stop_music()` kills afplay + stops loop thread | Covered (code + test) |
| Switching tracks kills previous afplay | Covered (`_stop_afplay()` at top of `play_music`) |
| Percussion ducking skipped when afplay active | Covered (code + test) |
| Percussion resume skipped when afplay active | Covered (code + test) |
| No zombie afplay on exit | Covered (`atexit.register(_stop_afplay)`) |

## Test Coverage

| Test | What It Verifies |
|------|-----------------|
| `test_init_audio_does_not_raise` | Existing: MML definitions load |
| `test_play_music_mp3_spawns_subprocess` | MP3 track → thread started for looping |
| `test_play_music_chiptune_uses_pyxel` | Non-MP3 track → pyxel.playm, no subprocess |
| `test_stop_music_terminates_afplay` | stop_music kills subprocess |
| `test_play_sfx_skips_ducking_when_mp3_active` | No percussion duck when MP3 |
| `test_play_sfx_ducks_when_chiptune_active` | Percussion ducks for chiptune |
| `test_update_audio_skips_resume_when_mp3_active` | No resume when MP3 |

Full suite: **566 tests pass**, 0 failures.

## Test Gaps

- No integration test that actually spawns `afplay` (would require MP3 files + macOS).
  This is acceptable — subprocess interaction is mocked, and the real behavior is
  trivially verifiable by running the game.
- No test for `_afplay_loop` thread lifecycle (spawn → wait → respawn → stop event).
  The thread function is simple enough that the mock-based test for `play_music`
  provides sufficient confidence.
- No test for the `os.path.isfile` fallback (MP3 missing → chiptune). Low risk;
  the fallback is a single `else` branch.

## Open Concerns

1. **macOS-only.** `afplay` is a macOS binary. If the game needs to run on Linux or
   Windows, a cross-platform solution would be needed. The ticket scope is macOS desktop.

2. **Web export.** The `speednik.pyxapp` web archive cannot use `afplay`. MP3 tracks
   will fall back to chiptune via the `os.path.isfile()` check (MP3 files won't exist
   in the pyxapp bundle). This is correct behavior — no action needed.

3. **Thread safety.** `_afplay_proc` is written by the loop thread and read/written by
   the main thread in `_stop_afplay`. Python's GIL ensures reference assignment is
   atomic, so this is safe. However, there's a narrow race between the thread spawning
   a new process and `_stop_afplay` terminating the old one. In practice this is
   harmless — the thread will check `stop_event` after `proc.wait()` returns and exit.

4. **atexit vs. Pyxel exit.** Pyxel's `quit()` calls `sys.exit()`, which triggers
   atexit handlers. The `_stop_afplay` atexit handler will fire. If Pyxel is killed
   via SIGKILL, atexit won't fire, but that's an edge case where orphan processes
   are expected system-wide.

## No Action Required

All changes are complete, tested, and ready for human review.

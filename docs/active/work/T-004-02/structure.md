# Structure — T-004-02: Audio SFX and Music

## 1. Files Changed

### Created

| File | Purpose |
|------|---------|
| `speednik/audio.py` | Audio module: SFX definitions, music compositions, playback API |

### Modified

None. The audio module is self-contained with no changes needed to existing files.
Integration with `main.py` is deferred to T-004-03 (game state machine).

### Deleted

None.

## 2. Module Architecture: `speednik/audio.py`

### 2.1 Module-Level Constants

```
SFX_RING        = 0     SFX_ENEMY_BOUNCE  = 5    SFX_STAGE_CLEAR  = 10
SFX_JUMP        = 1     SFX_SPRING        = 6    SFX_BOSS_HIT     = 11
SFX_SPINDASH_CH = 2     SFX_RING_LOSS     = 7    SFX_LIQUID_RISE  = 12
SFX_SPINDASH_RE = 3     SFX_HURT          = 8    SFX_MENU_SELECT  = 13
SFX_ENEMY_DEST  = 4     SFX_CHECKPOINT    = 9    SFX_MENU_CONFIRM = 14
                                                   SFX_1UP          = 15

MUSIC_TITLE     = 0     MUSIC_BOSS        = 4
MUSIC_HILLSIDE  = 1     MUSIC_CLEAR       = 5
MUSIC_PIPEWORKS = 2     MUSIC_GAMEOVER    = 6
MUSIC_SKYBRIDGE = 3

CH_MELODY       = 0
CH_BASS         = 1
CH_PERCUSSION   = 2
CH_SFX          = 3

# Jingle tracks (played without looping)
_JINGLE_TRACKS  = {MUSIC_CLEAR, MUSIC_GAMEOVER}
```

### 2.2 Module-Level State

```
_current_music: int | None    # Currently playing music track ID, or None
_sfx_ducking: bool            # True when percussion is ducked for SFX
```

### 2.3 Internal Functions

```
_define_sfx() -> None
    Defines sounds[0..15] via pyxel.sounds[i].set(...).
    Called once by init_audio().

_define_music() -> None
    Defines sounds[16..36+] (music sequences) and musics[0..6].
    Called once by init_audio().
    Internally organized as:
        _define_track_title()
        _define_track_hillside()
        _define_track_pipeworks()
        _define_track_skybridge()
        _define_track_boss()
        _define_track_clear()
        _define_track_gameover()
    Each sub-function defines 3 sound slots and 1 musics[] entry.

_resume_percussion() -> None
    Resumes the current music's percussion channel after SFX ducking.
    Replays the percussion sound sequence on channel 2 with resume=True.
```

### 2.4 Public API

```
init_audio() -> None
    Entry point. Calls _define_sfx() and _define_music().
    Must be called after pyxel.init() and before any playback.

play_sfx(sfx_id: int) -> None
    Plays sounds[sfx_id] on channel 3.
    Stops channel 2 (percussion ducking).
    Sets _sfx_ducking = True.

play_music(track_id: int) -> None
    Plays musics[track_id] via pyxel.playm().
    Loop = True except for jingle tracks (5, 6).
    Updates _current_music state.

stop_music() -> None
    Stops channels 0, 1, 2. Sets _current_music = None.

update_audio() -> None
    Per-frame update. Checks if SFX ducking is active.
    If ducking and channel 3 is silent, resumes percussion.
```

### 2.5 Standalone Test Block

```
if __name__ == "__main__":
    # Minimal Pyxel app for interactive audio testing
    class AudioTest:
        __init__: pyxel.init(), init_audio(), pyxel.run()
        update: Key handlers for music tracks and SFX, calls update_audio()
        draw: Display key mapping overlay
```

## 3. Sound Slot Layout

### SFX Slots (0–15)

Direct 1:1 mapping per the spec table. Each slot = one `sounds[i].set()` call.

### Music Sequence Slots (16–36)

| Slot | Track | Channel | Content |
|------|-------|---------|---------|
| 16 | Title | melody | Lead melody, pulse tone |
| 17 | Title | bass | Root notes, triangle tone |
| 18 | Title | percussion | Kick/snare pattern, noise tone |
| 19 | Hillside | melody | Energetic lead |
| 20 | Hillside | bass | Driving bassline |
| 21 | Hillside | percussion | Fast beat |
| 22 | Pipeworks | melody | Industrial melody |
| 23 | Pipeworks | bass | Heavy bass |
| 24 | Pipeworks | percussion | Mechanical rhythm |
| 25 | Skybridge | melody | Urgent lead |
| 26 | Skybridge | bass | Intense bassline |
| 27 | Skybridge | percussion | Rapid beat |
| 28 | Boss | melody | Aggressive lead |
| 29 | Boss | bass | Driving bass |
| 30 | Boss | percussion | Heavy drums |
| 31 | Clear | melody | Ascending fanfare |
| 32 | Clear | bass | Harmonic support |
| 33 | Clear | percussion | Celebratory hits |
| 34 | Gameover | melody | Somber phrase |
| 35 | Gameover | bass | Low sustain |
| 36 | Gameover | percussion | Sparse/silent |

Additional slots (37+) available if any track needs multi-section chaining.

### Music Track Entries (musics[0–6])

Each `musics[i].set()` receives three lists of sound slot indices:

```
musics[0].set([16], [17], [18])       # Title — single section, loops
musics[1].set([19], [20], [21])       # Hillside
musics[2].set([22], [23], [24])       # Pipeworks
musics[3].set([25], [26], [27])       # Skybridge
musics[4].set([28], [29], [30])       # Boss
musics[5].set([31], [32], [33])       # Clear (no loop)
musics[6].set([34], [35], [36])       # Game over (no loop)
```

If a track needs verse/chorus structure, its channel lists expand:
e.g., `musics[1].set([19, 37], [20, 38], [21, 39])` for a two-section Hillside track.

## 4. Data Flow

```
Game startup:
    main.py → pyxel.init() → audio.init_audio()
                                ├── _define_sfx()      → sounds[0..15]
                                └── _define_music()     → sounds[16..36+], musics[0..6]

Gameplay loop (each frame):
    main.py → update()
                ├── game logic → audio.play_sfx(id)    → pyxel.play(3, id) + duck ch2
                ├── state changes → audio.play_music(id) → pyxel.playm(id, loop=...)
                └── audio.update_audio()                → check ducking, resume ch2

State transitions:
    title screen → audio.play_music(MUSIC_TITLE)
    enter stage  → audio.play_music(MUSIC_HILLSIDE)
    boss fight   → audio.play_music(MUSIC_BOSS)
    stage clear  → audio.stop_music(); audio.play_music(MUSIC_CLEAR)
    game over    → audio.stop_music(); audio.play_music(MUSIC_GAMEOVER)
```

## 5. Dependencies

- **Import:** `import pyxel` only.
- **Runtime:** Requires `pyxel.init()` to have been called before `init_audio()`.
- **No circular dependencies:** audio.py imports nothing from the speednik package.

## 6. Interface Boundaries

The audio module exposes exactly 5 functions and a set of integer constants.
All internal state (_current_music, _sfx_ducking) is module-private.
Callers interact only through the public API — they never touch pyxel.sounds,
pyxel.musics, or pyxel.play/playm/stop directly for audio purposes.

This encapsulation means T-004-03 (game state machine) can integrate audio by
importing constants and calling functions, with no knowledge of slot assignments
or channel allocation.

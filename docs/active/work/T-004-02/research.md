# Research — T-004-02: Audio SFX and Music

## 1. Current Codebase State

The project is minimally scaffolded (T-001-01 complete). Relevant files:

- `speednik/main.py` — Class-based Pyxel app: 256x224, 60fps. No audio code.
- `speednik/constants.py` — Empty stub. No audio constants defined.
- `speednik/__init__.py` — Empty package marker.
- `speednik/stages/__init__.py` — Empty stages package.
- `pyproject.toml` — Dependencies: `pyxel` only. Build: hatchling.

No `audio.py` exists. No audio-related imports or calls anywhere in the codebase.
The audio module is entirely greenfield — no existing patterns to conform to or conflict with.

## 2. Pyxel Audio API (from type stubs and examples)

### 2.1 Core Objects

| Object | Description |
|--------|-------------|
| `pyxel.sounds[0..63]` | Sound slots. Each is a `Sound` instance with notes, tones, volumes, effects, speed. |
| `pyxel.musics[0..7]` | Music slots. Each is a `Music` instance with `seqs: Seq[Seq[int]]`. |
| `pyxel.channels[0..3]` | Playback channels with gain and detune controls. |

### 2.2 Sound.set() Parameters

```python
pyxel.sounds[slot].set(
    notes: str,    # MML: "[CDEFGAB][#-]?[0-4]" or "R" for rest. Space-separated groups.
    tones: str,    # Per-note: T(riangle), S(quare), P(ulse), N(oise)
    volumes: str,  # Per-note: 0–7
    effects: str,  # Per-note: N(one), S(lide), V(ibrato), F(adeout)
    speed: int,    # Frames per note tick
)
```

- Notes string: each character pair is a note. Spaces are ignored (cosmetic grouping).
- Tones/volumes/effects strings: one character per note, applied sequentially.
- If tones/volumes/effects are shorter than notes, the last value repeats.

### 2.3 Sound.mml() Method

```python
pyxel.sounds[slot].mml(code: str)  # Full MML parsing (note lengths, tempo, etc.)
```

An alternative to `.set()` — uses standard MML syntax with tempo, octave, note length commands. Less documented but more expressive for complex melodies.

### 2.4 Playback Functions

```python
pyxel.play(ch, snd, *, loop=False)     # Play sound(s) on a channel
pyxel.playm(msc, *, loop=False)        # Play a music entry (auto-assigns channels 0,1,2,...)
pyxel.stop(ch=None)                     # Stop a channel or all channels
pyxel.play_pos(ch) -> (snd_idx, tick)   # Query playback position, None if stopped
```

- `playm(msc, loop=True)` plays `musics[msc]`, assigning seq[0]→ch0, seq[1]→ch1, seq[2]→ch2.
- `play(ch, snd)` can take a single int, list of ints, Sound object, or MML string.
- When `play()` receives a list, sounds play sequentially on that channel.

### 2.5 Music.set() Parameters

```python
pyxel.musics[slot].set(
    [list_of_sound_ids_ch0],  # Melody: sounds played sequentially on channel 0
    [list_of_sound_ids_ch1],  # Bass: sounds played sequentially on channel 1
    [list_of_sound_ids_ch2],  # Percussion: sounds played sequentially on channel 2
)
```

Each list contains sound slot indices. When played via `playm()`, each list loops independently on its assigned channel.

### 2.6 Resource Limits

- 64 sound slots: `sounds[0..63]`
- 8 music slots: `musics[0..7]`
- 4 playback channels: `channels[0..3]`

## 3. Specification Constraints (Section 6)

### 3.1 Channel Allocation (Fixed)

| Channel | Role |
|---------|------|
| 0 | Music: melody/lead |
| 1 | Music: bass/harmony |
| 2 | Music: percussion/rhythm |
| 3 | SFX |

### 3.2 SFX Requirements (16 slots, sounds[0..15])

| Slot | Name | Character |
|------|------|-----------|
| 0 | Ring collect | Short ascending arpeggio, ~4 frames |
| 1 | Jump | Quick rising tone |
| 2 | Spindash charge | Ascending buzz, retriggered |
| 3 | Spindash release | Sharp burst |
| 4 | Enemy destroy | Pop + descending sparkle |
| 5 | Enemy bounce | Higher jump variant |
| 6 | Spring | Sine pitch bend (boing) |
| 7 | Ring loss | Scatter, descending |
| 8 | Hurt/death | Harsh descending |
| 9 | Checkpoint | Two-tone chime |
| 10 | Stage clear | Ascending fanfare (longer) |
| 11 | Boss hit | Metallic impact |
| 12 | Liquid rising | Low rumble loop |
| 13 | Menu select | Click |
| 14 | Menu confirm | Chime |
| 15 | 1-up | Classic jingle |

### 3.3 Music Requirements (7 tracks, musics[0..6])

| Slot | Reference | Usage |
|------|-----------|-------|
| 0 | Genesis_of_Glory.mp3 | Title/menu |
| 1 | Pixel_Pursuit.mp3 | Stage 1: Hillside Rush |
| 2 | Chrome_Citadel.mp3 | Stage 2: Pipe Works |
| 3 | Genesis_Gauntlet.mp3 | Stage 3: Skybridge Gauntlet |
| 4 | (original) | Boss theme |
| 5 | (original) | Stage clear jingle |
| 6 | (original) | Game over |

Each uses 3 channels (melody, bass, percussion) via musics[] entry.

### 3.4 SFX Priority

- Channel 3 SFX preempts immediately (no queue).
- Channel 2 (percussion) ducks during SFX playback, then resumes.

### 3.5 Loop Requirement

All music tracks must loop cleanly — no audible gap at the loop point.

## 4. Reference Assets

Four MP3 files in `assets/` (~721KB each):
- `MAIN_MENU_Genesis_of_Glory.mp3`
- `LV1_Pixel_Pursuit.mp3`
- `LV2_Chrome_Citadel.mp3`
- `LV3_Genesis_Gauntlet.mp3`

These are compositional references only — not loaded at runtime.
Cannot be analyzed programmatically in this context. MML transcription will capture the intended feel (tempo, key, melodic contour, rhythmic character) as described by their names and usage context.

## 5. Sound Slot Budget

- SFX: slots 0–15 (16 slots)
- Music sequences: slots 16–63 (48 slots available)
- 7 tracks × 3 channels = 21 sound sequences needed for music
- Slots 16–36 for music sequences, leaving 37–63 free for future use

## 6. Integration Points

- `init_audio()` must be called during app startup, after `pyxel.init()`.
- `play_sfx(sfx_id)` called by future game modules (player.py, objects.py, enemies.py).
- `play_music(track_id)` and `stop_music()` called by game state machine (T-004-03).
- Module must be self-contained with no dependencies beyond `pyxel`.

## 7. Constraints and Risks

1. **No programmatic MP3 analysis** — MML transcriptions are creative approximations.
2. **4-frame SFX limitation** — very short sounds need careful note/speed choices.
3. **Channel 2 ducking** — requires tracking music playback state to resume percussion.
4. **Loop gaps** — sound sequence lengths must align across all 3 channels for clean loops.
5. **Speed parameter affects all notes equally** — no per-note duration control in `.set()`.
6. **Standalone test mode** — module must be runnable directly for audio verification.

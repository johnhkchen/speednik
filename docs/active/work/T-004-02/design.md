# Design — T-004-02: Audio SFX and Music

## 1. Sound Definition Approach

### Option A: `Sound.set()` with note strings

Use the `.set(notes, tones, volumes, effects, speed)` API for all sounds. Each SFX and
music sequence is a single call with explicit note, tone, volume, and effect strings.

**Pros:** Well-documented in Pyxel examples. Direct control over every parameter. Easy to
read and modify. Each sound is self-contained in one call.

**Cons:** No per-note duration control — all notes share the same `speed` value. Complex
melodies with varying rhythms need workarounds (rests for longer notes, multiple sounds
chained for tempo changes).

### Option B: `Sound.mml()` with MML code strings

Use the newer `.mml(code)` method which supports standard MML with tempo (T), octave (O),
note length (L), and per-note duration control.

**Pros:** More expressive for complex melodies. Standard MML syntax is well-known.
Per-note duration. Tempo control within a single sound.

**Cons:** Less documented in Pyxel. Unclear if all MML features are fully supported.
Mixing `.mml()` and `.set()` in the same codebase could be confusing.

### Option C: Hybrid — `.set()` for SFX, `.set()` for music sequences

Use `.set()` for everything. Handle rhythm variation in music by chaining multiple sound
slots per channel (each with different speed values), assembled via `musics[].set()`.

**Pros:** Consistent API usage. Sound chaining naturally models musical sections
(verse, chorus). Different speeds per section enable rhythmic variety.

**Cons:** Uses more sound slots. More sound slots to manage.

### Decision: Option C — Hybrid with `.set()` throughout

**Rationale:** The `.set()` API is battle-tested in Pyxel examples and has clear semantics.
SFX are short enough that fixed speed works perfectly. Music sequences can be broken into
sections (each a sound slot) with different speeds if needed, then chained via the
`musics[].set()` list mechanism. This avoids underdocumented `.mml()` behavior and keeps
the entire module consistent.

## 2. Sound Slot Allocation Strategy

### Layout

```
Slots 0–15:   SFX (fixed by spec)
Slots 16–36:  Music sequences (3 per track × 7 tracks = 21 slots)
Slots 37–63:  Reserved for future use
```

### Music Slot Mapping

Each music track needs 3 sound sequences (melody, bass, percussion):

| Track | Melody | Bass | Percussion | Purpose |
|-------|--------|------|------------|---------|
| 0 | 16 | 17 | 18 | Title/menu |
| 1 | 19 | 20 | 21 | Hillside Rush |
| 2 | 22 | 23 | 24 | Pipe Works |
| 3 | 25 | 26 | 27 | Skybridge Gauntlet |
| 4 | 28 | 29 | 30 | Boss theme |
| 5 | 31 | 32 | 33 | Stage clear jingle |
| 6 | 34 | 35 | 36 | Game over |

For tracks with multiple sections (verse/chorus), chain multiple sound slots per channel.
Additional slots drawn from 37+ as needed.

## 3. SFX Design Philosophy

Each SFX must be instantly recognizable for its game purpose:

- **Bright/positive events** (ring, 1-up, checkpoint): Major key arpeggios, ascending.
- **Action events** (jump, spring, spindash): Quick tonal sweeps with movement feel.
- **Negative events** (hurt, ring loss, death): Descending, harsh tones.
- **Impact events** (enemy destroy, boss hit): Sharp attack, noise component.
- **UI events** (menu select, confirm): Clean, short, non-intrusive.

Design parameters per SFX:
- **Speed:** 4–8 for very short SFX (ring, click), 10–15 for medium (jump, spring),
  20–30 for longer SFX (stage clear, 1-up).
- **Tone:** Square/Pulse for melodic SFX, Noise for impacts/percussion, Triangle for smooth tones.
- **Effects:** Slide for pitch bends, Fadeout for trails, Vibrato for sustain, None for sharp attacks.

## 4. Music Composition Strategy

### 4.1 Reference Interpretation

Cannot programmatically analyze the MP3 files, so compositions are original chiptune
arrangements that capture the implied feel from the track names and usage context:

| Track | Name/Feel | Tempo | Key | Character |
|-------|-----------|-------|-----|-----------|
| 0 | Genesis of Glory | ~120 BPM | C major | Triumphant, heroic, menu-worthy |
| 1 | Pixel Pursuit | ~140 BPM | G major | Energetic, driving, green-hills feel |
| 2 | Chrome Citadel | ~130 BPM | D minor | Industrial, mechanical, underground |
| 3 | Genesis Gauntlet | ~150 BPM | E minor | Intense, high-altitude, urgent |
| 4 | Boss theme | ~160 BPM | A minor | Tense, rhythmic, aggressive |
| 5 | Stage clear | ~120 BPM | C major | Short ascending fanfare (no loop) |
| 6 | Game over | ~80 BPM | C minor | Short somber phrase (no loop) |

### 4.2 Three-Channel Arrangement

Each track uses the fixed channel allocation:
- **Ch 0 (Melody):** Pulse or Square tone. Lead melody with vibrato/slide effects.
- **Ch 1 (Bass):** Triangle tone. Root notes and fifths, steady rhythm.
- **Ch 2 (Percussion):** Noise tone. Kick/snare/hi-hat patterns via pitch variation.

### 4.3 Loop Strategy

- Tracks 0–4: Full loops. All three channel sequences must have identical total tick
  counts so they realign at loop point. Achieved by padding shorter sequences with rests.
- Tracks 5–6: Jingles. Played with `loop=False`. Still defined via musics[] for
  consistent API, but `play_music()` passes loop=False for these slots.

## 5. SFX Priority / Channel Ducking Design

### The Problem

Spec requires: "channel 3 SFX preempts immediately, channel 2 (percussion) ducks during
SFX." Pyxel has no built-in ducking mechanism.

### Approach: Software-Managed Ducking

`play_sfx()` will:
1. Play the SFX on channel 3 via `pyxel.play(3, sfx_id)`.
2. Stop channel 2 (percussion) via `pyxel.stop(2)`.
3. Set a module-level flag `_sfx_ducking = True`.

`update_audio()` (called each frame from game loop) will:
1. Check if `_sfx_ducking` is True.
2. Query `pyxel.play_pos(3)` — if None (SFX finished), resume percussion.
3. Resume by replaying the current music's percussion sequence with `resume=True`.
4. Clear the ducking flag.

### Alternative Considered: No ducking

Just play SFX on channel 3 and let percussion continue. Simpler but violates spec.

**Decision:** Implement software ducking. The `update_audio()` function is a small addition
and the game loop already calls update functions every frame.

## 6. Public API Design

```python
def init_audio() -> None
def play_sfx(sfx_id: int) -> None
def play_music(track_id: int) -> None
def stop_music() -> None
def update_audio() -> None  # Called each frame for ducking management
```

`update_audio()` is not in the acceptance criteria but is necessary for ducking. It's a
lightweight per-frame call that only does work when ducking is active.

## 7. Standalone Test Mode

When `audio.py` is run directly (`python -m speednik.audio`), it will:
1. Initialize Pyxel with a minimal window.
2. Call `init_audio()`.
3. Display a key mapping: number keys 0–6 for music tracks, letter keys for SFX.
4. Allow interactive testing of all sounds and music.

This satisfies the acceptance criterion for standalone verification.

## 8. Rejected Alternatives

1. **External audio files (WAV/OGG):** Spec mandates Pyxel's native engine only.
2. **Resource file (.pyxres):** Would require the Pyxel editor. Code-defined sounds are
   more version-controllable and reviewable.
3. **Dynamic sound generation:** Computing MML at runtime adds complexity for no benefit.
   All sounds are static data defined at init time.

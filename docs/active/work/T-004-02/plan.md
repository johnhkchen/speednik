# Plan — T-004-02: Audio SFX and Music

## Step 1: Create audio.py scaffold with constants and state

Create `speednik/audio.py` with:
- All SFX_* and MUSIC_* constants
- Channel constants (CH_MELODY, CH_BASS, CH_PERCUSSION, CH_SFX)
- _JINGLE_TRACKS set
- Module state variables (_current_music, _sfx_ducking)
- Empty function stubs for all public and internal functions
- Standalone test block skeleton

**Verification:** File imports without error: `python -c "from speednik import audio"`

## Step 2: Implement all 16 SFX definitions

Fill in `_define_sfx()` with `pyxel.sounds[0..15].set()` calls:

- Slot 0 (Ring collect): Ascending arpeggio — notes like c4e4g4c5, pulse tone, speed 4
- Slot 1 (Jump): Rising tone — c3 to g3 slide, square tone, speed 5
- Slot 2 (Spindash charge): Ascending buzz — low to high with noise, speed 3
- Slot 3 (Spindash release): Sharp burst — high note with fast fadeout, speed 2
- Slot 4 (Enemy destroy): Pop then descending sparkle, speed 5
- Slot 5 (Enemy bounce): Higher jump variant, speed 5
- Slot 6 (Spring): Pitch bend boing — sine sweep, triangle tone, speed 6
- Slot 7 (Ring loss): Descending scatter — falling notes, speed 5
- Slot 8 (Hurt/death): Harsh descending — square tone, speed 8
- Slot 9 (Checkpoint): Two-tone chime — two clean notes, speed 10
- Slot 10 (Stage clear): Ascending fanfare — longer, speed 12
- Slot 11 (Boss hit): Metallic impact — noise burst, speed 3
- Slot 12 (Liquid rising): Low rumble — triangle low octave, speed 15
- Slot 13 (Menu select): Click — single noise note, speed 3
- Slot 14 (Menu confirm): Chime — clean high note, speed 6
- Slot 15 (1-up): Classic jingle — ascending phrase, speed 10

**Verification:** Standalone test mode plays each SFX by pressing keys.

## Step 3: Implement public API functions

Implement the 5 public functions:

- `init_audio()`: Calls _define_sfx() and _define_music().
- `play_sfx(sfx_id)`: Play on ch3, duck ch2, set flag.
- `play_music(track_id)`: playm with loop logic, update state.
- `stop_music()`: Stop ch 0–2, clear state.
- `update_audio()`: Check ducking, resume percussion when SFX ends.

**Verification:** Can call init_audio(), play_sfx(), play_music(), stop_music() without error.

## Step 4: Compose music track 0 — Title/Menu (Genesis of Glory feel)

Define sounds[16–18] and musics[0]:
- Melody (slot 16): Heroic, triumphant theme in C major. Pulse tone, moderate tempo.
  Broad intervals, strong melody. ~120 BPM feel (speed ~20).
- Bass (slot 17): Root-fifth pattern. Triangle tone. Steady quarter notes.
- Percussion (slot 18): Standard rock beat. Noise tone. Kick-snare alternation.

**Verification:** `play_music(0)` plays a recognizable title theme that loops cleanly.

## Step 5: Compose music track 1 — Hillside Rush (Pixel Pursuit feel)

Define sounds[19–21] and musics[1]:
- Melody (slot 19): Bright, energetic in G major. Fast runs and arpeggios.
  Green-hills Sonic vibe. ~140 BPM feel (speed ~15).
- Bass (slot 20): Driving eighth-note bassline. Triangle tone.
- Percussion (slot 21): Upbeat pattern. Fast hi-hat feel.

**Verification:** `play_music(1)` plays an energetic stage theme that loops cleanly.

## Step 6: Compose music track 2 — Pipe Works (Chrome Citadel feel)

Define sounds[22–24] and musics[2]:
- Melody (slot 22): Dark, industrial in D minor. Square tone with vibrato.
  Mechanical, underground feel. ~130 BPM (speed ~18).
- Bass (slot 23): Heavy, syncopated bass. Triangle tone.
- Percussion (slot 24): Mechanical rhythm with emphasis on even beats.

**Verification:** `play_music(2)` plays a moody underground theme that loops cleanly.

## Step 7: Compose music track 3 — Skybridge Gauntlet (Genesis Gauntlet feel)

Define sounds[25–27] and musics[3]:
- Melody (slot 25): Intense, urgent in E minor. Fast tempo, driving melody.
  High-altitude tension. ~150 BPM (speed ~12).
- Bass (slot 26): Aggressive bassline. Triangle tone.
- Percussion (slot 27): Rapid beat, driving rhythm.

**Verification:** `play_music(3)` plays an intense action theme that loops cleanly.

## Step 8: Compose music track 4 — Boss theme (original)

Define sounds[28–30] and musics[4]:
- Melody (slot 28): Tense, aggressive in A minor. Short aggressive phrases.
  ~160 BPM (speed ~10).
- Bass (slot 29): Driving, ominous bass. Triangle tone.
- Percussion (slot 30): Heavy, relentless beat.

**Verification:** `play_music(4)` plays a tense boss theme that loops cleanly.

## Step 9: Compose music track 5 — Stage clear jingle (original)

Define sounds[31–33] and musics[5]:
- Melody (slot 31): Short ascending fanfare in C major. Celebratory.
- Bass (slot 32): Harmonic support chord tones.
- Percussion (slot 33): Celebratory rhythm hits.
- Played with loop=False.

**Verification:** `play_music(5)` plays a short victory jingle that ends naturally.

## Step 10: Compose music track 6 — Game over (original)

Define sounds[34–36] and musics[6]:
- Melody (slot 34): Short somber phrase in C minor. Descending.
- Bass (slot 35): Low sustained notes.
- Percussion (slot 36): Minimal or silent.
- Played with loop=False.

**Verification:** `play_music(6)` plays a short somber phrase that ends naturally.

## Step 11: Implement standalone test mode

Complete the `if __name__ == "__main__"` block:
- Full Pyxel app with key mapping display.
- Number keys 0–6 trigger music tracks.
- Letter keys a–p trigger SFX 0–15.
- Space stops music.
- Calls `update_audio()` each frame.
- Visual feedback: show currently playing track and last SFX triggered.

**Verification:** `uv run python -m speednik.audio` launches interactive audio tester.

## Step 12: Final verification and commit

- Run the standalone test to verify all 16 SFX and 7 music tracks play.
- Verify loop points on tracks 0–4 (no audible gap).
- Verify jingles (tracks 5–6) end naturally.
- Verify SFX ducking works (play music, trigger SFX, percussion resumes).
- Commit the completed audio.py.

**Verification:** All acceptance criteria met. Clean commit.

## Testing Strategy

- **Primary:** Standalone interactive test mode (visual + auditory verification).
- **Import test:** `python -c "from speednik.audio import init_audio, play_sfx, play_music, stop_music, update_audio"`
- **No automated unit tests for audio output** — chiptune correctness is subjective
  and requires human listening. The standalone test mode serves as the verification tool.
- **API contract test:** Verify functions accept correct argument types and don't crash.

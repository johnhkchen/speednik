# Progress — T-004-02: Audio SFX and Music

## Completed

- [x] Step 1: Created audio.py scaffold with all constants, state, and function stubs
- [x] Step 2: Implemented all 16 SFX definitions (sounds[0..15])
  - Fixed octave range issues: Pyxel supports octaves 0–4 only
  - Fixed tone/volume/effect string lengths to match note counts (including rests)
- [x] Step 3: Implemented public API (init_audio, play_sfx, play_music, stop_music, update_audio)
- [x] Step 4: Composed Track 0 — Title/Menu (Genesis of Glory feel, C major, speed 20)
- [x] Step 5: Composed Track 1 — Hillside Rush (Pixel Pursuit feel, G major, speed 15)
- [x] Step 6: Composed Track 2 — Pipe Works (Chrome Citadel feel, D minor, speed 18)
- [x] Step 7: Composed Track 3 — Skybridge Gauntlet (Genesis Gauntlet feel, E minor, speed 12)
- [x] Step 8: Composed Track 4 — Boss theme (original, A minor, speed 10)
- [x] Step 9: Composed Track 5 — Stage clear jingle (C major, speed 12, no loop)
- [x] Step 10: Composed Track 6 — Game over (C minor, speed 20, no loop)
- [x] Step 11: Implemented standalone test mode (AudioTest class, key bindings)
- [x] Step 12: Final verification
  - All 16 SFX define without error
  - All 7 music tracks define with 3 channels each
  - All looping tracks have aligned channel tick counts
  - Public API functions execute without crashes
  - Import verification passes

## Deviations from Plan

1. **Octave range:** Original SFX designs used octaves 5–6, which are out of Pyxel's 0–4 range.
   Transposed all affected notes down by 1–2 octaves. Affects SFX 0 (ring), 10 (stage clear),
   15 (1-up), and Track 5 melody (clear jingle).

2. **Rest handling:** Pyxel requires tone/volume/effect characters for rest notes too.
   Fixed SFX 9 (checkpoint) where tone string had mismatched length.

3. **Percussion alignment:** Track 5 (clear) percussion had 20 notes vs 16 for melody/bass.
   Trimmed to 16 notes for clean alignment.

## Remaining

None. All steps complete.

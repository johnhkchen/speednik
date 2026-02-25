# Review — T-004-02: Audio SFX and Music

## Summary of Changes

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `speednik/audio.py` | 688 | Complete audio module: 16 SFX, 7 music tracks, playback API, standalone tester |

### Files Modified

None. The audio module is fully self-contained with no changes to existing files.

## Acceptance Criteria Status

- [x] `audio.py` implements `init_audio()` — defines all sounds[] and musics[] at startup
- [x] `audio.py` implements `play_sfx(sfx_id)` — plays on channel 3
- [x] `audio.py` implements `play_music(track_id)` — starts music looping on channels 0–2
- [x] `audio.py` implements `stop_music()` — stops all music channels
- [x] 16 SFX defined in sounds[0..15] with recognizable character per spec descriptions
- [x] 7 music tracks defined in musics[0..6]:
  - Track 0: Title/menu — heroic C major theme (Genesis of Glory feel)
  - Track 1: Hillside Rush — energetic G major (Pixel Pursuit feel)
  - Track 2: Pipe Works — dark D minor industrial (Chrome Citadel feel)
  - Track 3: Skybridge Gauntlet — intense E minor (Genesis Gauntlet feel)
  - Track 4: Boss — tense A minor, aggressive and rhythmic
  - Track 5: Stage clear — short ascending C major fanfare
  - Track 6: Game over — short somber descending phrase
- [x] Each music track uses 3 channels (melody, bass, percussion)
- [x] SFX priority: channel 3 preempts, channel 2 ducks during SFX via `update_audio()`
- [x] All looping tracks (0–4) have aligned tick counts across channels for clean loop points
- [x] Jingle tracks (5–6) play once without looping
- [x] Standalone test: `uv run python -m speednik.audio` launches interactive audio tester

## Architecture Decisions

1. **`update_audio()` added to public API** — not in the original acceptance criteria but
   required for SFX ducking. This is a lightweight per-frame call that only does work when
   ducking is active. The game loop must call it each frame.

2. **Sound slot layout** — SFX in slots 0–15, music sequences in 16–36, leaving 37–63 free.
   Music tracks use single-section sound sequences (one slot per channel per track).

3. **All sounds use `.set()` API** — consistent with Pyxel examples. Avoided the less-documented
   `.mml()` method. Rhythm variation per track achieved through different `speed` values.

## Test Coverage

### Automated Verification

- **Import test:** All public symbols import without error.
- **Init test:** `init_audio()` successfully defines all 16 SFX and 7 music tracks.
- **Channel alignment:** All 7 tracks verified to have matching tick counts across 3 channels.
- **API contract:** `play_sfx()`, `play_music()`, `stop_music()`, `update_audio()` all
  execute without crashes.

### Manual Verification Required

- **Auditory quality:** SFX and music compositions need human listening via the standalone
  tester (`uv run python -m speednik.audio`). Each SFX should be recognizable for its
  purpose, and music tracks should evoke the intended mood.
- **Loop smoothness:** Looping tracks need ear-testing for audible gaps at the loop point.
- **Ducking behavior:** Play a music track, trigger SFX, verify percussion ducks and resumes.

## Open Concerns

1. **Compositional quality is subjective.** The MML note sequences are original chiptune
   arrangements guided by track names and usage context. Without programmatic analysis of the
   reference MP3s, the compositions capture the *intended feel* rather than specific melodic
   transcriptions. A human composer may want to refine the note sequences after listening.

2. **Pyxel octave range (0–4).** Some SFX that would benefit from very high notes (ring
   collect, 1-up jingle) are constrained to octave 4 maximum. This limits the brightness of
   ascending arpeggios but is a hard engine constraint.

3. **Percussion ducking granularity.** The current implementation stops and resumes the entire
   percussion sequence. If a very long SFX plays, percussion resumes from a `resume=True`
   position which may not perfectly align with the beat. In practice, most SFX are short
   enough (~50–200ms) that this is not audible.

4. **No per-note duration control.** All notes within a single sound share the same `speed`
   value. Complex rhythmic patterns (dotted notes, triplets) would require splitting into
   multiple sound slots. Current compositions use uniform note lengths within each sequence.

5. **`b-` (B-flat) usage** in Pipe Works melody — verified to parse correctly but is less
   common in the Pyxel examples. If issues arise, can substitute `a#`.

## Integration Notes for T-004-03

The game state machine (T-004-03) integrates audio by:
```python
from speednik.audio import init_audio, play_sfx, play_music, stop_music, update_audio
from speednik.audio import MUSIC_TITLE, MUSIC_HILLSIDE, SFX_RING, SFX_JUMP, ...
```

- Call `init_audio()` once after `pyxel.init()`.
- Call `update_audio()` once per frame in the game loop.
- Use `play_music(MUSIC_*)` on state transitions (title → stage → boss → clear/gameover).
- Use `play_sfx(SFX_*)` for game events.
- Use `stop_music()` before switching tracks.

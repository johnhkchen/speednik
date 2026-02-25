# Design: Music Transcription, Slope Collision, Loop Entry

**Date:** 2026-02-25
**Issues addressed:** music not using MP3 reference assets, player stuttering on slope transitions, loop entry blocked by wall sensors.

---

## 1. Music — Audio Analysis + MML Transcription

### Problem
`audio.py` composes all tracks manually with generic MML strings. The four reference MP3s in `assets/` are unused. The chiptune tracks capture the right key/tempo metadata but feel generic and don't match the reference tracks' melodies and rhythms.

### Approach
Use `librosa` (dev dependency, analysis-only) to extract BPM and note onsets from each MP3, then hand-map those to Pyxel MML notation.

Pipeline per track:
1. Load MP3 with `librosa.load()`
2. Extract tempo with `librosa.beat.beat_track()`
3. Detect harmonic content with `librosa.effects.harmonic()` + `librosa.feature.chroma_stft()` to identify the dominant scale
4. Detect note onsets with `librosa.onset.onset_detect()` and pitch-track the dominant melody line with `librosa.yin()`
5. Quantise detected pitches to the nearest semitone and map to Pyxel note names (c/d/e/f/g/a/b + octave digit)
6. Rewrite the `pyxel.sounds[N].set(...)` calls in `audio.py` with the extracted sequences

The analysis is a one-time dev step — `librosa` is not imported by the game at runtime.

### Scope
- Rewrite `_define_track_title()`, `_define_track_hillside()`, `_define_track_pipeworks()`, `_define_track_skybridge()` with analysed data
- Boss, clear, and gameover tracks are original compositions — leave untouched
- All four tracks: melody (pulse), bass (triangle), percussion (noise) — same channel layout

---

## 2. Slope Transition — Two-pass Quadrant Resolve

### Problem
`resolve_collision()` in `terrain.py` computes `quadrant = get_quadrant(state.angle)` once at frame start. Floor sensors fire in that quadrant's direction. `_snap_to_floor()` then updates `state.angle` to the new tile's angle — but the new quadrant doesn't take effect until the **next** frame. On the frame of a tile-angle transition (e.g. flat→45° slope), the sensor fires in the wrong direction and the snap is incorrect, causing a one-frame stutter or the player to briefly detach.

### Approach
After snapping, check whether the new angle implies a different quadrant. If it does, immediately re-run `find_floor()` with the updated state and snap again. This is a second pass within the same frame.

```
resolve_collision():
  q = get_quadrant(state.angle)
  floor = find_floor(state, tile_lookup)  # pass 1, uses old quadrant
  if on_ground and floor within snap distance:
    _snap_to_floor(state, floor, q)         # updates state.angle
    new_q = get_quadrant(state.angle)
    if new_q != q:                          # quadrant changed
      floor2 = find_floor(state, tile_lookup)  # pass 2, uses new quadrant
      if floor2 within snap distance:
        _snap_to_floor(state, floor2, new_q)
```

At most two passes per frame. The second pass only fires on actual quadrant transitions, which are rare, so there is no meaningful performance cost.

### Scope
- Modify `resolve_collision()` in `terrain.py` only
- No changes to sensor cast functions or data structures

---

## 3. Loop Entry — Angle-Gated Wall Sensor

### Problem
The right wall sensor casts horizontally from the player's center. Loop entry tiles have shallow angles (15–35°) but their `width_array` at the player's center row is non-zero. The sensor interprets this as a wall and pushes the player leftward, preventing loop entry.

### Root cause
`width_array()` is computed for all tiles regardless of angle. There is no check whether the hit tile is actually meant to act as a wall rather than a floor.

### Approach
In `find_wall_push()`, after the sensor cast returns a hit, check the hit tile's `tile_angle`. If the angle is within the "floor quadrant" range (byte angle ≤ 48 or ≥ 208, corresponding to ±67° of flat), ignore the hit. Only genuinely steep tiles (> 67° from flat) can block horizontal movement.

```python
result = _sensor_cast(...)
if result.found:
    deg = byte_angle * 360 / 256
    is_floor_angle = deg <= 67 or deg >= 293
    if is_floor_angle:
        return SensorResult(found=False, ...)
```

The 67° threshold leaves wall sensors active for genuinely vertical surfaces (loop walls at 90°+) while ignoring shallow entry ramps.

### Scope
- Modify `find_wall_push()` in `terrain.py` only
- The angle threshold (67°) maps to byte value 48 — add a named constant `WALL_ANGLE_THRESHOLD = 48`

---

## Testing

Each fix needs regression tests:

- **Music**: Snapshot test that the MML strings in `audio.py` have changed from defaults; basic pyxel mock test that `init_audio()` does not raise
- **Slope transition**: Unit test in `test_terrain.py` — player at quadrant 0 snaps correctly to a tile with quadrant-1 angle within the same frame; no one-frame detach
- **Loop entry**: Unit test in `test_terrain.py` — wall sensor returns `found=False` for a hit tile with byte angle 20 (shallow slope); returns `found=True` for byte angle 64 (steep wall)

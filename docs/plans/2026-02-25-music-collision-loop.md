# Music Transcription, Slope Collision, and Loop Entry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two physics bugs (slope transition stutter, loop entry blocked by wall sensors) and improve the four stage music tracks by transcribing from the reference MP3s using librosa.

**Architecture:** Two targeted one-function edits to `terrain.py`, one constant added to `constants.py`, and a one-time dev-time audio analysis script that feeds a rewrite of the four track-define functions in `audio.py`.

**Tech Stack:** Python, Pyxel chiptune MML, librosa (dev-only analysis), pytest.

---

## Task 1: Add `WALL_ANGLE_THRESHOLD` constant

**Files:**
- Modify: `speednik/constants.py` (after the `ANGLE_STEPS` line, ~line 118)

**Step 1: Add the constant**

After the `ANGLE_STEPS = 256` line in `constants.py`, add:

```python
# Wall sensor angle gate (§3.5)
# Tiles with byte angle <= this or >= (256 - this) are considered floor-range
# and must not block horizontal wall sensors. 48 ≈ 67.5°.
WALL_ANGLE_THRESHOLD = 48
```

**Step 2: Verify the test suite still passes**

```bash
uv run pytest tests/ -q
```

Expected: all tests pass, no failures.

**Step 3: Commit**

```bash
git add speednik/constants.py
git commit -m "feat: add WALL_ANGLE_THRESHOLD constant for wall sensor angle gate"
```

---

## Task 2: Loop entry — angle-gated wall sensor

**Files:**
- Modify: `speednik/terrain.py` — `find_wall_push()` function
- Test: `tests/test_terrain.py`

**Context:** `find_wall_push()` currently returns a blocking hit for any tile that has solid content at the sensor row, regardless of the tile's angle. Loop entry tiles are shallow-angled floor tiles (byte angle 10–35) that appear as a wall to the right wall sensor. The fix: after the cast, check `result.tile_angle`; if it is in the floor range, discard the hit.

### Step 1: Write the failing tests

Add to `tests/test_terrain.py`:

```python
from speednik.constants import WALL_SENSOR_EXTENT, STANDING_HEIGHT_RADIUS


class TestWallSensorAngleGate:
    """Wall sensor must not block movement onto shallow-angled floor tiles."""

    def _state_moving_right(self):
        """Player on flat ground, moving right at speed 5."""
        return PhysicsState(x=100.0, y=96.0, x_vel=5.0, on_ground=True, angle=0)

    def _lookup_at_sensor(self, tile):
        """Return a tile lookup that places `tile` exactly at the right wall sensor."""
        # Sensor is at x = 100 + WALL_SENSOR_EXTENT = 110, y = 96
        # tile_x = 110 // 16 = 6,  tile_y = 96 // 16 = 6
        def lookup(tx, ty):
            if tx == 6 and ty == 6:
                return tile
            return None
        return lookup

    def test_shallow_angle_tile_does_not_block(self):
        """Tile with byte angle < WALL_ANGLE_THRESHOLD must not block horizontal movement."""
        shallow = Tile(height_array=[16] * 16, angle=20, solidity=FULL)
        state = self._state_moving_right()
        result = find_wall_push(state, self._lookup_at_sensor(shallow), RIGHT)
        assert not result.found, (
            "Shallow-angled tile (loop entry) should be ignored by wall sensor"
        )

    def test_steep_angle_tile_does_block(self):
        """Tile with byte angle >= WALL_ANGLE_THRESHOLD must still block movement."""
        steep = Tile(height_array=[16] * 16, angle=64, solidity=FULL)
        state = self._state_moving_right()
        result = find_wall_push(state, self._lookup_at_sensor(steep), RIGHT)
        assert result.found and result.distance < 0, (
            "Steep-angled tile (genuine wall) must block horizontal movement"
        )

    def test_left_wall_shallow_angle_does_not_block(self):
        """Same gate applies to the left wall sensor."""
        shallow = Tile(height_array=[16] * 16, angle=236, solidity=FULL)
        # angle=236: 236*360/256 ≈ 332°, mirror of 28° — floor range on left side
        state = PhysicsState(x=100.0, y=96.0, x_vel=-5.0, on_ground=True, angle=0)
        # Left sensor at x = 100 - 10 = 90, tile_x = 90//16 = 5, tile_y = 6
        def lookup(tx, ty):
            if tx == 5 and ty == 6:
                return shallow
            return None
        result = find_wall_push(state, lookup, LEFT)
        assert not result.found, (
            "Shallow-angled tile on the left should also be ignored"
        )
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_terrain.py::TestWallSensorAngleGate -v
```

Expected: all three tests FAIL with `AssertionError` (gate not yet implemented).

**Step 3: Add the import to `terrain.py`**

In the imports at the top of `speednik/terrain.py`, add `WALL_ANGLE_THRESHOLD` to the existing `from speednik.constants import (...)` block:

```python
from speednik.constants import (
    ROLLING_HEIGHT_RADIUS,
    ROLLING_WIDTH_RADIUS,
    STANDING_HEIGHT_RADIUS,
    STANDING_WIDTH_RADIUS,
    WALL_ANGLE_THRESHOLD,   # ← add this line
    WALL_SENSOR_EXTENT,
)
```

**Step 4: Add the angle gate to `find_wall_push()`**

`find_wall_push()` ends with:

```python
    return _sensor_cast(sensor_x, sensor_y, cast_dir, tile_lookup, _no_top_only_filter)
```

Replace that final `return` with:

```python
    result = _sensor_cast(sensor_x, sensor_y, cast_dir, tile_lookup, _no_top_only_filter)

    # Angle gate: ignore hits on floor-range tiles (loop entry ramps, gentle slopes).
    # Only tiles whose angle is genuinely wall-like (steeper than ~67°) should block.
    if result.found:
        a = result.tile_angle
        if a <= WALL_ANGLE_THRESHOLD or a >= ANGLE_STEPS - WALL_ANGLE_THRESHOLD:
            return SensorResult(found=False, distance=0.0, tile_angle=0)

    return result
```

`ANGLE_STEPS` is already imported from `speednik.physics` via `byte_angle_to_rad`, which imports it from constants. To use it directly in `terrain.py`, also add `ANGLE_STEPS` to the constants import block:

```python
from speednik.constants import (
    ANGLE_STEPS,            # ← add this line
    ROLLING_HEIGHT_RADIUS,
    ROLLING_WIDTH_RADIUS,
    STANDING_HEIGHT_RADIUS,
    STANDING_WIDTH_RADIUS,
    WALL_ANGLE_THRESHOLD,
    WALL_SENSOR_EXTENT,
)
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_terrain.py::TestWallSensorAngleGate -v
```

Expected: all three tests PASS.

**Step 6: Run full test suite**

```bash
uv run pytest tests/ -q
```

Expected: all tests pass.

**Step 7: Commit**

```bash
git add speednik/terrain.py speednik/constants.py tests/test_terrain.py
git commit -m "fix: wall sensor ignores shallow-angled tiles (fixes loop entry blocked)"
```

---

## Task 3: Slope transition — two-pass quadrant resolve

**Files:**
- Modify: `speednik/terrain.py` — `resolve_collision()` function
- Test: `tests/test_terrain.py`

**Context:** `resolve_collision()` computes `quadrant = get_quadrant(state.angle)` once at frame start. After `_snap_to_floor()` updates `state.angle` to a new tile's angle, the implied quadrant may have changed — but the snap just performed used the wrong sensor direction (old quadrant). On the very next frame, the sensor fires in the new direction and jumps the player's position, causing a visual stutter. Fix: after snapping, if the quadrant changed, immediately run a second `find_floor()` + snap with the new quadrant in the same frame.

### Step 1: Write the failing test

Add to `tests/test_terrain.py`:

```python
class TestTwoPassQuadrantResolve:
    """Slope transitions must not cause a one-frame position jump."""

    def test_quadrant_transition_resolved_in_one_frame(self):
        """When snap changes the active quadrant, position is corrected immediately."""
        # angle=35 is byte 35, get_quadrant(35) = 1 (right-wall mode, 33–96).
        # Player starts at quadrant 0 (angle=0).  Floor sensor casts DOWN, finds
        # the tile (height=8 → surface_y at tile_y*16+8), snaps y.  After snap,
        # angle becomes 35 → quadrant 1.  Second pass fires: floor sensor casts
        # RIGHT from (x+h_rad, y±w_rad).  The same tile is returned for any
        # (tx, ty) so it is found, and x is snapped as well.
        slope_tile = Tile(height_array=[8] * 16, angle=35, solidity=FULL)

        def tile_lookup(tx, ty):
            return slope_tile

        # Set up player just above where the down sensor will find the surface.
        # Floor sensor A at (x - 9, y + 20) = (91, 112). Tile at (5, 7).
        # height=8 → surface_y = 7*16 + (16-8) = 120.  dist = 120-112 = 8.
        state = PhysicsState(x=100.0, y=92.0, angle=0, on_ground=True)

        resolve_collision(state, tile_lookup)

        assert state.on_ground, "Player must remain on ground across quadrant transition"
        assert state.angle == 35, "Player angle must update to new tile angle"
        # Two-pass: after the q0 y-snap (y=100) and angle→35→q1, a second q1
        # x-snap must also have fired. Without second pass, x stays at 100.0.
        # q1 sensor A at (100+20, 100+9)=(120,109) → tile (7,6), surface_x=7*16=112,
        # dist=112-120=-8 → snap x += -8 → x=92.
        assert state.x == 92.0, (
            f"Two-pass snap should correct x to 92.0, got {state.x}. "
            "Without the fix, x stays at 100.0 and the correction is deferred one frame."
        )
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_terrain.py::TestTwoPassQuadrantResolve -v
```

Expected: FAIL. `AssertionError: Two-pass snap should correct x to 92.0, got 100.0`.

**Step 3: Implement the two-pass logic in `resolve_collision()`**

The current on-ground snap block in `resolve_collision()` is:

```python
    if state.on_ground:
        if floor_result.found and abs(floor_result.distance) <= _GROUND_SNAP_DISTANCE:
            # Snap to surface
            _snap_to_floor(state, floor_result, quadrant)
        else:
            # No floor — detach
            state.on_ground = False
            state.angle = 0
```

Replace it with:

```python
    if state.on_ground:
        if floor_result.found and abs(floor_result.distance) <= _GROUND_SNAP_DISTANCE:
            # Snap to surface
            _snap_to_floor(state, floor_result, quadrant)
            # Two-pass: if snapping changed the active quadrant, re-run the floor
            # sensor immediately with the new quadrant so the position is fully
            # corrected this frame instead of one frame later.
            new_quadrant = get_quadrant(state.angle)
            if new_quadrant != quadrant:
                floor_result2 = find_floor(state, tile_lookup)
                if floor_result2.found and abs(floor_result2.distance) <= _GROUND_SNAP_DISTANCE:
                    _snap_to_floor(state, floor_result2, new_quadrant)
        else:
            # No floor — detach
            state.on_ground = False
            state.angle = 0
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_terrain.py::TestTwoPassQuadrantResolve -v
```

Expected: PASS.

**Step 5: Run full test suite**

```bash
uv run pytest tests/ -q
```

Expected: all tests pass.

**Step 6: Commit**

```bash
git add speednik/terrain.py tests/test_terrain.py
git commit -m "fix: two-pass quadrant resolve eliminates slope transition stutter"
```

---

## Task 4: Audio analysis — extract tempo and key from reference MP3s

**Files:**
- Create: `tools/analyze_mp3s.py`

**Context:** `librosa` is used only at dev time to extract tempo (BPM) and dominant key from the four reference tracks. The output informs the MML rewrite in Task 5. `librosa` is added as a dev dependency and is **never imported by the game**.

**Step 1: Add librosa as a dev dependency**

```bash
uv add --dev librosa
```

Expected: `pyproject.toml` updated, `uv.lock` updated.

**Step 2: Write the analysis script**

Create `tools/analyze_mp3s.py`:

```python
"""tools/analyze_mp3s.py — Extract tempo, key, and melody hints from reference MP3s.

Usage:
    uv run python tools/analyze_mp3s.py

Output is printed to stdout. Use it to inform the MML rewrites in audio.py.
"""

from pathlib import Path

import librosa
import numpy as np

ASSETS = Path(__file__).parent.parent / "assets"
TRACKS = [
    ("MAIN_MENU_Genesis_of_Glory.mp3", "title",     "MUSIC_TITLE"),
    ("LV1_Pixel_Pursuit.mp3",          "hillside",  "MUSIC_HILLSIDE"),
    ("LV2_Chrome_Citadel.mp3",         "pipeworks", "MUSIC_PIPEWORKS"),
    ("LV3_Genesis_Gauntlet.mp3",       "skybridge", "MUSIC_SKYBRIDGE"),
]

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PYXEL_NOTE_NAMES = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]


def hz_to_pyxel_note(hz: float) -> str:
    """Convert a frequency in Hz to a Pyxel note string like 'g3' or 'c#4'."""
    if hz <= 0 or np.isnan(hz):
        return "r"
    midi = librosa.hz_to_midi(hz)
    octave = int(midi // 12) - 1          # MIDI octave 0=C0; Pyxel C1=octave1
    pyxel_octave = max(1, min(4, octave))  # clamp to Pyxel range 1–4
    note_idx = int(round(midi)) % 12
    return f"{PYXEL_NOTE_NAMES[note_idx]}{pyxel_octave}"


def analyze(path: Path):
    print(f"Loading {path.name}...")
    y, sr = librosa.load(str(path), duration=30.0)  # analyse first 30s

    # Tempo
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(tempo)

    # Key (dominant pitch class via chroma)
    harmonic = librosa.effects.harmonic(y)
    chroma = librosa.feature.chroma_stft(y=harmonic, sr=sr)
    dominant_pc = int(np.argmax(np.mean(chroma, axis=1)))
    key_name = NOTE_NAMES[dominant_pc]

    # Melody — fundamental frequency on harmonic component, sampled at beats
    f0, voiced, _ = librosa.pyin(
        harmonic,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C6"),
        sr=sr,
    )
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    f0_times = librosa.frames_to_time(np.arange(len(f0)), sr=sr)

    # Sample f0 at each beat
    melody_notes = []
    for bt in beat_times[:32]:
        idx = int(np.argmin(np.abs(f0_times - bt)))
        if voiced[idx]:
            melody_notes.append(hz_to_pyxel_note(f0[idx]))
        else:
            melody_notes.append("r")

    return {
        "tempo_bpm": round(tempo, 1),
        "dominant_key": key_name,
        "melody_sample": melody_notes,
    }


def main():
    for filename, track_id, const_name in TRACKS:
        path = ASSETS / filename
        if not path.exists():
            print(f"MISSING: {path}")
            continue
        result = analyze(path)
        print()
        print(f"=== {const_name} ({track_id}) ===")
        print(f"  Tempo:   {result['tempo_bpm']} BPM")
        print(f"  Key:     {result['dominant_key']}")
        print(f"  Melody sample (first 32 beats):")
        # Print as a Pyxel-style note string, 8 notes per line
        notes = result["melody_sample"]
        for i in range(0, len(notes), 8):
            chunk = " ".join(notes[i:i+8])
            print(f"    {chunk}")


if __name__ == "__main__":
    main()
```

**Step 3: Run the analysis script and record the output**

```bash
uv run python tools/analyze_mp3s.py
```

Expected: four blocks of output, one per track. **Copy the full output to a scratch note** — you will need the tempo, key, and melody sample in Task 5.

Example output format:
```
=== MUSIC_TITLE (title) ===
  Tempo:   118.0 BPM
  Key:     C
  Melody sample (first 32 beats):
    e3 g3 c4 b3 a3 g3 e3 r
    ...
```

**Step 4: Commit the script (not the analysis output)**

```bash
git add tools/analyze_mp3s.py pyproject.toml uv.lock
git commit -m "chore: add librosa dev dependency and MP3 analysis script"
```

---

## Task 5: Rewrite the four stage music tracks

**Files:**
- Modify: `speednik/audio.py` — `_define_track_title()`, `_define_track_hillside()`, `_define_track_pipeworks()`, `_define_track_skybridge()`

**Context:** Using the tempo/key/melody output from Task 4, rewrite each track function so the chiptune better matches the reference MP3. The channel layout (melody on slot N, bass on N+1, percussion on N+2) stays the same. The sound slots used stay the same (16–18 title, 19–21 hillside, 22–24 pipeworks, 25–27 skybridge).

**Pyxel `sounds[N].set()` quick reference:**

```
pyxel.sounds[N].set(
    notes,    # space-separated note string: "c3 e3 g3 r" or "c3e3g3r" (no spaces also valid)
    tones,    # one char per note: p=pulse s=square t=triangle n=noise
    volumes,  # one char per note: 0–7
    effects,  # one char per note: n=none s=slide v=vibrato f=fadeout
    speed,    # tempo: lower = faster; 1 frame per step at speed=1
)
```

One `speed` unit = 1 game frame (1/60 s). To convert BPM to speed:
`speed = round(60 / bpm * 60 / 4)` (assuming 4 steps per beat).

For reference: at 140 BPM → speed ≈ `60/140 * 60 / 4 ≈ 6.4` → use 6.

**Step 1: Write a smoke test before making changes**

Add to `tests/test_web_export.py` (or a new `tests/test_audio.py`):

```python
from unittest.mock import MagicMock, patch


def test_init_audio_does_not_raise():
    """init_audio() must define all slots without raising even with mock pyxel."""
    with patch("speednik.audio.pyxel") as mock_pyxel:
        sounds = {i: MagicMock() for i in range(40)}
        musics = {i: MagicMock() for i in range(8)}
        mock_pyxel.sounds = sounds
        mock_pyxel.musics = musics

        from speednik.audio import init_audio
        init_audio()   # must not raise

        # All 4 stage music tracks must register their music slot
        from speednik.audio import MUSIC_TITLE, MUSIC_HILLSIDE, MUSIC_PIPEWORKS, MUSIC_SKYBRIDGE
        musics[MUSIC_TITLE].set.assert_called_once()
        musics[MUSIC_HILLSIDE].set.assert_called_once()
        musics[MUSIC_PIPEWORKS].set.assert_called_once()
        musics[MUSIC_SKYBRIDGE].set.assert_called_once()
```

Run it to confirm it passes before you touch audio.py:

```bash
uv run pytest tests/ -k test_init_audio -v
```

Expected: PASS.

**Step 2: Rewrite `_define_track_title()`**

Using the tempo and key from the analysis output for `MUSIC_TITLE`, rewrite `_define_track_title()` in `audio.py`. Keep the same structure (melody slot 16, bass slot 17, percussion slot 18, then `pyxel.musics[MUSIC_TITLE].set([16], [17], [18])`).

Guidelines:
- Set `speed` based on the detected BPM: `round(60 / bpm * 60 / 4)`, minimum 6.
- Use the melody sample notes directly where they fit the Pyxel octave range (1–4).
- Fill gaps (rests) with bass and percussion to keep the track full.
- Melody tone: `"p"` (pulse) — bright lead.
- Bass tone: `"t"` (triangle) — warm low end.
- Percussion tone: `"n"` (noise) — kick/snare pattern.
- Each `sounds[N].set()` string length must be the same across all three channels.

**Step 3: Rewrite `_define_track_hillside()`**

Same approach using hillside analysis output (slots 19, 20, 21).

**Step 4: Rewrite `_define_track_pipeworks()`**

Same approach using pipeworks analysis output (slots 22, 23, 24). This track should feel heavier/darker — prefer square wave `"s"` for the melody.

**Step 5: Rewrite `_define_track_skybridge()`**

Same approach using skybridge analysis output (slots 25, 26, 27). Most intense track — use faster speed and denser notes.

**Step 6: Run the smoke test**

```bash
uv run pytest tests/ -k test_init_audio -v
```

Expected: PASS. If it fails, check that all `sounds[N].set()` arguments are valid strings with matching lengths.

**Step 7: Run full test suite**

```bash
uv run pytest tests/ -q
```

Expected: all tests pass.

**Step 8: Commit**

```bash
git add speednik/audio.py
git commit -m "feat: rewrite stage music tracks transcribed from reference MP3s"
```

---

## Final verification

After all five tasks are complete:

```bash
uv run pytest tests/ -v
```

Expected: all tests pass including:
- `TestWallSensorAngleGate` (3 tests)
- `TestTwoPassQuadrantResolve` (1 test)
- `test_init_audio_does_not_raise` (1 test)
- All pre-existing terrain, physics, and integration tests

Then rebuild the web export to test in browser:

```bash
rm -f speednik.pyxapp speednik.html
uv run pyxel package . web_entry.py
uv run pyxel app2html speednik.pyxapp
```

Verify in browser:
1. Music plays on the title screen
2. Player can enter the loop in Stage 1
3. No stutter when running across slope transitions

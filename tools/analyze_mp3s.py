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
    tempo = float(np.atleast_1d(tempo)[0])

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

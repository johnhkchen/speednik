"""Audio module for Speednik — SFX definitions, music compositions, playback API.

Defines all 16 sound effects (sounds[0..15]) and 7 music tracks (musics[0..6])
using Pyxel's native 4-channel chiptune engine. Provides a simple public API for
game modules to trigger sounds and music without touching Pyxel audio internals.

Four stage tracks (title, hillside, pipeworks, skybridge) play professionally
composed MP3 files via afplay subprocess when available; remaining tracks use
chiptune playback.

Standalone test: `uv run python -m speednik.audio`
"""

import sys
import os

# Pyodide (web) has no subprocess or threading — detect early
_IS_WEB = sys.platform == "emscripten"

if not _IS_WEB:
    import atexit
    import subprocess
    import threading

import pyxel

# ---------------------------------------------------------------------------
# SFX constants (sounds[] slot indices)
# ---------------------------------------------------------------------------
SFX_RING = 0
SFX_JUMP = 1
SFX_SPINDASH_CHARGE = 2
SFX_SPINDASH_RELEASE = 3
SFX_ENEMY_DESTROY = 4
SFX_ENEMY_BOUNCE = 5
SFX_SPRING = 6
SFX_RING_LOSS = 7
SFX_HURT = 8
SFX_CHECKPOINT = 9
SFX_STAGE_CLEAR = 10
SFX_BOSS_HIT = 11
SFX_LIQUID_RISING = 12
SFX_MENU_SELECT = 13
SFX_MENU_CONFIRM = 14
SFX_1UP = 15

# ---------------------------------------------------------------------------
# Music constants (musics[] slot indices)
# ---------------------------------------------------------------------------
MUSIC_TITLE = 0
MUSIC_HILLSIDE = 1
MUSIC_PIPEWORKS = 2
MUSIC_SKYBRIDGE = 3
MUSIC_BOSS = 4
MUSIC_CLEAR = 5
MUSIC_GAMEOVER = 6

# ---------------------------------------------------------------------------
# Channel allocation
# ---------------------------------------------------------------------------
CH_MELODY = 0
CH_BASS = 1
CH_PERCUSSION = 2
CH_SFX = 3

# Jingle tracks — played without looping
_JINGLE_TRACKS = {MUSIC_CLEAR, MUSIC_GAMEOVER}

# ---------------------------------------------------------------------------
# MP3 playback mapping (afplay subprocess)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_MP3_TRACKS: dict[int, str] = {
    MUSIC_TITLE: os.path.join(_PROJECT_ROOT, "assets", "MAIN_MENU_Genesis_of_Glory.mp3"),
    MUSIC_HILLSIDE: os.path.join(_PROJECT_ROOT, "assets", "LV1_Pixel_Pursuit.mp3"),
    MUSIC_PIPEWORKS: os.path.join(_PROJECT_ROOT, "assets", "LV2_Chrome_Citadel.mp3"),
    MUSIC_SKYBRIDGE: os.path.join(_PROJECT_ROOT, "assets", "LV3_Genesis_Gauntlet.mp3"),
}

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_current_music: int | None = None
_sfx_ducking: bool = False
_afplay_proc: object | None = None
_loop_stop: object | None = None
_mp3_active: bool = False


# ===========================================================================
# SFX Definitions
# ===========================================================================

def _define_sfx() -> None:
    """Define all 16 sound effects in sounds[0..15]."""

    # 0: Ring collect — bright ascending arpeggio, ~4 notes
    pyxel.sounds[0].set(
        "c3e3g3c4",
        "pppp",
        "7654",
        "nnnn",
        4,
    )

    # 1: Jump — quick rising tone
    pyxel.sounds[1].set(
        "c3e3g3b3",
        "ssss",
        "6543",
        "ssss",
        3,
    )

    # 2: Spindash charge — ascending buzz, retriggered each press
    pyxel.sounds[2].set(
        "c2c2d2d2e2e2f2f2",
        "ssssssss",
        "76666666",
        "nnnnnnnn",
        2,
    )

    # 3: Spindash release — sharp burst
    pyxel.sounds[3].set(
        "g3c4e4g4",
        "nnnn",
        "7531",
        "nnff",
        2,
    )

    # 4: Enemy destroy — pop + descending sparkle
    pyxel.sounds[4].set(
        "c4g3e3c3g2e2",
        "nppppp",
        "765432",
        "nfffff",
        4,
    )

    # 5: Enemy bounce — higher-pitched jump variant
    pyxel.sounds[5].set(
        "e3g3b3e4",
        "ssss",
        "6543",
        "ssss",
        3,
    )

    # 6: Spring — sine wave pitch bend (boing)
    pyxel.sounds[6].set(
        "c2g2c3g3c4g3c3",
        "ttttttt",
        "7776543",
        "sssssss",
        4,
    )

    # 7: Ring loss — scatter sound, descending
    pyxel.sounds[7].set(
        "e4c4g3e3c3g2e2c2",
        "pppppppp",
        "76655443",
        "nnnnffff",
        3,
    )

    # 8: Hurt / death — harsh descending tone
    pyxel.sounds[8].set(
        "g3f3e3d3c3b2a2g2f2e2d2c2",
        "ssssssssssss",
        "776655443322",
        "nnnnnnffffff",
        5,
    )

    # 9: Checkpoint — two-tone chime
    pyxel.sounds[9].set(
        "e4r g4r",
        "tttt",
        "7007",
        "nnnn",
        8,
    )

    # 10: Stage clear — ascending fanfare (longer)
    pyxel.sounds[10].set(
        "c3r e3r g3r c4r e4r g4",
        "pppppppppp",
        "6677776677",
        "nnnnnnnnnn",
        10,
    )

    # 11: Boss hit — metallic impact
    pyxel.sounds[11].set(
        "c2g2c2",
        "nnn",
        "730",
        "nff",
        2,
    )

    # 12: Liquid rising — low rumble loop
    pyxel.sounds[12].set(
        "c1d1e1d1c1d1e1d1",
        "tttttttt",
        "55555555",
        "vvvvvvvv",
        12,
    )

    # 13: Menu select — click
    pyxel.sounds[13].set(
        "c4",
        "n",
        "5",
        "f",
        2,
    )

    # 14: Menu confirm — chime
    pyxel.sounds[14].set(
        "e4g4",
        "tt",
        "66",
        "nf",
        6,
    )

    # 15: 1-up — classic jingle, ascending phrase
    pyxel.sounds[15].set(
        "c3e3g3c4e4g4c4",
        "ppppppp",
        "5667776",
        "nnnnnnn",
        7,
    )


# ===========================================================================
# Music Definitions
# ===========================================================================

def _define_track_title() -> None:
    # Title — 92 BPM, D# major — triumphant opening.
    # speed=10 → 4 steps/beat. Notes repeated for sustain. 32 steps = 2 bars.
    # Melody arc: root → 4th → 5th → octave → down → rest → variation → resolve
    pyxel.sounds[16].set(
        "d#3 d#3 d#3 r  g#3 g#3 a#3 r  d#4 d#4 r   r "
        "c4  a#3 g#3 r  d#3 d#3 g3  r  g#3 g#3 r   g3 "
        "f3  f3  r   r  d#3 d#3 r   r ",
        "p", "6", "n", 10)
    # Bass: whole-note chord roots (4 steps each) — I V VII IV I VI IV V
    pyxel.sounds[17].set(
        "g#2 g#2 g#2 g#2  d#3 d#3 d#3 d#3  c3  c3  c3  c3 "
        "a#2 a#2 a#2 a#2  g#2 g#2 g#2 g#2  c3  c3  c3  c3 "
        "a#2 a#2 a#2 a#2  d#2 d#2 d#2 d#2 ",
        "t", "4", "n", 10)
    # Perc: kick on beats 1&3, snare on beats 2&4 (4 steps = 1 beat)
    pyxel.sounds[18].set(
        "c3 r  r  r  f3 r  r  r  c3 r  r  r  f3 r  r  r "
        "c3 r  r  r  f3 r  r  r  c3 r  r  r  f3 r  r  r ",
        "n", "7", "n", 10)
    pyxel.musics[MUSIC_TITLE].set([16], [17], [18])


def _define_track_hillside() -> None:
    # Hillside — 99 BPM, C# major — bright, bouncy. speed=9, 32 steps.
    # Melody rises through the scale, peaks at c4, resolves back to c#3.
    pyxel.sounds[19].set(
        "c#3 c#3 r   r   d#3 r   f#3 r   g#3 g#3 r   r "
        "f#3 d#3 c#3 r   c#3 r   g#3 r   a#3 a#3 r   r "
        "c4  r   a#3 r   g#3 f#3 d#3 r  ",
        "p", "6", "n", 9)
    # Bass: I V IV I  VI III IV V
    pyxel.sounds[20].set(
        "c#2 c#2 c#2 c#2  g#2 g#2 g#2 g#2  f#2 f#2 f#2 f#2 "
        "c#2 c#2 c#2 c#2  a#2 a#2 a#2 a#2  f2  f2  f2  f2 "
        "f#2 f#2 f#2 f#2  g#2 g#2 g#2 g#2 ",
        "t", "4", "n", 9)
    # Perc: kick on 1&3, snare on 2&4
    pyxel.sounds[21].set(
        "c3 r  r  r  f3 r  r  r  c3 r  r  r  f3 r  r  r "
        "c3 r  r  r  f3 r  r  r  c3 r  r  r  f3 r  r  r ",
        "n", "7", "n", 9)
    pyxel.musics[MUSIC_HILLSIDE].set([19], [20], [21])


def _define_track_pipeworks() -> None:
    # Pipeworks — 103 BPM, F minor — dark, industrial. speed=9, square lead.
    # Sparse melody with punchy rests; heavier kick pattern for industrial feel.
    pyxel.sounds[22].set(
        "f3 r  f3 r   r   r  g#3 r  a#3 a#3 r   r "
        "g#3 r  f3 r   d#3 d#3 r   r  c3  r  f3  r "
        "r   r  d#3 r  a#3 r  f3  r  ",
        "s", "6", "n", 9)
    # Bass: deep, repeating root drone for grinding industrial feel
    pyxel.sounds[23].set(
        "f2  f2  f2  f2   f2  f2  f2  f2   d#2 d#2 d#2 d#2 "
        "d#2 d#2 d#2 d#2  c3  c3  c3  c3   c3  c3  c3  c3 "
        "a#2 a#2 a#2 a#2  f2  f2  f2  f2  ",
        "t", "5", "n", 9)
    # Perc: kick-kick-snare for heavier industrial pattern
    pyxel.sounds[24].set(
        "c3 c3 r  r  f3 r  r  r  c3 c3 r  r  f3 r  r  r "
        "c3 c3 r  r  f3 r  r  r  c3 c3 r  r  f3 r  r  r ",
        "n", "7", "n", 9)
    pyxel.musics[MUSIC_PIPEWORKS].set([22], [23], [24])


def _define_track_skybridge() -> None:
    # Skybridge — 161 BPM, D# major — fast, soaring. speed=6, 32 steps.
    # 8th-note driven melody with clear arc; driving two-beat bass.
    pyxel.sounds[25].set(
        "d#3 r  f3  r  g#3 r  a#3 r  g#3 r  f3  r  d#3 r  f3  r "
        "g3  r  a#3 r  c4  r  a#3 r  g#3 r  f3  r  d#3 r  r   r  ",
        "p", "6", "n", 6)
    # Bass: half-note roots (2 steps each) for forward push
    pyxel.sounds[26].set(
        "d#2 d#2  g#2 g#2  a#2 a#2  f2  f2  d#2 d#2  g2  g2  g#2 g#2  a#2 a#2 "
        "d#2 d#2  g#2 g#2  a#2 a#2  f2  f2  c3  c3   c3  c3  g#2 g#2  d#2 d#2 ",
        "t", "4", "n", 6)
    # Perc: kick on 1&3, snare on 2&4 (4 steps/beat at speed=6)
    pyxel.sounds[27].set(
        "c3 r  r  r  f3 r  r  r  c3 r  r  r  f3 r  r  r "
        "c3 r  r  r  f3 r  r  r  c3 r  r  r  f3 r  r  r ",
        "n", "7", "n", 6)
    pyxel.musics[MUSIC_SKYBRIDGE].set([25], [26], [27])


def _define_track_boss() -> None:
    """Track 4: Boss theme — original. Tense, A minor, ~160 BPM."""

    # Melody (slot 28): Aggressive, tense lead
    pyxel.sounds[28].set(
        "a3a3c4c4 e4e4a3a3 b3b3d4d4 e4e4b3b3 "
        "a3c4e4a4 g4e4c4a3 b3d4f4b4 a4f4d4b3 "
        "a3a3c4c4 e4e4a3a3 b3b3d4d4 e4e4b3b3 "
        "a3c4e4a4 g4e4c4a3 a3a3a3a3 a3r r r ",
        "s",
        "7",
        "nnnn nnnn nnnn nnnn nnnn nnnn nnnn nnnn "
        "nnnn nnnn nnnn nnnn nnnn nnnn nnnf nnnn",
        10,
    )

    # Bass (slot 29): Driving, ominous bass
    pyxel.sounds[29].set(
        "a1e2a1e2 a1e2a1e2 e1b1e1b1 e1b1e1b1 "
        "a1e2a1e2 a1e2a1e2 e1b1e1b1 e1b1e1b1 "
        "a1e2a1e2 a1e2a1e2 e1b1e1b1 e1b1e1b1 "
        "a1e2a1e2 a1e2a1e2 a1e2a1e2 a1e2a1e2",
        "t",
        "6",
        "n",
        10,
    )

    # Percussion (slot 30): Heavy, relentless beat
    pyxel.sounds[30].set(
        "c1c1c2c1 c1c1c2c1 c1c1c2c1 c1c1c2c1 "
        "c1c1c2c1 c1c1c2c1 c1c1c2c1 c1c1c2c1 "
        "c1c1c2c1 c1c1c2c1 c1c1c2c1 c1c1c2c1 "
        "c1c1c2c1 c1c1c2c1 c1c1c2c1 c1c1c2c1",
        "n",
        "7060 7060 7060 7060 7060 7060 7060 7060 "
        "7060 7060 7060 7060 7060 7060 7060 7060",
        "f",
        10,
    )

    pyxel.musics[MUSIC_BOSS].set([28], [29], [30])


def _define_track_clear() -> None:
    """Track 5: Stage clear jingle — ascending fanfare, no loop."""

    # Melody (slot 31): Short ascending celebration
    pyxel.sounds[31].set(
        "c3e3g3r c4e4g4r c4c4c4c4 c4r r r ",
        "pppppppp pppppppp",
        "66776677 66776677",
        "nnnnnnnn nnnnvvff",
        12,
    )

    # Bass (slot 32): Harmonic support
    pyxel.sounds[32].set(
        "c3g3c3g3 c3g3c3g3 c3c3c3c3 c3r r r ",
        "tttttttt tttttttt",
        "55555555 55555555",
        "nnnnnnnn nnnnnnff",
        12,
    )

    # Percussion (slot 33): Celebratory hits
    pyxel.sounds[33].set(
        "c2r c2r c2r c2r c2r c2r c2c2c2c2",
        "n",
        "6060 6060 6060 6677",
        "f",
        12,
    )

    pyxel.musics[MUSIC_CLEAR].set([31], [32], [33])


def _define_track_gameover() -> None:
    """Track 6: Game over — short somber phrase, no loop."""

    # Melody (slot 34): Descending somber melody
    pyxel.sounds[34].set(
        "e3d3c3b2 a2g2f2e2 d2c2b1a1 a1r r r ",
        "ssssssss ssssssss",
        "66665555 44433322",
        "nnnnnnnn nnnnnnff",
        20,
    )

    # Bass (slot 35): Low sustained notes
    pyxel.sounds[35].set(
        "a1a1a1a1 g1g1g1g1 f1f1f1f1 a1r r r ",
        "tttttttt tttttttt",
        "55554444 33332222",
        "nnnnnnnn nnnnnnff",
        20,
    )

    # Percussion (slot 36): Sparse — just soft taps
    pyxel.sounds[36].set(
        "c1r r r  c1r r r  c1r r r  r r r r ",
        "n",
        "4000 4000 4000 0000",
        "f",
        20,
    )

    pyxel.musics[MUSIC_GAMEOVER].set([34], [35], [36])


def _define_music() -> None:
    """Define all 7 music tracks: sound sequences and musics[] entries."""
    _define_track_title()
    _define_track_hillside()
    _define_track_pipeworks()
    _define_track_skybridge()
    _define_track_boss()
    _define_track_clear()
    _define_track_gameover()


# ===========================================================================
# Internal helpers
# ===========================================================================

def _get_percussion_for_track(track_id: int) -> int | None:
    """Return the percussion sound slot for a given music track, or None."""
    mapping = {
        MUSIC_TITLE: 18,
        MUSIC_HILLSIDE: 21,
        MUSIC_PIPEWORKS: 24,
        MUSIC_SKYBRIDGE: 27,
        MUSIC_BOSS: 30,
        MUSIC_CLEAR: 33,
        MUSIC_GAMEOVER: 36,
    }
    return mapping.get(track_id)


def _stop_afplay() -> None:
    """Kill any active afplay subprocess and stop the loop thread."""
    global _afplay_proc, _loop_stop, _mp3_active

    if _IS_WEB:
        _mp3_active = False
        return

    if _loop_stop is not None:
        _loop_stop.set()
    if _afplay_proc is not None:
        _afplay_proc.terminate()
        _afplay_proc.wait()
        _afplay_proc = None
    _loop_stop = None
    _mp3_active = False


def _afplay_loop(path: str, stop_event: "threading.Event") -> None:
    """Loop function for daemon thread — restarts afplay until stopped."""
    global _afplay_proc

    while not stop_event.is_set():
        proc = subprocess.Popen(["afplay", path])
        _afplay_proc = proc
        proc.wait()
        if stop_event.is_set():
            break


# ===========================================================================
# Public API
# ===========================================================================

def init_audio() -> None:
    """Initialize all sound effects and music tracks.

    Must be called after pyxel.init() and before any playback.
    """
    _define_sfx()
    _define_music()
    if not _IS_WEB:
        atexit.register(_stop_afplay)


def play_sfx(sfx_id: int) -> None:
    """Play a sound effect on channel 3 with percussion ducking.

    Args:
        sfx_id: Sound slot index (0–15).
    """
    global _sfx_ducking

    pyxel.play(CH_SFX, sfx_id)
    # Duck percussion channel while SFX plays (skip when MP3 is active —
    # pyxel percussion channel isn't used in that case)
    if _current_music is not None and not _mp3_active:
        pyxel.stop(CH_PERCUSSION)
        _sfx_ducking = True


def play_music(track_id: int) -> None:
    """Start a music track.

    MP3-mapped tracks (title, hillside, pipeworks, skybridge) play via afplay
    subprocess. Remaining tracks use pyxel chiptune engine.
    Looping tracks restart automatically. Jingle tracks (5–6) play once.

    Args:
        track_id: Music slot index (0–6).
    """
    global _current_music, _sfx_ducking, _afplay_proc, _loop_stop, _mp3_active

    _stop_afplay()

    mp3_path = _MP3_TRACKS.get(track_id)
    if not _IS_WEB and mp3_path is not None and os.path.isfile(mp3_path):
        loop = track_id not in _JINGLE_TRACKS
        if loop:
            stop_event = threading.Event()
            _loop_stop = stop_event
            t = threading.Thread(
                target=_afplay_loop, args=(mp3_path, stop_event), daemon=True
            )
            t.start()
        else:
            _afplay_proc = subprocess.Popen(["afplay", mp3_path])
        _mp3_active = True
    else:
        loop = track_id not in _JINGLE_TRACKS
        pyxel.playm(track_id, loop=loop)
        _mp3_active = False

    _current_music = track_id
    _sfx_ducking = False


def stop_music() -> None:
    """Stop all music playback — kills afplay subprocess and pyxel channels."""
    global _current_music, _sfx_ducking, _mp3_active

    _stop_afplay()
    pyxel.stop(CH_MELODY)
    pyxel.stop(CH_BASS)
    pyxel.stop(CH_PERCUSSION)
    _current_music = None
    _sfx_ducking = False
    _mp3_active = False


def update_audio() -> None:
    """Per-frame audio update. Resumes percussion after SFX ducking ends.

    Call this once per frame from the game loop.
    """
    global _sfx_ducking

    if _sfx_ducking and not _mp3_active and pyxel.play_pos(CH_SFX) is None:
        # SFX finished — resume percussion
        if _current_music is not None:
            perc_slot = _get_percussion_for_track(_current_music)
            if perc_slot is not None:
                pyxel.play(CH_PERCUSSION, perc_slot, loop=True, resume=True)
        _sfx_ducking = False


# ===========================================================================
# Standalone test mode
# ===========================================================================

if __name__ == "__main__":

    _SFX_NAMES = [
        "Ring", "Jump", "SpinCharge", "SpinRelease",
        "EnemyPop", "EnemyBounce", "Spring", "RingLoss",
        "Hurt", "Checkpoint", "StageClear", "BossHit",
        "LiquidRise", "MenuSelect", "MenuConfirm", "1-Up",
    ]

    _MUSIC_NAMES = [
        "Title", "Hillside", "PipeWorks", "Skybridge",
        "Boss", "Clear", "GameOver",
    ]

    # SFX key bindings: A-P maps to SFX 0-15
    _SFX_KEYS = [
        pyxel.KEY_A, pyxel.KEY_B, pyxel.KEY_C, pyxel.KEY_D,
        pyxel.KEY_E, pyxel.KEY_F, pyxel.KEY_G, pyxel.KEY_H,
        pyxel.KEY_I, pyxel.KEY_J, pyxel.KEY_K, pyxel.KEY_L,
        pyxel.KEY_M, pyxel.KEY_N, pyxel.KEY_O, pyxel.KEY_P,
    ]

    class AudioTest:
        def __init__(self) -> None:
            pyxel.init(256, 224, title="Speednik Audio Test", fps=60)
            init_audio()
            self._last_sfx: str = ""
            self._playing_music: str = ""
            pyxel.run(self.update, self.draw)

        def update(self) -> None:
            if pyxel.btnp(pyxel.KEY_Q):
                pyxel.quit()

            # Number keys 0-6: music tracks
            for i in range(7):
                if pyxel.btnp(pyxel.KEY_0 + i):
                    play_music(i)
                    self._playing_music = _MUSIC_NAMES[i]

            # Space: stop music
            if pyxel.btnp(pyxel.KEY_SPACE):
                stop_music()
                self._playing_music = ""

            # Letter keys A-P: SFX 0-15
            for i, key in enumerate(_SFX_KEYS):
                if pyxel.btnp(key):
                    play_sfx(i)
                    self._last_sfx = _SFX_NAMES[i]

            update_audio()

        def draw(self) -> None:
            pyxel.cls(1)
            pyxel.text(8, 4, "SPEEDNIK AUDIO TEST", 7)
            pyxel.text(8, 16, "Q: Quit  SPACE: Stop music", 13)

            # Music section
            pyxel.text(8, 32, "MUSIC (0-6):", 10)
            for i, name in enumerate(_MUSIC_NAMES):
                y = 42 + i * 8
                col = 11 if self._playing_music == name else 7
                pyxel.text(16, y, f"{i}: {name}", col)

            # SFX section
            pyxel.text(8, 102, "SFX (A-P):", 10)
            for i in range(8):
                y = 112 + i * 8
                letter = chr(ord("A") + i)
                pyxel.text(16, y, f"{letter}: {_SFX_NAMES[i]}", 7)
            for i in range(8, 16):
                y = 112 + (i - 8) * 8
                letter = chr(ord("A") + i)
                pyxel.text(128, y, f"{letter}: {_SFX_NAMES[i]}", 7)

            # Status
            pyxel.text(8, 185, f"Music: {self._playing_music or 'None'}", 11)
            pyxel.text(8, 195, f"Last SFX: {self._last_sfx or 'None'}", 14)

    AudioTest()

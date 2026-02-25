"""Audio module for Speednik — SFX definitions, music compositions, playback API.

Defines all 16 sound effects (sounds[0..15]) and 7 music tracks (musics[0..6])
using Pyxel's native 4-channel chiptune engine. Provides a simple public API for
game modules to trigger sounds and music without touching Pyxel audio internals.

Standalone test: `uv run python -m speednik.audio`
"""

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
# Module state
# ---------------------------------------------------------------------------
_current_music: int | None = None
_sfx_ducking: bool = False


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
    """Track 0: Title/Menu — Genesis of Glory feel. Heroic, C major, ~120 BPM."""

    # Melody (slot 16): Heroic lead, pulse tone
    pyxel.sounds[16].set(
        "e3e3g3g3 c4c4b3a3 g3g3e3e3 g3a3b3c4 "
        "e3e3g3g3 c4c4b3a3 g3g3a3a3 g3r r r "
        "c4c4e4e4 d4d4c4b3 c4c4g3g3 e3g3a3b3 "
        "c4c4e4e4 d4d4c4b3 c4c4r r  c4r r r ",
        "p",
        "6",
        "nnnv nnnn nnnv nnnn nnnv nnnn nnnf nnnn "
        "nnnv nnnn nnnv nnnn nnnv nnnn nnnf nnnn",
        20,
    )

    # Bass (slot 17): Root-fifth pattern, triangle tone
    pyxel.sounds[17].set(
        "c2g2c2g2 c2g2c2g2 c2g2c2g2 c2g2c2g2 "
        "c2g2c2g2 c2g2c2g2 c2g2c2g2 c2g2c2g2 "
        "a1e2a1e2 g1d2g1d2 a1e2a1e2 e1b1e1b1 "
        "a1e2a1e2 g1d2g1d2 c2g2c2g2 c2g2c2g2",
        "t",
        "5",
        "n",
        20,
    )

    # Percussion (slot 18): Kick-snare pattern, noise tone
    pyxel.sounds[18].set(
        "c1r f2r c1r f2r c1r f2r c1r f2r "
        "c1r f2r c1r f2r c1r f2r c1r f2r "
        "c1r f2r c1r f2r c1r f2r c1r f2r "
        "c1r f2r c1r f2r c1r f2r c1c1f2f2",
        "n",
        "6060 6060 6060 6060 6060 6060 6060 6060 "
        "6060 6060 6060 6060 6060 6060 6060 6677",
        "f",
        20,
    )

    pyxel.musics[MUSIC_TITLE].set([16], [17], [18])


def _define_track_hillside() -> None:
    """Track 1: Hillside Rush — Pixel Pursuit feel. Energetic, G major, ~140 BPM."""

    # Melody (slot 19): Bright, energetic lead
    pyxel.sounds[19].set(
        "g3a3b3d4 g4g4f4e4 d4d4b3a3 g3a3b3d4 "
        "e4e4d4c4 b3b3a3g3 a3b3c4d4 e4d4c4b3 "
        "g3a3b3d4 g4g4f4e4 d4d4b3a3 g3a3b3d4 "
        "e4e4d4c4 b3b3a3g3 a3a3g3g3 g3r r r ",
        "p",
        "6",
        "nnns nnnn nnns nnnn nnns nnnn nnns nnnn "
        "nnns nnnn nnns nnnn nnns nnnn nnnf nnnn",
        15,
    )

    # Bass (slot 20): Driving eighth-note bassline
    pyxel.sounds[20].set(
        "g1d2g1d2 g1d2g1d2 e1b1e1b1 e1b1e1b1 "
        "c2g2c2g2 c2g2c2g2 d2a2d2a2 d2a2d2a2 "
        "g1d2g1d2 g1d2g1d2 e1b1e1b1 e1b1e1b1 "
        "c2g2c2g2 c2g2c2g2 d2a2d2a2 g1d2g1d2",
        "t",
        "5",
        "n",
        15,
    )

    # Percussion (slot 21): Upbeat pattern
    pyxel.sounds[21].set(
        "c1r c2r c1r c2r c1r c2r c1r c2r "
        "c1r c2r c1r c2r c1r c2r c1r c2r "
        "c1r c2r c1r c2r c1r c2r c1r c2r "
        "c1r c2r c1r c2r c1r c2r c1c1c2c2",
        "n",
        "6050 6050 6050 6050 6050 6050 6050 6050 "
        "6050 6050 6050 6050 6050 6050 6050 6677",
        "f",
        15,
    )

    pyxel.musics[MUSIC_HILLSIDE].set([19], [20], [21])


def _define_track_pipeworks() -> None:
    """Track 2: Pipe Works — Chrome Citadel feel. Industrial, D minor, ~130 BPM."""

    # Melody (slot 22): Dark industrial melody, square tone with vibrato
    pyxel.sounds[22].set(
        "d3r f3r a3r d4r c4c4b-3a3 g3f3e3d3 "
        "d3r f3r a3r d4r c4c4b-3a3 g3a3b-3a3 "
        "f3r a3r c4r f4r e4e4d4c4 b-3a3g3f3 "
        "d3r f3r a3r d4r c4c4b-3a3 d3r r r ",
        "s",
        "6",
        "nvnv nvnv nnnn nnnn nvnv nvnv nnnn nnnn "
        "nvnv nvnv nnnn nnnn nvnv nvnv nnnn nnnn",
        18,
    )

    # Bass (slot 23): Heavy syncopated bass
    pyxel.sounds[23].set(
        "d1a1d1a1 d1a1d1a1 d1a1d1a1 d1a1d1a1 "
        "d1a1d1a1 d1a1d1a1 d1a1d1a1 d1a1d1a1 "
        "f1c2f1c2 f1c2f1c2 f1c2f1c2 f1c2f1c2 "
        "d1a1d1a1 d1a1d1a1 d1a1d1a1 d1a1d1a1",
        "t",
        "5",
        "n",
        18,
    )

    # Percussion (slot 24): Mechanical rhythm
    pyxel.sounds[24].set(
        "c1c2c1c2 c1c2c1c2 c1c2c1c2 c1c2c1c2 "
        "c1c2c1c2 c1c2c1c2 c1c2c1c2 c1c2c1c2 "
        "c1c2c1c2 c1c2c1c2 c1c2c1c2 c1c2c1c2 "
        "c1c2c1c2 c1c2c1c2 c1c2c1c2 c1c2c1c2",
        "n",
        "6050 6050 6050 6050 6050 6050 6050 6050 "
        "6050 6050 6050 6050 6050 6050 6050 6050",
        "f",
        18,
    )

    pyxel.musics[MUSIC_PIPEWORKS].set([22], [23], [24])


def _define_track_skybridge() -> None:
    """Track 3: Skybridge Gauntlet — Genesis Gauntlet feel. Intense, E minor, ~150 BPM."""

    # Melody (slot 25): Urgent, intense lead
    pyxel.sounds[25].set(
        "e3g3b3e4 d4d4c4b3 e3g3b3e4 d4c4b3a3 "
        "g3b3d4g4 f4f4e4d4 e3g3b3e4 d4e4f4e4 "
        "e3g3b3e4 d4d4c4b3 e3g3b3e4 d4c4b3a3 "
        "g3b3d4g4 f4f4e4d4 e4e4d4d4 e4r r r ",
        "s",
        "6",
        "nnnn nnnn nnnn nnnn nnnn nnnn nnnn nnnn "
        "nnnn nnnn nnnn nnnn nnnn nnnn nnnf nnnn",
        12,
    )

    # Bass (slot 26): Aggressive bassline
    pyxel.sounds[26].set(
        "e1b1e1b1 e1b1e1b1 e1b1e1b1 e1b1e1b1 "
        "g1d2g1d2 g1d2g1d2 e1b1e1b1 e1b1e1b1 "
        "e1b1e1b1 e1b1e1b1 e1b1e1b1 e1b1e1b1 "
        "g1d2g1d2 g1d2g1d2 e1b1e1b1 e1b1e1b1",
        "t",
        "6",
        "n",
        12,
    )

    # Percussion (slot 27): Rapid driving beat
    pyxel.sounds[27].set(
        "c1c2c1c2 c1c2c1c2 c1c2c1c2 c1c2c1c2 "
        "c1c2c1c2 c1c2c1c2 c1c2c1c2 c1c2c1c2 "
        "c1c2c1c2 c1c2c1c2 c1c2c1c2 c1c2c1c2 "
        "c1c2c1c2 c1c2c1c2 c1c2c1c2 c1c2c1c2",
        "n",
        "7060 7060 7060 7060 7060 7060 7060 7060 "
        "7060 7060 7060 7060 7060 7060 7060 7060",
        "f",
        12,
    )

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


# ===========================================================================
# Public API
# ===========================================================================

def init_audio() -> None:
    """Initialize all sound effects and music tracks.

    Must be called after pyxel.init() and before any playback.
    """
    _define_sfx()
    _define_music()


def play_sfx(sfx_id: int) -> None:
    """Play a sound effect on channel 3 with percussion ducking.

    Args:
        sfx_id: Sound slot index (0–15).
    """
    global _sfx_ducking

    pyxel.play(CH_SFX, sfx_id)
    # Duck percussion channel while SFX plays
    if _current_music is not None:
        pyxel.stop(CH_PERCUSSION)
        _sfx_ducking = True


def play_music(track_id: int) -> None:
    """Start a music track.

    Looping tracks (0–4) loop continuously. Jingle tracks (5–6) play once.

    Args:
        track_id: Music slot index (0–6).
    """
    global _current_music, _sfx_ducking

    loop = track_id not in _JINGLE_TRACKS
    pyxel.playm(track_id, loop=loop)
    _current_music = track_id
    _sfx_ducking = False


def stop_music() -> None:
    """Stop all music channels (0–2)."""
    global _current_music, _sfx_ducking

    pyxel.stop(CH_MELODY)
    pyxel.stop(CH_BASS)
    pyxel.stop(CH_PERCUSSION)
    _current_music = None
    _sfx_ducking = False


def update_audio() -> None:
    """Per-frame audio update. Resumes percussion after SFX ducking ends.

    Call this once per frame from the game loop.
    """
    global _sfx_ducking

    if _sfx_ducking and pyxel.play_pos(CH_SFX) is None:
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

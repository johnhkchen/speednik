"""Tests for speednik.audio — chiptune MML definitions."""
from unittest.mock import MagicMock, patch
import importlib
import sys


def test_init_audio_does_not_raise():
    """init_audio() must define all slots without raising even with mock pyxel."""
    # Ensure pyxel is mocked in sys.modules before import/reload
    mock_pyxel_module = MagicMock()
    sys.modules["pyxel"] = mock_pyxel_module

    import speednik.audio
    importlib.reload(speednik.audio)

    # Now patch the already-imported pyxel reference inside the module
    sounds = {i: MagicMock() for i in range(40)}
    musics = {i: MagicMock() for i in range(8)}
    speednik.audio.pyxel.sounds = sounds
    speednik.audio.pyxel.musics = musics

    from speednik.audio import init_audio
    init_audio()

    from speednik.audio import MUSIC_TITLE, MUSIC_HILLSIDE, MUSIC_PIPEWORKS, MUSIC_SKYBRIDGE
    musics[MUSIC_TITLE].set.assert_called_once()
    musics[MUSIC_HILLSIDE].set.assert_called_once()
    musics[MUSIC_PIPEWORKS].set.assert_called_once()
    musics[MUSIC_SKYBRIDGE].set.assert_called_once()

"""Tests for speednik.audio — chiptune MML definitions and MP3 playback."""
from unittest.mock import MagicMock, patch, call
import importlib
import sys


def _setup_audio_module():
    """Reload speednik.audio with mocked pyxel and return the module."""
    mock_pyxel_module = MagicMock()
    sys.modules["pyxel"] = mock_pyxel_module

    import speednik.audio
    importlib.reload(speednik.audio)

    sounds = {i: MagicMock() for i in range(40)}
    musics = {i: MagicMock() for i in range(8)}
    speednik.audio.pyxel.sounds = sounds
    speednik.audio.pyxel.musics = musics

    return speednik.audio


def test_init_audio_does_not_raise():
    """init_audio() must define all slots without raising even with mock pyxel."""
    mod = _setup_audio_module()

    mod.init_audio()

    musics = mod.pyxel.musics
    assert musics[mod.MUSIC_TITLE].set.called
    assert musics[mod.MUSIC_HILLSIDE].set.called
    assert musics[mod.MUSIC_PIPEWORKS].set.called
    assert musics[mod.MUSIC_SKYBRIDGE].set.called


def test_play_music_mp3_spawns_subprocess():
    """play_music() with an MP3-mapped track spawns afplay subprocess."""
    mod = _setup_audio_module()
    mod.init_audio()

    mock_proc = MagicMock()
    mock_proc.wait = MagicMock()

    with patch.object(mod.os.path, "isfile", return_value=True), \
         patch.object(mod.subprocess, "Popen", return_value=mock_proc) as mock_popen, \
         patch.object(mod.threading, "Thread") as mock_thread_cls:

        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        mod.play_music(mod.MUSIC_TITLE)

        # Looping track should use a thread
        mock_thread_cls.assert_called_once()
        mock_thread.start.assert_called_once()
        assert mod._mp3_active is True
        assert mod._current_music == mod.MUSIC_TITLE


def test_play_music_chiptune_uses_pyxel():
    """play_music() with a non-MP3 track uses pyxel.playm()."""
    mod = _setup_audio_module()
    mod.init_audio()

    with patch.object(mod.subprocess, "Popen") as mock_popen:
        mod.play_music(mod.MUSIC_BOSS)

        mock_popen.assert_not_called()
        mod.pyxel.playm.assert_called_with(mod.MUSIC_BOSS, loop=True)
        assert mod._mp3_active is False
        assert mod._current_music == mod.MUSIC_BOSS


def test_stop_music_terminates_afplay():
    """stop_music() terminates afplay subprocess."""
    mod = _setup_audio_module()
    mod.init_audio()

    mock_proc = MagicMock()
    mod._afplay_proc = mock_proc
    mod._loop_stop = MagicMock()
    mod._mp3_active = True
    mod._current_music = mod.MUSIC_TITLE

    mod.stop_music()

    mock_proc.terminate.assert_called_once()
    mock_proc.wait.assert_called_once()
    assert mod._afplay_proc is None
    assert mod._mp3_active is False
    assert mod._current_music is None


def test_play_sfx_skips_ducking_when_mp3_active():
    """play_sfx() does not duck percussion when MP3 track is active."""
    mod = _setup_audio_module()
    mod.init_audio()

    mod._current_music = mod.MUSIC_TITLE
    mod._mp3_active = True
    mod.pyxel.stop.reset_mock()

    mod.play_sfx(mod.SFX_RING)

    # pyxel.play should be called for the SFX
    mod.pyxel.play.assert_called_with(mod.CH_SFX, mod.SFX_RING)
    # percussion should NOT be stopped
    mod.pyxel.stop.assert_not_called()
    assert mod._sfx_ducking is False


def test_play_sfx_ducks_when_chiptune_active():
    """play_sfx() ducks percussion when chiptune track is active."""
    mod = _setup_audio_module()
    mod.init_audio()

    mod._current_music = mod.MUSIC_BOSS
    mod._mp3_active = False
    mod.pyxel.stop.reset_mock()

    mod.play_sfx(mod.SFX_RING)

    mod.pyxel.play.assert_called_with(mod.CH_SFX, mod.SFX_RING)
    mod.pyxel.stop.assert_called_with(mod.CH_PERCUSSION)
    assert mod._sfx_ducking is True


def test_update_audio_skips_resume_when_mp3_active():
    """update_audio() does not resume percussion when MP3 is active."""
    mod = _setup_audio_module()
    mod.init_audio()

    mod._sfx_ducking = True
    mod._mp3_active = True
    mod._current_music = mod.MUSIC_TITLE
    mod.pyxel.play_pos.return_value = None
    mod.pyxel.play.reset_mock()

    mod.update_audio()

    # Percussion should NOT be resumed via pyxel.play on CH_PERCUSSION
    for c in mod.pyxel.play.call_args_list:
        assert c[0][0] != mod.CH_PERCUSSION
    # _sfx_ducking should remain True (not cleared, since the mp3 guard skips)
    assert mod._sfx_ducking is True

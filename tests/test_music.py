from unittest.mock import patch
from handlers.music import PlayPauseHandler, NextHandler, PrevHandler, VolumeHandler
from tests.conftest import make_handler_input


def test_playpause_can_handle():
    hi = make_handler_input("AMAZON.PauseIntent")
    assert PlayPauseHandler().can_handle(hi) is True


def test_playpause_sends_key():
    hi = make_handler_input("AMAZON.PauseIntent")
    with patch("handlers.music.send_key") as mock_key:
        PlayPauseHandler().handle(hi)
        mock_key.assert_called_once_with(0xB3)


def test_next_sends_key():
    hi = make_handler_input("AMAZON.NextIntent")
    with patch("handlers.music.send_key") as mock_key:
        NextHandler().handle(hi)
        mock_key.assert_called_once_with(0xB0)


def test_prev_sends_key():
    hi = make_handler_input("AMAZON.PreviousIntent")
    with patch("handlers.music.send_key") as mock_key:
        PrevHandler().handle(hi)
        mock_key.assert_called_once_with(0xB1)


def test_volume_up():
    hi = make_handler_input("VolumeIntent", slots={"direction": "subir"})
    with patch("handlers.music.send_key") as mock_key:
        VolumeHandler().handle(hi)
        mock_key.assert_called_once_with(0xAF)


def test_volume_down():
    hi = make_handler_input("VolumeIntent", slots={"direction": "bajar"})
    with patch("handlers.music.send_key") as mock_key:
        VolumeHandler().handle(hi)
        mock_key.assert_called_once_with(0xAE)
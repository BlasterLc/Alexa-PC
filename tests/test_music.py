from unittest.mock import patch
from handlers.music import (
    PlayPauseHandler, NextHandler, PrevHandler,
    VolumeUpHandler, VolumeDownHandler, PlaySongHandler, PlayArtistHandler,
)
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


def test_volume_up_sends_key_five_times():
    hi = make_handler_input("VolumeUpIntent")
    with patch("handlers.music.send_key") as mock_key:
        VolumeUpHandler().handle(hi)
        mock_key.assert_called_once_with(0xAF, times=5)


def test_volume_down_sends_key_five_times():
    hi = make_handler_input("VolumeDownIntent")
    with patch("handlers.music.send_key") as mock_key:
        VolumeDownHandler().handle(hi)
        mock_key.assert_called_once_with(0xAE, times=5)


def test_playsong_can_handle():
    hi = make_handler_input("PlaySongIntent")
    assert PlaySongHandler().can_handle(hi) is True


def test_playsong_searches_and_navigates():
    hi = make_handler_input("PlaySongIntent", slots={"songName": "Bohemian Rhapsody"})
    fake_results = [{"videoId": "abc123", "title": "Bohemian Rhapsody"}]
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.open_or_navigate") as mock_nav:
        MockYT.return_value.search.return_value = fake_results
        PlaySongHandler().handle(hi)
        MockYT.return_value.search.assert_called_once_with(
            "Bohemian Rhapsody", filter="songs", limit=1
        )
        assert "abc123" in mock_nav.call_args[0][0]


def test_playsong_no_results():
    hi = make_handler_input("PlaySongIntent", slots={"songName": "xyzzy"})
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.open_or_navigate"):
        MockYT.return_value.search.return_value = []
        PlaySongHandler().handle(hi)
        hi.response_builder.speak.assert_called_with("No encontré esa canción.")


def test_playartist_searches_and_navigates():
    hi = make_handler_input("PlayArtistIntent", slots={"artistName": "Radiohead"})
    fake_results = [{"browseId": "UC123", "artist": "Radiohead"}]
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.open_or_navigate") as mock_nav:
        MockYT.return_value.search.return_value = fake_results
        PlayArtistHandler().handle(hi)
        MockYT.return_value.search.assert_called_once_with(
            "Radiohead", filter="artists", limit=1
        )
        assert "UC123" in mock_nav.call_args[0][0]


# --- Cerrar sesión en comandos que dejan música sonando fuerte ---
# (evita falsos VolumeUpIntent por el micrófono abierto captando la música)

def test_next_ends_session():
    hi = make_handler_input("AMAZON.NextIntent")
    with patch("handlers.music.send_key"):
        NextHandler().handle(hi)
    hi.response_builder.set_should_end_session.assert_called_with(True)
    hi.response_builder.ask.assert_not_called()


def test_prev_ends_session():
    hi = make_handler_input("AMAZON.PreviousIntent")
    with patch("handlers.music.send_key"):
        PrevHandler().handle(hi)
    hi.response_builder.set_should_end_session.assert_called_with(True)
    hi.response_builder.ask.assert_not_called()


def test_volume_up_ends_session():
    hi = make_handler_input("VolumeUpIntent")
    with patch("handlers.music.send_key"):
        VolumeUpHandler().handle(hi)
    hi.response_builder.set_should_end_session.assert_called_with(True)
    hi.response_builder.ask.assert_not_called()


def test_volume_down_ends_session():
    hi = make_handler_input("VolumeDownIntent")
    with patch("handlers.music.send_key"):
        VolumeDownHandler().handle(hi)
    hi.response_builder.set_should_end_session.assert_called_with(True)
    hi.response_builder.ask.assert_not_called()


def test_playsong_success_ends_session():
    hi = make_handler_input("PlaySongIntent", slots={"songName": "Bohemian Rhapsody"})
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.open_or_navigate"):
        MockYT.return_value.search.return_value = [{"videoId": "abc123", "title": "X"}]
        PlaySongHandler().handle(hi)
    hi.response_builder.set_should_end_session.assert_called_with(True)
    hi.response_builder.ask.assert_not_called()


def test_playartist_success_ends_session():
    hi = make_handler_input("PlayArtistIntent", slots={"artistName": "Radiohead"})
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.open_or_navigate"):
        MockYT.return_value.search.return_value = [{"browseId": "UC123", "artist": "X"}]
        PlayArtistHandler().handle(hi)
    hi.response_builder.set_should_end_session.assert_called_with(True)
    hi.response_builder.ask.assert_not_called()


def test_resume_ends_session():
    hi = make_handler_input("AMAZON.ResumeIntent")
    with patch("handlers.music.send_key"):
        PlayPauseHandler().handle(hi)
    hi.response_builder.set_should_end_session.assert_called_with(True)
    hi.response_builder.ask.assert_not_called()


def test_pause_keeps_session_open():
    # Pause no deja música sonando -> el micrófono abierto es seguro, mantenemos el encadenamiento
    hi = make_handler_input("AMAZON.PauseIntent")
    with patch("handlers.music.send_key"):
        PlayPauseHandler().handle(hi)
    hi.response_builder.ask.assert_called_with("¿Algo más?")

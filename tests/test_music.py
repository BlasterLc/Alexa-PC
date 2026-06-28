from unittest.mock import patch
from handlers.music import PlayPauseHandler, NextHandler, PrevHandler, VolumeHandler, PlaySongHandler, PlayArtistHandler
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


def test_playsong_can_handle():
    hi = make_handler_input("PlaySongIntent")
    assert PlaySongHandler().can_handle(hi) is True


def test_playsong_searches_and_opens():
    hi = make_handler_input("PlaySongIntent", slots={"songName": "Bohemian Rhapsody"})
    fake_results = [{"videoId": "abc123", "title": "Bohemian Rhapsody"}]
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.subprocess.run") as mock_run:
        MockYT.return_value.search.return_value = fake_results
        PlaySongHandler().handle(hi)
        MockYT.return_value.search.assert_called_once_with(
            "Bohemian Rhapsody", filter="songs", limit=1
        )
        url_arg = " ".join(mock_run.call_args[0][0])
        assert "abc123" in url_arg


def test_playsong_no_results():
    hi = make_handler_input("PlaySongIntent", slots={"songName": "xyzzy"})
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.subprocess.run"):
        MockYT.return_value.search.return_value = []
        PlaySongHandler().handle(hi)
        hi.response_builder.speak.assert_called_with("No encontré esa canción.")


def test_playartist_searches_and_opens():
    hi = make_handler_input("PlayArtistIntent", slots={"artistName": "Radiohead"})
    fake_results = [{"browseId": "UC123", "artist": "Radiohead"}]
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.subprocess.run") as mock_run:
        MockYT.return_value.search.return_value = fake_results
        PlayArtistHandler().handle(hi)
        MockYT.return_value.search.assert_called_once_with(
            "Radiohead", filter="artists", limit=1
        )
        url_arg = " ".join(mock_run.call_args[0][0])
        assert "UC123" in url_arg


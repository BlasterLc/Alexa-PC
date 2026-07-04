from unittest.mock import patch
from handlers.urls import UrlHandler
from tests.conftest import make_handler_input


def test_url_can_handle():
    hi = make_handler_input("OpenUrlIntent")
    assert UrlHandler().can_handle(hi) is True


def test_open_github():
    hi = make_handler_input("OpenUrlIntent", slots={"siteName": "github"})
    with patch("handlers.urls.subprocess.run") as mock_run:
        UrlHandler().handle(hi)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "start" in cmd
        assert "https://github.com" in cmd
        hi.response_builder.speak.assert_called_with("Abriendo github.")


def test_github_split_by_asr():
    # es-MX ASR often transcribes "github" as two words: "git hub"
    hi = make_handler_input("OpenUrlIntent", slots={"siteName": "git hub"})
    with patch("handlers.urls.subprocess.run") as mock_run:
        UrlHandler().handle(hi)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "https://github.com" in cmd


def test_open_youtube_music_still_matches():
    hi = make_handler_input("OpenUrlIntent", slots={"siteName": "youtube music"})
    with patch("handlers.urls.subprocess.run") as mock_run:
        UrlHandler().handle(hi)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "https://music.youtube.com" in cmd


def test_unknown_site_returns_error():
    hi = make_handler_input("OpenUrlIntent", slots={"siteName": "sitio inexistente"})
    with patch("handlers.urls.subprocess.run") as mock_run:
        UrlHandler().handle(hi)
        mock_run.assert_not_called()
        hi.response_builder.speak.assert_called_with("No conozco ese sitio.")

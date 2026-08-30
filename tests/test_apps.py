from unittest.mock import patch
from handlers.apps import AppHandler
from tests.conftest import make_handler_input


def test_app_can_handle():
    hi = make_handler_input("AppIntent")
    assert AppHandler().can_handle(hi) is True


def test_open_chrome():
    hi = make_handler_input("AppIntent", slots={"appName": "Chrome", "appAction": "abrir"})
    with patch("handlers.apps.subprocess.run") as mock_run:
        AppHandler().handle(hi)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "start" in cmd
        assert "chrome.exe" in cmd
        assert mock_run.call_args.kwargs["cwd"] == "/mnt/c"


def test_open_accepts_accented_name():
    # es-MX transcribe "opera" como "ópera"
    hi = make_handler_input("AppIntent", slots={"appName": "ópera", "appAction": "abrir"})
    with patch("handlers.apps.subprocess.run") as mock_run:
        AppHandler().handle(hi)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "opera.exe" in cmd
        hi.response_builder.speak.assert_called_with("Abriendo opera.")


def test_open_app_with_launcher_args():
    # Discord: Update.exe --processStart Discord.exe
    hi = make_handler_input("AppIntent", slots={"appName": "discord", "appAction": "abrir"})
    with patch("handlers.apps.subprocess.run") as mock_run:
        AppHandler().handle(hi)
        argv = mock_run.call_args[0][0]
        assert "--processStart" in argv
        assert argv[-1] == "Discord.exe"


def test_close_discord():
    hi = make_handler_input("AppIntent", slots={"appName": "Discord", "appAction": "cerrar"})
    with patch("handlers.apps.subprocess.run") as mock_run:
        AppHandler().handle(hi)
        argv = mock_run.call_args[0][0]
        assert "Stop-Process" in argv
        assert "Discord" in argv  # nombre de proceso, no la ruta del Update.exe


def test_unknown_app_returns_error():
    hi = make_handler_input("AppIntent", slots={"appName": "UnknownApp", "appAction": "abrir"})
    with patch("handlers.apps.subprocess.run"):
        AppHandler().handle(hi)
        hi.response_builder.speak.assert_called_with("No conozco esa aplicación.")

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
        assert "Start-Process" in cmd
        assert "chrome.exe" in cmd


def test_close_discord():
    hi = make_handler_input("AppIntent", slots={"appName": "Discord", "appAction": "cerrar"})
    with patch("handlers.apps.subprocess.run") as mock_run:
        AppHandler().handle(hi)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "Stop-Process" in cmd


def test_unknown_app_returns_error():
    hi = make_handler_input("AppIntent", slots={"appName": "UnknownApp", "appAction": "abrir"})
    with patch("handlers.apps.subprocess.run"):
        AppHandler().handle(hi)
        hi.response_builder.speak.assert_called_with("No conozco esa aplicación.")
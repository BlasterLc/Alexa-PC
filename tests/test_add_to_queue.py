from unittest.mock import patch, MagicMock
from handlers.chrome_cdp import add_to_queue


def test_add_to_queue_returns_false_when_no_cdp():
    """Si CDP no está disponible, devuelve False."""
    with patch("handlers.chrome_cdp._get_tabs", return_value=None):
        result = add_to_queue("dQw4w9WgXcQ")
    assert result is False


def test_add_to_queue_returns_false_when_no_yt_tab():
    """Si Chrome está abierto pero no hay tab de YT Music, devuelve False."""
    tabs = [{"url": "https://google.com", "type": "page", "webSocketDebuggerUrl": "ws://..."}]
    with patch("handlers.chrome_cdp._get_tabs", return_value=tabs):
        result = add_to_queue("dQw4w9WgXcQ")
    assert result is False

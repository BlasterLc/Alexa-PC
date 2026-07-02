from unittest.mock import patch, MagicMock
from handlers.chrome_cdp import add_to_queue
from handlers.music import AddToQueueHandler
from tests.conftest import make_handler_input


_YT_TAB = [{
    "url": "https://music.youtube.com/",
    "type": "page",
    "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/ABC",
}]


def test_add_to_queue_returns_false_when_no_cdp():
    """Si CDP no está disponible, devuelve False."""
    with patch("handlers.chrome_cdp._get_tabs", return_value=None):
        result = add_to_queue("dQw4w9WgXcQ", "rick astley")
    assert result is False


def test_add_to_queue_returns_false_when_no_yt_tab():
    """Si Chrome está abierto pero no hay tab de YT Music, devuelve False."""
    tabs = [{"url": "https://google.com", "type": "page", "webSocketDebuggerUrl": "ws://..."}]
    with patch("handlers.chrome_cdp._get_tabs", return_value=tabs):
        result = add_to_queue("dQw4w9WgXcQ", "rick astley")
    assert result is False


def _cdp_side_effect(mapping):
    """Build a _cdp_eval side_effect that dispatches on a marker in the JS expression."""
    def se(ws, expr, timeout=20):
        for marker, value in mapping.items():
            if marker in expr:
                return value
        return None
    return se


def _run_add_to_queue(mapping):
    with patch("handlers.chrome_cdp._get_tabs", return_value=_YT_TAB), \
         patch("handlers.chrome_cdp.websocket.create_connection"), \
         patch("handlers.chrome_cdp.time.sleep"), \
         patch("handlers.chrome_cdp._cdp_eval", side_effect=_cdp_side_effect(mapping)):
        return add_to_queue("dQw4w9WgXcQ", "rick astley")


def test_add_to_queue_returns_false_when_search_box_missing():
    """Si la caja de búsqueda no está disponible, aborta."""
    result = _run_add_to_queue({"/*SEARCH*/": False})
    assert result is False


def test_add_to_queue_returns_false_when_row_not_found():
    """Si ninguna fila-canción aparece para la búsqueda, devuelve False (no clickea a ciegas)."""
    result = _run_add_to_queue({
        "/*SEARCH*/": True,
        "/*READY*/": True,
        "/*LOCATE*/": {"found": False},
    })
    assert result is False


def test_add_to_queue_returns_false_when_menu_never_opens():
    """Si el menú no abre (popup nunca aparece), aborta sin clickear a ciegas."""
    result = _run_add_to_queue({
        "/*SEARCH*/": True,
        "/*READY*/": True,
        "/*LOCATE*/": {"found": True, "title": "X"},
        "/*OPENMENU*/": {"ok": True},
        "/*HASITEMS*/": False,
        "/*CLOSE*/": True,
    })
    assert result is False


def test_add_to_queue_returns_true_when_item_clicked():
    """Si encuentra la fila-canción, abre el menú y clickea 'Agregar a la fila', devuelve True."""
    result = _run_add_to_queue({
        "/*SEARCH*/": True,
        "/*READY*/": True,
        "/*LOCATE*/": {"found": True, "title": "X"},
        "/*OPENMENU*/": {"ok": True},
        "/*HASITEMS*/": True,
        "/*CLICKQ*/": {"ok": True},
    })
    assert result is True


# --- AddToQueueHandler ---

def test_add_to_queue_handler_can_handle():
    hi = make_handler_input("AddToQueueIntent")
    assert AddToQueueHandler().can_handle(hi) is True


def test_add_to_queue_handler_song_not_found():
    hi = make_handler_input("AddToQueueIntent", slots={"songName": "cancion inexistente xyz"})
    with patch("handlers.music.YTMusic") as MockYT:
        MockYT.return_value.search.return_value = []
        AddToQueueHandler().handle(hi)
    hi.response_builder.speak.assert_called_with("No encontré esa canción.")


def test_add_to_queue_handler_no_yt_tab():
    hi = make_handler_input("AddToQueueIntent", slots={"songName": "bohemian rhapsody"})
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.add_to_queue", return_value=False):
        MockYT.return_value.search.return_value = [
            {"videoId": "abc123", "title": "Bohemian Rhapsody"}
        ]
        AddToQueueHandler().handle(hi)
    hi.response_builder.speak.assert_called_with(
        "No hay ninguna canción sonando, no pude agregar a la cola."
    )


def test_add_to_queue_handler_success():
    hi = make_handler_input("AddToQueueIntent", slots={"songName": "bohemian rhapsody"})
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.add_to_queue", return_value=True) as mock_queue:
        MockYT.return_value.search.return_value = [
            {"videoId": "abc123", "title": "Bohemian Rhapsody"}
        ]
        AddToQueueHandler().handle(hi)
    mock_queue.assert_called_once_with("abc123", "bohemian rhapsody")
    hi.response_builder.speak.assert_called_with("Bohemian Rhapsody agregada a la cola.")
    # cierra la sesión: música sonando fuerte -> mic abierto dispara falsos VolumeUpIntent
    hi.response_builder.set_should_end_session.assert_called_with(True)
    hi.response_builder.ask.assert_not_called()

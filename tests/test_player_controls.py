from unittest.mock import patch
from handlers.chrome_cdp import player_action


_YT_TAB = [{
    "url": "https://music.youtube.com/",
    "type": "page",
    "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/page/ABC",
}]


def _cdp_recorder(mapping, seen):
    """_cdp_eval side_effect that dispatches on a marker in the JS and records hits."""
    def se(ws, expr, timeout=20):
        for marker, value in mapping.items():
            if marker in expr:
                seen.append(marker)
                return value
        return None
    return se


def _run_player_action(action, mapping):
    seen = []
    with patch("handlers.chrome_cdp._get_tabs", return_value=_YT_TAB), \
         patch("handlers.chrome_cdp.websocket.create_connection"), \
         patch("handlers.chrome_cdp._cdp_eval", side_effect=_cdp_recorder(mapping, seen)):
        result = player_action(action)
    return result, seen


def test_player_action_no_cdp():
    """Sin CDP disponible -> ok False."""
    with patch("handlers.chrome_cdp._get_tabs", return_value=None):
        assert player_action("shuffle") == {"ok": False, "state": None}


def test_player_action_no_yt_tab():
    """Chrome abierto pero sin tab de YT Music -> ok False."""
    tabs = [{"url": "https://google.com", "type": "page", "webSocketDebuggerUrl": "ws://x"}]
    with patch("handlers.chrome_cdp._get_tabs", return_value=tabs):
        assert player_action("shuffle") == {"ok": False, "state": None}


def test_player_action_unknown_action():
    """Acción desconocida -> ok False (no clickea nada)."""
    result, _ = _run_player_action("nope", {})
    assert result == {"ok": False, "state": None}


def test_shuffle_ok():
    result, seen = _run_player_action("shuffle", {"/*SHUFFLE*/": {"ok": True}})
    assert result == {"ok": True, "state": None}
    assert "/*SHUFFLE*/" in seen


def test_shuffle_button_missing():
    result, _ = _run_player_action("shuffle", {"/*SHUFFLE*/": {"ok": False}})
    assert result == {"ok": False, "state": None}

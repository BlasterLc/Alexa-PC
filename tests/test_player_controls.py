from unittest.mock import patch
from handlers.chrome_cdp import player_action
from handlers.music import LikeHandler, DislikeHandler
from tests.conftest import make_handler_input


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


def test_like_when_indifferent_clicks():
    """Estado INDIFFERENT -> clickea like, estado final LIKE."""
    result, seen = _run_player_action("like", {
        "/*LIKESTATE*/": "INDIFFERENT",
        "/*LIKECLICK*/": {"ok": True},
    })
    assert result == {"ok": True, "state": "LIKE"}
    assert "/*LIKECLICK*/" in seen


def test_like_when_already_liked_is_idempotent():
    """Ya en LIKE -> NO clickea (idempotente), estado sigue LIKE."""
    result, seen = _run_player_action("like", {"/*LIKESTATE*/": "LIKE"})
    assert result == {"ok": True, "state": "LIKE"}
    assert "/*LIKECLICK*/" not in seen


def test_dislike_when_indifferent_clicks():
    result, seen = _run_player_action("dislike", {
        "/*LIKESTATE*/": "INDIFFERENT",
        "/*LIKECLICK*/": {"ok": True},
    })
    assert result == {"ok": True, "state": "DISLIKE"}
    assert "/*LIKECLICK*/" in seen


def test_dislike_when_already_disliked_is_idempotent():
    result, seen = _run_player_action("dislike", {"/*LIKESTATE*/": "DISLIKE"})
    assert result == {"ok": True, "state": "DISLIKE"}
    assert "/*LIKECLICK*/" not in seen


def test_like_state_unreadable():
    """Si no se puede leer el like renderer (None) -> ok False."""
    result, _ = _run_player_action("like", {"/*LIKESTATE*/": None})
    assert result == {"ok": False, "state": None}


def test_like_click_fails_returns_false_with_stale_state():
    """Estado no-target pero el click no se confirma -> ok False, state = estado previo."""
    result, seen = _run_player_action("like", {
        "/*LIKESTATE*/": "INDIFFERENT",
        "/*LIKECLICK*/": {"ok": False},
    })
    assert result == {"ok": False, "state": "INDIFFERENT"}
    assert "/*LIKECLICK*/" in seen


def test_repeat_reads_state():
    result, seen = _run_player_action("repeat", {"/*REPEAT*/": {"ok": True, "state": "ALL"}})
    assert result == {"ok": True, "state": "ALL"}
    assert "/*REPEAT*/" in seen


def test_repeat_state_unknown():
    """Clickea pero no pudo leer el modo -> state None, ok True."""
    result, _ = _run_player_action("repeat", {"/*REPEAT*/": {"ok": True, "state": None}})
    assert result == {"ok": True, "state": None}


def test_repeat_button_missing():
    result, _ = _run_player_action("repeat", {"/*REPEAT*/": {"ok": False}})
    assert result == {"ok": False, "state": None}


def test_like_handler_can_handle():
    assert LikeHandler().can_handle(make_handler_input("LikeIntent")) is True


def test_like_handler_success():
    hi = make_handler_input("LikeIntent")
    with patch("handlers.music.player_action", return_value={"ok": True, "state": "LIKE"}):
        LikeHandler().handle(hi)
    hi.response_builder.speak.assert_called_with("Me gusta.")
    hi.response_builder.set_should_end_session.assert_called_with(True)
    hi.response_builder.ask.assert_not_called()


def test_like_handler_no_music():
    hi = make_handler_input("LikeIntent")
    with patch("handlers.music.player_action", return_value={"ok": False, "state": None}):
        LikeHandler().handle(hi)
    hi.response_builder.speak.assert_called_with("No hay ninguna canción sonando.")
    hi.response_builder.ask.assert_called_with("¿Algo más?")


def test_dislike_handler_success():
    hi = make_handler_input("DislikeIntent")
    with patch("handlers.music.player_action", return_value={"ok": True, "state": "DISLIKE"}):
        DislikeHandler().handle(hi)
    hi.response_builder.speak.assert_called_with("No me gusta.")
    hi.response_builder.set_should_end_session.assert_called_with(True)

from unittest.mock import patch
from handlers.system import SystemHandler
from tests.conftest import make_handler_input


def test_system_can_handle():
    hi = make_handler_input("SystemIntent")
    assert SystemHandler().can_handle(hi) is True


def test_lock_executes_without_confirmation():
    hi = make_handler_input("SystemIntent", slots={"action": "bloquear"})
    with patch("handlers.system.subprocess.run") as mock_run:
        SystemHandler().handle(hi)
        cmd = " ".join(mock_run.call_args[0][0])
        assert "LockWorkStation" in cmd


def test_shutdown_asks_for_confirmation():
    hi = make_handler_input("SystemIntent", slots={"action": "apagar"})
    with patch("handlers.system.subprocess.run"):
        SystemHandler().handle(hi)
        hi.response_builder.ask.assert_called()


def test_restart_asks_for_confirmation():
    hi = make_handler_input("SystemIntent", slots={"action": "reiniciar"})
    with patch("handlers.system.subprocess.run"):
        SystemHandler().handle(hi)
        hi.response_builder.ask.assert_called()


def test_shutdown_via_spoken_synonym():
    # Alexa manda lo hablado ("apaga"), no el canónico: se mapea a "apagar".
    hi = make_handler_input("SystemIntent", slots={"action": "apaga"})
    with patch("handlers.system.subprocess.run"):
        SystemHandler().handle(hi)
        hi.response_builder.ask.assert_called()


def test_unknown_action_is_rejected():
    hi = make_handler_input("SystemIntent", slots={"action": "explota"})
    with patch("handlers.system.subprocess.run") as mock_run:
        SystemHandler().handle(hi)
        mock_run.assert_not_called()
        hi.response_builder.speak.assert_called_with("No entendí esa acción.")

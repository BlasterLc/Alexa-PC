from unittest.mock import patch

from ask_sdk_model import IntentConfirmationStatus

from handlers.system import SystemHandler, StrayYesNoHandler
from tests.conftest import make_handler_input


def test_system_can_handle():
    hi = make_handler_input("SystemIntent")
    assert SystemHandler().can_handle(hi) is True


def test_unconfirmed_delegates_to_alexa():
    hi = make_handler_input(
        "SystemIntent", slots={"action": "apaga"},
        confirmation_status=IntentConfirmationStatus.NONE,
    )
    with patch("handlers.system.subprocess.run") as mock_run:
        SystemHandler().handle(hi)
        mock_run.assert_not_called()
        hi.response_builder.add_directive.assert_called()


def test_denied_cancels_without_running():
    hi = make_handler_input(
        "SystemIntent", slots={"action": "apaga"},
        confirmation_status=IntentConfirmationStatus.DENIED,
    )
    with patch("handlers.system.subprocess.run") as mock_run:
        SystemHandler().handle(hi)
        mock_run.assert_not_called()
        hi.response_builder.speak.assert_called_with("Cancelado.")


def test_confirmed_shutdown_runs():
    hi = make_handler_input(
        "SystemIntent", slots={"action": "apaga"},
        confirmation_status=IntentConfirmationStatus.CONFIRMED,
    )
    with patch("handlers.system.subprocess.run") as mock_run:
        SystemHandler().handle(hi)
        assert "Stop-Computer" in " ".join(mock_run.call_args[0][0])
        hi.response_builder.speak.assert_called_with("Apagando la PC.")


def test_confirmed_lock_runs():
    hi = make_handler_input(
        "SystemIntent", slots={"action": "bloquear"},
        confirmation_status=IntentConfirmationStatus.CONFIRMED,
    )
    with patch("handlers.system.subprocess.run") as mock_run:
        SystemHandler().handle(hi)
        assert "LockWorkStation" in " ".join(mock_run.call_args[0][0])


def test_confirmed_unknown_action_rejected():
    hi = make_handler_input(
        "SystemIntent", slots={"action": "explota"},
        confirmation_status=IntentConfirmationStatus.CONFIRMED,
    )
    with patch("handlers.system.subprocess.run") as mock_run:
        SystemHandler().handle(hi)
        mock_run.assert_not_called()
        hi.response_builder.speak.assert_called_with("No entendí esa acción.")


def test_stray_yes_no_is_answered():
    hi = make_handler_input("AMAZON.NoIntent")
    assert StrayYesNoHandler().can_handle(hi) is True
    StrayYesNoHandler().handle(hi)
    hi.response_builder.speak.assert_called_with("No hay nada que confirmar.")

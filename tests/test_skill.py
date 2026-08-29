from skill import CatchAllExceptionHandler
from tests.conftest import make_handler_input


def test_catch_all_handles_any_exception():
    hi = make_handler_input("CualquierIntent")
    handler = CatchAllExceptionHandler()
    assert handler.can_handle(hi, RuntimeError("boom")) is True
    handler.handle(hi, RuntimeError("boom"))
    hi.response_builder.speak.assert_called_with("Perdón, algo salió mal. Intenta de nuevo.")
    hi.response_builder.set_should_end_session.assert_called_with(True)

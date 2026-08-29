import subprocess

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import IntentConfirmationStatus, Response
from ask_sdk_model.dialog import DelegateDirective

from handlers.base import POWERSHELL_EXE

_PS_COMMANDS: dict[str, list[str]] = {
    "apagar": [POWERSHELL_EXE, "Stop-Computer", "-Force"],
    "reiniciar": [POWERSHELL_EXE, "Restart-Computer", "-Force"],
    "bloquear": [POWERSHELL_EXE, "-Command", "rundll32.exe user32.dll,LockWorkStation"],
}

_SYNONYMS: dict[str, str] = {
    "apaga": "apagar", "apagá": "apagar", "shutdown": "apagar",
    "reinicia": "reiniciar", "reiniciá": "reiniciar", "restart": "reiniciar",
    "bloquea": "bloquear", "bloqueá": "bloquear", "lock": "bloquear",
}

_DONE_MSG: dict[str, str] = {
    "apagar": "Apagando la PC.",
    "reiniciar": "Reiniciando la PC.",
    "bloquear": "Pantalla bloqueada.",
}


def _resolve_action(slot) -> str:
    """Valor canónico del slot `action`; si Alexa no lo resolvió, cae a lo
    hablado mapeando sinónimos a mano."""
    if slot is None:
        return ""
    try:
        resolutions = slot.resolutions.resolutions_per_authority
        if resolutions and resolutions[0].status.code.value == "ER_SUCCESS_MATCH":
            return resolutions[0].values[0].value.name
    except (AttributeError, IndexError):
        pass
    raw = (slot.value or "").lower()
    return _SYNONYMS.get(raw, raw)


class SystemHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("SystemIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        intent = handler_input.request_envelope.request.intent
        rb = handler_input.response_builder

        # La confirmación la maneja Alexa (Intent Confirmation en el modelo).
        if intent.confirmation_status == IntentConfirmationStatus.DENIED:
            return rb.speak("Cancelado.").set_should_end_session(True).response

        if intent.confirmation_status != IntentConfirmationStatus.CONFIRMED:
            # Sin delegación automática: pedirle a Alexa que corra el prompt.
            return rb.add_directive(DelegateDirective()).response

        action = _resolve_action((intent.slots or {}).get("action"))
        if action not in _PS_COMMANDS:
            return rb.speak("No entendí esa acción.").set_should_end_session(True).response

        subprocess.run(_PS_COMMANDS[action], check=True)
        return rb.speak(_DONE_MSG[action]).set_should_end_session(True).response


class StrayYesNoHandler(AbstractRequestHandler):
    """`AMAZON.YesIntent` / `AMAZON.NoIntent` sueltos, fuera del flujo de
    confirmación (que lo maneja Alexa). Responde limpio en vez de caer en el
    exception handler."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (
            ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input)
            or ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input)
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder
            .speak("No hay nada que confirmar.")
            .set_should_end_session(True)
            .response
        )

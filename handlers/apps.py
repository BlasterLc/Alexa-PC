import subprocess
import unicodedata

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from config import APPS
from handlers.base import CMD_EXE, POWERSHELL_EXE

_OPEN_SYNONYMS = {"abrir", "abrí", "abre", "lanzar", "lanzá"}
_CLOSE_SYNONYMS = {"cerrar", "cerrá", "cierra", "matar", "matá"}


def _normalize(text: str) -> str:
    """Minúsculas, sin tildes ni símbolos: 'ópera' -> 'opera', 'VS Code' -> 'vscode'.
    El ASR es-MX a veces mete tildes ('ópera') que rompían el match exacto."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c) and c.isalnum())


def _process_name(target: str | list[str]) -> str:
    exe = target[-1] if isinstance(target, list) else target
    return exe.replace("\\", "/").rsplit("/", 1)[-1].removesuffix(".exe")


class AppHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AppIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        slots = handler_input.request_envelope.request.intent.slots
        app_name = slots["appName"].value or ""
        app_action = (slots["appAction"].value or "").lower()

        target_key = _normalize(app_name)
        app_key = next((k for k in APPS if _normalize(k) == target_key), None)
        if not app_key:
            return (
                handler_input.response_builder
                .speak("No conozco esa aplicación.")
                .set_should_end_session(False)
                .response
            )

        # El valor puede ser un exe suelto o una lista [exe, arg, arg] (p. ej.
        # Discord se lanza con Update.exe --processStart Discord.exe).
        target = APPS[app_key]
        args = target if isinstance(target, list) else [target]

        if app_action in _CLOSE_SYNONYMS:
            subprocess.run(
                [POWERSHELL_EXE, "Stop-Process", "-Name", _process_name(target), "-Force"],
                cwd="/mnt/c", check=True,
            )
            speech = f"Cerrando {app_key}."
        else:
            subprocess.run([CMD_EXE, "/c", "start", "", *args], cwd="/mnt/c", check=True)
            speech = f"Abriendo {app_key}."

        return (
            handler_input.response_builder
            .speak(speech)
            .ask("¿Algo más?")
            .response
        )

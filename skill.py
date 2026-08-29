import logging

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler, AbstractExceptionHandler,
)
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from handlers.music import (
    PlayPauseHandler, NextHandler, PrevHandler,
    VolumeUpHandler, VolumeDownHandler, PlaySongHandler, PlayArtistHandler,
    AddToQueueHandler, LikeHandler, DislikeHandler, ShuffleHandler, RepeatHandler,
)
from handlers.system import SystemHandler, StrayYesNoHandler
from handlers.apps import AppHandler
from handlers.urls import UrlHandler

logger = logging.getLogger(__name__)


class LaunchHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder
            .speak("Mi PC lista. ¿Qué quieres hacer?")
            .ask("¿Qué quieres hacer?")
            .response
        )


class HelpHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder
            .speak(
                "Puedes decir: pausa, siguiente, anterior, sube el volumen, "
                "toca una canción, toca algo de un artista, agrega a la cola, "
                "me gusta, no me gusta, pon aleatorio, repite, "
                "abre o cierra una app, apaga la pc, reinicia, o bloquea la pantalla."
            )
            .ask("¿Qué quieres hacer?")
            .response
        )


class CancelStopHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (
            ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
            ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder
            .speak("Hasta luego.")
            .set_should_end_session(True)
            .response
        )


class FallbackHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder
            .speak("No entendí ese comando. Puedes decir pausa, siguiente, o abre una app.")
            .ask("¿Qué quieres hacer?")
            .response
        )


class SessionEndedHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Última red: cualquier intent sin handler o error en un handler responde
    hablado en vez de tirar un 500 ("hubo un problema con la skill")."""

    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.exception("Error no manejado: %s", exception)
        return (
            handler_input.response_builder
            .speak("Perdón, algo salió mal. Intenta de nuevo.")
            .set_should_end_session(True)
            .response
        )


sb = SkillBuilder()
sb.add_request_handler(LaunchHandler())
sb.add_request_handler(PlayPauseHandler())
sb.add_request_handler(NextHandler())
sb.add_request_handler(PrevHandler())
sb.add_request_handler(VolumeUpHandler())
sb.add_request_handler(VolumeDownHandler())
sb.add_request_handler(PlaySongHandler())
sb.add_request_handler(PlayArtistHandler())
sb.add_request_handler(AddToQueueHandler())
sb.add_request_handler(LikeHandler())
sb.add_request_handler(DislikeHandler())
sb.add_request_handler(ShuffleHandler())
sb.add_request_handler(RepeatHandler())
sb.add_request_handler(SystemHandler())
sb.add_request_handler(StrayYesNoHandler())
sb.add_request_handler(AppHandler())
sb.add_request_handler(UrlHandler())
sb.add_request_handler(HelpHandler())
sb.add_request_handler(CancelStopHandler())
sb.add_request_handler(FallbackHandler())
sb.add_request_handler(SessionEndedHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

skill = sb.create()

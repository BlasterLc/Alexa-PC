from pathlib import Path

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ytmusicapi import YTMusic

from handlers.base import send_key, VK_CODES
from handlers.chrome_cdp import open_or_navigate, add_to_queue

_OAUTH_PATH = Path(__file__).parent.parent / "browser.json"


class PlayPauseHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (
            ask_utils.is_intent_name("AMAZON.PauseIntent")(handler_input) or
            ask_utils.is_intent_name("AMAZON.ResumeIntent")(handler_input)
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["play_pause"])
        rb = handler_input.response_builder.speak("Listo.")
        # Resume deja música sonando fuerte -> cerramos sesión para que el mic
        # abierto no capte el audio y dispare falsos intents (ver VolumeUpIntent).
        if ask_utils.is_intent_name("AMAZON.ResumeIntent")(handler_input):
            return rb.set_should_end_session(True).response
        return rb.ask("¿Algo más?").response


class NextHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.NextIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["next"])
        return (
            handler_input.response_builder
            .speak("Siguiente.")
            .set_should_end_session(True)
            .response
        )


class PrevHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.PreviousIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["prev"])
        return (
            handler_input.response_builder
            .speak("Anterior.")
            .set_should_end_session(True)
            .response
        )


class VolumeUpHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("VolumeUpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["vol_up"], times=5)
        return (
            handler_input.response_builder
            .speak("Subiendo el volumen.")
            .set_should_end_session(True)
            .response
        )


class VolumeDownHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("VolumeDownIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["vol_down"], times=5)
        return (
            handler_input.response_builder
            .speak("Bajando el volumen.")
            .set_should_end_session(True)
            .response
        )


class PlaySongHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("PlaySongIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        song_name = handler_input.request_envelope.request.intent.slots["songName"].value
        yt = YTMusic(str(_OAUTH_PATH), language="es")
        results = yt.search(song_name, filter="songs", limit=1)
        if not results:
            return (
                handler_input.response_builder
                .speak("No encontré esa canción.")
                .set_should_end_session(False)
                .response
            )
        video_id = results[0]["videoId"]
        title = results[0]["title"]
        url = f"https://music.youtube.com/watch?v={video_id}"
        open_or_navigate(url)
        return (
            handler_input.response_builder
            .speak(f"Reproduciendo {title}.")
            .set_should_end_session(True)
            .response
        )


class PlayArtistHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("PlayArtistIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        artist_name = handler_input.request_envelope.request.intent.slots["artistName"].value
        yt = YTMusic(str(_OAUTH_PATH), language="es")
        results = yt.search(artist_name, filter="artists", limit=1)
        if not results:
            return (
                handler_input.response_builder
                .speak("No encontré ese artista.")
                .set_should_end_session(False)
                .response
            )
        browse_id = results[0]["browseId"]
        artist = results[0]["artist"]
        url = f"https://music.youtube.com/channel/{browse_id}"
        open_or_navigate(url)
        return (
            handler_input.response_builder
            .speak(f"Reproduciendo música de {artist}.")
            .set_should_end_session(True)
            .response
        )


class AddToQueueHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AddToQueueIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        song_name = handler_input.request_envelope.request.intent.slots["songName"].value
        yt = YTMusic(str(_OAUTH_PATH), language="es")
        results = yt.search(song_name, filter="songs", limit=1)
        if not results:
            return (
                handler_input.response_builder
                .speak("No encontré esa canción.")
                .set_should_end_session(False)
                .response
            )
        video_id = results[0]["videoId"]
        title = results[0]["title"]
        if not add_to_queue(video_id, song_name):
            return (
                handler_input.response_builder
                .speak("No hay ninguna canción sonando, no pude agregar a la cola.")
                .ask("¿Algo más?")
                .response
            )
        return (
            handler_input.response_builder
            .speak(f"{title} agregada a la cola.")
            .set_should_end_session(True)
            .response
        )
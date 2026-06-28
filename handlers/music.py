import subprocess
from pathlib import Path

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ytmusicapi import YTMusic

from handlers.base import send_key, VK_CODES

_OAUTH_PATH = Path(__file__).parent.parent / "browser.json"


class PlayPauseHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (
            ask_utils.is_intent_name("AMAZON.PauseIntent")(handler_input) or
            ask_utils.is_intent_name("AMAZON.ResumeIntent")(handler_input)
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["play_pause"])
        return (
            handler_input.response_builder
            .speak("Listo.")
            .set_should_end_session(False)
            .response
        )


class NextHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.NextIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["next"])
        return (
            handler_input.response_builder
            .speak("Siguiente.")
            .set_should_end_session(False)
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
            .set_should_end_session(False)
            .response
        )


class VolumeUpHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("VolumeUpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["vol_up"])
        return (
            handler_input.response_builder
            .speak("Subiendo el volumen.")
            .set_should_end_session(False)
            .response
        )


class VolumeDownHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("VolumeDownIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["vol_down"])
        return (
            handler_input.response_builder
            .speak("Bajando el volumen.")
            .set_should_end_session(False)
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
        subprocess.run(["cmd.exe", "/c", "start", "", "chrome.exe", f"--app={url}"], check=True)
        return (
            handler_input.response_builder
            .speak(f"Reproduciendo {title}.")
            .set_should_end_session(False)
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
        subprocess.run(["cmd.exe", "/c", "start", "", "chrome.exe", f"--app={url}"], check=True)
        return (
            handler_input.response_builder
            .speak(f"Reproduciendo música de {artist}.")
            .set_should_end_session(False)
            .response
        )
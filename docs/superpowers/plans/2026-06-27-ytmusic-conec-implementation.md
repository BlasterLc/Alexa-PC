# YtMusic-Conec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir un servidor FastAPI en WSL2 que recibe comandos de una Alexa Skill ("mi pc") y controla YT Music + sistema + apps via PowerShell.

**Architecture:** Echo Dot → Alexa Cloud → Cloudflare Tunnel → FastAPI (WSL2) → Handlers Python → PowerShell/ytmusicapi. Los handlers de media keys usan `keybd_event` via PowerShell; los de búsqueda usan `ytmusicapi`; los de sistema y apps usan comandos PowerShell directos.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, ask-sdk-core, ask-sdk-webservice-utils, ytmusicapi, python-dotenv, pytest

---

## Estructura de archivos

```
YtMusic-Conec/
├── main.py                   # FastAPI app + startup del tunnel
├── skill.py                  # SkillBuilder: ensambla todos los handlers
├── config.py                 # Variables de entorno + carga de apps.json
├── handlers/
│   ├── __init__.py
│   ├── base.py               # send_key() + utilidades compartidas
│   ├── music.py              # PlayPause, Next, Prev, Volume, PlaySong, PlayArtist
│   ├── system.py             # SystemIntent (apagar/reiniciar/bloquear)
│   └── apps.py               # AppIntent (abrir/cerrar apps)
├── apps.json                 # Mapa nombre → ejecutable
├── tests/
│   ├── conftest.py           # Helpers para crear HandlerInput mock
│   ├── test_base.py
│   ├── test_music.py
│   ├── test_system.py
│   └── test_apps.py
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Prerequisitos manuales (hacer antes de ejecutar el plan)

1. **Cuenta Alexa Developer Console:** crear skill en https://developer.amazon.com/alexa/console/ask con invocation name `mi pc`, locale `es-AR`.
2. **Cloudflare Tunnel:** instalar `cloudflared` y autenticarse: `cloudflared tunnel login`.
3. **ytmusicapi OAuth:** después del Task 5, ejecutar `ytmusicapi oauth` y guardar el `oauth.json` generado en la raíz del proyecto.

---

## Task 1: Project setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Crear requirements.txt**

```
fastapi>=0.110.0
uvicorn>=0.29.0
ask-sdk-core>=1.19.0
ask-sdk-webservice-utils>=1.19.0
ytmusicapi>=1.6.0
python-dotenv>=1.0.0
pytest>=8.0.0
httpx>=0.27.0
```

- [ ] **Step 2: Crear .env.example**

```
SKILL_ID=amzn1.ask.skill.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PORT=8000
```

- [ ] **Step 3: Crear .gitignore**

```
.env
oauth.json
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: Instalar dependencias**

```bash
pip install -r requirements.txt
```

Resultado esperado: instalación sin errores.

- [ ] **Step 5: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore
git commit -m "chore: project setup"
```

---

## Task 2: Configuración

**Files:**
- Create: `config.py`
- Create: `apps.json`
- Create: `.env` (desde .env.example — no se commitea)

- [ ] **Step 1: Escribir test de configuración**

`tests/test_config.py`:
```python
import os
import json
import pytest

def test_skill_id_loaded(monkeypatch):
    monkeypatch.setenv("SKILL_ID", "amzn1.ask.skill.test")
    monkeypatch.setenv("PORT", "8000")
    import importlib, config
    importlib.reload(config)
    assert config.SKILL_ID == "amzn1.ask.skill.test"
    assert config.PORT == 8000

def test_apps_json_loads():
    import config
    assert isinstance(config.APPS, dict)
    assert "Chrome" in config.APPS
```

- [ ] **Step 2: Verificar que el test falla**

```bash
pytest tests/test_config.py -v
```

Resultado esperado: `ModuleNotFoundError` o `ImportError`.

- [ ] **Step 3: Crear apps.json**

```json
{
  "Chrome": "chrome.exe",
  "Discord": "Discord.exe",
  "Spotify": "Spotify.exe",
  "VS Code": "Code.exe",
  "Notepad": "notepad.exe"
}
```

- [ ] **Step 4: Crear config.py**

```python
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SKILL_ID: str = os.environ["SKILL_ID"]
PORT: int = int(os.getenv("PORT", "8000"))

_apps_path = Path(__file__).parent / "apps.json"
APPS: dict[str, str] = json.loads(_apps_path.read_text())
```

- [ ] **Step 5: Copiar .env.example a .env y completar SKILL_ID**

```bash
cp .env.example .env
# Editar .env con el Skill ID real de Alexa Developer Console
```

- [ ] **Step 6: Correr tests**

```bash
pytest tests/test_config.py -v
```

Resultado esperado: PASS en ambos tests.

- [ ] **Step 7: Commit**

```bash
git add config.py apps.json tests/test_config.py
git commit -m "feat: configuration and apps registry"
```

---

## Task 3: Utilidad send_key + conftest

**Files:**
- Create: `handlers/__init__.py`
- Create: `handlers/base.py`
- Create: `tests/conftest.py`
- Create: `tests/test_base.py`

- [ ] **Step 1: Crear conftest.py con helper para HandlerInput mock**

`tests/conftest.py`:
```python
from unittest.mock import MagicMock
from ask_sdk_core.handler_input import HandlerInput


def make_handler_input(intent_name: str, slots: dict[str, str] | None = None) -> HandlerInput:
    hi = MagicMock(spec=HandlerInput)
    intent = MagicMock()
    intent.name = intent_name
    intent.slots = {}
    if slots:
        for name, value in slots.items():
            slot = MagicMock()
            slot.value = value
            intent.slots[name] = slot
    hi.request_envelope.request.intent = intent
    rb = MagicMock()
    rb.speak.return_value = rb
    rb.ask.return_value = rb
    rb.set_should_end_session.return_value = rb
    rb.response = MagicMock()
    hi.response_builder = rb
    return hi
```

- [ ] **Step 2: Escribir test de send_key**

`tests/test_base.py`:
```python
from unittest.mock import patch, call
from handlers.base import send_key, VK_CODES


def test_send_key_calls_powershell():
    with patch("handlers.base.subprocess.run") as mock_run:
        send_key(VK_CODES["play_pause"])
        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "powershell.exe" in cmd
        assert "0xB3" in " ".join(str(a) for a in cmd)


def test_send_key_raises_on_failure():
    import subprocess
    with patch("handlers.base.subprocess.run", side_effect=subprocess.CalledProcessError(1, "ps")):
        try:
            send_key(VK_CODES["play_pause"])
            assert False, "debería haber lanzado excepción"
        except subprocess.CalledProcessError:
            pass
```

- [ ] **Step 3: Verificar que los tests fallan**

```bash
pytest tests/test_base.py -v
```

Resultado esperado: `ModuleNotFoundError: No module named 'handlers'`.

- [ ] **Step 4: Crear handlers/__init__.py**

Archivo vacío:
```python
```

- [ ] **Step 5: Crear handlers/base.py**

```python
import subprocess

VK_CODES: dict[str, int] = {
    "play_pause": 0xB3,
    "next": 0xB0,
    "prev": 0xB1,
    "vol_up": 0xAF,
    "vol_down": 0xAE,
    "vol_mute": 0xAD,
}

_PS_KEY_SCRIPT = (
    "Add-Type -MemberDefinition '"
    '[DllImport("user32.dll")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);'
    "' -Name 'User32' -Namespace 'Win32' -ErrorAction SilentlyContinue;"
    "[Win32.User32]::keybd_event({vk}, 0, 0, 0);"
    "[Win32.User32]::keybd_event({vk}, 0, 2, 0)"
)


def send_key(vk_code: int) -> None:
    script = _PS_KEY_SCRIPT.format(vk=hex(vk_code))
    subprocess.run(["powershell.exe", "-Command", script], check=True)
```

- [ ] **Step 6: Correr tests**

```bash
pytest tests/test_base.py -v
```

Resultado esperado: PASS en ambos tests.

- [ ] **Step 7: Commit**

```bash
git add handlers/__init__.py handlers/base.py tests/conftest.py tests/test_base.py
git commit -m "feat: send_key utility and test helpers"
```

---

## Task 4: Music handlers — media keys

**Files:**
- Create: `handlers/music.py`
- Create: `tests/test_music.py`

- [ ] **Step 1: Escribir tests para PlayPause, Next, Prev, Volume**

`tests/test_music.py`:
```python
from unittest.mock import patch
from handlers.music import PlayPauseHandler, NextHandler, PrevHandler, VolumeHandler
from tests.conftest import make_handler_input


def test_playpause_can_handle():
    hi = make_handler_input("PlayPauseIntent")
    assert PlayPauseHandler().can_handle(hi) is True


def test_playpause_sends_key():
    hi = make_handler_input("PlayPauseIntent")
    with patch("handlers.music.send_key") as mock_key:
        PlayPauseHandler().handle(hi)
        mock_key.assert_called_once_with(0xB3)


def test_next_sends_key():
    hi = make_handler_input("NextIntent")
    with patch("handlers.music.send_key") as mock_key:
        NextHandler().handle(hi)
        mock_key.assert_called_once_with(0xB0)


def test_prev_sends_key():
    hi = make_handler_input("PrevIntent")
    with patch("handlers.music.send_key") as mock_key:
        PrevHandler().handle(hi)
        mock_key.assert_called_once_with(0xB1)


def test_volume_up():
    hi = make_handler_input("VolumeIntent", slots={"direction": "subir"})
    with patch("handlers.music.send_key") as mock_key:
        VolumeHandler().handle(hi)
        mock_key.assert_called_once_with(0xAF)


def test_volume_down():
    hi = make_handler_input("VolumeIntent", slots={"direction": "bajar"})
    with patch("handlers.music.send_key") as mock_key:
        VolumeHandler().handle(hi)
        mock_key.assert_called_once_with(0xAE)
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
pytest tests/test_music.py -v
```

Resultado esperado: `ModuleNotFoundError: No module named 'handlers.music'`.

- [ ] **Step 3: Crear handlers/music.py con handlers de media keys**

```python
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from handlers.base import send_key, VK_CODES


class PlayPauseHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("PlayPauseIntent")(handler_input)

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
        return ask_utils.is_intent_name("NextIntent")(handler_input)

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
        return ask_utils.is_intent_name("PrevIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        send_key(VK_CODES["prev"])
        return (
            handler_input.response_builder
            .speak("Anterior.")
            .set_should_end_session(False)
            .response
        )


class VolumeHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("VolumeIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        direction = handler_input.request_envelope.request.intent.slots["direction"].value
        vk = VK_CODES["vol_up"] if direction in ("subir", "arriba", "más", "sube") else VK_CODES["vol_down"]
        send_key(vk)
        word = "Subiendo" if vk == VK_CODES["vol_up"] else "Bajando"
        return (
            handler_input.response_builder
            .speak(f"{word} el volumen.")
            .set_should_end_session(False)
            .response
        )
```

- [ ] **Step 4: Correr tests**

```bash
pytest tests/test_music.py -v
```

Resultado esperado: PASS en los 6 tests.

- [ ] **Step 5: Commit**

```bash
git add handlers/music.py tests/test_music.py
git commit -m "feat: music media key handlers"
```

---

## Task 5: Music handlers — ytmusicapi

**Files:**
- Modify: `handlers/music.py` (agregar PlaySongHandler, PlayArtistHandler)
- Modify: `tests/test_music.py` (agregar tests)

> **Nota:** Para este task necesitás el `oauth.json` generado por `ytmusicapi oauth`. Si todavía no lo tenés, crearlo ahora antes de continuar.

- [ ] **Step 1: Agregar tests para PlaySong y PlayArtist**

Agregar al final de `tests/test_music.py`:
```python
from handlers.music import PlaySongHandler, PlayArtistHandler


def test_playsong_can_handle():
    hi = make_handler_input("PlaySongIntent")
    assert PlaySongHandler().can_handle(hi) is True


def test_playsong_searches_and_opens():
    hi = make_handler_input("PlaySongIntent", slots={"songName": "Bohemian Rhapsody"})
    fake_results = [{"videoId": "abc123", "title": "Bohemian Rhapsody"}]
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.subprocess.run") as mock_run:
        MockYT.return_value.search.return_value = fake_results
        PlaySongHandler().handle(hi)
        MockYT.return_value.search.assert_called_once_with(
            "Bohemian Rhapsody", filter="songs", limit=1
        )
        url_arg = mock_run.call_args[0][0]
        assert "abc123" in " ".join(url_arg)


def test_playsong_no_results():
    hi = make_handler_input("PlaySongIntent", slots={"songName": "xyzzy"})
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.subprocess.run"):
        MockYT.return_value.search.return_value = []
        response = PlaySongHandler().handle(hi)
        hi.response_builder.speak.assert_called_with("No encontré esa canción.")


def test_playartist_searches_and_opens():
    hi = make_handler_input("PlayArtistIntent", slots={"artistName": "Radiohead"})
    fake_results = [{"browseId": "UC123", "artist": "Radiohead"}]
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.subprocess.run") as mock_run:
        MockYT.return_value.search.return_value = fake_results
        PlayArtistHandler().handle(hi)
        MockYT.return_value.search.assert_called_once_with(
            "Radiohead", filter="artists", limit=1
        )
        url_arg = mock_run.call_args[0][0]
        assert "UC123" in " ".join(url_arg)
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
pytest tests/test_music.py::test_playsong_searches_and_opens -v
```

Resultado esperado: `ImportError` o `AttributeError`.

- [ ] **Step 3: Agregar PlaySongHandler y PlayArtistHandler a handlers/music.py**

Agregar al inicio del archivo (imports):
```python
import subprocess
from pathlib import Path
from ytmusicapi import YTMusic

_OAUTH_PATH = Path(__file__).parent.parent / "oauth.json"
```

Agregar al final del archivo:
```python
class PlaySongHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("PlaySongIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        song_name = handler_input.request_envelope.request.intent.slots["songName"].value
        yt = YTMusic(str(_OAUTH_PATH))
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
        subprocess.run(["powershell.exe", "Start-Process", url], check=True)
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
        yt = YTMusic(str(_OAUTH_PATH))
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
        subprocess.run(["powershell.exe", "Start-Process", url], check=True)
        return (
            handler_input.response_builder
            .speak(f"Reproduciendo música de {artist}.")
            .set_should_end_session(False)
            .response
        )
```

- [ ] **Step 4: Correr todos los tests de música**

```bash
pytest tests/test_music.py -v
```

Resultado esperado: PASS en los 10 tests.

- [ ] **Step 5: Commit**

```bash
git add handlers/music.py tests/test_music.py
git commit -m "feat: ytmusicapi song and artist handlers"
```

---

## Task 6: System handlers

**Files:**
- Create: `handlers/system.py`
- Create: `tests/test_system.py`

- [ ] **Step 1: Escribir tests**

`tests/test_system.py`:
```python
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
        # debe usar .ask() para esperar confirmación, no .speak() directo con acción
        hi.response_builder.ask.assert_called()


def test_restart_asks_for_confirmation():
    hi = make_handler_input("SystemIntent", slots={"action": "reiniciar"})
    with patch("handlers.system.subprocess.run"):
        SystemHandler().handle(hi)
        hi.response_builder.ask.assert_called()
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
pytest tests/test_system.py -v
```

Resultado esperado: `ModuleNotFoundError`.

- [ ] **Step 3: Crear handlers/system.py**

```python
import subprocess

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

_DESTRUCTIVE = {"apagar", "reiniciar"}

_PS_COMMANDS: dict[str, list[str]] = {
    "apagar": ["powershell.exe", "Stop-Computer", "-Force"],
    "reiniciar": ["powershell.exe", "Restart-Computer", "-Force"],
    "bloquear": ["powershell.exe", "-Command", "rundll32.exe user32.dll,LockWorkStation"],
}

_SYNONYMS: dict[str, str] = {
    "apagá": "apagar", "shutdown": "apagar",
    "reiniciá": "reiniciar", "restart": "reiniciar",
    "bloqueá": "bloquear", "lock": "bloquear", "bloquear pantalla": "bloquear",
}


class SystemHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("SystemIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        raw = handler_input.request_envelope.request.intent.slots["action"].value or ""
        action = _SYNONYMS.get(raw.lower(), raw.lower())

        if action in _DESTRUCTIVE:
            handler_input.attributes_manager.session_attributes["pending_action"] = action
            return (
                handler_input.response_builder
                .speak(f"¿Seguro que querés {action} la PC?")
                .ask("Decí sí para confirmar o no para cancelar.")
                .response
            )

        if action == "bloquear":
            subprocess.run(_PS_COMMANDS["bloquear"], check=True)
            return (
                handler_input.response_builder
                .speak("Pantalla bloqueada.")
                .set_should_end_session(True)
                .response
            )

        return (
            handler_input.response_builder
            .speak("No entendí esa acción.")
            .set_should_end_session(False)
            .response
        )


class SystemConfirmHandler(AbstractRequestHandler):
    """Recibe el 'sí' o 'no' después de pedir confirmación de apagar/reiniciar."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        session = handler_input.attributes_manager.session_attributes
        return (
            ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input)
            and "pending_action" in session
        ) or (
            ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input)
            and "pending_action" in session
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        session = handler_input.attributes_manager.session_attributes
        action = session.pop("pending_action", None)

        if ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input) or not action:
            return (
                handler_input.response_builder
                .speak("Cancelado.")
                .set_should_end_session(True)
                .response
            )

        subprocess.run(_PS_COMMANDS[action], check=True)
        return (
            handler_input.response_builder
            .speak(f"Ejecutando {action}.")
            .set_should_end_session(True)
            .response
        )
```

- [ ] **Step 4: Correr tests**

```bash
pytest tests/test_system.py -v
```

Resultado esperado: PASS en los 4 tests.

- [ ] **Step 5: Commit**

```bash
git add handlers/system.py tests/test_system.py
git commit -m "feat: system handlers with confirmation for destructive actions"
```

---

## Task 7: App handlers

**Files:**
- Create: `handlers/apps.py`
- Create: `tests/test_apps.py`

- [ ] **Step 1: Escribir tests**

`tests/test_apps.py`:
```python
from unittest.mock import patch
from handlers.apps import AppHandler
from tests.conftest import make_handler_input


def test_app_can_handle():
    hi = make_handler_input("AppIntent")
    assert AppHandler().can_handle(hi) is True


def test_open_chrome():
    hi = make_handler_input("AppIntent", slots={"appName": "Chrome", "appAction": "abrir"})
    with patch("handlers.apps.subprocess.run") as mock_run:
        AppHandler().handle(hi)
        cmd = mock_run.call_args[0][0]
        assert "Start-Process" in cmd
        assert "chrome.exe" in cmd


def test_close_discord():
    hi = make_handler_input("AppIntent", slots={"appName": "Discord", "appAction": "cerrar"})
    with patch("handlers.apps.subprocess.run") as mock_run:
        AppHandler().handle(hi)
        cmd = mock_run.call_args[0][0]
        assert "Stop-Process" in cmd


def test_unknown_app_returns_error():
    hi = make_handler_input("AppIntent", slots={"appName": "UnknownApp", "appAction": "abrir"})
    with patch("handlers.apps.subprocess.run"):
        AppHandler().handle(hi)
        hi.response_builder.speak.assert_called_with("No conozco esa aplicación.")
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
pytest tests/test_apps.py -v
```

Resultado esperado: `ModuleNotFoundError`.

- [ ] **Step 3: Crear handlers/apps.py**

```python
import subprocess

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from config import APPS

_OPEN_SYNONYMS = {"abrir", "abrí", "abre", "lanzá", "lanzar"}
_CLOSE_SYNONYMS = {"cerrar", "cerrá", "cierra", "matá", "matar"}


class AppHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AppIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        slots = handler_input.request_envelope.request.intent.slots
        app_name = slots["appName"].value or ""
        app_action = (slots["appAction"].value or "").lower()

        exe = APPS.get(app_name)
        if not exe:
            return (
                handler_input.response_builder
                .speak("No conozco esa aplicación.")
                .set_should_end_session(False)
                .response
            )

        if app_action in _OPEN_SYNONYMS:
            subprocess.run(["powershell.exe", "Start-Process", exe], check=True)
            speech = f"Abriendo {app_name}."
        elif app_action in _CLOSE_SYNONYMS:
            process_name = exe.replace(".exe", "")
            subprocess.run(
                ["powershell.exe", "Stop-Process", "-Name", process_name, "-Force"],
                check=True,
            )
            speech = f"Cerrando {app_name}."
        else:
            speech = "No entendí si querés abrir o cerrar."

        return (
            handler_input.response_builder
            .speak(speech)
            .set_should_end_session(False)
            .response
        )
```

- [ ] **Step 4: Correr tests**

```bash
pytest tests/test_apps.py -v
```

Resultado esperado: PASS en los 4 tests.

- [ ] **Step 5: Commit**

```bash
git add handlers/apps.py tests/test_apps.py
git commit -m "feat: app open/close handler"
```

---

## Task 8: Skill builder + built-in intents

**Files:**
- Create: `skill.py`

- [ ] **Step 1: Crear skill.py**

```python
from ask_sdk_core.skill_builder import SkillBuilder
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

from handlers.music import (
    PlayPauseHandler, NextHandler, PrevHandler,
    VolumeHandler, PlaySongHandler, PlayArtistHandler,
)
from handlers.system import SystemHandler, SystemConfirmHandler
from handlers.apps import AppHandler


class HelpHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        help_text = (
            "Podés decir: pausa, siguiente, anterior, subí el volumen, "
            "tocá una canción, tocá algo de un artista, "
            "abrí o cerrá una app, apagá la pc, reiniciá, o bloqueá la pantalla."
        )
        return (
            handler_input.response_builder
            .speak(help_text)
            .ask("¿Qué querés hacer?")
            .response
        )


class CancelStopHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or \
               ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)

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
            .speak("No entendí ese comando. Podés decir pausa, siguiente, o abrí una app.")
            .ask("¿Qué querés hacer?")
            .response
        )


class LaunchHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        from ask_sdk_model import LaunchRequest
        return isinstance(handler_input.request_envelope.request, LaunchRequest)

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder
            .speak("Mi PC lista. ¿Qué querés hacer?")
            .ask("¿Qué querés hacer?")
            .response
        )


sb = SkillBuilder()
sb.add_request_handler(LaunchHandler())
sb.add_request_handler(PlayPauseHandler())
sb.add_request_handler(NextHandler())
sb.add_request_handler(PrevHandler())
sb.add_request_handler(VolumeHandler())
sb.add_request_handler(PlaySongHandler())
sb.add_request_handler(PlayArtistHandler())
sb.add_request_handler(SystemHandler())
sb.add_request_handler(SystemConfirmHandler())
sb.add_request_handler(AppHandler())
sb.add_request_handler(HelpHandler())
sb.add_request_handler(CancelStopHandler())
sb.add_request_handler(FallbackHandler())

skill = sb.create()
```

- [ ] **Step 2: Verificar que importa sin errores**

```bash
python -c "from skill import skill; print('OK')"
```

Resultado esperado: `OK`.

- [ ] **Step 3: Commit**

```bash
git add skill.py
git commit -m "feat: skill builder with all handlers and built-ins"
```

---

## Task 9: FastAPI endpoint + main.py

**Files:**
- Create: `main.py`

- [ ] **Step 1: Crear main.py**

```python
import json
import subprocess

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from ask_sdk_webservice_utils.webservice_handler import WebserviceSkillHandler

from config import PORT, SKILL_ID
from skill import skill

app = FastAPI()
handler = WebserviceSkillHandler(skill=skill, verify_signature=True, verify_timestamp=True)


@app.post("/alexa")
async def alexa_webhook(request: Request) -> Response:
    body = await request.body()
    headers = dict(request.headers)
    response_str = handler.verify_request_and_dispatch(headers, body.decode("utf-8"))
    return JSONResponse(content=json.loads(response_str))


def start_tunnel() -> subprocess.Popen:
    return subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{PORT}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    tunnel = start_tunnel()
    print(f"Cloudflare Tunnel iniciado. Revisá la URL en: cloudflared tunnel info")
    try:
        uvicorn.run(app, host="0.0.0.0", port=PORT)
    finally:
        tunnel.terminate()
```

- [ ] **Step 2: Verificar que el servidor arranca**

```bash
python main.py
```

Resultado esperado: servidor corriendo en `http://0.0.0.0:8000` y tunnel iniciado. Ctrl+C para detener.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: FastAPI endpoint with Cloudflare Tunnel startup"
```

---

## Task 10: Correr suite completa y verificar

- [ ] **Step 1: Correr todos los tests**

```bash
pytest -v
```

Resultado esperado: todos los tests en PASS, 0 errores.

- [ ] **Step 2: Verificar importaciones completas**

```bash
python -c "import main; print('OK')"
```

Resultado esperado: `OK`.

- [ ] **Step 3: Commit final**

```bash
git add .
git commit -m "chore: all tests passing"
```

---

## Pasos manuales post-implementación

1. **Obtener URL del tunnel:** ejecutar `cloudflared tunnel list` o revisar la salida de `main.py` para conseguir la URL pública (ej: `https://xxxx.trycloudflare.com`).
2. **Configurar el endpoint en Alexa Developer Console:** en la sección *Endpoint*, pegar la URL del tunnel + `/alexa` (ej: `https://xxxx.trycloudflare.com/alexa`), tipo *HTTPS*, certificado *Wildcard*.
3. **Cargar intents en la consola:** seguir el spec `docs/superpowers/specs/2026-06-27-alexa-intents-design.md` para crear los intents, slots y utterances en el Interaction Model.
4. **Build del modelo:** click en "Build Model" en la consola.
5. **Test en la consola:** ir a la pestaña *Test*, activar la skill, probar `"pausa"`, `"siguiente"`, `"abrí Chrome"`.

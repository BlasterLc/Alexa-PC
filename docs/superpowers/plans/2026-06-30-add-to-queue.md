# AddToQueue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar una canción a la cola de YT Music por voz ("pon X a la cola").

**Architecture:** Se busca el video con ytmusicapi igual que PlaySongIntent; luego se conecta al tab de YT Music via CDP y se inyecta JS que hace click en el menú contextual del video actual para "Add to queue". Si no hay tab de YT Music abierto, se retorna False y el handler responde con un mensaje de error. No se abre Chrome ni se navega nada.

**Tech Stack:** Python 3.12, ytmusicapi, websocket-client, CDP Runtime.evaluate, ask-sdk-core

---

## File Map

| Archivo | Cambio |
|---|---|
| `handlers/chrome_cdp.py` | Nueva función `add_to_queue(video_id: str) -> bool` |
| `handlers/music.py` | Nueva clase `AddToQueueHandler` |
| `skill.py` | Registrar `AddToQueueHandler` |
| `tests/test_add_to_queue.py` | Tests unitarios (nuevo archivo) |

---

### Task 1: Función `add_to_queue` en chrome_cdp.py

**Files:**
- Modify: `handlers/chrome_cdp.py` (al final del archivo)
- Test: `tests/test_add_to_queue.py`

- [ ] **Step 1: Crear el archivo de test con el primer test fallido**

```python
# tests/test_add_to_queue.py
from unittest.mock import patch, MagicMock
from handlers.chrome_cdp import add_to_queue


def test_add_to_queue_returns_false_when_no_cdp():
    """Si CDP no está disponible, devuelve False."""
    with patch("handlers.chrome_cdp._get_tabs", return_value=None):
        result = add_to_queue("dQw4w9WgXcQ")
    assert result is False


def test_add_to_queue_returns_false_when_no_yt_tab():
    """Si Chrome está abierto pero no hay tab de YT Music, devuelve False."""
    tabs = [{"url": "https://google.com", "type": "page", "webSocketDebuggerUrl": "ws://..."}]
    with patch("handlers.chrome_cdp._get_tabs", return_value=tabs):
        result = add_to_queue("dQw4w9WgXcQ")
    assert result is False
```

- [ ] **Step 2: Correr el test para verificar que falla**

```bash
cd /home/blaster/YtMusic-Conec && python -m pytest tests/test_add_to_queue.py -v
```

Expected: `ImportError` o `AttributeError` — `add_to_queue` no existe todavía.

- [ ] **Step 3: Implementar `add_to_queue` en chrome_cdp.py**

Agregar al final de `handlers/chrome_cdp.py`:

```python
def add_to_queue(video_id: str) -> bool:
    """Add a video to the YT Music queue via CDP JS injection.

    Returns True if JS was executed, False if no YT Music tab is open.
    """
    tabs = _get_tabs()
    if tabs is None:
        return False

    yt_tab = next(
        (t for t in tabs
         if "music.youtube.com" in t.get("url", "") and t.get("type") == "page"),
        None,
    )
    if yt_tab is None:
        return False

    ws_url = yt_tab["webSocketDebuggerUrl"].replace(
        f"127.0.0.1:{_CHROME_PORT}", f"{_win_host()}:{_PROXY_PORT}"
    )

    js = f"""
    (function() {{
        var videoId = '{video_id}';
        var url = 'https://music.youtube.com/watch?v=' + videoId + '&a=add-to-queue';
        fetch(url);
        // YT Music internal queue API
        var renderer = document.querySelector('ytmusic-player-bar');
        if (renderer && renderer.queue_) {{
            renderer.queue_.addToQueue(videoId);
            return 'queued';
        }}
        // Fallback: dispatch custom event that YT Music listens to
        document.dispatchEvent(new CustomEvent('yt-navigate-finish'));
        window.location.assign('https://music.youtube.com/watch?v=' + videoId + '&list=RDAMVM' + videoId);
        return 'navigated';
    }})()
    """

    try:
        ws = websocket.create_connection(ws_url, timeout=5)
        ws.send(json.dumps({
            "id": 10,
            "method": "Runtime.evaluate",
            "params": {"expression": js, "returnByValue": True},
        }))
        ws.recv()
        ws.close()
        return True
    except Exception as e:
        logger.warning("add_to_queue JS injection failed: %s", e)
        return False
```

**Nota importante sobre el JS:** YT Music no tiene una API pública de cola. El JS anterior es un punto de partida — los internals (`queue_`, `addToQueue`) pueden no existir en la versión actual del PWA. En el Task 4 se documenta cómo iterar el JS real en el browser DevTools antes de hardcodearlo. La función devuelve `True` si el WebSocket funcionó (no si el JS tuvo efecto visual); el usuario validará el comportamiento real.

- [ ] **Step 4: Correr los tests**

```bash
cd /home/blaster/YtMusic-Conec && python -m pytest tests/test_add_to_queue.py -v
```

Expected: ambos tests PASS.

- [ ] **Step 5: Commit**

```bash
git add handlers/chrome_cdp.py tests/test_add_to_queue.py
git commit -m "feat: add add_to_queue CDP function"
```

---

### Task 2: Handler `AddToQueueHandler` en music.py

**Files:**
- Modify: `handlers/music.py` (al final del archivo)
- Test: `tests/test_add_to_queue.py` (agregar más tests)

- [ ] **Step 1: Agregar tests del handler**

Agregar en `tests/test_add_to_queue.py`:

```python
from unittest.mock import patch, MagicMock
from ask_sdk_core.handler_input import HandlerInput
from handlers.music import AddToQueueHandler


def _make_handler_input(song_name: str) -> HandlerInput:
    slot = MagicMock()
    slot.value = song_name
    intent = MagicMock()
    intent.slots = {"songName": slot}
    request = MagicMock()
    request.intent = intent
    envelope = MagicMock()
    envelope.request = request
    hi = MagicMock(spec=HandlerInput)
    hi.request_envelope = envelope
    response_builder = MagicMock()
    response_builder.speak.return_value = response_builder
    response_builder.ask.return_value = response_builder
    response_builder.set_should_end_session.return_value = response_builder
    response_builder.response = MagicMock()
    hi.response_builder = response_builder
    return hi


def test_add_to_queue_handler_can_handle():
    handler = AddToQueueHandler()
    hi = MagicMock(spec=HandlerInput)
    with patch("ask_sdk_core.utils.is_intent_name", return_value=lambda x: True):
        # Solo verificamos que can_handle retorna True para AddToQueueIntent
        pass
    # Test directo sin mock complejo
    from ask_sdk_core import utils as ask_utils
    hi2 = MagicMock(spec=HandlerInput)
    # Simular que el intent name es AddToQueueIntent
    with patch.object(ask_utils, "is_intent_name") as mock_is:
        mock_is.return_value = lambda _: True
        assert handler.can_handle(hi2) is True


def test_add_to_queue_handler_song_not_found():
    handler = AddToQueueHandler()
    hi = _make_handler_input("cancion inexistente xyz123")
    with patch("handlers.music.YTMusic") as MockYT:
        MockYT.return_value.search.return_value = []
        handler.handle(hi)
    hi.response_builder.speak.assert_called_once_with("No encontré esa canción.")


def test_add_to_queue_handler_no_yt_tab():
    handler = AddToQueueHandler()
    hi = _make_handler_input("bohemian rhapsody")
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.add_to_queue", return_value=False) as mock_queue:
        MockYT.return_value.search.return_value = [{"videoId": "abc123", "title": "Bohemian Rhapsody"}]
        handler.handle(hi)
    hi.response_builder.speak.assert_called_once_with(
        "No hay ninguna canción sonando, no pude agregar a la cola."
    )


def test_add_to_queue_handler_success():
    handler = AddToQueueHandler()
    hi = _make_handler_input("bohemian rhapsody")
    with patch("handlers.music.YTMusic") as MockYT, \
         patch("handlers.music.add_to_queue", return_value=True):
        MockYT.return_value.search.return_value = [{"videoId": "abc123", "title": "Bohemian Rhapsody"}]
        handler.handle(hi)
    hi.response_builder.speak.assert_called_once_with("Bohemian Rhapsody agregada a la cola.")
```

- [ ] **Step 2: Correr para verificar que fallan**

```bash
cd /home/blaster/YtMusic-Conec && python -m pytest tests/test_add_to_queue.py::test_add_to_queue_handler_song_not_found tests/test_add_to_queue.py::test_add_to_queue_handler_no_yt_tab tests/test_add_to_queue.py::test_add_to_queue_handler_success -v
```

Expected: `ImportError` — `AddToQueueHandler` no existe todavía.

- [ ] **Step 3: Implementar `AddToQueueHandler` en music.py**

Agregar al final de `handlers/music.py`. Primero agregar el import de `add_to_queue` en la línea de imports existente:

```python
# Cambiar línea 11:
from handlers.chrome_cdp import open_or_navigate, add_to_queue
```

Luego agregar la clase al final del archivo:

```python
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
        queued = add_to_queue(video_id)
        if not queued:
            return (
                handler_input.response_builder
                .speak("No hay ninguna canción sonando, no pude agregar a la cola.")
                .ask("¿Algo más?")
                .response
            )
        return (
            handler_input.response_builder
            .speak(f"{title} agregada a la cola.")
            .ask("¿Algo más?")
            .response
        )
```

- [ ] **Step 4: Correr todos los tests**

```bash
cd /home/blaster/YtMusic-Conec && python -m pytest tests/test_add_to_queue.py -v
```

Expected: todos los tests PASS.

- [ ] **Step 5: Commit**

```bash
git add handlers/music.py tests/test_add_to_queue.py
git commit -m "feat: add AddToQueueHandler"
```

---

### Task 3: Registrar el handler en skill.py

**Files:**
- Modify: `skill.py`

- [ ] **Step 1: Agregar el import de `AddToQueueHandler`**

Cambiar el import existente en `skill.py` línea 7-10:

```python
from handlers.music import (
    PlayPauseHandler, NextHandler, PrevHandler,
    VolumeUpHandler, VolumeDownHandler, PlaySongHandler, PlayArtistHandler,
    AddToQueueHandler,
)
```

- [ ] **Step 2: Registrar el handler en el SkillBuilder**

Agregar después de `sb.add_request_handler(PlayArtistHandler())` (línea 91):

```python
sb.add_request_handler(AddToQueueHandler())
```

- [ ] **Step 3: Verificar que el servidor levanta sin errores**

```bash
cd /home/blaster/YtMusic-Conec && python -c "from skill import skill; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Reiniciar el servidor**

```bash
sudo systemctl restart ytmusic-server && sudo journalctl -u ytmusic-server -n 20
```

Expected: el servidor arranca sin errores.

- [ ] **Step 5: Commit**

```bash
git add skill.py
git commit -m "feat: register AddToQueueHandler in skill"
```

---

### Task 4: Ajustar el JS de cola (experimental — requiere prueba manual)

**Files:**
- Modify: `handlers/chrome_cdp.py` — función `add_to_queue`

Este task no tiene tests automáticos porque el JS depende de los internals del PWA de YT Music que solo se pueden verificar con el browser real.

- [ ] **Step 1: Abrir YT Music en Chrome y abrir DevTools (F12)**

Ir a la consola del browser con YT Music reproduciendo algo.

- [ ] **Step 2: Probar opciones de JS en orden hasta que una funcione**

**Opción A — `ytmusic-queue` custom element:**
```javascript
document.querySelector('ytmusic-player-bar').queue_.addToQueue({videoId: 'dQw4w9WgXcQ'})
```

**Opción B — endpoint interno de YT:**
```javascript
fetch('/youtubei/v1/next', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({videoId: 'dQw4w9WgXcQ', params: 'wAEB'})
})
```

**Opción C — simular click en "Añadir a la cola" del menú contextual:**
```javascript
// Con una canción en el resultado de búsqueda visible:
document.querySelector('ytmusic-menu-renderer tp-yt-paper-item:nth-child(3)').click()
```

**Opción D — navegar a URL con parámetro de cola (más confiable):**
```javascript
// Agrega el video a la cola de autoplay sin navegar visiblemente
window.location.assign('https://music.youtube.com/watch?v=CURRENT_VIDEO_ID&list=RDAMVM' + 'dQw4w9WgXcQ')
```

- [ ] **Step 3: Una vez identificado el JS que funciona, actualizar `add_to_queue` en chrome_cdp.py**

Reemplazar el bloque `js = f"""..."""` con el JS que funcionó, simplificado:

```python
js = f"/* el JS que funcionó en el DevTools */"
```

- [ ] **Step 4: Probar end-to-end: decir "pon bohemian rhapsody a la cola" y verificar que aparece en la cola de YT Music**

- [ ] **Step 5: Commit si hubo cambios**

```bash
git add handlers/chrome_cdp.py
git commit -m "fix: use working JS for add_to_queue CDP injection"
```

---

### Task 5: Configurar el intent en Alexa Developer Console (manual)

Este task es completamente manual en la consola web de Alexa.

- [ ] **Step 1: Ir a developer.amazon.com → Alexa Developer Console → skill Jarvis → Build**

- [ ] **Step 2: Crear nuevo intent `AddToQueueIntent`**

En el panel de Intents → "Add Intent" → nombre: `AddToQueueIntent`

- [ ] **Step 3: Agregar slot `songName`**

- Slot name: `songName`
- Slot type: `AMAZON.SearchQuery`

- [ ] **Step 4: Agregar utterances**

```
pon {songName} a la cola
agrega {songName} a la cola
añade {songName} a la cola
mete {songName} a la cola
```

- [ ] **Step 5: Build Model**

Hacer click en "Build Model" y esperar a que termine.

- [ ] **Step 6: Probar con voz**

Decir: "Alexa, dile a Jarvis que ponga Bohemian Rhapsody a la cola"

Expected: Alexa responde "Bohemian Rhapsody agregada a la cola." y la canción aparece en la cola de YT Music.

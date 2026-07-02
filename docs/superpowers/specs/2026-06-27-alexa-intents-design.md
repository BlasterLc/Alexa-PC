# Alexa Skill — Diseño de Intents (YtMusic-Conec)

**Fecha:** 2026-06-27  
**Estado:** Aprobado

## Contexto

La Alexa Skill "mi pc" permite controlar la PC por voz via Echo Dot. Se comunica con un servidor FastAPI en WSL2 a través de Cloudflare Tunnel. El control de YT Music usa media keys (PowerShell) para comandos básicos y `ytmusicapi` para búsquedas de canciones/artistas.

## Nombre de invocación

`mi pc`

## Locale

`es-AR` (español Argentina). Agregar `es-MX` y `es-ES` como locales secundarios si se necesita en el futuro.

## Modos de interacción

- **Comando directo:** `"Alexa, dile a mi pc que pause"`
- **Sesión abierta:** `"Alexa, abre mi pc"` → luego `"pausa"`, `"siguiente"`, `"abrí Chrome"` sin repetir el nombre

---

## Intents

### Music Intents

#### `PlayPauseIntent`
Toggle play/pause via media key `VK_MEDIA_PLAY_PAUSE` (0xB3).

Utterances:
- `pausa`
- `play`
- `pausá`
- `reproducí`
- `detené la música`
- `reanudá la música`

---

#### `NextIntent`
Siguiente pista via media key `VK_MEDIA_NEXT_TRACK` (0xB0).

Utterances:
- `siguiente`
- `siguiente canción`
- `próxima canción`
- `saltá esta`
- `la que sigue`

---

#### `PrevIntent`
Pista anterior via media key `VK_MEDIA_PREV_TRACK` (0xB1).

Utterances:
- `anterior`
- `la anterior`
- `canción anterior`
- `volvé`
- `volvé atrás`

---

#### `VolumeIntent`
Sube o baja el volumen via media keys `VK_VOLUME_UP` (0xAF) / `VK_VOLUME_DOWN` (0xAE).

Slot: `direction`
- Tipo: Custom Slot Type `DIRECTION_TYPE`
- Valores: `subir` (sinónimos: arriba, más, sube), `bajar` (sinónimos: abajo, menos, baja)

Utterances:
- `subí el volumen`
- `bajá el volumen`
- `más volumen`
- `menos volumen`
- `{direction} el volumen`
- `volumen {direction}`

---

#### `PlaySongIntent`
Busca una canción específica con `ytmusicapi.search()` y abre la URL en Chrome (PWA).

Slot: `songName`
- Tipo: `AMAZON.SearchQuery`

Utterances:
- `tocá {songName}`
- `poné {songName}`
- `reproducí {songName}`
- `buscá {songName}`
- `quiero escuchar {songName}`

---

#### `PlayArtistIntent`
Busca por artista con `ytmusicapi.search()` filtrando por artista y abre el primer resultado.

Slot: `artistName`
- Tipo: `AMAZON.SearchQuery`

Utterances:
- `tocá algo de {artistName}`
- `poné música de {artistName}`
- `algo de {artistName}`
- `música de {artistName}`

---

### System Intents

#### `SystemIntent`
Ejecuta acciones del sistema via `subprocess` + PowerShell.

Slot: `action`
- Tipo: Custom Slot Type `SYSTEM_ACTION_TYPE`
- Valores:
  - `apagar` (sinónimos: apagá, shutdown)
  - `reiniciar` (sinónimos: reiniciá, restart)
  - `bloquear` (sinónimos: bloqueá, lock, bloquear pantalla)

**Confirmación requerida:** Para `apagar` y `reiniciar`, Alexa debe pedir confirmación antes de ejecutar: `"¿Seguro que querés {action} la PC?"`. Para `bloquear` no se requiere confirmación.

Utterances:
- `apagá la pc`
- `reiniciá la pc`
- `bloqueá la pantalla`
- `{action} la computadora`
- `{action} la pc`

---

### App Intents

#### `AppIntent`
Abre o cierra una aplicación. La lista de apps viene de `apps.json` — modificar el JSON y actualizar el modelo en Alexa Developer Console para agregar nuevas apps.

Slots:
- `appName`: Custom Slot Type `APP_NAME_TYPE` (valores desde `apps.json`)
- `appAction`: Custom Slot Type `APP_ACTION_TYPE`
  - Valores: `abrir` (sinónimos: abrí, abre, lanzá), `cerrar` (sinónimos: cerrá, cierra, matá)

Apps iniciales en `apps.json`:
```json
{
  "Chrome": "chrome.exe",
  "Discord": "discord.exe",
  "Spotify": "Spotify.exe",
  "VS Code": "Code.exe",
  "Notepad": "notepad.exe"
}
```

Utterances:
- `abrí {appName}`
- `cerrá {appName}`
- `abrí el {appName}`
- `cerrá el {appName}`
- `{appAction} {appName}`

---

### Built-in Intents (obligatorios)

| Intent | Comportamiento |
|---|---|
| `AMAZON.CancelIntent` | Cierra la sesión. Responde: `"Hasta luego."` |
| `AMAZON.StopIntent` | Igual que Cancel. |
| `AMAZON.HelpIntent` | Lista los comandos disponibles en voz. |
| `AMAZON.FallbackIntent` | `"No entendí ese comando. Podés decir pausa, siguiente, o abrí una app."` |

---

## Resumen de Slot Types

| Slot Type | Valores |
|---|---|
| `DIRECTION_TYPE` | `subir`, `bajar` |
| `SYSTEM_ACTION_TYPE` | `apagar`, `reiniciar`, `bloquear` |
| `APP_ACTION_TYPE` | `abrir`, `cerrar` |
| `APP_NAME_TYPE` | Dinámico desde `apps.json` |
| `AMAZON.SearchQuery` | Built-in (texto libre — usado para canciones y artistas) |

**Total: 10 intents, 5 slot types (3 custom + 1 AMAZON built-in usado en 2 intents)**

---

## Flujo de sesión

```
"Alexa, abre mi pc"
  → Alexa: "Mi PC lista. ¿Qué querés hacer?"
  → Usuario: "pausa" / "siguiente" / "abrí Chrome" ...
  → cada respuesta mantiene la sesión abierta
  → "Alexa, para" → cierra sesión
```

En modo comando directo la sesión se cierra automáticamente tras responder.

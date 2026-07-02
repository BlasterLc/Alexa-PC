import json
import logging
import subprocess
import time

import requests
import websocket

from handlers.base import CMD_EXE

logger = logging.getLogger(__name__)

_CHROME_PORT = 9222   # Chrome debug port (Windows localhost only)
_PROXY_PORT = 9223    # netsh portproxy port reachable from WSL2
_CHROME_EXE = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
_USER_DATA_DIR = "C:\\Users\\Blaster\\AppData\\Local\\ChromeYTMusic"


def _win_host() -> str:
    """Get Windows host IP from WSL2 default gateway."""
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True, text=True, timeout=2,
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if "via" in parts:
                return parts[parts.index("via") + 1]
    except Exception:
        pass
    return "172.22.96.1"


def _cdp_base() -> str:
    return f"http://{_win_host()}:{_PROXY_PORT}"


def _get_tabs() -> list[dict] | None:
    try:
        r = requests.get(f"{_cdp_base()}/json", timeout=1)
        return r.json()
    except Exception as e:
        logger.warning("CDP not available at %s: %s", _cdp_base(), e)
        return None


def _navigate(ws_url: str, url: str) -> None:
    ws_url = ws_url.replace(f"127.0.0.1:{_CHROME_PORT}", f"{_win_host()}:{_PROXY_PORT}")
    ws = websocket.create_connection(ws_url, timeout=5)
    try:
        # Enable Page events so we can intercept the beforeunload dialog
        ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
        ws.recv()

        ws.send(json.dumps({"id": 2, "method": "Page.navigate", "params": {"url": url}}))

        # Wait for navigation response; auto-dismiss any "leave page?" dialog
        deadline = time.time() + 8
        while time.time() < deadline:
            ws.settimeout(max(0.1, deadline - time.time()))
            try:
                msg = json.loads(ws.recv())
            except websocket.WebSocketTimeoutException:
                break
            if msg.get("method") == "Page.javascriptDialogOpening":
                ws.send(json.dumps({
                    "id": 3,
                    "method": "Page.handleJavaScriptDialog",
                    "params": {"accept": True},
                }))
            elif msg.get("id") == 2:
                break
    finally:
        ws.close()


def _start_chrome(url: str) -> None:
    subprocess.run(
        [CMD_EXE, "/c", "start", "", _CHROME_EXE,
         f"--user-data-dir={_USER_DATA_DIR}",
         f"--remote-debugging-port={_CHROME_PORT}",
         "--remote-allow-origins=*",
         "--window-size=1200,800",
         "--window-position=360,140",
         f"--app={url}"],
        check=True,
        cwd="/mnt/c",
    )
    time.sleep(2)


_msg_id = 0


def _next_id() -> int:
    global _msg_id
    _msg_id += 1
    return _msg_id


def _cdp_eval(ws, expression: str, timeout: float = 20.0):
    """Run Runtime.evaluate (awaiting any returned promise) and return the JS value.

    Returns the serialized JS return value, or None on timeout/failure.
    """
    msg_id = _next_id()
    ws.send(json.dumps({
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        },
    }))
    deadline = time.time() + timeout
    while time.time() < deadline:
        ws.settimeout(max(0.1, deadline - time.time()))
        try:
            msg = json.loads(ws.recv())
        except websocket.WebSocketTimeoutException:
            break
        except Exception as e:
            logger.warning("_cdp_eval recv failed: %s", e)
            break
        if msg.get("id") == msg_id:
            return msg.get("result", {}).get("result", {}).get("value")
    return None


# --- Genuine UI automation for "add to queue" ---
# Each CDP eval is a stateless step; the Python side (add_to_queue) orchestrates and
# polls between them. We drive the in-app search box (SPA nav that does NOT reload the
# page or cut playback, unlike location.assign) and click the real context-menu item.
# Defensive at every gate: we never click the queue item unless the popup actually
# opened, and we only ever target a playable SONG/VIDEO row — never an album/artist
# card (whose "Agregar a la fila" would queue the whole album).

# Genuine search via the search box's own router methods. This performs a real
# SPA search (fetches fresh results) WITHOUT reloading the page or cutting playback
# — unlike location.assign, which pauses the audio.
_JS_SEARCH = r"""/*SEARCH*/
(function(query){
  const box = document.querySelector('ytmusic-search-box');
  if (!box || typeof box.setQuery !== 'function' || typeof box.navigateToQueryResults !== 'function') return false;
  box.setQuery(query);
  box.navigateToQueryResults();
  return true;
})(__QUERY__)
"""


def _js_search_ready(query: str) -> str:
    """True once the address bar's ?q= reflects the query (fresh results loaded)."""
    return (
        "/*READY*/(function(q){"
        "const cur = new URLSearchParams(location.search).get('q') || '';"
        "return cur.trim().toLowerCase() === q.trim().toLowerCase();"
        "})(" + json.dumps(query) + ")"
    )

# Row selection rule (shared by locate + open-menu). Preference:
#   1. a SONG/VIDEO row whose own play videoId == the ytmusicapi videoId (exact match);
#   2. otherwise the first SONG/VIDEO row (the top result for the query).
# Album/artist cards (browseEndpoint) are always skipped.
_PICK_ROW = r"""
  function __pickRow(vid){
    const rows = document.querySelectorAll('ytmusic-responsive-list-item-renderer');
    let firstSong = null;
    for (const row of rows) {
      const d = row.data || (row.__data && row.__data.data);
      if (!d) continue;
      if (d.navigationEndpoint && d.navigationEndpoint.browseEndpoint) continue;  // skip album/artist
      let ownVid = null;
      try { ownVid = d.overlay.musicItemThumbnailOverlayRenderer.content.musicPlayButtonRenderer.playNavigationEndpoint.watchEndpoint.videoId; } catch (e) {}
      if (!ownVid) continue;                 // must be a playable song/video row
      if (!firstSong) firstSong = row;       // fallback: top song result
      if (ownVid === vid) return row;        // preferred: exact ytmusicapi match
    }
    return firstSong;
  }
"""


def _js_locate(video_id: str) -> str:
    return (
        "/*LOCATE*/(function(vid){" + _PICK_ROW +
        "const r = __pickRow(vid);"
        "return r ? {found:true, title:(r.querySelector('.title')?.textContent||'').trim()} : {found:false};"
        "})(" + json.dumps(video_id) + ")"
    )


def _js_open_menu(video_id: str) -> str:
    return (
        "/*OPENMENU*/(function(vid){" + _PICK_ROW +
        "const r = __pickRow(vid);"
        "if (!r) return {ok:false, reason:'row-gone'};"
        "const b = r.querySelector('ytmusic-menu-renderer tp-yt-paper-icon-button')"
        " || r.querySelector('ytmusic-menu-renderer yt-button-shape button')"
        " || r.querySelector('ytmusic-menu-renderer button');"
        "if (!b) return {ok:false, reason:'no-menu-btn'};"
        "b.click(); return {ok:true};"
        "})(" + json.dumps(video_id) + ")"
    )


_JS_HAS_ITEMS = (
    "/*HASITEMS*/(function(){"
    "return document.querySelectorAll('ytmusic-menu-service-item-renderer').length > 0;"
    "})()"
)

_JS_CLICK_QUEUE = (
    "/*CLICKQ*/(function(){"
    "const els = document.querySelectorAll('ytmusic-menu-service-item-renderer');"
    "let target = null;"
    "for (const it of els){"
    "  const t = (it.textContent||'').trim().toLowerCase();"
    "  if (t.includes('agregar a la fila') || t.includes('add to queue')) { target = it; break; }"
    "}"
    "if (!target) return {ok:false, reason:'no-queue-item'};"
    "target.click(); return {ok:true, clicked:(target.textContent||'').trim()};"
    "})()"
)

_JS_CLOSE = (
    "/*CLOSE*/(function(){"
    "document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', keyCode:27, which:27, bubbles:true}));"
    "return true;"
    "})()"
)


def add_to_queue(video_id: str, query: str) -> bool:
    """Add a song to the existing YT Music queue via genuine UI automation.

    Types `query` into the open YT Music tab's search box, locates the top
    playable song row (preferring an exact `video_id` match, never an album/artist
    card), opens its context menu and clicks "Agregar a la fila".

    Returns True only if the menu item was found and clicked. Returns False if
    there is no YT Music tab, or if the UI flow could not be completed safely
    (search box missing, no song row, or the menu never opened).
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

    try:
        ws = websocket.create_connection(ws_url, timeout=5)
    except Exception as e:
        logger.warning("add_to_queue: cannot connect to CDP: %s", e)
        return False
    try:
        # 1. Genuine in-app search (keeps playback going).
        if _cdp_eval(ws, _JS_SEARCH.replace("__QUERY__", json.dumps(query))) is not True:
            logger.warning("add_to_queue: search box unavailable")
            return False

        # 2. Wait until the results page actually reflects this query, so we never
        #    act on stale rows left over from a previous search.
        for _ in range(20):  # up to ~6s
            time.sleep(0.3)
            if _cdp_eval(ws, _js_search_ready(query)) is True:
                break
        time.sleep(0.8)  # let the new result rows render

        # 3. Poll until a playable song row for this query renders.
        located = False
        for _ in range(20):  # up to ~8s
            time.sleep(0.4)
            res = _cdp_eval(ws, _js_locate(video_id))
            if isinstance(res, dict) and res.get("found"):
                located = True
                break
        if not located:
            logger.warning("add_to_queue: no song row found for %r", query)
            return False

        # 4. Open that row's context menu.
        res = _cdp_eval(ws, _js_open_menu(video_id))
        if not (isinstance(res, dict) and res.get("ok")):
            logger.warning("add_to_queue: could not open row menu (%s)", res)
            return False

        # 5. Confirm the popup actually opened BEFORE clicking anything.
        items_ready = False
        for _ in range(30):  # up to ~3s
            time.sleep(0.1)
            if _cdp_eval(ws, _JS_HAS_ITEMS) is True:
                items_ready = True
                break
        if not items_ready:
            _cdp_eval(ws, _JS_CLOSE)  # never click blindly; dismiss the (possibly) open menu
            logger.warning("add_to_queue: context menu did not open")
            return False

        # 6. Click the "Agregar a la fila" item.
        res = _cdp_eval(ws, _JS_CLICK_QUEUE)
        ok = isinstance(res, dict) and res.get("ok") is True
        if not ok:
            logger.warning("add_to_queue: queue item not clicked (%s)", res)
        return ok
    finally:
        try:
            ws.close()
        except Exception:
            pass


def open_or_navigate(url: str) -> None:
    """Navigate the existing YT Music window to url, or open Chrome if not running."""
    tabs = _get_tabs()

    if tabs is not None:
        yt_tab = next(
            (t for t in tabs
             if "music.youtube.com" in t.get("url", "") and t.get("type") == "page"),
            None,
        )
        if yt_tab:
            _navigate(yt_tab["webSocketDebuggerUrl"], url)
            return

        # Chrome up but no YT Music tab → open one via CDP
        try:
            requests.get(f"{_cdp_base()}/json/new?{url}", timeout=2)
            return
        except Exception:
            pass

    # Chrome not running → start with the song URL directly
    _start_chrome(url)

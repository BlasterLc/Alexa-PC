import json
import subprocess
import time

import requests
import websocket

from handlers.base import CMD_EXE

_PORT = 9222
_CDP_BASE = f"http://localhost:{_PORT}"


def _get_tabs() -> list[dict] | None:
    """Returns tab list if Chrome debug port is up, None otherwise."""
    try:
        r = requests.get(f"{_CDP_BASE}/json", timeout=1)
        return r.json()
    except Exception:
        return None


def _navigate(ws_url: str, url: str) -> None:
    ws = websocket.create_connection(ws_url, timeout=3)
    ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": url}}))
    ws.recv()
    ws.close()


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

        # Chrome has debug port but no YT Music tab → open one
        try:
            requests.get(f"{_CDP_BASE}/json/new?{url}", timeout=2)
            return
        except Exception:
            pass

    # Chrome not running with debug port → start it
    subprocess.run(
        [CMD_EXE, "/c", "start", "", "chrome.exe",
         f"--remote-debugging-port={_PORT}", f"--app={url}"],
        check=True,
    )
    # Give Chrome a moment to initialize the debug port for the next call
    time.sleep(2)

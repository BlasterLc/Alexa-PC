import json
import subprocess
import time

import requests
import websocket

from handlers.base import CMD_EXE

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
    except Exception:
        return None


def _navigate(ws_url: str, url: str) -> None:
    # ws_url from Chrome uses 127.0.0.1 — replace with Win host so WSL2 can reach it
    ws_url = ws_url.replace(f"127.0.0.1:{_CHROME_PORT}", f"{_win_host()}:{_PROXY_PORT}")
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

        # Chrome up but no YT Music tab → open one via CDP
        try:
            requests.get(f"{_cdp_base()}/json/new?{url}", timeout=2)
            return
        except Exception:
            pass

    # Chrome not running → start with separate profile and debug port
    subprocess.run(
        [CMD_EXE, "/c", "start", "", _CHROME_EXE,
         f"--user-data-dir={_USER_DATA_DIR}",
         f"--remote-debugging-port={_CHROME_PORT}",
         f"--app=https://music.youtube.com"],
        check=True,
    )
    time.sleep(2)

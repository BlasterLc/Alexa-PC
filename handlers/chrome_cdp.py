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

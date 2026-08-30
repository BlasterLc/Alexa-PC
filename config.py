import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SKILL_ID: str = os.environ["SKILL_ID"]
PORT: int = int(os.getenv("PORT", "8000"))

_apps_path = Path(__file__).parent / "apps.json"
# valor = exe suelto ("chrome.exe") o lista [exe, arg, ...] para lanzadores con args
APPS: dict[str, str | list[str]] = json.loads(_apps_path.read_text())

_urls_path = Path(__file__).parent / "urls.json"
URLS: dict[str, str] = json.loads(_urls_path.read_text())
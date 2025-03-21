import os
import json
import re
from pathlib import Path
from globals import download_status

USER_HOME = os.path.expanduser("~")
DOWNLOAD_DIR = Path(USER_HOME) / "/downloads"
STATUS_FILE = DOWNLOAD_DIR / "downloads.json"

def remove_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def save_downloads():
    with open(STATUS_FILE, "w") as f:
        json.dump(download_status["logs"], f, indent=4)

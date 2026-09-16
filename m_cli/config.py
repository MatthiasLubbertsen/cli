import json
import os
import sys
from pathlib import Path

APP_NAME = "m"

DEFAULT_COMMANDS = {
    "redeploy": {
        "description": "pull latest code and restart the docker compose stack",
        "run": ["docker compose down", "git pull", "docker compose up -d"],
    },
    "boot": {
        "description": "push boot.py to a connected micropython board",
        "run": "mpremote resume fs cp boot.py :boot.py",
    },
}


def config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / APP_NAME
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_NAME


def config_path() -> Path:
    return config_dir() / "commands.json"


def load_commands() -> dict:
    path = config_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULT_COMMANDS, indent=2) + "\n", encoding="utf-8")
        return dict(DEFAULT_COMMANDS)
    return json.loads(path.read_text(encoding="utf-8"))


def save_commands(commands: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8")

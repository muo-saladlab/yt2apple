import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "yt2apple"
CONFIG_FILE = CONFIG_DIR / "config.json"

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())

def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))

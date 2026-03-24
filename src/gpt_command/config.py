import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

APP_NAME = "gptc"
CONFIG_DIR = Path.home() / ".config" / APP_NAME
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_json_file(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if default is None:
        default = {}

    if not path.exists():
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json_file(path: Path, data: Dict[str, Any]) -> None:
    ensure_config_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.chmod(path, 0o600)


def load_config() -> Dict[str, Any]:
    return load_json_file(CONFIG_FILE, default={})


def save_config(data: Dict[str, Any]) -> None:
    save_json_file(CONFIG_FILE, data)


def get_api_key() -> Optional[str]:
    # 1순위: 환경변수
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        return env_key.strip()

    # 2순위: 로컬 설정 파일
    config = load_config()
    key = config.get("OPENAI_API_KEY")
    if isinstance(key, str) and key.strip():
        return key.strip()

    return None


def get_default_model() -> str:
    env_model = os.environ.get("OPENAI_MODEL")
    if env_model and env_model.strip():
        return env_model.strip()

    config = load_config()
    model = config.get("DEFAULT_MODEL")
    if isinstance(model, str) and model.strip():
        return model.strip()

    return "gpt-4.1"


def set_default_model(model: str) -> None:
    config = load_config()
    config["DEFAULT_MODEL"] = model
    save_config(config)
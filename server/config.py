import os, json
from pathlib import Path
from typing import Optional

SERVER_CFG_PATHS = [
    Path(os.getenv("QIBO_SERVER_CONFIG", "")) if os.getenv("QIBO_SERVER_CONFIG") else None,
    Path.home() / ".qibo_server.json",
    Path.cwd() / ".qibo_server.json",
]
SERVER_CFG_PATHS = [p for p in SERVER_CFG_PATHS if p is not None]

def _read_cfg_file() -> dict:
    for p in SERVER_CFG_PATHS:
        try:
            if p.exists():
                with open(p, "r") as f:
                    return json.load(f)
        except Exception:
            continue
    return {}

def _write_cfg_file(data: dict) -> None:
    target = None
    if os.getenv("QIBO_SERVER_CONFIG"):
        target = Path(os.getenv("QIBO_SERVER_CONFIG"))
    else:
        target = Path.home() / ".qibo_server.json"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: could not write server config: {e}")

class Config:
    DB_URI: str = "sqlite:///qibo.db"
    API_TOKEN: Optional[str] = None
    DEBUG: bool = False
    MAX_CONTENT_LENGTH: int = int(os.getenv("QIBO_MAX_UPLOAD_BYTES", str(500 * 1024 * 1024)))

    @classmethod
    def load(cls, cli_api_token: Optional[str] = None):
        cfg = _read_cfg_file()
        api_token = (cli_api_token or os.getenv("QIBO_API_TOKEN") or cfg.get("api_token") or None)
        db_uri = os.getenv("QIBO_DB_URI") or cfg.get("db_uri") or cls.DB_URI
        debug_env = os.getenv("QIBO_DEBUG", "0")
        debug_file = cfg.get("debug", False)
        debug = (debug_env in {"1","true","True","yes","on"}) or bool(debug_file)
        C = type("C", (), {})()
        C.DB_URI = db_uri
        C.API_TOKEN = api_token
        C.DEBUG = debug
        C.MAX_CONTENT_LENGTH = cls.MAX_CONTENT_LENGTH
        return C

    @staticmethod
    def persist(api_token: Optional[str] = None, db_uri: Optional[str] = None, debug: Optional[bool] = None):
        data = _read_cfg_file()
        if api_token is not None:
            data["api_token"] = api_token
        if db_uri is not None:
            data["db_uri"] = db_uri
        if debug is not None:
            data["debug"] = bool(debug)
        _write_cfg_file(data)

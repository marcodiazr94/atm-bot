"""Carga y valida config.json."""
import json
import os
from pathlib import Path

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config(path: str = None) -> dict:
    config_path = Path(path) if path else Path(os.environ.get("ATM_CONFIG", str(_DEFAULT_CONFIG_PATH)))
    if not config_path.exists():
        raise FileNotFoundError(
            f"No se encontró config.json en {config_path}. "
            "Copia config.example.json a config.json y rellena los valores."
        )
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)

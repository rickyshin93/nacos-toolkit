from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

_CONFIG_EXTENSIONS = [".json", ".yaml", ".yml"]


def find_local_config(*, file_name: str, file_path: str) -> str | None:
    dir_path = Path(file_path).resolve()
    for ext in _CONFIG_EXTENSIONS:
        config_path = dir_path / f"{file_name}{ext}"
        if config_path.exists():
            return str(config_path)
    return None


def parse_config_file(*, file_path: str) -> dict[str, Any]:
    p = Path(file_path)
    ext = p.suffix.lower()
    content = p.read_text(encoding="utf-8")

    if ext == ".json":
        return json.loads(content)
    if ext in (".yaml", ".yml"):
        return yaml.safe_load(content)
    raise ValueError(f"Unsupported file format: {ext}")


def get_local_config(*, file_name: str, file_path: str) -> dict[str, Any] | None:
    if not file_name:
        return None

    local_path = find_local_config(file_name=file_name, file_path=file_path)
    if not local_path:
        logger.warning(f"No local configuration found for {file_name}")
        return None

    return parse_config_file(file_path=local_path)

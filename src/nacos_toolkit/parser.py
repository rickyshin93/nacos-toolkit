from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

import yaml
from loguru import logger


class NacosParser(StrEnum):
    YAML = ".yml"
    JSON = ".json"


class ConfigParser:
    @staticmethod
    def parse(raw: str | dict, fmt: NacosParser) -> dict[str, Any]:
        try:
            if fmt == NacosParser.JSON:
                if isinstance(raw, str):
                    return json.loads(raw)
                return dict(raw)
            result = yaml.safe_load(raw)
            if not isinstance(result, dict):
                return {}
            return result
        except Exception:
            logger.warning("Failed to parse config, returning empty dict")
            return {}

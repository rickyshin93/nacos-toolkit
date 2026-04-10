from __future__ import annotations

import copy
from typing import Any


class ConfigMerger:
    @staticmethod
    def merge(base: dict[str, Any], custom: dict[str, Any] | None) -> dict[str, Any]:
        if custom is None:
            custom = {}
        return _deep_merge(copy.deepcopy(base), custom)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base

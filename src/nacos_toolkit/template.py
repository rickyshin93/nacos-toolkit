from __future__ import annotations

import re
from collections import deque
from typing import Any

_TEMPLATE_PATTERN = re.compile(r"\$\{([^}]+)\}")

MAX_RENDER_DEPTH = 5


def _get_nested_property(obj: Any, path: str) -> Any:
    keys = path.split(".")
    result = obj
    for key in keys:
        if result is None:
            return None
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return None
    return result


def _set_nested_property(obj: dict, path: str, value: Any) -> None:
    keys = path.split(".")
    current = obj
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


class TemplateEngine:
    @staticmethod
    def contains_template(text: str) -> bool:
        return bool(_TEMPLATE_PATTERN.search(text))

    @staticmethod
    def is_text_only(value: Any) -> bool:
        if not isinstance(value, str):
            return True
        return not _TEMPLATE_PATTERN.search(value)

    @staticmethod
    def render_text(text: str, context: dict[str, Any]) -> str:
        current = text
        for _ in range(MAX_RENDER_DEPTH):
            previous = current

            def _replace(m: re.Match) -> str:
                key = m.group(1)
                val = _get_nested_property(context, key)
                if val is None:
                    return m.group(0)
                return str(val)

            current = _TEMPLATE_PATTERN.sub(_replace, current)
            if current == previous:
                break
        return current

    @staticmethod
    def render(config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        # Extract all template params first
        params = _extract_template_params(config)
        enriched_context = {**context}

        # Resolve each param in context
        for param in params:
            val = _get_nested_property(context, param)
            while isinstance(val, str) and not TemplateEngine.is_text_only(val):
                new_val = TemplateEngine.render_text(val, context)
                if new_val == val:
                    break
                val = new_val
            _set_nested_property(enriched_context, param, val)

        # BFS traversal to render all string values
        root: dict[str, Any] = {**config}
        seen: set[int] = set()
        queue: deque[tuple[dict, str, Any]] = deque()
        queue.append((root, "", root))

        while queue:
            parent, key, value = queue.popleft()

            if isinstance(value, str):
                rendered = TemplateEngine.render_text(value, enriched_context)
                if key:
                    parent[key] = rendered
            elif isinstance(value, list):
                new_array = []
                for item in value:
                    if isinstance(item, str):
                        new_array.append(TemplateEngine.render_text(item, enriched_context))
                    elif isinstance(item, dict):
                        copy = {**item}
                        queue.append((copy, "", copy))
                        new_array.append(copy)
                    else:
                        new_array.append(item)
                if key:
                    parent[key] = new_array
            elif isinstance(value, dict):
                obj_id = id(value)
                if obj_id in seen:
                    continue
                seen.add(obj_id)
                for k, v in value.items():
                    queue.append((value, k, v))

        return root


def _extract_template_params(config: Any) -> set[str]:
    params: set[str] = set()

    def _traverse(obj: Any) -> None:
        if isinstance(obj, str):
            for m in _TEMPLATE_PATTERN.finditer(obj):
                params.add(m.group(1))
        elif isinstance(obj, list):
            for item in obj:
                _traverse(item)
        elif isinstance(obj, dict):
            for v in obj.values():
                _traverse(v)

    _traverse(config)
    return params

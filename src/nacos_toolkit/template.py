from __future__ import annotations

import copy
import re
from collections import deque
from typing import Any

_TEMPLATE_PATTERN = re.compile(r"\$\{([^}]+)\}")
# 整值占位符：整个字符串恰为单个 ${...}，无其它字面量。用于「引用即取值」语义。
_WHOLE_TEMPLATE_PATTERN = re.compile(r"^\$\{([^}]+)\}$")

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
    def render_value(value: str, context: dict[str, Any]) -> Any:
        """渲染单个字符串值，可能返回非字符串。

        当整个值恰为一个占位符 `${x}`（无其它字面量）且解析结果是容器（dict/list）时，
        返回该对象本身以保留结构与类型；否则退回 `render_text` 做字符串内文本替换。
        这让「`account: ${platform.gcp.account}`」这类整值引用拿到真正的 dict，
        而非 `str(dict)` 产生的 Python repr 字符串。标量（int/bool/str）仍按原文本替换语义。
        """
        match = _WHOLE_TEMPLATE_PATTERN.match(value)
        if match:
            resolved = _get_nested_property(context, match.group(1))
            if isinstance(resolved, (dict, list)):
                return resolved
        return TemplateEngine.render_text(value, context)

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

        # BFS traversal to render all string values。depth 仅在「整值占位符解析出容器后
        # 重新入队」时递增，用于给自引用容器（${a} 指向含 ${a} 的 dict）兜底，避免无限展开。
        root: dict[str, Any] = {**config}
        seen: set[int] = set()
        queue: deque[tuple[Any, Any, Any, int]] = deque()
        queue.append((root, "", root, 0))

        while queue:
            parent, key, value, depth = queue.popleft()

            if isinstance(value, str):
                rendered = TemplateEngine.render_value(value, enriched_context)
                if isinstance(rendered, (dict, list)) and depth < MAX_RENDER_DEPTH:
                    # 整值占位符解析出容器：deepcopy 后重新入队，递归渲染其内部占位符，
                    # 同时避免改动共享的 context 对象。
                    rendered = copy.deepcopy(rendered)
                    if key:
                        parent[key] = rendered
                    queue.append((parent, key, rendered, depth + 1))
                elif isinstance(rendered, (dict, list)):
                    # 超出深度：保留结构（deepcopy），不再展开内部占位符，防环。
                    if key:
                        parent[key] = copy.deepcopy(rendered)
                elif key:
                    parent[key] = rendered
            elif isinstance(value, list):
                new_array = []
                for item in value:
                    if isinstance(item, str):
                        new_array.append(TemplateEngine.render_text(item, enriched_context))
                    elif isinstance(item, dict):
                        item_copy = {**item}
                        queue.append((item_copy, "", item_copy, depth))
                        new_array.append(item_copy)
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
                    queue.append((value, k, v, depth))

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

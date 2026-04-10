from __future__ import annotations

from typing import Any

from nacos_toolkit.merger import ConfigMerger
from nacos_toolkit.parser import ConfigParser, NacosParser
from nacos_toolkit.template import TemplateEngine


class NacosConfigUtils:
    @staticmethod
    def process_configuration(
        raw_config: str | dict,
        *,
        fmt: NacosParser = NacosParser.YAML,
        external_vars: dict[str, Any] | None = None,
        convert_array_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        if external_vars is None:
            external_vars = {}
        if convert_array_fields is None:
            convert_array_fields = ["cors.whitelist"]

        parsed = ConfigParser.parse(raw_config, fmt)
        context = {**external_vars, **parsed}
        result = TemplateEngine.render(parsed, context)
        return NacosConfigUtils.convert_string_fields_to_arrays(result, convert_array_fields)

    @staticmethod
    def process_and_merge_custom_config(
        base_config: dict[str, Any],
        custom_config: str | dict,
        *,
        fmt: NacosParser = NacosParser.YAML,
        external_vars: dict[str, Any] | None = None,
        convert_array_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        processed_base = {**base_config}
        merged_vars = {**(external_vars or {}), **processed_base}

        processed_custom = NacosConfigUtils.process_configuration(
            custom_config,
            fmt=fmt,
            external_vars=merged_vars,
            convert_array_fields=convert_array_fields,
        )
        return ConfigMerger.merge(processed_base, processed_custom)

    @staticmethod
    def merge_configurations(base: dict[str, Any], custom: dict[str, Any] | None) -> dict[str, Any]:
        return ConfigMerger.merge(base, custom)

    @staticmethod
    def contains_template(text: str) -> bool:
        return TemplateEngine.contains_template(text)

    @staticmethod
    def convert_string_fields_to_arrays(config: dict[str, Any], field_paths: list[str]) -> dict[str, Any]:
        result = {**config}
        for path in field_paths:
            value = NacosConfigUtils.get_nested_property(result, path)
            if isinstance(value, str) and "," in value:
                NacosConfigUtils.set_nested_property(result, path, [item.strip() for item in value.split(",")])
        return result

    @staticmethod
    def get_nested_property(obj: Any, path: str) -> Any:
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

    @staticmethod
    def set_nested_property(obj: dict, path: str, value: Any) -> None:
        keys = path.split(".")
        current = obj
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

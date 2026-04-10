from __future__ import annotations

from typing import Any

import yaml
from loguru import logger

from nacos_toolkit.parser import NacosParser
from nacos_toolkit.utils import NacosConfigUtils


class NacosConfigManager:
    _instance: NacosConfigManager | None = None

    def __init__(self) -> None:
        self._client: Any = None
        self._config_cache: dict[str, Any] | None = None
        self._raw_config: dict[str, Any] | None = None

    @classmethod
    def get_instance(cls) -> NacosConfigManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _create_client(self, config: dict[str, str]) -> Any:
        import nacos

        return nacos.NacosClient(
            server_addresses=config["server_addr"],
            namespace=config["namespace"],
            username=config["username"],
            password=config["password"],
        )

    def _init_client(self, config: dict[str, str]) -> Any:
        if self._client is None:
            self._client = self._create_client(config)
        return self._client

    async def get_config(
        self,
        connection: dict[str, str],
        base_configs: list[dict[str, str]],
        override_config: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if self._config_cache is not None:
            return self._config_cache

        client = self._init_client(connection)

        try:
            config_contents: list[str] = []
            for cfg in base_configs:
                content = await client.get_config(cfg["data_id"], cfg["group"])
                config_contents.append(content)

            all_data: dict[str, Any] = {}
            for content in config_contents:
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict):
                    all_data.update(parsed)

            last_content = config_contents[-1]
            last_config = yaml.safe_load(last_content)
            if not isinstance(last_config, dict):
                last_config = {}

            self._raw_config = all_data

            self._config_cache = NacosConfigUtils.process_configuration(
                last_config,
                fmt=NacosParser.JSON,
                external_vars={**all_data, "DEPLOY_ENV": connection["namespace"]},
            )

            if override_config and override_config.get("data_id"):
                custom_content = await client.get_config(override_config["data_id"], override_config["group"])
                fmt = _determine_format(override_config["data_id"])
                self._config_cache = NacosConfigUtils.process_and_merge_custom_config(
                    self._config_cache,
                    custom_content,
                    fmt=fmt,
                    external_vars={**all_data, "DEPLOY_ENV": connection["namespace"]},
                )

            return self._config_cache

        except Exception as e:
            logger.error(f"Failed to fetch Nacos config: {e}")
            raise

    def clear_cache(self) -> None:
        self._config_cache = None
        self._raw_config = None

    def get_raw_config(self) -> dict[str, Any] | None:
        return self._raw_config


async def get_nacos_config(
    *,
    connection: dict[str, str],
    base_configs: list[dict[str, str]],
    override_config: dict[str, str] | None = None,
    debug: bool = False,
) -> dict[str, Any]:
    mgr = NacosConfigManager.get_instance()
    config = await mgr.get_config(connection, base_configs, override_config)
    result: dict[str, Any] = {"config": config}
    if debug:
        result["raw"] = mgr.get_raw_config()
    return result


def setup_config_listener(
    *,
    nacos_config: dict[str, str],
    listen_requests: list[dict[str, str]],
    callback: Any = None,
) -> None:
    mgr = NacosConfigManager.get_instance()
    client = mgr._init_client(nacos_config)

    for req in listen_requests:
        data_id = req["data_id"]
        group = req["group"]

        def _on_change(content: str, _data_id: str = data_id) -> None:
            logger.info(f"[Nacos] Config updated: {_data_id}")
            if callback:
                callback(content)
            else:
                parsed = yaml.safe_load(content)
                if isinstance(parsed, dict) and mgr._config_cache is not None:
                    mgr._config_cache.update(parsed)

        client.subscribe(data_id, group, _on_change)


def _determine_format(data_id: str) -> NacosParser:
    if data_id.endswith(".json"):
        return NacosParser.JSON
    return NacosParser.YAML

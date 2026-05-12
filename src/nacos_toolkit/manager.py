from __future__ import annotations

from typing import Any, Callable

import yaml
from loguru import logger
from v2.nacos import ClientConfigBuilder, ConfigParam, NacosConfigService

from nacos_toolkit.parser import NacosParser
from nacos_toolkit.utils import NacosConfigUtils


class NacosConfigManager:
    _instance: NacosConfigManager | None = None

    def __init__(self) -> None:
        self._config_service: NacosConfigService | None = None
        self._config_cache: dict[str, Any] | None = None
        self._raw_config: dict[str, Any] | None = None

    @classmethod
    def get_instance(cls) -> NacosConfigManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _create_config_service(self, config: dict[str, str]) -> NacosConfigService:
        client_config = (
            ClientConfigBuilder()
            .server_address(config["server_addr"])
            .namespace_id(config["namespace"])
            .username(config["username"])
            .password(config["password"])
            .build()
        )
        return await NacosConfigService.create_config_service(client_config)

    async def _init_config_service(self, config: dict[str, str]) -> NacosConfigService:
        if self._config_service is None:
            self._config_service = await self._create_config_service(config)
        return self._config_service

    async def get_config(
        self,
        connection: dict[str, str],
        base_configs: list[dict[str, str]],
        override_config: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if self._config_cache is not None:
            return self._config_cache

        service = await self._init_config_service(connection)

        try:
            config_contents: list[str] = []
            for cfg in base_configs:
                content = await service.get_config(ConfigParam(data_id=cfg["data_id"], group=cfg["group"]))
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
                custom_content = await service.get_config(
                    ConfigParam(data_id=override_config["data_id"], group=override_config["group"])
                )
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

    async def shutdown(self) -> None:
        if self._config_service is not None:
            await self._config_service.shutdown()
            self._config_service = None


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


async def setup_config_listener(
    *,
    nacos_config: dict[str, str],
    listen_requests: list[dict[str, str]],
    callback: Callable | None = None,
) -> None:
    mgr = NacosConfigManager.get_instance()
    service = await mgr._init_config_service(nacos_config)

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

        await service.add_listener(data_id, group, _on_change)


def _determine_format(data_id: str) -> NacosParser:
    if data_id.endswith(".json"):
        return NacosParser.JSON
    return NacosParser.YAML

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from nacos_toolkit.manager import NacosConfigManager, get_nacos_config, setup_config_listener


class TestNacosConfigManagerSingleton:
    def setup_method(self):
        NacosConfigManager._instance = None

    def test_singleton_returns_same_instance(self):
        a = NacosConfigManager.get_instance()
        b = NacosConfigManager.get_instance()
        assert a is b

    def test_clear_cache_resets(self):
        mgr = NacosConfigManager.get_instance()
        mgr._config_cache = {"key": "val"}
        mgr._raw_config = {"raw": True}
        mgr.clear_cache()
        assert mgr._config_cache is None
        assert mgr._raw_config is None


class TestGetNacosConfig:
    def setup_method(self):
        NacosConfigManager._instance = None

    @pytest.mark.asyncio
    async def test_fetches_and_processes_config(self):
        common_yaml = yaml.dump({"db_host": "mysql-server", "db_port": "3306"})
        env_yaml = yaml.dump({"env": "dev1"})
        app_yaml = yaml.dump({"host": "${db_host}", "port": 8080})

        mock_service = MagicMock()
        mock_service.get_config = AsyncMock(side_effect=[common_yaml, env_yaml, app_yaml])

        with patch.object(NacosConfigManager, "_create_config_service", return_value=mock_service):
            result = await get_nacos_config(
                connection={"server_addr": "localhost:8848", "namespace": "dev1", "username": "u", "password": "p"},
                base_configs=[
                    {"data_id": "common.yml", "group": "DEFAULT_GROUP"},
                    {"data_id": "env.yml", "group": "DEFAULT_GROUP"},
                    {"data_id": "app.yml", "group": "DEFAULT_GROUP"},
                ],
            )

        assert result["config"]["host"] == "mysql-server"
        assert result["config"]["port"] == 8080

    @pytest.mark.asyncio
    async def test_debug_mode_returns_raw(self):
        common_yaml = yaml.dump({"key": "value"})
        app_yaml = yaml.dump({"name": "app"})

        mock_service = MagicMock()
        mock_service.get_config = AsyncMock(side_effect=[common_yaml, app_yaml])

        with patch.object(NacosConfigManager, "_create_config_service", return_value=mock_service):
            result = await get_nacos_config(
                connection={"server_addr": "localhost:8848", "namespace": "dev", "username": "u", "password": "p"},
                base_configs=[
                    {"data_id": "common.yml", "group": "DEFAULT_GROUP"},
                    {"data_id": "app.yml", "group": "DEFAULT_GROUP"},
                ],
                debug=True,
            )

        assert "raw" in result
        assert result["raw"] is not None

    @pytest.mark.asyncio
    async def test_cached_config_returned_on_second_call(self):
        app_yaml = yaml.dump({"name": "app"})
        mock_service = MagicMock()
        mock_service.get_config = AsyncMock(return_value=app_yaml)

        with patch.object(NacosConfigManager, "_create_config_service", return_value=mock_service):
            conn = {"server_addr": "localhost:8848", "namespace": "dev", "username": "u", "password": "p"}
            configs = [{"data_id": "app.yml", "group": "DEFAULT_GROUP"}]
            r1 = await get_nacos_config(connection=conn, base_configs=configs)
            r2 = await get_nacos_config(connection=conn, base_configs=configs)

        assert r1["config"] == r2["config"]
        assert mock_service.get_config.await_count == 1

    @pytest.mark.asyncio
    async def test_override_config_merges(self):
        base_yaml = yaml.dump({"host": "localhost", "port": 3000})
        override_yaml = yaml.dump({"port": 9999, "extra": "yes"})

        mock_service = MagicMock()
        mock_service.get_config = AsyncMock(side_effect=[base_yaml, override_yaml])

        with patch.object(NacosConfigManager, "_create_config_service", return_value=mock_service):
            result = await get_nacos_config(
                connection={"server_addr": "localhost:8848", "namespace": "dev", "username": "u", "password": "p"},
                base_configs=[{"data_id": "app.yml", "group": "DEFAULT_GROUP"}],
                override_config={"data_id": "override.yml", "group": "DEFAULT_GROUP"},
            )

        assert result["config"]["host"] == "localhost"
        assert result["config"]["port"] == 9999
        assert result["config"]["extra"] == "yes"

    @pytest.mark.asyncio
    async def test_deploy_env_injected(self):
        app_yaml = yaml.dump({"env": "${DEPLOY_ENV}"})

        mock_service = MagicMock()
        mock_service.get_config = AsyncMock(return_value=app_yaml)

        with patch.object(NacosConfigManager, "_create_config_service", return_value=mock_service):
            result = await get_nacos_config(
                connection={
                    "server_addr": "localhost:8848", "namespace": "production",
                    "username": "u", "password": "p",
                },
                base_configs=[{"data_id": "app.yml", "group": "DEFAULT_GROUP"}],
            )

        assert result["config"]["env"] == "production"


class TestSetupConfigListener:
    def setup_method(self):
        NacosConfigManager._instance = None

    @pytest.mark.asyncio
    async def test_subscribes_to_configs(self):
        mock_service = MagicMock()
        mock_service.add_listener = AsyncMock()

        with patch.object(NacosConfigManager, "_create_config_service", return_value=mock_service):
            await setup_config_listener(
                nacos_config={"server_addr": "localhost:8848", "namespace": "dev", "username": "u", "password": "p"},
                listen_requests=[
                    {"data_id": "app.yml", "group": "DEFAULT_GROUP"},
                ],
            )

        mock_service.add_listener.assert_awaited_once()

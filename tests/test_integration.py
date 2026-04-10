"""Integration tests matching the Node.js yaml-array.test.ts test suite."""

from nacos_toolkit import NacosConfigUtils, NacosParser


class TestYamlArrayConfiguration:
    """Matches the Node.js yaml-array.test.ts test cases exactly."""

    def test_preserve_array_types_in_yaml(self):
        yaml_config = """
cors:
  whitelist:
    - http://localhost:8000
    - http://example.com
logLevel: info
"""
        result = NacosConfigUtils.process_configuration(yaml_config, fmt=NacosParser.YAML)
        assert isinstance(result["cors"]["whitelist"], list)
        assert result["cors"]["whitelist"] == ["http://localhost:8000", "http://example.com"]
        assert result["logLevel"] == "info"

    def test_arrays_with_template_variables(self):
        yaml_config = """
cors:
  whitelist:
    - ${BASE_URL}
    - http://localhost:8000
    - ${CUSTOM_DOMAIN}
"""
        result = NacosConfigUtils.process_configuration(
            yaml_config,
            fmt=NacosParser.YAML,
            external_vars={"BASE_URL": "http://example.com", "CUSTOM_DOMAIN": "http://custom.com"},
        )
        assert isinstance(result["cors"]["whitelist"], list)
        assert result["cors"]["whitelist"] == [
            "http://example.com",
            "http://localhost:8000",
            "http://custom.com",
        ]

    def test_mixed_types(self):
        yaml_config = """
features:
  apis:
    - name: user
      endpoints: ["/api/user", "/api/profile"]
    - name: auth
      endpoints: ["/api/login", "/api/logout"]
  enabled: true
  count: 42
"""
        result = NacosConfigUtils.process_configuration(yaml_config, fmt=NacosParser.YAML)
        assert isinstance(result["features"]["apis"], list)
        assert len(result["features"]["apis"]) == 2
        assert isinstance(result["features"]["apis"][0]["endpoints"], list)
        assert result["features"]["apis"][0]["endpoints"] == ["/api/user", "/api/profile"]
        assert result["features"]["enabled"] is True
        assert result["features"]["count"] == 42

    def test_real_whitelist_issue(self):
        yaml_config = """
cors:
  whitelist:
    - http://web-app-dev.dev1.eks.example.com
    - http://localhost:8000
"""
        result = NacosConfigUtils.process_configuration(yaml_config, fmt=NacosParser.YAML)
        assert isinstance(result["cors"]["whitelist"], list)
        assert result["cors"]["whitelist"] == [
            "http://web-app-dev.dev1.eks.example.com",
            "http://localhost:8000",
        ]


class TestFullPipeline:
    def test_end_to_end_config_processing(self):
        common_yaml = """
REDIS_HOSTNAME: master.redis.example.com
REDIS_PORT: "6379"
REDIS_PASSWORD: test-password-placeholder
"""
        app_yaml = """
logLevel: info
debugMode: false
redis:
  database: 0
  hostname: ${REDIS_HOSTNAME}
  port: ${REDIS_PORT}
  password: ${REDIS_PASSWORD}
cors:
  enabled: "true"
  whitelist:
    - http://base-web.dev.example.com
    - http://localhost:8000
  credentials: "true"
serverOptions:
  proxyTimeout: "60000"
  timeout: "60000"
"""
        import yaml

        common = yaml.safe_load(common_yaml)
        result = NacosConfigUtils.process_configuration(
            app_yaml,
            external_vars={**common, "DEPLOY_ENV": "dev1"},
        )

        assert result["logLevel"] == "info"
        assert result["debugMode"] is False
        assert result["redis"]["hostname"] == "master.redis.example.com"
        assert result["redis"]["port"] == "6379"
        assert result["redis"]["database"] == 0
        assert isinstance(result["cors"]["whitelist"], list)
        assert len(result["cors"]["whitelist"]) == 2

    def test_end_to_end_with_override(self):
        base_config = {
            "host": "localhost",
            "port": 3000,
            "cors": {"whitelist": ["http://a.com"]},
        }
        override_yaml = """
port: 9999
cors:
  whitelist:
    - http://b.com
    - http://c.com
"""
        result = NacosConfigUtils.process_and_merge_custom_config(base_config, override_yaml)
        assert result["host"] == "localhost"
        assert result["port"] == 9999
        assert result["cors"]["whitelist"] == ["http://b.com", "http://c.com"]


class TestImports:
    def test_all_public_api_importable(self):
        from nacos_toolkit import (
            NacosParser,
        )

        assert NacosParser.YAML == ".yml"
        assert NacosParser.JSON == ".json"

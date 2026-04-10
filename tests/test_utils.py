from nacos_toolkit.parser import NacosParser
from nacos_toolkit.utils import NacosConfigUtils


class TestGetNestedProperty:
    def test_simple_key(self):
        assert NacosConfigUtils.get_nested_property({"a": 1}, "a") == 1

    def test_nested_key(self):
        assert NacosConfigUtils.get_nested_property({"a": {"b": 2}}, "a.b") == 2

    def test_missing_key(self):
        assert NacosConfigUtils.get_nested_property({"a": 1}, "b") is None

    def test_deeply_nested(self):
        obj = {"a": {"b": {"c": {"d": 42}}}}
        assert NacosConfigUtils.get_nested_property(obj, "a.b.c.d") == 42

    def test_none_intermediate(self):
        assert NacosConfigUtils.get_nested_property({"a": None}, "a.b") is None


class TestSetNestedProperty:
    def test_simple_set(self):
        obj = {}
        NacosConfigUtils.set_nested_property(obj, "a", 1)
        assert obj == {"a": 1}

    def test_nested_set(self):
        obj = {}
        NacosConfigUtils.set_nested_property(obj, "a.b", 2)
        assert obj == {"a": {"b": 2}}

    def test_overwrite_existing(self):
        obj = {"a": {"b": 1}}
        NacosConfigUtils.set_nested_property(obj, "a.b", 99)
        assert obj == {"a": {"b": 99}}


class TestConvertStringFieldsToArrays:
    def test_converts_comma_separated_string(self):
        config = {"cors": {"whitelist": "http://a.com, http://b.com"}}
        result = NacosConfigUtils.convert_string_fields_to_arrays(config, ["cors.whitelist"])
        assert result["cors"]["whitelist"] == ["http://a.com", "http://b.com"]

    def test_no_comma_keeps_string(self):
        config = {"cors": {"whitelist": "http://a.com"}}
        result = NacosConfigUtils.convert_string_fields_to_arrays(config, ["cors.whitelist"])
        assert result["cors"]["whitelist"] == "http://a.com"

    def test_already_array_unchanged(self):
        config = {"cors": {"whitelist": ["http://a.com", "http://b.com"]}}
        result = NacosConfigUtils.convert_string_fields_to_arrays(config, ["cors.whitelist"])
        assert result["cors"]["whitelist"] == ["http://a.com", "http://b.com"]

    def test_missing_field_no_error(self):
        config = {"other": "value"}
        result = NacosConfigUtils.convert_string_fields_to_arrays(config, ["cors.whitelist"])
        assert result == {"other": "value"}

    def test_trims_whitespace(self):
        config = {"tags": "a , b , c"}
        result = NacosConfigUtils.convert_string_fields_to_arrays(config, ["tags"])
        assert result["tags"] == ["a", "b", "c"]


class TestProcessConfiguration:
    def test_basic_yaml_processing(self):
        yaml_str = "name: test\nport: 8080"
        result = NacosConfigUtils.process_configuration(yaml_str)
        assert result == {"name": "test", "port": 8080}

    def test_yaml_with_template_vars(self):
        yaml_str = "host: ${HOST}\nport: 3000"
        result = NacosConfigUtils.process_configuration(yaml_str, external_vars={"HOST": "localhost"})
        assert result["host"] == "localhost"
        assert result["port"] == 3000

    def test_json_processing(self):
        json_str = '{"name": "test"}'
        result = NacosConfigUtils.process_configuration(json_str, fmt=NacosParser.JSON)
        assert result == {"name": "test"}

    def test_self_referencing_variables(self):
        yaml_str = "host: localhost\nurl: http://${host}:8080"
        result = NacosConfigUtils.process_configuration(yaml_str)
        assert result["url"] == "http://localhost:8080"

    def test_default_cors_whitelist_conversion(self):
        yaml_str = "cors:\n  whitelist: 'http://a.com, http://b.com'"
        result = NacosConfigUtils.process_configuration(yaml_str)
        assert result["cors"]["whitelist"] == ["http://a.com", "http://b.com"]

    def test_preserves_yaml_arrays(self):
        yaml_str = "cors:\n  whitelist:\n    - http://localhost:8000\n    - http://example.com\nlogLevel: info"
        result = NacosConfigUtils.process_configuration(yaml_str)
        assert isinstance(result["cors"]["whitelist"], list)
        assert result["cors"]["whitelist"] == ["http://localhost:8000", "http://example.com"]
        assert result["logLevel"] == "info"

    def test_arrays_with_template_variables(self):
        yaml_str = "cors:\n  whitelist:\n    - ${BASE_URL}\n    - http://localhost:8000\n    - ${CUSTOM_DOMAIN}"
        result = NacosConfigUtils.process_configuration(
            yaml_str,
            external_vars={"BASE_URL": "http://example.com", "CUSTOM_DOMAIN": "http://custom.com"},
        )
        assert isinstance(result["cors"]["whitelist"], list)
        assert result["cors"]["whitelist"] == [
            "http://example.com",
            "http://localhost:8000",
            "http://custom.com",
        ]

    def test_mixed_types(self):
        yaml_str = """
features:
  apis:
    - name: user
      endpoints: ["/api/user", "/api/profile"]
    - name: auth
      endpoints: ["/api/login", "/api/logout"]
  enabled: true
  count: 42
"""
        result = NacosConfigUtils.process_configuration(yaml_str)
        assert isinstance(result["features"]["apis"], list)
        assert len(result["features"]["apis"]) == 2
        assert isinstance(result["features"]["apis"][0]["endpoints"], list)
        assert result["features"]["apis"][0]["endpoints"] == ["/api/user", "/api/profile"]
        assert result["features"]["enabled"] is True
        assert result["features"]["count"] == 42

    def test_real_whitelist_issue(self):
        yaml_str = "cors:\n  whitelist:\n    - http://web-app-dev.dev1.eks.example.com\n    - http://localhost:8000"
        result = NacosConfigUtils.process_configuration(yaml_str)
        assert isinstance(result["cors"]["whitelist"], list)
        assert result["cors"]["whitelist"] == [
            "http://web-app-dev.dev1.eks.example.com",
            "http://localhost:8000",
        ]


class TestProcessAndMergeCustomConfig:
    def test_merge_custom_overrides_base(self):
        base = {"host": "localhost", "port": 3000}
        custom_yaml = "port: 8080\nnewKey: value"
        result = NacosConfigUtils.process_and_merge_custom_config(base, custom_yaml)
        assert result["host"] == "localhost"
        assert result["port"] == 8080
        assert result["newKey"] == "value"

    def test_custom_can_use_base_vars(self):
        base = {"host": "localhost", "port": 3000}
        custom_yaml = "url: http://${host}:${port}"
        result = NacosConfigUtils.process_and_merge_custom_config(base, custom_yaml)
        assert result["url"] == "http://localhost:3000"

    def test_external_vars_available(self):
        base = {"host": "localhost"}
        custom_yaml = "env: ${DEPLOY_ENV}"
        result = NacosConfigUtils.process_and_merge_custom_config(
            base, custom_yaml, external_vars={"DEPLOY_ENV": "production"}
        )
        assert result["env"] == "production"

    def test_json_custom_config(self):
        base = {"a": 1}
        custom_json = '{"b": 2}'
        result = NacosConfigUtils.process_and_merge_custom_config(base, custom_json, fmt=NacosParser.JSON)
        assert result == {"a": 1, "b": 2}


class TestMergeConfigurations:
    def test_delegates_to_merger(self):
        result = NacosConfigUtils.merge_configurations({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

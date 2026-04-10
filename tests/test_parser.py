
from nacos_toolkit.parser import ConfigParser, NacosParser


class TestConfigParser:
    def test_parse_yaml_string(self):
        yaml_str = "name: test\nport: 8080"
        result = ConfigParser.parse(yaml_str, NacosParser.YAML)
        assert result == {"name": "test", "port": 8080}

    def test_parse_json_string(self):
        json_str = '{"name": "test", "port": 8080}'
        result = ConfigParser.parse(json_str, NacosParser.JSON)
        assert result == {"name": "test", "port": 8080}

    def test_parse_json_object(self):
        obj = {"name": "test", "port": 8080}
        result = ConfigParser.parse(obj, NacosParser.JSON)
        assert result == {"name": "test", "port": 8080}

    def test_parse_yaml_with_nested(self):
        yaml_str = "server:\n  host: localhost\n  port: 3000"
        result = ConfigParser.parse(yaml_str, NacosParser.YAML)
        assert result == {"server": {"host": "localhost", "port": 3000}}

    def test_parse_yaml_with_array(self):
        yaml_str = "items:\n  - a\n  - b\n  - c"
        result = ConfigParser.parse(yaml_str, NacosParser.YAML)
        assert result == {"items": ["a", "b", "c"]}

    def test_parse_invalid_yaml_returns_empty(self):
        result = ConfigParser.parse(":::invalid", NacosParser.YAML)
        assert result == {}

    def test_parse_invalid_json_returns_empty(self):
        result = ConfigParser.parse("{invalid}", NacosParser.JSON)
        assert result == {}


class TestNacosParser:
    def test_yaml_value(self):
        assert NacosParser.YAML == ".yml"

    def test_json_value(self):
        assert NacosParser.JSON == ".json"

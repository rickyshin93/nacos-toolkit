import json

import yaml

from nacos_toolkit.local_config import find_local_config, get_local_config, parse_config_file


class TestFindLocalConfig:
    def test_finds_json_file(self, tmp_path):
        (tmp_path / "app.json").write_text("{}")
        result = find_local_config(file_name="app", file_path=str(tmp_path))
        assert result is not None
        assert result.endswith("app.json")

    def test_finds_yaml_file(self, tmp_path):
        (tmp_path / "app.yaml").write_text("name: test")
        result = find_local_config(file_name="app", file_path=str(tmp_path))
        assert result is not None
        assert result.endswith("app.yaml")

    def test_finds_yml_file(self, tmp_path):
        (tmp_path / "app.yml").write_text("name: test")
        result = find_local_config(file_name="app", file_path=str(tmp_path))
        assert result is not None
        assert result.endswith("app.yml")

    def test_json_has_priority_over_yaml(self, tmp_path):
        (tmp_path / "app.json").write_text("{}")
        (tmp_path / "app.yaml").write_text("name: test")
        result = find_local_config(file_name="app", file_path=str(tmp_path))
        assert result.endswith("app.json")

    def test_returns_none_when_not_found(self, tmp_path):
        result = find_local_config(file_name="missing", file_path=str(tmp_path))
        assert result is None


class TestParseConfigFile:
    def test_parse_json_file(self, tmp_path):
        f = tmp_path / "config.json"
        f.write_text(json.dumps({"name": "test", "port": 8080}))
        result = parse_config_file(file_path=str(f))
        assert result == {"name": "test", "port": 8080}

    def test_parse_yaml_file(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text(yaml.dump({"name": "test", "port": 8080}))
        result = parse_config_file(file_path=str(f))
        assert result == {"name": "test", "port": 8080}

    def test_parse_yml_file(self, tmp_path):
        f = tmp_path / "config.yml"
        f.write_text(yaml.dump({"items": [1, 2, 3]}))
        result = parse_config_file(file_path=str(f))
        assert result == {"items": [1, 2, 3]}

    def test_unsupported_format_raises(self, tmp_path):
        f = tmp_path / "config.txt"
        f.write_text("hello")
        import pytest

        with pytest.raises(ValueError, match="Unsupported"):
            parse_config_file(file_path=str(f))


class TestGetLocalConfig:
    def test_reads_existing_config(self, tmp_path):
        f = tmp_path / "app.json"
        f.write_text(json.dumps({"key": "value"}))
        result = get_local_config(file_name="app", file_path=str(tmp_path))
        assert result == {"key": "value"}

    def test_returns_none_when_not_found(self, tmp_path):
        result = get_local_config(file_name="missing", file_path=str(tmp_path))
        assert result is None

    def test_returns_none_when_empty_filename(self, tmp_path):
        result = get_local_config(file_name="", file_path=str(tmp_path))
        assert result is None

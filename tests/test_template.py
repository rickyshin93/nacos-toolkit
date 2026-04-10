from nacos_toolkit.template import TemplateEngine


class TestContainsTemplate:
    def test_detects_template_expression(self):
        assert TemplateEngine.contains_template("${HOST}") is True

    def test_no_template(self):
        assert TemplateEngine.contains_template("just text") is False

    def test_template_in_mixed_text(self):
        assert TemplateEngine.contains_template("http://${HOST}:${PORT}") is True

    def test_empty_string(self):
        assert TemplateEngine.contains_template("") is False


class TestIsTextOnly:
    def test_plain_text_is_text_only(self):
        assert TemplateEngine.is_text_only("hello") is True

    def test_non_string_is_text_only(self):
        assert TemplateEngine.is_text_only(123) is True

    def test_template_is_not_text_only(self):
        assert TemplateEngine.is_text_only("${VAR}") is False

    def test_mixed_text_is_not_text_only(self):
        assert TemplateEngine.is_text_only("http://${HOST}") is False


class TestRenderText:
    def test_simple_variable_substitution(self):
        result = TemplateEngine.render_text("${HOST}", {"HOST": "localhost"})
        assert result == "localhost"

    def test_multiple_variables(self):
        result = TemplateEngine.render_text("${HOST}:${PORT}", {"HOST": "localhost", "PORT": "8080"})
        assert result == "localhost:8080"

    def test_undefined_variable_keeps_original(self):
        result = TemplateEngine.render_text("${UNKNOWN}", {})
        assert result == "${UNKNOWN}"

    def test_nested_variable_resolution(self):
        context = {"URL": "${HOST}:${PORT}", "HOST": "localhost", "PORT": "3000"}
        result = TemplateEngine.render_text("${URL}", context)
        assert result == "localhost:3000"

    def test_max_render_depth_prevents_infinite_loop(self):
        context = {"A": "${B}", "B": "${A}"}
        result = TemplateEngine.render_text("${A}", context)
        assert isinstance(result, str)


class TestRender:
    def test_render_simple_config(self):
        config = {"host": "${HOST}", "port": "${PORT}"}
        context = {"HOST": "localhost", "PORT": "8080"}
        result = TemplateEngine.render(config, context)
        assert result["host"] == "localhost"
        assert result["port"] == "8080"

    def test_render_nested_config(self):
        config = {"server": {"host": "${HOST}", "port": 3000}}
        context = {"HOST": "localhost"}
        result = TemplateEngine.render(config, context)
        assert result["server"]["host"] == "localhost"
        assert result["server"]["port"] == 3000

    def test_render_preserves_arrays(self):
        config = {"whitelist": ["http://a.com", "http://b.com"]}
        result = TemplateEngine.render(config, {})
        assert isinstance(result["whitelist"], list)
        assert result["whitelist"] == ["http://a.com", "http://b.com"]

    def test_render_templates_in_array_items(self):
        config = {"urls": ["${BASE_URL}", "http://localhost"]}
        context = {"BASE_URL": "http://example.com"}
        result = TemplateEngine.render(config, context)
        assert result["urls"] == ["http://example.com", "http://localhost"]

    def test_render_objects_in_array(self):
        config = {"apis": [{"url": "${API_HOST}/users"}]}
        context = {"API_HOST": "http://api.com"}
        result = TemplateEngine.render(config, context)
        assert result["apis"][0]["url"] == "http://api.com/users"

    def test_render_with_nested_template_references(self):
        config = {"full_url": "${URL}"}
        context = {"URL": "${PROTO}://${HOST}", "PROTO": "https", "HOST": "example.com"}
        result = TemplateEngine.render(config, context)
        assert result["full_url"] == "https://example.com"

    def test_render_preserves_non_string_values(self):
        config = {"enabled": True, "count": 42, "name": "${NAME}"}
        context = {"NAME": "test"}
        result = TemplateEngine.render(config, context)
        assert result["enabled"] is True
        assert result["count"] == 42
        assert result["name"] == "test"

    def test_render_does_not_mutate_original(self):
        config = {"host": "${HOST}"}
        context = {"HOST": "localhost"}
        result = TemplateEngine.render(config, context)
        assert result["host"] == "localhost"
        assert config["host"] == "${HOST}"

    def test_render_enriches_context_with_resolved_params(self):
        config = {"db_url": "${DB_HOST}:${DB_PORT}"}
        context = {"DB_HOST": "mysql-server", "DB_PORT": "3306"}
        result = TemplateEngine.render(config, context)
        assert result["db_url"] == "mysql-server:3306"

    def test_render_handles_dot_notation_in_context(self):
        config = {"url": "${api.host}"}
        context = {"api": {"host": "http://api.com"}}
        result = TemplateEngine.render(config, context)
        assert result["url"] == "http://api.com"

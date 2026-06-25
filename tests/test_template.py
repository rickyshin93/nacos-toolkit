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


class TestRenderValue:
    """整值占位符 `${x}` 引用容器时应保留类型，而非 str(dict) 成 repr 字符串。"""

    def test_whole_placeholder_to_dict_preserves_dict(self):
        result = TemplateEngine.render_value("${gcp.account}", {"gcp": {"account": {"project_id": "p"}}})
        assert result == {"project_id": "p"}
        assert isinstance(result, dict)

    def test_whole_placeholder_to_list_preserves_list(self):
        result = TemplateEngine.render_value("${kb_list}", {"kb_list": ["a", "b"]})
        assert result == ["a", "b"]
        assert isinstance(result, list)

    def test_whole_placeholder_to_string_substitutes(self):
        result = TemplateEngine.render_value("${host}", {"host": "localhost"})
        assert result == "localhost"

    def test_scalar_placeholder_keeps_text_substitution(self):
        # 标量仍走文本替换语义（保持原行为，最小化对消费端的影响）
        result = TemplateEngine.render_value("${port}", {"port": 8080})
        assert result == "8080"

    def test_embedded_placeholder_not_treated_as_whole(self):
        # 非整值（含其它字面量）即便引用 dict 也只能字符串替换
        result = TemplateEngine.render_value("x-${gcp}", {"gcp": {"a": 1}})
        assert isinstance(result, str)

    def test_undefined_whole_placeholder_keeps_original(self):
        assert TemplateEngine.render_value("${missing}", {}) == "${missing}"


class TestRenderContainerSubstitution:
    """render() 全流程：整值占位符引用 dict/list 时落进配置树并保留类型。"""

    def test_render_account_dict_via_whole_placeholder(self):
        config = {"gcp": {"account": "${platform.gcp.account}"}}
        context = {"platform": {"gcp": {"account": {"type": "service_account", "project_id": "bigdata"}}}}
        result = TemplateEngine.render(config, context)
        assert result["gcp"]["account"] == {"type": "service_account", "project_id": "bigdata"}

    def test_render_list_via_whole_placeholder(self):
        config = {"kb_list": "${platform.kb_list}"}
        context = {"platform": {"kb_list": ["medical", "diagnosis"]}}
        result = TemplateEngine.render(config, context)
        assert result["kb_list"] == ["medical", "diagnosis"]

    def test_render_inner_placeholders_of_substituted_dict(self):
        # 被引用的 dict 内部还有占位符时，应继续渲染
        config = {"open_api": "${platform.open_api}"}
        context = {
            "platform": {"open_api": {"base_url": "http://${DEPLOY_ENV}.example.com", "is_action": False}},
            "DEPLOY_ENV": "test3",
        }
        result = TemplateEngine.render(config, context)
        assert result["open_api"]["base_url"] == "http://test3.example.com"
        assert result["open_api"]["is_action"] is False

    def test_render_self_referential_container_terminates(self):
        # ${a} 指向含 ${a} 的 dict —— 深度兜底应让渲染终止而非死循环/爆栈
        config = {"x": "${a}"}
        context = {"a": {"inner": "${a}"}}
        result = TemplateEngine.render(config, context)
        assert isinstance(result["x"], dict)  # 结构保留，未死循环

    def test_render_does_not_mutate_context_container(self):
        ctx_account = {"project_id": "p"}
        context = {"platform": {"account": ctx_account}}
        config = {"a": "${platform.account}", "b": "${platform.account}"}
        result = TemplateEngine.render(config, context)
        result["a"]["project_id"] = "changed"
        # 改 result 不应回写 context（deepcopy 隔离），且两处互不影响
        assert ctx_account["project_id"] == "p"
        assert result["b"]["project_id"] == "p"

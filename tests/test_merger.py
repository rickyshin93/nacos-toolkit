from nacos_toolkit.merger import ConfigMerger


class TestConfigMerger:
    def test_merge_flat_objects(self):
        base = {"a": 1, "b": 2}
        custom = {"b": 3, "c": 4}
        result = ConfigMerger.merge(base, custom)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_objects(self):
        base = {"server": {"host": "localhost", "port": 3000}}
        custom = {"server": {"port": 8080}}
        result = ConfigMerger.merge(base, custom)
        assert result == {"server": {"host": "localhost", "port": 8080}}

    def test_arrays_are_replaced_not_merged(self):
        base = {"items": [1, 2, 3]}
        custom = {"items": [4, 5]}
        result = ConfigMerger.merge(base, custom)
        assert result == {"items": [4, 5]}

    def test_merge_with_none_custom(self):
        base = {"a": 1}
        result = ConfigMerger.merge(base, None)
        assert result == {"a": 1}

    def test_merge_does_not_mutate_originals(self):
        base = {"a": 1, "nested": {"x": 1}}
        custom = {"nested": {"y": 2}}
        result = ConfigMerger.merge(base, custom)
        assert result["nested"] == {"x": 1, "y": 2}
        assert base["nested"] == {"x": 1}

    def test_merge_deeply_nested(self):
        base = {"a": {"b": {"c": 1, "d": 2}}}
        custom = {"a": {"b": {"c": 99}}}
        result = ConfigMerger.merge(base, custom)
        assert result == {"a": {"b": {"c": 99, "d": 2}}}

    def test_merge_empty_custom(self):
        base = {"a": 1}
        result = ConfigMerger.merge(base, {})
        assert result == {"a": 1}

    def test_merge_empty_base(self):
        result = ConfigMerger.merge({}, {"a": 1})
        assert result == {"a": 1}

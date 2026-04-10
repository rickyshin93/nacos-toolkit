# nacos-toolkit

**English** | [中文](./README.zh-CN.md)

An AI-native Python toolkit for Nacos configuration parsing and management.

## Highlights

- **AI-Native** — Ships with [`llms.txt`](./llms.txt) for instant agent comprehension, letting AI coding assistants understand and use the API without reading source code
- **Agent-Ready** — [`AGENTS.md`](./AGENTS.md) guides AI contributors on architecture, data flow, and conventions
- **Template Engine** — `${VAR}` syntax with dot-notation, recursive resolution, and cycle protection
- **Deep Merge** — Merge multiple YAML/JSON configs with intuitive dict-merge and array-replace semantics
- **Async Nacos Client** — Fetch, cache, and listen for config changes from Nacos server
- **Zero Config** — Sensible defaults, works out of the box with a single function call

## Installation

```bash
uv add nacos-toolkit
```

Or with pip:

```bash
pip install nacos-toolkit
```

## Quick Start

### Fetch Config from Nacos

```python
import asyncio
from nacos_toolkit import get_nacos_config

async def main():
    result = await get_nacos_config(
        connection={
            "server_addr": "nacos-server:8848",
            "namespace": "production",
            "username": "nacos",
            "password": "nacos",
        },
        base_configs=[
            {"data_id": "common.yml", "group": "DEFAULT_GROUP"},
            {"data_id": "app.yml", "group": "DEFAULT_GROUP"},
        ],
    )
    print(result["config"])

asyncio.run(main())
```

**How it works:**

1. Fetches all `base_configs` in order
2. Shallow-merges them into a single variable context
3. Processes only the **last** config, rendering `${VAR}` templates against the merged context
4. Auto-injects `DEPLOY_ENV = namespace`

### With Override Config

```python
result = await get_nacos_config(
    connection={...},
    base_configs=[
        {"data_id": "common.yml", "group": "DEFAULT_GROUP"},
        {"data_id": "app.yml", "group": "DEFAULT_GROUP"},
    ],
    override_config={
        "data_id": "app-customized.yml",
        "group": "DEFAULT_GROUP",
    },
)
```

The override config is deep-merged on top of the base config. Override values take precedence.

### Debug Mode

```python
result = await get_nacos_config(
    connection={...},
    base_configs=[...],
    debug=True,
)
print(result["config"])  # Processed config
print(result["raw"])     # Merged raw config (before template rendering)
```

## Config Processing

### Process YAML/JSON Configs

```python
from nacos_toolkit import NacosConfigUtils, NacosParser

# Process YAML config (default format)
config = NacosConfigUtils.process_configuration(
    """
    server:
      host: ${HOST}
      port: ${PORT}
    database:
      url: ${DB_HOST}:3306
    """,
    external_vars={
        "HOST": "localhost",
        "PORT": "8080",
        "DB_HOST": "mysql-server",
    },
)
# config = {"server": {"host": "localhost", "port": "8080"}, "database": {"url": "mysql-server:3306"}}

# Process JSON config
config = NacosConfigUtils.process_configuration(
    '{"name": "${APP_NAME}"}',
    fmt=NacosParser.JSON,
    external_vars={"APP_NAME": "my-app"},
)
```

**Template features:**

- `${VAR}` syntax
- Dot-notation nested references: `${redis.hostname}`
- Recursive template resolution: `${URL}` -> `${PROTO}://${HOST}` -> `https://example.com`
- Max resolution depth of 5 to prevent infinite loops
- Undefined variables are left as-is: `${UNKNOWN}`

### Merge Custom Config

```python
base = {"host": "localhost", "port": 3000, "cors": {"whitelist": ["http://a.com"]}}

merged = NacosConfigUtils.process_and_merge_custom_config(
    base,
    """
    port: 9999
    cors:
      whitelist:
        - http://b.com
        - http://c.com
    """,
)
# merged = {"host": "localhost", "port": 9999, "cors": {"whitelist": ["http://b.com", "http://c.com"]}}
```

**Merge rules:**

- Dicts are deep-merged
- Arrays are replaced entirely (no element-level merge)
- Custom config can reference base config variables

### Auto-convert Comma-separated Strings to Arrays

By default, comma-separated strings in `cors.whitelist` are converted to arrays:

```python
config = NacosConfigUtils.process_configuration(
    "cors:\n  whitelist: 'http://a.com, http://b.com'"
)
# config["cors"]["whitelist"] = ["http://a.com", "http://b.com"]

# Custom fields to convert
config = NacosConfigUtils.process_configuration(
    "tags: 'a, b, c'",
    convert_array_fields=["tags"],
)
# config["tags"] = ["a", "b", "c"]
```

YAML array values are preserved as-is and not re-processed.

## Config Listener

```python
from nacos_toolkit import setup_config_listener

def on_update(content: str):
    print(f"Config updated: {content}")

setup_config_listener(
    nacos_config={
        "server_addr": "nacos-server:8848",
        "namespace": "production",
        "username": "nacos",
        "password": "nacos",
    },
    listen_requests=[
        {"data_id": "app.yml", "group": "DEFAULT_GROUP"},
    ],
    callback=on_update,
)
```

When no `callback` is provided, the cached config is updated automatically.

## Local Config Files

```python
from nacos_toolkit import get_local_config, find_local_config, parse_config_file

# Auto-discover and parse (priority: .json -> .yaml -> .yml)
config = get_local_config(file_name="app", file_path="./config")

# Find file path only
path = find_local_config(file_name="app", file_path="./config")
# path = "/abs/path/config/app.yml" or None

# Parse a specific file
config = parse_config_file(file_path="/path/to/config.yml")
```

## Low-level Utilities

```python
from nacos_toolkit import NacosConfigUtils, ConfigMerger, TemplateEngine

# Deep merge
merged = ConfigMerger.merge({"a": 1, "b": {"x": 1}}, {"b": {"y": 2}, "c": 3})
# {"a": 1, "b": {"x": 1, "y": 2}, "c": 3}

# Nested property access
val = NacosConfigUtils.get_nested_property({"a": {"b": {"c": 42}}}, "a.b.c")
# 42

# Nested property set
obj = {}
NacosConfigUtils.set_nested_property(obj, "a.b.c", 42)
# obj = {"a": {"b": {"c": 42}}}

# Template detection
TemplateEngine.contains_template("${HOST}")  # True
TemplateEngine.contains_template("plain")    # False
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest -v

# Lint
uv run ruff check .
```

## API Reference

| Function / Class | Description |
|---|---|
| `await get_nacos_config(...)` | Fetch and process config from Nacos |
| `setup_config_listener(...)` | Listen for Nacos config changes |
| `get_local_config(...)` | Read local config files |
| `NacosConfigUtils.process_configuration()` | Parse config + render templates |
| `NacosConfigUtils.process_and_merge_custom_config()` | Process and merge custom config |
| `NacosConfigUtils.merge_configurations()` | Deep-merge two configs |
| `NacosConfigUtils.contains_template()` | Check if string contains templates |
| `NacosConfigUtils.convert_string_fields_to_arrays()` | Convert comma strings to arrays |
| `NacosConfigUtils.get_nested_property()` | Get nested property by dot path |
| `NacosConfigUtils.set_nested_property()` | Set nested property by dot path |
| `find_local_config(...)` | Find local config file path |
| `parse_config_file(...)` | Parse JSON/YAML file |
| `NacosParser.YAML / .JSON` | Config format enum |

## License

MIT

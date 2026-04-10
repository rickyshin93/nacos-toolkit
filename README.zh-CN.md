# nacos-toolkit

[English](./README.md) | **中文**

AI 原生的 Nacos 配置解析与管理工具。

## 特性

- **AI 原生** — 内置 [`llms.txt`](./llms.txt)，AI 编程助手无需阅读源码即可理解和调用 API
- **Agent 友好** — [`AGENTS.md`](./AGENTS.md) 为 AI 贡献者提供架构、数据流和开发规范指引
- **模板引擎** — `${VAR}` 语法，支持点号嵌套引用、递归解析、循环保护
- **深度合并** — 多个 YAML/JSON 配置智能合并，字典递归合并、数组整体替换
- **异步 Nacos 客户端** — 从 Nacos 服务端拉取、缓存、监听配置变更
- **开箱即用** — 合理的默认值，一个函数调用即可完成配置处理

## 安装

```bash
uv add nacos-toolkit
```

或使用 pip：

```bash
pip install nacos-toolkit
```

## 快速开始

### 从 Nacos 获取配置

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

**处理流程：**

1. 按顺序拉取所有 `base_configs` 的内容
2. 浅合并所有配置，作为模板变量上下文
3. 仅处理最后一个配置文件，渲染其中的 `${VAR}` 模板
4. 自动注入 `DEPLOY_ENV = namespace`

### 带覆盖配置

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

覆盖配置会与基础配置深度合并，覆盖配置的值优先。

### Debug 模式

```python
result = await get_nacos_config(
    connection={...},
    base_configs=[...],
    debug=True,
)
print(result["config"])  # 处理后的配置
print(result["raw"])     # 合并后的原始配置（未经模板渲染）
```

## 配置处理工具

### 处理 YAML/JSON 配置

```python
from nacos_toolkit import NacosConfigUtils, NacosParser

# 处理 YAML 配置（默认格式）
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

# 处理 JSON 配置
config = NacosConfigUtils.process_configuration(
    '{"name": "${APP_NAME}"}',
    fmt=NacosParser.JSON,
    external_vars={"APP_NAME": "my-app"},
)
```

**模板特性：**

- 支持 `${VAR}` 语法
- 支持点号嵌套引用：`${redis.hostname}`
- 支持嵌套模板解析：`${URL}` -> `${PROTO}://${HOST}` -> `https://example.com`
- 最大渲染深度 5 层，防止无限循环
- 未定义的变量保持原样 `${UNKNOWN}`

### 合并自定义配置

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

**合并规则：**

- 字典深度合并
- 数组直接替换（不做元素合并）
- 自定义配置中可使用基础配置的变量

### 逗号分隔字符串自动转数组

默认会将 `cors.whitelist` 字段的逗号分隔字符串转为数组：

```python
config = NacosConfigUtils.process_configuration(
    "cors:\n  whitelist: 'http://a.com, http://b.com'"
)
# config["cors"]["whitelist"] = ["http://a.com", "http://b.com"]

# 自定义需要转换的字段
config = NacosConfigUtils.process_configuration(
    "tags: 'a, b, c'",
    convert_array_fields=["tags"],
)
# config["tags"] = ["a", "b", "c"]
```

如果值是 YAML 数组格式则保持不变，不会重复处理。

## 配置监听

```python
from nacos_toolkit import setup_config_listener

def on_update(content: str):
    print(f"配置已更新: {content}")

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

不传 `callback` 时，默认自动更新缓存中的配置。

## 本地配置文件

```python
from nacos_toolkit import get_local_config, find_local_config, parse_config_file

# 自动查找并解析（按 .json -> .yaml -> .yml 优先级）
config = get_local_config(file_name="app", file_path="./config")

# 仅查找文件路径
path = find_local_config(file_name="app", file_path="./config")
# path = "/abs/path/config/app.yml" 或 None

# 解析指定文件
config = parse_config_file(file_path="/path/to/config.yml")
```

## 底层工具

```python
from nacos_toolkit import NacosConfigUtils, ConfigMerger, TemplateEngine

# 深度合并
merged = ConfigMerger.merge({"a": 1, "b": {"x": 1}}, {"b": {"y": 2}, "c": 3})
# {"a": 1, "b": {"x": 1, "y": 2}, "c": 3}

# 嵌套属性访问
val = NacosConfigUtils.get_nested_property({"a": {"b": {"c": 42}}}, "a.b.c")
# 42

# 嵌套属性设置
obj = {}
NacosConfigUtils.set_nested_property(obj, "a.b.c", 42)
# obj = {"a": {"b": {"c": 42}}}

# 模板检测
TemplateEngine.contains_template("${HOST}")  # True
TemplateEngine.contains_template("plain")    # False
```

## 开发

```bash
# 安装依赖
uv sync

# 运行测试
uv run pytest -v

# 代码检查
uv run ruff check .
```

## API 一览

| 函数 / 类 | 说明 |
|---|---|
| `await get_nacos_config(...)` | 从 Nacos 拉取并处理配置 |
| `setup_config_listener(...)` | 监听 Nacos 配置变更 |
| `get_local_config(...)` | 读取本地配置文件 |
| `NacosConfigUtils.process_configuration()` | 解析配置 + 渲染模板 |
| `NacosConfigUtils.process_and_merge_custom_config()` | 处理并合并自定义配置 |
| `NacosConfigUtils.merge_configurations()` | 深度合并两个配置 |
| `NacosConfigUtils.contains_template()` | 检测字符串是否包含模板 |
| `NacosConfigUtils.convert_string_fields_to_arrays()` | 逗号字符串转数组 |
| `NacosConfigUtils.get_nested_property()` | 点号路径读取嵌套属性 |
| `NacosConfigUtils.set_nested_property()` | 点号路径设置嵌套属性 |
| `find_local_config(...)` | 查找本地配置文件路径 |
| `parse_config_file(...)` | 解析 JSON/YAML 文件 |
| `NacosParser.YAML / .JSON` | 配置格式枚举 |

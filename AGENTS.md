# Agent Guidelines for nacos-toolkit

## Project Overview

A Python library for Nacos configuration parsing and management. It provides template rendering (`${VAR}`), deep config merging, and local config file utilities.

## Architecture

```
src/nacos_toolkit/
├── __init__.py       # Public API re-exports
├── manager.py        # NacosConfigManager (singleton), get_nacos_config(), setup_config_listener()
├── utils.py          # NacosConfigUtils — main facade for config processing
├── template.py       # TemplateEngine — ${VAR} rendering with BFS traversal
├── merger.py         # ConfigMerger — recursive deep merge
├── parser.py         # ConfigParser + NacosParser enum — YAML/JSON parsing
└── local_config.py   # Local file discovery and parsing
```

### Module Responsibilities

- **manager.py**: Nacos server interaction. Singleton pattern with config caching. Depends on `nacos-sdk-python`.
- **utils.py**: Stateless facade. Orchestrates parser → template → merger pipeline. No I/O.
- **template.py**: Pure `${VAR}` template engine. Supports dot-notation, recursive resolution (max depth 5), BFS traversal over nested dicts/lists.
- **merger.py**: Pure deep-merge. Dicts merge recursively; arrays and scalars are replaced.
- **parser.py**: Thin wrapper over `yaml.safe_load` / `json.loads`.
- **local_config.py**: File discovery by convention (.json > .yaml > .yml priority).

### Data Flow

```
Raw config string
  → ConfigParser.parse()        # str → dict
  → TemplateEngine.render()     # ${VAR} substitution
  → convert_string_fields_to_arrays()  # "a,b" → ["a","b"]
  → ConfigMerger.merge()        # deep merge with override
  → Final config dict
```

## Development

### Setup

```bash
uv sync
```

### Running Tests

```bash
uv run pytest -v
```

### Linting

```bash
uv run ruff check .
```

### Code Style

- Line length: 120 chars
- Ruff rules: E, F, I, W
- Type hints required on all public APIs
- Use `from __future__ import annotations` in all modules

### Key Conventions

- All public API is re-exported through `__init__.py`
- Use `NacosParser.YAML` / `NacosParser.JSON` enum, never raw strings
- `NacosConfigUtils` methods are all `@staticmethod` — no instance state
- `NacosConfigManager` is a singleton via `get_instance()`
- Template pattern: `${VAR}` with regex `\$\{([^}]+)\}`
- Tests mirror source structure: `test_utils.py`, `test_manager.py`, `test_integration.py`

### Testing Guidelines

- Unit tests for utils/template/merger are pure — no mocking needed
- Manager tests use `unittest.mock` to mock the Nacos client
- Integration tests in `test_integration.py` test the full pipeline without network
- Run the full suite before submitting changes

## Dependencies

- **Runtime**: `pyyaml`, `nacos-sdk-python`, `loguru`
- **Dev**: `pytest`, `pytest-asyncio`, `ruff`
- **Python**: >=3.12
- **Build**: `uv_build`

# Project Init Core

Tiny bootstrapper that reads project-level metadata from Config Manager and exposes it through a thin helper class.

## Overview
- Resolves the consolidated `.config` file via Config Manager on import
- Surfaces `project_init_core` settings (module name, descriptions, etc.) through `ProjectInit`
- Provides an example entry point for future project-specific initialization hooks

## Features
- **Config-backed helper** – `ProjectInit` wires `ConfigManager` once and stores `self.config` for repeated access
- **Utility method** – `display_module_name()` shows how to reach values defined under `project_init_core`
- **Extendable skeleton** – add your own initialization helpers without re-plumbing ConfigManager each time

## Quickstart

```python
from cores.project_init_core.project_init_core import ProjectInit

init = ProjectInit()
print(init.config.module_name)
init.display_module_name()  # convenience logging helper
```

## API

```python
class ProjectInit:
	def __init__(self) -> None: ...  # wires ConfigManager and stores config slice
	def display_module_name(self) -> None: ...  # prints the configured module name
```

## Notes
- This module is intentionally small; treat it as the recommended location for future project-level bootstrap helpers.
- Access additional keys via `init.config.<nested_key>`; each node is a generated dataclass from Config Manager.

## Requirements & prerequisites
- Config Manager must be initialized (it’s handled automatically when you instantiate `ProjectInit`).
- `.config` should contain a `project_init_core` section with a `module_name` key.

## Troubleshooting
- **`AttributeError: project_init_core`** – regenerate `.config` using Config Manager so the section exists.
- **Printed module name is blank** – populate `module_name` inside `.config` or your module template.
- **Need additional bootstrap data** – extend `.config` + generated keys; the helper mirrors whatever you add.

## Module structure

```
cores/project_init_core/
├─ __init__.py             # package marker
├─ project_init_core.py    # ProjectInit helper
├─ .config_template        # default config schema
├─ init.yaml               # module metadata
└─ README.md               # this file
```

## See also
- Config Manager – generates the typed config accessors consumed here
- Modules Controller Core – inspects project modules once the project is initialized
- Module Creator Core – scaffolds new modules that may hook into Project Init
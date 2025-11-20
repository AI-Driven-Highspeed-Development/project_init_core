# Project Init Core

The bootstrapping engine for ADHD Framework projects. It handles module cloning, dependency resolution, and workspace initialization.

## Overview
- **Clones Modules**: Reads `init.yaml` to find required modules and clones them from Git.
- **Resolves Dependencies**: Recursively finds and installs dependencies for all modules.
- **Initializes Workspace**: Generates a VS Code workspace file (`.code-workspace`) including all relevant modules.
- **Runs Initializers**: Executes `__init__.py` scripts for modules that require setup.
- **Installs Requirements**: Finds and installs `requirements.txt` files (via `RequirementsInstaller`).

## Features
- **Smart Cloning**: Uses `ModulesCloner` to efficiently clone repositories and prevent duplicates.
- **Workspace Generation**: Automatically adds modules to the VS Code workspace based on visibility rules.
- **Dependency Management**: Ensures all required modules are present before the project starts.
- **Requirements Installation**: Scans the project for Python dependencies and installs them.

## Quickstart

```python
from cores.project_init_core.project_init import ProjectInit

# Initialize the project (clone modules, setup workspace, etc.)
initializer = ProjectInit()
report = initializer.init_project()

print(f"Initialized {len(report)} modules.")
```

## API

```python
class ProjectInit:
    def __init__(self, project_root: Optional[str | Path] = None) -> None: ...
    def init_project(self) -> list[ModuleInfo]: ... # Main entry point
    def init_workspace_file(self, modules_report: Optional[ModulesReport] = None) -> None: ...
    def run_module_initializers(self, modules_report: Optional[ModulesReport] = None, ...) -> None: ...
```

## Requirements Installer

This core also includes the `RequirementsInstaller` for managing Python packages.

```python
from cores.project_init_core.requirements_installer import RequirementsInstaller

installer = RequirementsInstaller()
installer.install_all() # Installs from all requirements.txt files
```

## Module structure

```
cores/project_init_core/
├─ __init__.py             # package marker
├─ project_init.py         # Main ProjectInit class
├─ modules_cloner.py       # Git cloning logic
├─ requirements_installer.py # pip install logic
├─ init.yaml               # module metadata
└─ README.md               # this file
```

## See also
- Modules Controller Core – Used to scan and manage the modules after cloning.
- Workspace Core – Used to build the VS Code workspace file.

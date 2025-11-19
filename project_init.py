from __future__ import annotations

from pathlib import Path
from typing import Optional

from managers.config_manager import ConfigManager
from cores.project_init_core.modules_cloner import ModulesCloner
from cores.modules_controller_core.modules_controller import (
    ModuleInfo,
    ModulesController,
    ModulesReport,
)
from utils.logger_util.logger import Logger
from cores.workspace_core.workspace_builder import WorkspaceBuilder, WorkspaceBuildingStep


class ProjectInit:
    """Bootstrap helper that installs ADHD modules into a fresh project."""

    def __init__(self, project_root: Optional[str | Path] = None) -> None:
        self.logger = Logger(name=type(self).__name__)
        self.project_root = Path(project_root or Path.cwd()).resolve()

        self.modules_controller = ModulesController(self.project_root)
        self.cloner = ModulesCloner(self.project_root, self.modules_controller)

    def init_project(self) -> list[ModuleInfo]:
        """Clone required modules, resolve dependencies, and run initializers."""
        self.cloner.clone_from_project_init()
        report = self.cloner.modules_report or self.modules_controller.scan_all_modules()
        self.fix_repo_urls(report)
        self.run_module_initializers(report, logger=self.logger)
        self.init_workspace_file(report)
        return report.modules if report else []

    def get_modules_report(self) -> Optional[ModulesReport]:
        """Return the latest ModulesReport produced during cloning, if any."""
        return self.cloner.modules_report

    def display_module_name(self) -> None:
        config_manager = ConfigManager()
        config = config_manager.config.project_init_core
        module_name = getattr(config, "module_name", "<unknown>")
        print("Module Name:", module_name)

    def fix_repo_urls(self, report: Optional[ModulesReport]) -> None:
        """Update init.yaml files to add missing repo_url fields using cloner's canonical URLs."""
        if not report:
            return

        url_map = {
            result.destination.resolve(): result.repo_url
            for result in self.cloner.installed_modules
        }

        for module in report.modules:
            if module.repo_url:
                continue

            canonical_url = url_map.get(module.path.resolve())
            if canonical_url:
                self.modules_controller.update_module_init_yaml_field(
                    module.path,
                    "repo_url",
                    canonical_url,
                )

    def run_module_initializers(
        self,
        modules_report: Optional[ModulesReport] = None,
        *,
        logger: Optional[Logger] = None,
    ) -> None:
        """Execute module __init__.py files for modules listed in the provided report."""
        report = modules_report or self.modules_controller.list_all_modules()
        if not report:
            return
        self.modules_controller.run_initializers(
            report.modules,
            project_root=self.project_root,
            logger=logger or self.logger,
        )

    def init_workspace_file(self, modules_report: Optional[ModulesReport] = None) -> None:
        """Generate a VS Code workspace file listing modules that should appear in the workspace."""
        report = modules_report or self.modules_controller.list_all_modules()
        if not report:
            return

        workspace_path = self.project_root / f"{self.project_root.name}.code-workspace"

        folder_entries: list[dict[str, str]] = []
        seen_paths: set[str] = set()

        for module in report.modules:
            # Determine visibility: override > default
            is_visible = module.shows_in_workspace
            if is_visible is None:
                is_visible = module.module_type.shows_in_workspace
            
            if not is_visible:
                continue

            try:
                relative_path = module.path.relative_to(self.project_root)
            except ValueError:
                self.logger.warning(
                    f"Module path {module.path} is not under project root {self.project_root}. Skipping workspace entry."
                )
                continue
            folder_path = f"./{relative_path.as_posix()}"
            if folder_path not in seen_paths:
                folder_entries.append({"path": folder_path})
                seen_paths.add(folder_path)

        if "." not in seen_paths:
            folder_entries.append({"path": "."})

        builder = WorkspaceBuilder(str(workspace_path))
        builder.add_step(
            WorkspaceBuildingStep(
                target=[],
                content={
                    "folders": folder_entries,
                    "settings": {
                        "python.analysis.extraPaths": [
                            "../../../",
                            "../../",
                            "../",
                        ],
                    },
                },
            )
        )
        workspace_data = builder.build_workspace()
        builder.write_workspace(workspace_data)
        self.logger.info(f"Workspace file created at {workspace_path}")


__all__ = ["ProjectInit"]
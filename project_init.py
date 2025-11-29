from __future__ import annotations

from pathlib import Path
from typing import Optional

from managers.config_manager import ConfigManager
from cores.github_api_core.api import GithubApi
from cores.project_init_core.modules_cloner import ModulesCloner
from cores.modules_controller_core.modules_controller import (
    ModuleInfo,
    ModulesController,
    ModulesReport,
)
from utils.logger_util.logger import Logger


class ProjectInit:
    """Bootstrap helper that installs ADHD modules into a fresh project."""

    def __init__(self, project_root: Optional[str | Path] = None) -> None:
        self.logger = Logger(name=type(self).__name__)
        self.cm = ConfigManager()
        self.config = self.cm.config.project_init_core
        self.project_root = Path(project_root or Path.cwd()).resolve()

        self.modules_controller = ModulesController(self.project_root)
        self.cloner = ModulesCloner(self.project_root, self.modules_controller)

    def init_project(self) -> list[ModuleInfo]:
        """Clone required modules, resolve dependencies, and run initializers."""
        self.cloner.clone_from_project_init()
        report = self.cloner.modules_report or self.modules_controller.scan_all_modules()
        self.fix_repo_urls(report)
        self._install_framework_cli()
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
        # Delegate to ModulesController which now handles this logic centrally
        self.modules_controller.generate_workspace_file()

    def _install_framework_cli(self) -> None:
        """Download adhd_framework.py from the configured repository."""
        repo_url = self.config.framework_repo_url
        if not repo_url:
            self.logger.info("No framework_repo_url configured; skipping adhd_framework.py installation.")
            return
        
        try:
            api = GithubApi()
            repo = api.repo(repo_url)
            content = repo.get_file("adhd_framework.py")
            
            if content:
                dest_file = self.project_root / "adhd_framework.py"
                dest_file.write_text(content, encoding="utf-8")
                
                # Make executable
                try:
                    dest_file.chmod(dest_file.stat().st_mode | 0o111)
                except Exception:
                    pass # Ignore chmod errors on Windows etc.
                
                self.logger.info(f"✅ Installed adhd_framework.py to {dest_file}")
            else:
                self.logger.error("adhd_framework.py not found in the repository or is empty.")
                
        except Exception as e:
            self.logger.error(f"Failed to install adhd_framework.py: {e}")


__all__ = ["ProjectInit"]
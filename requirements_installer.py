from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List

from cores.modules_controller_core.modules_controller import ModulesController
from utils.logger_util.logger import Logger


class RequirementsInstaller:
    """Handles installation of requirements.txt files for the project and its modules."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self.logger = Logger(name="RequirementsInstaller")
        self.modules_controller = ModulesController(self.project_root)

    def install_all(self) -> None:
        """Find and install all requirements.txt files in modules and project root."""
        requirements_files = self._collect_requirements_files()

        if not requirements_files:
            self.logger.info("No requirements.txt files found.")
            return

        self.logger.info(f"Found {len(requirements_files)} requirements.txt files to install.")

        for req_file in requirements_files:
            self._install_file(req_file)

    def _collect_requirements_files(self) -> List[Path]:
        """Collect requirements.txt from root and all modules."""
        files: List[Path] = []

        # 1. Check root requirements.txt
        root_req = self.project_root / "requirements.txt"
        if root_req.exists() and root_req.is_file():
            files.append(root_req)

        # 2. Check modules
        report = self.modules_controller.scan_all_modules()
        for module in report.modules:
            mod_req = module.path / "requirements.txt"
            if mod_req.exists() and mod_req.is_file():
                # Avoid duplicates if root is also a module (unlikely but possible)
                if mod_req not in files:
                    files.append(mod_req)

        return files

    def _install_file(self, req_file: Path) -> None:
        """Install packages from a single requirements.txt file."""
        try:
            rel_path = req_file.relative_to(self.project_root)
        except ValueError:
            rel_path = req_file

        self.logger.info(f"Installing dependencies from {rel_path}...")

        try:
            # We use pip install -r <file>
            # We capture output to avoid clutter, but log it on error.
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.logger.info(f"✅ Installed {rel_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Failed to install {rel_path}")
            if e.stderr:
                self.logger.error(f"Error details: {e.stderr.strip()}")
            elif e.stdout:
                self.logger.error(f"Output: {e.stdout.strip()}")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error installing {rel_path}: {e}")

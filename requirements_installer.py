from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List

from utils.logger_util.logger import Logger


class RequirementsInstaller:
    """Handles installation of requirements.txt files for the project and its modules."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path.cwd()).resolve()
        self.logger = Logger(name="RequirementsInstaller")

    def install_all(self) -> None:
        """Find and install all requirements.txt files in the project root recursively."""
        self.install(self.project_root)

    def install(self, target_dir: Path) -> None:
        """Find and install all requirements.txt files in the target directory recursively."""
        target_path = target_dir.resolve()
        if not target_path.exists() or not target_path.is_dir():
            self.logger.warning(f"Target directory {target_path} does not exist or is not a directory.")
            return

        requirements_files = list(target_path.rglob("requirements.txt"))

        if not requirements_files:
            self.logger.debug(f"No requirements.txt files found in {target_path}.")
            return

        self.logger.info(f"Found {len(requirements_files)} requirements.txt files in {target_path} to install.")

        for req_file in requirements_files:
            self._install_file(req_file)

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

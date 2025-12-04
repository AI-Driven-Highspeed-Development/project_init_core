"""Framework updater for syncing adhd_framework.py from the source repository."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from managers.config_manager import ConfigManager
from cores.github_api_core.api import GithubApi
from cores.exceptions_core.adhd_exceptions import ADHDError
from utils.logger_util.logger import Logger


class FrameworkUpdater:
    """Updates adhd_framework.py from the configured source repository."""

    def __init__(self, project_root: Optional[str | Path] = None) -> None:
        self.logger = Logger(name=type(self).__name__)
        self.cm = ConfigManager()
        self.config = self.cm.config.project_init_core
        self.project_root = Path(project_root or Path.cwd()).resolve()

    def update_framework_file(self, *, dry_run: bool = False) -> bool:
        """
        Download and update adhd_framework.py from the configured source repository.
        
        Args:
            dry_run: If True, only check if update is available without applying.
            
        Returns:
            True if update was successful (or would be in dry_run), False otherwise.
        """
        repo_url = self.config.framework_repo_url
        if not repo_url:
            raise ADHDError(
                "No framework_repo_url configured in project_init_core config. "
                "Cannot update framework file."
            )

        dest_file = self.project_root / "adhd_framework.py"

        try:
            api = GithubApi()
            repo = api.repo(repo_url)

            remote_content = repo.get_file("adhd_framework.py")
            if not remote_content:
                raise ADHDError("adhd_framework.py not found in the source repository.")

            # Check if local file exists and compare
            if dest_file.exists():
                local_content = dest_file.read_text(encoding="utf-8")
                if local_content == remote_content:
                    self.logger.info("✅ adhd_framework.py is already up to date.")
                    return True

                if dry_run:
                    self.logger.info("🔄 Update available for adhd_framework.py")
                    return True

            if dry_run:
                self.logger.info("🔄 adhd_framework.py would be installed.")
                return True

            # Write the updated content
            dest_file.write_text(remote_content, encoding="utf-8")

            # Make executable on POSIX systems
            try:
                dest_file.chmod(dest_file.stat().st_mode | 0o111)
            except Exception:
                pass  # Ignore chmod errors on Windows

            self.logger.info(f"✅ Updated adhd_framework.py at {dest_file}")
            return True

        except ADHDError:
            raise
        except Exception as e:
            raise ADHDError(f"Failed to update framework file: {e}") from e

    def update_requirements_file(self, *, dry_run: bool = False) -> bool:
        """
        Download and update requirements.txt from the configured source repository.
        
        Args:
            dry_run: If True, only check if update is available without applying.
            
        Returns:
            True if update was successful (or would be in dry_run), False otherwise.
        """
        repo_url = self.config.framework_repo_url
        if not repo_url:
            raise ADHDError(
                "No framework_repo_url configured in project_init_core config. "
                "Cannot update requirements file."
            )

        dest_file = self.project_root / "requirements.txt"

        try:
            api = GithubApi()
            repo = api.repo(repo_url)

            remote_content = repo.get_file("requirements.txt")
            if not remote_content:
                self.logger.warning("requirements.txt not found in the source repository.")
                return False

            if dest_file.exists():
                local_content = dest_file.read_text(encoding="utf-8")
                if local_content == remote_content:
                    self.logger.info("✅ requirements.txt is already up to date.")
                    return True

                if dry_run:
                    self.logger.info("🔄 Update available for requirements.txt")
                    return True

            if dry_run:
                self.logger.info("🔄 requirements.txt would be installed.")
                return True

            dest_file.write_text(remote_content, encoding="utf-8")
            self.logger.info(f"✅ Updated requirements.txt at {dest_file}")
            return True

        except ADHDError:
            raise
        except Exception as e:
            raise ADHDError(f"Failed to update requirements file: {e}") from e

    def update_all(self, *, dry_run: bool = False) -> bool:
        """
        Update both adhd_framework.py and requirements.txt from source repository.
        
        Args:
            dry_run: If True, only check if updates are available without applying.
            
        Returns:
            True if all updates were successful.
        """
        framework_ok = self.update_framework_file(dry_run=dry_run)
        requirements_ok = self.update_requirements_file(dry_run=dry_run)
        return framework_ok and requirements_ok


__all__ = ["FrameworkUpdater"]

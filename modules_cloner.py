from __future__ import annotations

from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from cores.modules_controller_core.modules_controller import ModulesController, ModulesReport
from utils.logger_util.logger import Logger
from cores.github_api_core.api import GithubApi, GithubRepo
from cores.exceptions_core.adhd_exceptions import ADHDError
from cores.yaml_reading_core.yaml_reading import YamlReadingCore
from cores.project_init_core.requirements_installer import RequirementsInstaller
import re
import sys

@dataclass
class ModuleCloneResult:
    repo_url: str
    destination: Path
    requirements: List[str]


@dataclass
class ModulesCloner:
    """Clone modules from init.yaml and resolve dependency requirements."""
    project_root: Path
    modules_controller: ModulesController
    logger: Logger = field(default_factory=lambda: Logger(name="ModulesCloner"))
    cloned_repo_urls: Set[str] = field(default_factory=set)
    installed_modules: List[ModuleCloneResult] = field(default_factory=list)
    modules_report: Optional[ModulesReport] = field(default=None, init=False)
    module_type_paths: Dict[str, Path] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.project_root = self.project_root.resolve()
        module_types = self.modules_controller.module_types.get_all_types()
        self.module_type_paths = {}
        for module_type in module_types:
            module_type.path.mkdir(parents=True, exist_ok=True)
            self.module_type_paths[module_type.name.lower()] = module_type.path
            self.module_type_paths[module_type.plural_name.lower()] = module_type.path

    def clone_from_project_init(self, *, max_workers: int = 8) -> List[ModuleCloneResult]:
        # Check for venv
        if not (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
             raise ADHDError("Not running in a virtual environment. Please activate a venv before initializing modules.")

        project_init_file = self.project_root / "init.yaml"
        yf = YamlReadingCore.read_yaml(project_init_file)
        if not yf:
            raise FileNotFoundError(f"Project init.yaml not found at {project_init_file}")
        init_data = yf.to_dict()
        if max_workers < 1:
            raise ValueError("max_workers must be a positive integer")

        self.installed_modules = []

        # Seed install queue from init.yaml entries and keep track of normalized URLs.
        seed_modules = init_data.get("modules") or []
        pending: deque[str] = deque()
        scheduled: Set[str] = set()

        for url in seed_modules:
            self._enqueue_module_clone(url, pending, scheduled)

        inflight: Dict[Future[Optional[ModuleCloneResult]], str] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while pending or inflight:
                while pending and len(inflight) < max_workers:
                    repo_url = pending.popleft()
                    if repo_url in self.cloned_repo_urls:
                        continue
                    future = executor.submit(self._install_repo, repo_url)
                    inflight[future] = repo_url
                if not inflight:
                    if pending:
                        continue
                    break

                done, _ = wait(inflight.keys(), return_when=FIRST_COMPLETED)
                for future in done:
                    repo_url = inflight.pop(future)
                    self._handle_completed_clone(
                        future,
                        repo_url,
                        pending,
                        scheduled,
                    )

        self.modules_report = self.modules_controller.scan_all_modules()
        return self.installed_modules

    def _install_repo(self, repo_url: str) -> Optional[ModuleCloneResult]:
        """Clone a single repo directly into its module-type folder and record metadata."""
        github_api = GithubApi()
        repo = github_api.repo(repo_url)
        init_data = self._read_remote_init(repo)
        if not init_data:
            self.logger.error(f"Unable to read init.yaml for {repo_url}; skipping")
            return None

        module_type_name = str(init_data.get("type") or "").strip().lower()
        module_name = ModulesCloner._snakify_module_name(repo.repo_name)
        module_type_path = self.module_type_paths.get(module_type_name)
        if not module_type_path:
            self.logger.error(f"Unknown module type '{module_type_name}' for {repo_url}")
            return None

        destination = module_type_path / module_name
        requirements = self._normalize_requirements(init_data.get("requirements"))
        canonical_url = self._canonical_repo_url(init_data.get("repo_url"), repo)

        if destination.exists():
            self.logger.info(f"Module already exists at {destination}, skipping clone")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.logger.info(
                    f"Cloning {module_name} ({module_type_name}) into {destination}"
                )
                repo.clone_repo(dest_path=str(destination))
                
                # Install requirements immediately after cloning
                installer = RequirementsInstaller(self.project_root)
                installer.install(destination)
                
            except ADHDError as exc:
                self.logger.error(f"Failed to clone {repo_url}: {exc}")
                return None

        result_obj = ModuleCloneResult(
            repo_url=canonical_url,
            destination=destination,
            requirements=requirements,
        )
        return result_obj

    def _handle_completed_clone(
        self,
        future: Future[Optional[ModuleCloneResult]],
        repo_url: str,
        pending: deque[str],
        scheduled: Set[str],
    ) -> None:
        try:
            result = future.result()
        except Exception as exc:
            self.logger.error(f"Module clone task failed for {repo_url}: {exc}")
            self._mark_module_processed(repo_url)
            return

        if not result:
            self._mark_module_processed(repo_url)
            return

        self.installed_modules.append(result)
        self.cloned_repo_urls.add(result.repo_url)
        self._mark_module_processed(repo_url)

        for requirement in result.requirements:
            self._enqueue_module_clone(requirement, pending, scheduled)

    def _enqueue_module_clone(
        self,
        url: Any,
        queue: deque[str],
        scheduled: Set[str],
    ) -> None:
        clean_url = self._normalize_repo_url(url)
        if (
            clean_url
            and clean_url not in self.cloned_repo_urls
            and clean_url not in scheduled
        ):
            queue.append(clean_url)
            scheduled.add(clean_url)

    def _mark_module_processed(self, raw_url: str) -> None:
        normalized = self._normalize_repo_url(raw_url)
        if normalized:
            self.cloned_repo_urls.add(normalized)

    def _read_remote_init(self, repo: GithubRepo) -> Optional[Dict[str, Any]]:
        try:
            file_contents = repo.get_file("init.yaml")
        except ValueError:
            return None
        if not file_contents:
            return None
        yf = YamlReadingCore.read_yaml_str(file_contents)
        return yf.to_dict() if yf else None

    @staticmethod
    def _normalize_requirements(value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        normalized: List[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                normalized.append(item.strip())
        return normalized

    def _canonical_repo_url(self, config_url: Optional[str], repo: GithubRepo) -> str:
        if isinstance(config_url, str) and config_url.strip():
            return config_url.strip()
        return GithubApi.build_repo_url(repo.owner, repo.repo_name)

    @staticmethod
    def _normalize_repo_url(value: Any) -> Optional[str]:
        if isinstance(value, str):
            clean_value = value.strip()
            if clean_value:
                return clean_value
        return None
    
    @staticmethod
    def _snakify_module_name(name: str) -> str:
        """Convert a module name to snake_case; also replaces '-' with '_'."""
        sanitized = name.replace("-", "_").strip()
        s1 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", sanitized)
        s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
        snake = re.sub(r"_+", "_", s2)
        return snake.strip("_").lower()
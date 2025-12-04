import os
import sys

# Add path handling to work from the new nested directory structure
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.getcwd()  # Use current working directory as project root
sys.path.insert(0, project_root)

from cores.project_init_core.project_init import ProjectInit
from cores.project_init_core.requirements_installer import RequirementsInstaller
from cores.project_init_core.framework_updater import FrameworkUpdater

__all__ = ["ProjectInit", "RequirementsInstaller", "FrameworkUpdater"]

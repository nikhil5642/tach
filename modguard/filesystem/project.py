import os
import sys

from modguard.colors import BCOLORS
from modguard.constants import CONFIG_FILE_NAME
from modguard.core.config import ProjectConfig
import yaml


def print_no_modguard_yml() -> None:
    print(
        f"{BCOLORS.FAIL} {CONFIG_FILE_NAME}.(yml|yaml) not found in {os.getcwd()}",
        file=sys.stderr,
    )


def print_invalid_exclude(path: str) -> None:
    print(
        f"{BCOLORS.FAIL} {path} is not a valid dir or file. "
        f"Make sure the exclude list is comma separated and valid.",
        file=sys.stderr,
    )


def validate_project_config_path(root=".") -> str:
    file_path = os.path.join(root, f"{CONFIG_FILE_NAME}.yml")
    if os.path.exists(file_path):
        return file_path
    file_path = os.path.join(root, f"{CONFIG_FILE_NAME}.yaml")
    if os.path.exists(file_path):
        return file_path
    print_no_modguard_yml()
    sys.exit(1)


def parse_project_config(root=".") -> ProjectConfig:
    file_path = validate_project_config_path(root)
    with open(file_path, "r") as f:
        results = yaml.safe_load(f)
    return ProjectConfig(**results)

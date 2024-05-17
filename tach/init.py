import os
from dataclasses import field, dataclass
from typing import Optional


from tach import errors
from tach import filesystem as fs
from tach.check import check
from tach.colors import BCOLORS
from tach.constants import PACKAGE_FILE_NAME, CONFIG_FILE_NAME, TOOL_NAME
from tach.interactive import get_selected_packages_interactive, SelectedPackage
from tach.parsing import dump_project_config_to_yaml
from tach.sync import prune_dependency_constraints

__package_yml_template = """tags: ['{dir_name}']\n"""


@dataclass
class PackageInitResult:
    package_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def init_packages(selected_packages: list[SelectedPackage]) -> PackageInitResult:
    package_paths: list[str] = []
    warnings: list[str] = []
    for selected_package in selected_packages:
        init_py_path = os.path.join(selected_package.full_path, "__init__.py")
        if not os.path.exists(init_py_path):
            warnings.append(
                f"{BCOLORS.OKCYAN}Created __init__.py in selected package: '{selected_package.full_path}'{BCOLORS.ENDC}"
            )
            fs.write_file(init_py_path, f"# Generated by '{TOOL_NAME} init'")
        package_yml_path = os.path.join(
            selected_package.full_path, f"{PACKAGE_FILE_NAME}.yml"
        )
        package_paths.append(selected_package.full_path)
        if os.path.exists(package_yml_path):
            warnings.append(
                f"{BCOLORS.OKCYAN}Package file '{package_yml_path}' already exists.{BCOLORS.ENDC}"
            )
            continue
        package_yml_content = __package_yml_template.format(
            dir_name=fs.canonical(selected_package.full_path).replace(os.path.sep, ".")
        )
        fs.write_file(package_yml_path, package_yml_content)

    return PackageInitResult(package_paths=package_paths, warnings=warnings)


@dataclass
class InitRootResult:
    warnings: list[str] = field(default_factory=list)


def init_root(root: str, exclude_paths: Optional[list[str]] = None) -> InitRootResult:
    project_config_path = fs.get_project_config_path(root)
    if project_config_path:
        return InitRootResult(
            warnings=[
                f"{BCOLORS.OKCYAN}Project already contains {CONFIG_FILE_NAME}.yml{BCOLORS.ENDC}"
            ]
        )

    project_config = prune_dependency_constraints(root, exclude_paths=exclude_paths)

    tach_yml_path = os.path.join(root, f"{CONFIG_FILE_NAME}.yml")
    tach_yml_content = dump_project_config_to_yaml(project_config)
    fs.write_file(tach_yml_path, tach_yml_content)

    check_errors = check(
        root, project_config=project_config, exclude_paths=exclude_paths
    )
    if check_errors:
        return InitRootResult(
            warnings=[
                "Could not auto-detect all dependencies, use 'tach check' to finish initialization manually."
            ]
        )

    return InitRootResult(warnings=[])


def init_project(
    root: str, depth: int = 1, exclude_paths: Optional[list[str]] = None
) -> tuple[bool, list[str]]:
    if not os.path.isdir(root):
        raise errors.TachSetupError(f"The path {root} is not a directory.")

    if exclude_paths is None:
        exclude_paths = ["tests/", "docs/"]

    warnings: list[str] = []

    selected_packages = get_selected_packages_interactive(
        root,
        depth=depth,
        exclude_paths=exclude_paths,
        auto_select_initial_packages=True,
    )
    if selected_packages is not None:
        init_packages_result = init_packages(selected_packages=selected_packages)
        warnings.extend(init_packages_result.warnings)

        init_root_result = init_root(root, exclude_paths=exclude_paths)
        warnings.extend(init_root_result.warnings)
    else:
        return False, [f"{BCOLORS.OKCYAN}No changes saved.{BCOLORS.ENDC}"]

    return True, warnings

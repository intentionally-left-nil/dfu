from pathlib import Path
from shutil import rmtree

from dfu.config import Config
from dfu.installed_packages.pacman import diff_packages, get_installed_packages
from dfu.package.package_config import PackageConfig
from dfu.snapshots.snapper import Snapper


def diff_snapshot(config: Config, package_config_path: Path):
    package_config = PackageConfig.from_file(package_config_path)
    update_installed_packages(config, package_config)
    create_changed_placeholders(config, package_config)
    package_config.write(package_config_path)


def update_installed_packages(config: Config, package_config: PackageConfig):
    if len(package_config.snapshots) == 0:
        raise ValueError('Did not create a successful pre/post snapshot pair')
    old_packages = get_installed_packages(config, package_config.snapshot_mapping(use_pre_id=True))
    new_packages = get_installed_packages(config, package_config.snapshot_mapping(use_pre_id=False))

    diff = diff_packages(old_packages, new_packages)
    package_config.programs_added = diff.added
    package_config.programs_removed = diff.removed


def create_changed_placeholders(config: Config, package_config: PackageConfig):
    pre_mapping = package_config.snapshot_mapping(use_pre_id=True)
    post_mapping = package_config.snapshot_mapping(use_pre_id=False)

    placeholder_dir = config.get_package_dir() / package_config.name / 'placeholders'
    if placeholder_dir.exists():
        rmtree(placeholder_dir)

    placeholder_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    for snapper_name, pre_id in pre_mapping.items():
        post_id = post_mapping[snapper_name]
        snapper = Snapper(snapper_name)
        for change in snapper.get_delta(pre_id, post_id):
            path = placeholder_dir / change.path.lstrip('/')
            if not path.resolve().is_relative_to(placeholder_dir.resolve()):
                raise ValueError(f"Trying to create {path} failed because it is not relative to {placeholder_dir}")

            # We can't simply make all the parent directories, because the snapper diff doesn't distinguish between files and directories.
            # Therefore, we may have previously created a parent directory as a file. So, we need to manually walk the path
            # Delete any placeholder files that are actually directories, and re-create them as directories
            current_path = Path(path.parts[0])
            for child in path.parts[1:]:
                current_path = current_path / child

                if current_path.is_file() and current_path.read_text() == "PLACEHOLDER: CREATED":
                    current_path.unlink()
                    current_path.mkdir(mode=0o755)
                elif not current_path.is_dir():
                    raise ValueError(f"Trying to create {path} failed because {current_path} is not a directory")

            path.write_text(f"PLACEHOLDER: {change.action}")

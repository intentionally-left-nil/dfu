from pathlib import Path
from shutil import rmtree

from dfu.config import Config
from dfu.installed_packages.pacman import diff_packages, get_installed_packages
from dfu.package.package_config import PackageConfig
from dfu.revision.git import git_check_ignore
from dfu.snapshots.snapper import Snapper


def diff_snapshot(config: Config, package_dir: Path):
    package_config = PackageConfig.from_file(package_dir / "dfu_config.json")
    update_installed_packages(config, package_config)
    create_changed_placeholders(package_config, package_dir)
    package_config.write(package_dir / "dfu_config.json")


def update_installed_packages(config: Config, package_config: PackageConfig):
    if len(package_config.snapshots) == 0:
        raise ValueError('Did not create a successful pre/post snapshot pair')
    old_packages = get_installed_packages(config, package_config.snapshot_mapping(use_pre_id=True))
    new_packages = get_installed_packages(config, package_config.snapshot_mapping(use_pre_id=False))

    diff = diff_packages(old_packages, new_packages)
    package_config.programs_added = diff.added
    package_config.programs_removed = diff.removed


def create_changed_placeholders(package_config: PackageConfig, package_dir: Path):
    # This method has been performance optimized in several places. Take care when modifying the file for both correctness and speed
    pre_mapping = package_config.snapshot_mapping(use_pre_id=True)
    post_mapping = package_config.snapshot_mapping(use_pre_id=False)

    placeholder_dir = package_dir / 'placeholders'
    if placeholder_dir.exists():
        rmtree(placeholder_dir)

    placeholder_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    for snapper_name, pre_id in pre_mapping.items():
        post_id = post_mapping[snapper_name]
        snapper = Snapper(snapper_name)
        deltas = snapper.get_delta(pre_id, post_id)

        # Cumulatively, it's expensive to create files, so we want to filter out .gitignore files and skip writing them
        # git_check_ignore will return a list of all the paths that are ignored by git, but we need to be careful about the path
        # As far as git is concerned, the path should be placeholders/<path>, so we will set that once here
        # And then the code to actually write the file joins it with package_dir later
        for delta in deltas:
            delta.path = f"placeholders/{delta.path.lstrip('/')}"

        # Create a set of all the ignored files. Earlier attempts tried using a list and checking the last element, but the ordering wasn't exact
        ignored_paths = set(git_check_ignore(package_dir, [delta.path for delta in deltas]))
        for delta in deltas:
            if delta.path in ignored_paths:
                # Performance speedup: Don't write files that are ignored by git
                continue
            path = package_dir / delta.path
            try:
                # Performance speedup: Try calling mkdir once, to create all of the parent directories
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            except FileExistsError:
                # Calling mkdir() doesn't work in all cases, because sometimes we mistakenly create a file, instead of a directory
                # diff_packages doesn't distinguish between files and directories, so the placeholder algorithm assumes they're always files
                # Therefore, we may have previously created a parent directory as a file. So, we need to manually walk the path
                # Delete any placeholder files that are actually directories, and re-create them as directories
                # This is the slow path, so only do it if there are conflicts
                current_path = Path(path.parts[0])
                for child in path.parts[1:-1]:
                    current_path = current_path / child

                    if current_path.is_file():
                        current_path.unlink()
                        current_path.mkdir(mode=0o755)
                    elif not current_path.exists():
                        current_path.mkdir(mode=0o755)
                    elif not current_path.is_dir():
                        raise ValueError(f"Trying to create {path} failed because {current_path} is not a directory")

            path.write_text(f"PLACEHOLDER: {delta.action}\n")

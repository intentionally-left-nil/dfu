import re
import subprocess
from pathlib import Path
from shutil import copy2, rmtree
from textwrap import dedent
from typing import Literal

import click

from dfu.api import Event, Playground, Store
from dfu.api.store import Store
from dfu.helpers.normalize_snapshot_index import normalize_snapshot_index
from dfu.package.dfu_diff import DfuDiff
from dfu.revision.git import (
    DEFAULT_GITIGNORE,
    git_add,
    git_check_ignore,
    git_checkout,
    git_commit,
    git_default_branch,
    git_diff,
    git_init,
    git_ls_files,
)
from dfu.snapshots.snapper import Snapper


def begin_diff(store: Store, *, from_index: int, to_index: int):
    if store.state.diff is not None:
        raise ValueError("A diff is already in progress. Run `dfu diff --continue` to continue the diff.")

    if store.state.install is not None:
        raise ValueError("An installation is in progress. Run `dfu install --abort` to abort the installation.")

    from_index = normalize_snapshot_index(store.state.package_config, from_index)
    to_index = normalize_snapshot_index(store.state.package_config, to_index)
    diff = DfuDiff(from_index=from_index, to_index=to_index)
    store.state = store.state.update(diff=diff)
    continue_diff(store)


def abort_diff(store: Store):
    click.echo("Cleaning up...", err=True)
    _rmtree(store.state.package_dir, 'placeholders')
    _rmtree(store.state.package_dir, 'files')
    store.state = store.state.update(diff=None)
    git_checkout(store.state.package_dir, git_default_branch(store.state.package_dir), exist_ok=True)


def continue_diff(store: Store):
    if store.state.diff is None:
        raise ValueError("Cannot continue a diff if there is no diff in progress")
    if store.state.install is not None:
        raise ValueError("An installation is in progress. Run `dfu install --abort` to abort the installation.")
    if not store.state.diff.created_placeholders:
        playground = Playground(prefix="dfu_placeholders_")
        try:
            click.echo("Creating placeholder files...", err=True)
            create_changed_placeholders(store, playground)
            store.state = store.state.update(diff=store.state.diff.update(placeholder_dir=str(playground.location)))
            click.echo(
                dedent(
                    f"""\
                    Placeholder files have been created here:
                    {playground.location}
                    Run `git ls-files --others files` to see them.
                    If there are extra files, delete them.
                    Once completed, run `dfu diff --continue`."""
                ),
                err=True,
            )
            return
        except Exception:
            playground.cleanup()
            raise

    if not store.state.diff.created_base_branch:
        create_base_branch(store)
        click.echo(
            dedent(
                """\
                The files/ directory is now populated with the contents at the time of the initial `dfu snap`
                Make sure all the files here are what you wish to track. Then, commit ONLY the files/ directory to this base branch.
                After you've git committed any changes to the base branch, run `dfu diff --continue`."""
            ),
            err=True,
        )
        return

    if not store.state.diff.created_target_branch:
        create_target_branch(store)
        click.echo(
            dedent(
                """\
                The files/ directory is now populated with the contents at the time of the final `dfu snap`
                This represents the git diff for the files that were changed between the two snapshots.
                Double-check that the final git diff is correct. If it is, commit ONLY the files/ directory to this target branch.
                After you've git committed any changes to the target branch, run `dfu diff --continue`."""
            ),
            err=True,
        )
        return

    default_branch = git_default_branch(store.state.package_dir)
    click.echo(f"Checking out the {default_branch} branch", err=True)
    git_checkout(store.state.package_dir, default_branch, exist_ok=True)

    if not store.state.diff.created_patch_file:
        create_patch_file(store.state.package_dir, store.state.diff)
        store.state = store.state.update(diff=store.state.diff.update(created_patch_file=True))
        click.echo("Created the changes.patch file", err=True)

    assert store.state.diff
    if not store.state.diff.updated_installed_programs:
        click.echo("Detecting which programs were installed and removed...", err=True)
        store.dispatch(Event.TARGET_BRANCH_FINALIZED)
        click.echo("Updated the installed programs", err=True)

    click.echo("Cleaning up...", err=True)
    abort_diff(store)


def create_changed_placeholders(store: Store, playground: Playground):
    assert store.state.diff
    # This method has been performance optimized in several places. Take care when modifying the file for both correctness and speed
    pre_snapshot = store.state.package_config.snapshots[store.state.diff.from_index]
    post_snapshot = store.state.package_config.snapshots[store.state.diff.to_index]

    git_init(playground.location)
    gitignore = store.state.package_dir / '.gitignore'
    if gitignore.exists():
        copy2(gitignore, playground.location / '.gitignore')
    else:
        gitignore.write_text(DEFAULT_GITIGNORE)

    git_add(playground.location, ['.gitignore'])
    git_commit(playground.location, "Add gitignore")

    for snapper_name, pre_id in pre_snapshot.items():
        post_id = post_snapshot[snapper_name]
        snapper = Snapper(snapper_name)
        deltas = snapper.get_delta(pre_id, post_id)

        # Cumulatively, it's expensive to create files, so we want to filter out .gitignore files and skip writing them
        # git_check_ignore will return a list of all the paths that are ignored by git, but we need to be careful about the path
        # As far as git is concerned, the path should be placeholders/<path>, so we will set that once here
        # And then the code to actually write the file joins it with package_dir later
        for delta in deltas:
            delta.path = f"files/{delta.path.lstrip('/')}"

        # Create a set of all the ignored files. Earlier attempts tried using a list and checking the last element, but the ordering wasn't exact
        ignored_paths = set(git_check_ignore(store.state.package_dir, [delta.path for delta in deltas]))
        for delta in deltas:
            if delta.path in ignored_paths:
                # Performance speedup: Don't write files that are ignored by git
                continue
            path = playground.location / 'files' / delta.path
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


def copy_files(store: Store, *, snapshot_index):
    _rmtree(store.state.package_dir, 'files')
    for snapper_name, snapshot_id in store.state.package_config.snapshots[snapshot_index].items():
        snapper = Snapper(snapper_name)
        mountpoint = snapper.get_mountpoint()
        ls_dir = store.state.package_dir / 'placeholders' / _strip_placeholders(mountpoint)
        try:
            files_to_copy = [_strip_placeholders(f) for f in git_ls_files(ls_dir)]
        except FileNotFoundError:
            # The ls_dir doesn't exist, so there are no placeholders to copy
            continue
        snapshot_dir = snapper.get_snapshot_path(snapshot_id)
        for file in files_to_copy:
            sub_path = (Path('/') / file).relative_to(mountpoint)
            src = snapshot_dir / sub_path
            dest = store.state.package_dir / 'files' / file
            dest.parent.mkdir(mode=0o755, parents=True, exist_ok=True)

            if subprocess.run(['sudo', 'stat', str(src)], capture_output=True).returncode == 0:
                subprocess.run(
                    ['sudo', 'cp', '--no-dereference', '--preserve=all', str(src), str(dest)],
                    capture_output=True,
                    check=True,
                )


def create_base_branch(store: Store):
    assert store.state.diff
    branch_name = _branch_name(store.state.diff, 'base')
    click.echo(f"Creating base branch {branch_name}...", err=True)
    git_checkout(store.state.package_dir, branch_name, exist_ok=False)
    copy_files(store, snapshot_index=store.state.diff.from_index)
    if (store.state.package_dir / 'files').exists():
        git_add(store.state.package_dir, ['files'])
    store.state = store.state.update(diff=store.state.diff.update(created_base_branch=True))


def create_target_branch(store: Store):
    assert store.state.diff
    if not store.state.diff.created_base_branch:
        raise ValueError('Cannot create target branch without a base branch')
    git_checkout(store.state.package_dir, _branch_name(store.state.diff, 'base'), exist_ok=True)

    branch_name = _branch_name(store.state.diff, 'target')
    click.echo(f"Creating target branch {branch_name}...", err=True)
    git_checkout(store.state.package_dir, branch_name, exist_ok=False)
    copy_files(store, snapshot_index=store.state.diff.to_index)
    if (store.state.package_dir / 'files').exists():
        git_add(store.state.package_dir, ['files'])
    store.state = store.state.update(diff=store.state.diff.update(created_target_branch=True))


def create_patch_file(package_dir: Path, diff: DfuDiff):
    if not diff.created_base_branch or not diff.created_target_branch:
        raise ValueError('Cannot create a patch file without a base and target branch')
    patch = git_diff(package_dir, _branch_name(diff, 'base'), _branch_name(diff, 'target'))
    (package_dir / _patch_name(diff)).write_text(patch)


def _rmtree(package_dir: Path, subdir: str):
    placeholder_dir = package_dir / subdir
    if placeholder_dir.exists():
        rmtree(placeholder_dir)


def _strip_placeholders(p: Path | str) -> str:
    return re.sub(r'^placeholders/', '', str(p)).lstrip('/')


def _branch_name(diff: DfuDiff, branch_type: Literal['base', 'target']) -> str:
    return f"{diff.from_index:03}_to_{diff.to_index:03}_{branch_type}"


def _patch_name(diff: DfuDiff):
    return f"{diff.from_index:03}_to_{diff.to_index:03}.patch"

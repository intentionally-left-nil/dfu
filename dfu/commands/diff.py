import subprocess
from pathlib import Path
from shutil import copy2
from textwrap import dedent

import click

from dfu.api import Event, Playground, Store
from dfu.api.store import Store
from dfu.helpers.normalize_snapshot_index import normalize_snapshot_index
from dfu.package.dfu_diff import DfuDiff
from dfu.revision.git import (
    copy_template_gitignore,
    git_add,
    git_bundle,
    git_check_ignore,
    git_commit,
    git_diff,
    git_init,
    git_ls_files,
    git_num_commits,
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
    if store.state.diff and store.state.diff.placeholder_dir:
        Playground(location=Path(store.state.diff.placeholder_dir)).cleanup()
    if store.state.diff and store.state.diff.working_dir:
        Playground(location=Path(store.state.diff.working_dir)).cleanup()
    store.state = store.state.update(diff=None)


def continue_diff(store: Store):
    if store.state.diff is None:
        raise ValueError("Cannot continue a diff if there is no diff in progress")
    if store.state.install is not None:
        raise ValueError("An installation is in progress. Run `dfu install --abort` to abort the installation.")

    if not store.state.diff.placeholder_dir:
        placeholder_playground = Playground(prefix="dfu_placeholder_")
        _initialize_playground(store, placeholder_playground)
        store.state = store.state.update(
            diff=store.state.diff.update(placeholder_dir=str(placeholder_playground.location))
        )
        assert store.state.diff and store.state.diff.placeholder_dir

    placeholder_playground = Playground(location=Path(store.state.diff.placeholder_dir))
    if not store.state.diff.created_placeholders:
        click.echo("Creating placeholder files...", err=True)

        _create_changed_placeholders(store, placeholder_playground)
        store.state = store.state.update(diff=store.state.diff.update(created_placeholders=True))
        click.echo(
            dedent(
                """\
                Placeholder files have been created.
                Run dfu shell to inspect the contents.
                For example you could use git ls-files --others
                to see a list of all the modified files
                You can either remove files, or add them to the .gitignore
                Once completed, run dfu diff --continue."""
            ),
            err=True,
        )
        return

    if not store.state.diff.working_dir:
        playground = Playground(prefix="dfu_diff_")
        _initialize_playground(store, playground)
        store.state = store.state.update(diff=store.state.diff.update(working_dir=str(playground.location)))
        assert store.state.diff and store.state.diff.working_dir

    playground = Playground(location=Path(store.state.diff.working_dir))

    if not store.state.diff.copied_pre_files:
        _copy_files(store, snapshot_index=store.state.diff.from_index)
        git_add(playground.location, ['files'])
        store.state = store.state.update(diff=store.state.diff.update(copied_pre_files=True))
        click.echo(
            dedent(
                """\
                Initial files have been created here. Run dfu shell to inspect the changes.
                Once you're happy with the initial state, run git commit, and then dfu diff --continue"""
            ),
            err=True,
        )
        return

    if not store.state.diff.copied_post_files:
        _copy_files(store, snapshot_index=store.state.diff.to_index)
        git_add(playground.location, ['files'])
        store.state = store.state.update(diff=store.state.diff.update(copied_post_files=True))
        click.echo(
            dedent(
                """\
                Changes have been made to the diff directory. Run dfu shell to inspect the changes.
                When satisfied, run git commit, and then dfu diff --continue
                """
            ),
            err=True,
        )
        return

    if not store.state.diff.created_patch_file:
        if git_num_commits(playground.location) < 2:
            click.echo("No changes detected", err=True)
        else:
            patch_file = (
                store.state.package_dir / f"{store.state.diff.from_index:03}_to_{store.state.diff.to_index:03}.patch"
            )
            git_bundle(playground.location, patch_file.with_suffix(".pack"))
            patch_file.write_text(git_diff(playground.location, "HEAD~1", "HEAD", subdirectory="files"))
            click.echo(f"Created {patch_file.name}", err=True)
        store.state = store.state.update(diff=store.state.diff.update(created_patch_file=True))
        assert store.state.diff

    if not store.state.diff.updated_installed_programs:
        click.echo("Detecting which programs were installed and removed...", err=True)
        store.dispatch(Event.TARGET_BRANCH_FINALIZED)
        click.echo("Updated the installed programs", err=True)

    abort_diff(store)


def _create_changed_placeholders(store: Store, playground: Playground):
    assert store.state.diff
    # This method has been performance optimized in several places. Take care when modifying the file for both correctness and speed
    pre_snapshot = store.state.package_config.snapshots[store.state.diff.from_index]
    post_snapshot = store.state.package_config.snapshots[store.state.diff.to_index]

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
            path = playground.location / delta.path
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


def _copy_files(store: Store, *, snapshot_index: int):
    assert store.state.diff and store.state.diff.working_dir and store.state.diff.placeholder_dir
    placeholder_playground = Playground(location=Path(store.state.diff.placeholder_dir))
    working_playground = Playground(location=Path(store.state.diff.working_dir))
    for snapper_name, snapshot_id in store.state.package_config.snapshots[snapshot_index].items():
        snapper = Snapper(snapper_name)
        mountpoint = snapper.get_mountpoint()

        try:
            files_to_copy = [
                Path(p).relative_to('files')
                for p in git_ls_files(placeholder_playground.location / 'files' / mountpoint.relative_to(Path('/')))
            ]

        except FileNotFoundError:
            # The ls_dir doesn't exist, so there are no placeholders to copy
            continue
        snapshot_dir = snapper.get_snapshot_path(snapshot_id)
        for file in files_to_copy:
            sub_path = (Path('/') / file).relative_to(mountpoint)
            src = snapshot_dir / sub_path
            dest = working_playground.location / 'files' / file

            if subprocess.run(['sudo', 'stat', str(src)], capture_output=True).returncode == 0:
                dest.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                subprocess.run(
                    ['sudo', 'cp', '--no-dereference', '--preserve=all', str(src), str(dest)],
                    capture_output=True,
                    check=True,
                )


def _initialize_playground(store: Store, playground: Playground):
    git_init(playground.location)
    package_gitignore = store.state.package_dir / '.gitignore'
    (playground.location / "files").mkdir(mode=0o755, parents=True, exist_ok=True)
    if package_gitignore.exists():
        copy2(package_gitignore, playground.location / '.gitignore')
    else:
        copy_template_gitignore(playground.location)

    git_add(playground.location, ['.gitignore'])
    git_commit(playground.location, "Add gitignore")

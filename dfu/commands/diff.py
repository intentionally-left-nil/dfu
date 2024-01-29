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
    git_commit,
    git_diff,
    git_init,
    git_num_commits,
)
from dfu.snapshots.changes import files_modified
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
    if store.state.diff and store.state.diff.working_dir:
        Playground(location=Path(store.state.diff.working_dir)).cleanup()
    store.state = store.state.update(diff=None)


def continue_diff(store: Store):
    if store.state.diff is None:
        raise ValueError("Cannot continue a diff if there is no diff in progress")
    if store.state.install is not None:
        raise ValueError("An installation is in progress. Run `dfu install --abort` to abort the installation.")

    if not store.state.diff.working_dir:
        playground = Playground(prefix="dfu_diff_")
        _initialize_playground(store, playground)
        store.state = store.state.update(diff=store.state.diff.update(working_dir=str(playground.location)))
        assert store.state.diff and store.state.diff.working_dir

    playground = Playground(location=Path(store.state.diff.working_dir))

    sources: dict[str, list[str]] | None = None

    if not store.state.diff.copied_pre_files:
        sources = files_modified(
            store, from_index=store.state.diff.from_index, to_index=store.state.diff.to_index, only_ignored=False
        )
        _copy_files(store, snapshot_index=store.state.diff.from_index, sources=sources)
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
        if sources is None:
            sources = files_modified(
                store, from_index=store.state.diff.from_index, to_index=store.state.diff.to_index, only_ignored=False
            )

        _copy_files(store, snapshot_index=store.state.diff.to_index, sources=sources)
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


def _copy_files(store: Store, *, snapshot_index: int, sources: dict[str, list[str]]):
    assert store.state.diff and store.state.diff.working_dir
    working_playground = Playground(location=Path(store.state.diff.working_dir))
    for snapper_name, files in sources.items():
        snapshot_id = store.state.package_config.snapshots[snapshot_index][snapper_name]
        snapper = Snapper(snapper_name)
        mountpoint = snapper.get_mountpoint()
        snapshot_dir = snapper.get_snapshot_path(snapshot_id)
        for file in files:
            sub_path = Path(file).relative_to(mountpoint)
            src = snapshot_dir / sub_path
            dest = working_playground.location / 'files' / file.removeprefix('/')
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

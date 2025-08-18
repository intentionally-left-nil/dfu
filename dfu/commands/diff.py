import os
import pwd
import subprocess
from pathlib import Path
from shutil import copy2

import click

from dfu.api import Playground, Store, UpdateInstalledDependenciesEvent
from dfu.helpers.normalize_snapshot_index import normalize_snapshot_index
from dfu.helpers.subshell import subshell
from dfu.revision.git import (
    copy_template_gitignore,
    git_add,
    git_are_files_staged,
    git_bundle,
    git_commit,
    git_diff,
    git_init,
    git_num_commits,
)
from dfu.snapshots.changes import files_modified, get_permissions
from dfu.snapshots.snapper import Snapper, SnapperName


def generate_diff(store: Store, *, from_index: int, to_index: int, interactive: bool) -> None:
    from_index = normalize_snapshot_index(store.state.package_config, from_index)
    to_index = normalize_snapshot_index(store.state.package_config, to_index)
    if from_index > to_index:
        raise ValueError(f"from_index {from_index} is greater than to_index {to_index}")

    with Playground.temporary(prefix="dfu_diff_") as playground:
        _initialize_playground(store, playground)
        sources = files_modified(store, from_index=from_index, to_index=to_index, only_ignored=False)
        _copy_files(store, playground=playground, snapshot_index=from_index, sources=sources)
        _copy_permissions(
            store,
            playground=playground,
            files_modified=sources,
            snapshot_index=from_index,
        )
        _auto_commit(playground.location, "Initial files")
        _copy_files(store, playground=playground, snapshot_index=to_index, sources=sources)
        _copy_permissions(
            store,
            playground=playground,
            files_modified=sources,
            snapshot_index=to_index,
        )
        if interactive:
            click.echo("Launching a subshell with the changes. Type exit 0 to continue, or exit 1 to abort")
            if subshell(playground.location).returncode != 0:
                click.echo("Aborting...", err=True)
                return
        _auto_commit(playground.location, "Modified files")
        _create_patch(store, playground=playground, from_index=from_index, to_index=to_index)
        click.echo("Detecting which programs were installed and removed...", err=True)
        store.dispatch(UpdateInstalledDependenciesEvent(from_index=from_index, to_index=to_index))
        click.echo("Updated the installed programs", err=True)


def _copy_files(
    store: Store, *, playground: Playground, snapshot_index: int, sources: dict[SnapperName, list[str]]
) -> None:
    current_user = pwd.getpwuid(os.getuid()).pw_name
    for snapper_name, files in sources.items():
        snapshot_id = store.state.package_config.snapshots[snapshot_index][snapper_name]
        snapper = Snapper(snapper_name)
        mountpoint = snapper.get_mountpoint()
        snapshot_dir = snapper.get_snapshot_path(snapshot_id)
        for file in files:
            sub_path = Path(file).relative_to(mountpoint)
            src = snapshot_dir / sub_path
            dest = playground.location / 'files' / file.removeprefix('/')
            if subprocess.run(['sudo', 'stat', str(src)], capture_output=True).returncode == 0:
                dest.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                subprocess.run(
                    ['sudo', 'install', '-m', '755', '-o', current_user, '-g', current_user, str(src), str(dest)],
                    capture_output=True,
                    check=True,
                )


def _copy_permissions(
    store: Store,
    *,
    playground: Playground,
    files_modified: dict[SnapperName, list[str]],
    snapshot_index: int,
) -> None:
    permissions = get_permissions(store, files_modified=files_modified, snapshot_index=snapshot_index)
    dest = playground.location / "acl.txt"
    dest.write_text("\n".join(permissions))


def _initialize_playground(store: Store, playground: Playground) -> None:
    git_init(playground.location)
    package_gitignore = store.state.package_dir / '.gitignore'
    (playground.location / "files").mkdir(mode=0o755, parents=True, exist_ok=True)
    if package_gitignore.exists():
        copy2(package_gitignore, playground.location / '.gitignore')
    else:
        copy_template_gitignore(playground.location)

    git_add(playground.location, ['.gitignore'])
    git_commit(playground.location, "Add gitignore")


def _auto_commit(working_dir: Path, message: str) -> None:
    git_add(working_dir, ['files', 'acl.txt'])
    if git_are_files_staged(working_dir):
        git_commit(working_dir, message)


def _create_patch(store: Store, playground: Playground, from_index: int, to_index: int) -> None:
    if git_num_commits(playground.location) >= 2:
        patch_file = store.state.package_dir / f"{from_index:03}_to_{to_index:03}.patch"
        git_bundle(playground.location, patch_file.with_suffix(".pack"))
        patch_file.write_text(git_diff(playground.location, "HEAD~1", "HEAD"))
        click.echo(f"Created {patch_file.name}", err=True)

import os
import re
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent
from typing import NamedTuple

import click

from dfu.api import Event, Playground, Store
from dfu.helpers.subshell import subshell
from dfu.revision.git import git_add, git_are_files_staged, git_commit, git_init

PatchStep = NamedTuple("PatchStep", [("patch", Path), ("interactive", bool)])


def apply_package(store: Store, *, reverse: bool, interactive: bool, confirm: bool, dry_run: bool):
    if not reverse:
        store.dispatch(Event.INSTALL_DEPENDENCIES, confirm=confirm, dry_run=dry_run)

    with Playground.temporary(prefix="dfu_apply_") as playground:
        git_init(playground.location)
        _copy_base_files(store, playground=playground)
        _auto_commit(playground, "Initial files")
        _apply_patches(store, playground=playground, reverse=reverse, interactive=interactive)
        if confirm:
            _confirm_changes(playground)

        if dry_run:
            click.echo("Dry run: Skipping copying the files to the filesystem", err=True)
        else:
            playground.copy_files_to_filesystem()

    if reverse:
        store.dispatch(Event.UNINSTALL_DEPENDENCIES, confirm=confirm, dry_run=dry_run)


def _copy_base_files(store: Store, *, playground: Playground):
    patch_files = store.state.package_dir.glob('*.patch')
    files_to_copy: set[Path] = set()
    for patch in patch_files:
        files_to_copy.update(playground.list_files_in_patch(patch))
    playground.copy_files_from_filesystem(files_to_copy)


def _apply_patches(store: Store, *, playground: Playground, reverse: bool, interactive: bool):
    patches = list(sorted(store.state.package_dir.glob('*.patch')))
    if reverse:
        patches = list(reversed(patches))
        pass
    if interactive:
        steps = _patch_order_interactive(patches, reverse=reverse)
    else:
        steps = [PatchStep(patch=patch, interactive=False) for patch in patches]

    for step in steps:
        merged_cleanly = playground.apply_patch(step.patch, reverse=reverse)
        if not merged_cleanly:
            click.echo(
                dedent(
                    """\
                    There was a merge conflict applying the patches. A subshell has been created for manual intervention.
                    Make the correct changes, and then exit the subshell to continue."""
                )
            )
            subshell(playground.location).check_returncode()
        elif step.interactive:
            _confirm_changes(playground)
        _auto_commit(playground, f"Patch {step.patch.name}")


def _patch_order_interactive(patches: list[Path], *, reverse: bool) -> list[PatchStep]:
    with NamedTemporaryFile(prefix="dfu_apply_", suffix=".txt", mode="w+") as patch_order_file:
        template = f"""\
# {"Revert patches" if reverse else "Apply patches"}
# To make changes, you can reorder the patches, or delete any patches you don't want to apply.
# Commands:
# p, pick = use commit
# e, edit = use commit, but stop for amending
# d, drop = remove commit
{ "\n".join([str(p) for p in patches]) }
"""
        patch_order_file.write(template)
        patch_order_file.flush()
        editor = os.environ.get('EDITOR', 'vim')
        subprocess.run([editor, patch_order_file.name], check=True)
        patch_order_file.seek(0)
        lines = patch_order_file.read().splitlines()
    lines = [l for l in lines if not l.startswith('#')]
    lines = [l for l in lines if l.strip()]

    steps: list[PatchStep] = []

    line_regex = re.compile(r"^(?P<command>[ped])\s+(?P<patch>.*)$")

    for line in lines:
        if match := line_regex.match(line):
            command = match.group('command')
            patch = Path(match.group('patch'))
            if command == 'p':
                steps.append(PatchStep(patch=patch, interactive=False))
            elif command == 'e':
                steps.append(PatchStep(patch=patch, interactive=True))
            elif command == 'd':
                pass
        else:
            steps.append(PatchStep(patch=Path(line), interactive=False))
    return steps


def _confirm_changes(playground: Playground):
    while True:
        response: str = click.prompt(
            "[I]nspect, [C]ontinue, [A]bort",
            type=click.Choice(['i', 'inspect', 'c', 'continue', 'a', 'abort'], case_sensitive=False),
            show_choices=False,
        )
        match response.lower():
            case 'i' | 'inspect':
                subshell(playground.location)
            case 'c' | 'continue':
                break
            case 'a' | 'abort':
                raise ValueError("Aborting")
            case _:
                raise ValueError("Unexpected choice")


def _auto_commit(playground: Playground, message: str):
    git_add(playground.location, ['.'])
    if git_are_files_staged(playground.location):
        git_commit(playground.location, message)

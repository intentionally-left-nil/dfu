import subprocess
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from dfu.api.playground import Playground
from dfu.revision.git import (
    git_add,
    git_checkout,
    git_commit,
    git_default_branch,
    git_diff,
)


@pytest.fixture
def playground() -> Generator[Playground, None, None]:
    playground = Playground(prefix="unit_test")
    yield playground
    playground.cleanup()


@pytest.fixture
def mock_install():
    original_subprocess_run = subprocess.run

    def side_effect(args, **kwargs):
        assert args[0] == "sudo"
        return original_subprocess_run(args[1:], **kwargs)

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = side_effect
        yield mock_run


def test_list_files_in_patch_missing_file(playground: Playground):
    with pytest.raises(FileNotFoundError):
        playground.list_files_in_patch(playground.location / "missing.patch")


def test_list_files_empty_patch(playground: Playground):
    patch = playground.location / "empty.patch"
    patch.write_text("")
    assert playground.list_files_in_patch(patch) == set()


def test_list_files_new_file(tmp_path: Path, playground: Playground, setup_git):
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'new_branch')
    (tmp_path / 'files' / 'nested').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'files' / 'nested' / 'nested.txt').write_text('hello\nnested')
    (tmp_path / 'files' / 'file.txt').write_text('hello\nworld')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Created files')
    diff = git_diff(tmp_path, git_default_branch(tmp_path), 'new_branch')

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    assert playground.list_files_in_patch(patch) == {Path('/nested/nested.txt'), Path('/file.txt')}


def test_list_files_modified_file(tmp_path: Path, playground: Playground, setup_git):
    test_file = tmp_path / 'files' / 'file.txt'
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text('hello\nworld')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'new_branch')
    test_file.write_text('hello\nworld\nnew line')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Modified file')
    diff = git_diff(tmp_path, git_default_branch(tmp_path), 'new_branch')

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    assert playground.list_files_in_patch(patch) == {Path('/file.txt')}


def test_list_files_delete_file(tmp_path: Path, playground: Playground, setup_git):
    test_file = tmp_path / 'files' / 'file.txt'
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text('hello\nworld')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'new_branch')
    test_file.unlink()
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Deleted file')
    diff = git_diff(tmp_path, git_default_branch(tmp_path), 'new_branch')

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    assert playground.list_files_in_patch(patch) == {Path('/file.txt')}


def test_list_files_unknown_file(tmp_path: Path, playground: Playground, setup_git):
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'new_branch')
    (tmp_path / 'not_files' / 'nested').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'not_files' / 'nested' / 'nested.txt').write_text('hello\nnested')
    (tmp_path / 'not_files' / 'file.txt').write_text('hello\nworld')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Created files')
    diff = git_diff(tmp_path, git_default_branch(tmp_path), 'new_branch')

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    with pytest.raises(ValueError):
        playground.list_files_in_patch(patch)


def test_list_files_create_symlink(tmp_path: Path, playground: Playground, setup_git):
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'new_branch')
    (tmp_path / 'files' / 'nested').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'files' / 'nested' / 'file.txt').write_text('hello\nworld')
    (tmp_path / 'files' / 'link.txt').symlink_to('./nested/file.txt')
    (tmp_path / 'files' / 'link_directory').symlink_to('./nested')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Created files')
    diff = git_diff(tmp_path, git_default_branch(tmp_path), 'new_branch')

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    assert playground.list_files_in_patch(patch) == {
        Path('/nested/file.txt'),
        Path('/link.txt'),
        Path('/link_directory'),
    }


def test_list_files_multiple_actions(tmp_path: Path, playground: Playground, setup_git):
    (tmp_path / '.gitignore').touch()
    (tmp_path / 'files' / 'nested').mkdir(parents=True, exist_ok=True)
    deleted_file = tmp_path / 'files' / 'deleted.txt'
    deleted_file.write_text('delete me')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'new_branch')
    (tmp_path / 'files' / 'nested' / 'nested.txt').write_text('hello\nnested')
    (tmp_path / 'files' / 'file.txt').write_text('hello\nworld')
    (tmp_path / 'files' / 'file.txt').write_text('hello\nworld\nnew line')
    (tmp_path / 'files' / 'nested' / 'nested.txt').write_text('hello\nnested\nnew line')
    (tmp_path / 'files' / 'nested' / 'new.txt').write_text('hello\nnew')
    (tmp_path / 'files' / 'new.txt').write_text('hello\nnew')
    (tmp_path / 'files' / 'link.txt').symlink_to('./nested/nested.txt')
    (tmp_path / 'files' / 'link_directory').symlink_to('./nested')
    deleted_file.unlink()
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Modified files')
    diff = git_diff(tmp_path, git_default_branch(tmp_path), 'new_branch')

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    assert playground.list_files_in_patch(patch) == {
        Path('/nested/nested.txt'),
        Path('/nested/new.txt'),
        Path('/file.txt'),
        Path('/new.txt'),
        Path('/deleted.txt'),
        Path('/link.txt'),
        Path('/link_directory'),
    }


def test_copy_files_from_filesystem_no_files(playground: Playground):
    playground.copy_files_from_filesystem([])
    assert not (playground.location / 'files').exists()


def test_copy_files_from_filesystem_absolute_file(tmp_path: Path, playground: Playground):
    file = tmp_path / 'file.txt'
    file.write_text('hello\nworld')
    file.chmod(0o777)
    playground.copy_files_from_filesystem([file])
    expected = playground.location / 'files' / Path(*tmp_path.parts[1:]) / 'file.txt'
    assert expected.read_text() == 'hello\nworld'
    assert (expected.stat().st_mode & 0o777) == 0o777


def test_copy_files_from_filesystem_relative_file(tmp_path: Path, playground: Playground):
    file = tmp_path / 'file.txt'
    file.write_text('hello\nworld')
    file.chmod(0o777)

    cwd = Path(".").resolve()
    num_parents = len(cwd.parts[1:])

    root_relative_to_cwd = Path("../" * num_parents)
    assert root_relative_to_cwd.resolve() == Path("/").resolve()
    relative_path = root_relative_to_cwd / Path(*file.parts[1:])
    assert relative_path.resolve() == file.resolve()

    playground.copy_files_from_filesystem([relative_path])
    expected = playground.location / 'files' / Path(*tmp_path.parts[1:]) / 'file.txt'
    assert expected.read_text() == 'hello\nworld'
    assert (expected.stat().st_mode & 0o777) == 0o777


def test_copy_files_from_filesystem_skip_directories(tmp_path: Path, playground: Playground):
    file = tmp_path / 'file.txt'
    file.write_text('hello\nworld')
    file.chmod(0o777)
    playground.copy_files_from_filesystem([file, file.parent])
    expected = playground.location / 'files' / Path(*tmp_path.parts[1:]) / 'file.txt'
    assert expected.read_text() == 'hello\nworld'
    assert (expected.stat().st_mode & 0o777) == 0o777


@patch('subprocess.run')
def test_copy_protected_file(mock_run: MagicMock, tmp_path: Path, playground: Playground):
    file = tmp_path / 'file.txt'
    file.write_text('hello\nworld')
    file.chmod(0o000)
    playground.copy_files_from_filesystem([file, file.parent])
    mock_run.assert_called_once_with(
        [
            "sudo",
            "cp",
            "-p",
            "-P",
            file.resolve(),
            Path(playground.location / 'files' / Path(*tmp_path.parts[1:]) / 'file.txt').resolve(),
        ],
        check=True,
        capture_output=True,
    )
    assert mock_run.call_count == 1


def test_copy_files_to_filesystem_no_files(tmp_path: Path, playground: Playground, mock_install):
    assert not (playground.location / 'files').exists()
    playground.copy_files_to_filesystem(dest=tmp_path)
    assert [p for p in tmp_path.glob('**/*')] == []


def test_copy_files_to_filesystem_only_directories(tmp_path: Path, playground, mock_install):
    (playground.location / 'files' / 'many' / 'nested' / 'dirs').mkdir(parents=True, exist_ok=True)
    playground.copy_files_to_filesystem(dest=tmp_path)
    assert [p for p in tmp_path.glob('**/*')] == []


def test_copy_files_to_filesystem_one_file(tmp_path: Path, playground: Playground, mock_install):
    file = playground.location / 'files' / 'file.txt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('file')
    existing = tmp_path / 'existing.txt'
    existing.write_text('existing')
    playground.copy_files_to_filesystem(dest=tmp_path)
    assert {p for p in tmp_path.glob('**/*')} == {
        Path(tmp_path / 'file.txt').resolve(),
        Path(tmp_path / 'existing.txt').resolve(),
    }
    assert (tmp_path / 'file.txt').read_text() == 'file'
    assert existing.read_text() == 'existing'


def test_copy_files_to_filesystem_creates_directories(tmp_path: Path, playground: Playground, mock_install):
    # Create the test file
    file = playground.location / 'files' / 'etc' / 'nested' / 'file.txt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('file')
    file.chmod(0o777)

    # Set up the filesystem to have some existing files, but not nested
    (tmp_path / 'etc' / 'other').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'etc' / 'etc.txt').write_text('etc')
    (tmp_path / 'etc' / 'other' / 'other.txt').write_text('other')

    playground.copy_files_to_filesystem(dest=tmp_path)
    assert [p for p in tmp_path.glob('**/*') if p.is_file()] == [
        Path(tmp_path / 'etc' / 'etc.txt').resolve(),
        Path(tmp_path / 'etc' / 'other' / 'other.txt').resolve(),
        Path(tmp_path / 'etc' / 'nested' / 'file.txt').resolve(),
    ]

    actual = tmp_path / 'etc' / 'nested' / 'file.txt'
    assert actual.stat().st_mode & 0o777 == 0o777
    assert actual.read_text() == 'file'


def test_overwrites_existing_file(tmp_path: Path, playground: Playground, mock_install):
    file = playground.location / 'files' / 'etc' / 'nested' / 'file.txt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('file')
    file.chmod(0o777)

    existing = tmp_path / 'etc' / 'nested' / 'file.txt'
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text('existing')
    existing.chmod(0o644)
    assert (existing.stat().st_mode & 0o777) == 0o644

    playground.copy_files_to_filesystem(dest=tmp_path)
    assert [p for p in tmp_path.glob('**/*') if p.is_file()] == [
        Path(tmp_path / 'etc' / 'nested' / 'file.txt').resolve(),
    ]

    assert existing.stat().st_mode & 0o777 == 0o777
    assert existing.read_text() == 'file'
